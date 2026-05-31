#!/usr/bin/env python3
"""
pubmed_search.py — PubMed search, fetch, cache.

Auto-detects best execution tier (biopython > requests > urllib) and degrades
gracefully. Always caches abstracts under ~/.cache/pubmed-research/abstracts/
so verification (L3) doesn't re-hit NCBI.

Subcommands:
    search  <query> [--max N] [--output FILE] [--format json|md|bibtex|csv]
    fetch   <pmid1> <pmid2> ... [--output FILE] [--format ...]
    cache   --stats | --show PMID | --clear

Never prints, logs, or echoes the API key.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

# ---------- Configuration ----------

ENV_FILE = Path.home() / ".config" / "pubmed-research" / ".env"
CACHE_DIR = Path.home() / ".cache" / "pubmed-research" / "abstracts"
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "pubmed-research-skill"

# ---------- .env loader (does not pollute parent shell) ----------

def load_env() -> dict[str, str]:
    """Load .env into a dict. Returns empty dict if file is missing."""
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


# ---------- HTTP layer with tier detection ----------

def _detect_tier() -> str:
    """Return 'requests' if available, else 'urllib'."""
    try:
        import requests  # noqa: F401
        return "requests"
    except ImportError:
        return "urllib"


def http_get(url: str, params: dict[str, str], timeout: int = 30) -> str:
    """GET request that works with either requests or urllib stdlib."""
    tier = _detect_tier()
    if tier == "requests":
        import requests
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.text
    else:
        import urllib.request
        qs = urllib.parse.urlencode(params)
        full_url = f"{url}?{qs}"
        req = urllib.request.Request(full_url, headers={"User-Agent": TOOL_NAME})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")


# ---------- Rate limiter ----------

class RateLimiter:
    """Minimal token-bucket. Default 3 req/sec; 10 if API key present."""
    def __init__(self, per_second: int):
        self.interval = 1.0 / max(per_second, 1)
        self.last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delta = now - self.last
        if delta < self.interval:
            time.sleep(self.interval - delta)
        self.last = time.monotonic()


# ---------- E-utilities wrappers ----------

def common_params(env: dict[str, str]) -> dict[str, str]:
    p: dict[str, str] = {"tool": TOOL_NAME}
    api_key = env.get("NCBI_API_KEY") or os.getenv("NCBI_API_KEY")
    email = env.get("NCBI_EMAIL") or os.getenv("NCBI_EMAIL")
    if api_key:
        p["api_key"] = api_key
    if email:
        p["email"] = email
    return p


def esearch(query: str, retmax: int, env: dict[str, str], limiter: RateLimiter) -> list[str]:
    """Run esearch.fcgi → return list of PMID strings."""
    limiter.wait()
    params = common_params(env)
    params.update({
        "db": "pubmed",
        "term": query,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
    })
    text = http_get(f"{BASE_URL}/esearch.fcgi", params)
    data = json.loads(text)
    return data.get("esearchresult", {}).get("idlist", [])


def efetch_xml(pmids: list[str], env: dict[str, str], limiter: RateLimiter) -> str:
    """Run efetch.fcgi for a batch of PMIDs → raw PubMed XML."""
    limiter.wait()
    params = common_params(env)
    params.update({
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
    })
    return http_get(f"{BASE_URL}/efetch.fcgi", params)


# ---------- XML → structured record ----------

def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    parts: list[str] = []
    for t in el.itertext():
        parts.append(t)
    return " ".join("".join(parts).split())


def parse_pubmed_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse PubmedArticleSet XML into list of canonical records."""
    records: list[dict[str, Any]] = []
    root = ET.fromstring(xml_text)
    for article in root.findall(".//PubmedArticle"):
        med = article.find("MedlineCitation")
        if med is None:
            continue

        pmid_el = med.find("PMID")
        pmid = _text(pmid_el)

        art = med.find("Article")
        title = _text(art.find("ArticleTitle")) if art is not None else ""

        # Abstract may have multiple labeled sections
        abstract_parts: list[str] = []
        if art is not None:
            for ab in art.findall("Abstract/AbstractText"):
                label = ab.get("Label")
                txt = _text(ab)
                if label:
                    abstract_parts.append(f"{label}: {txt}")
                else:
                    abstract_parts.append(txt)
        abstract = " ".join(abstract_parts).strip()

        # Authors
        authors: list[str] = []
        if art is not None:
            for au in art.findall("AuthorList/Author"):
                last = _text(au.find("LastName"))
                init = _text(au.find("Initials"))
                if last:
                    authors.append(f"{last} {init}".strip())
                else:
                    coll = _text(au.find("CollectiveName"))
                    if coll:
                        authors.append(coll)

        # Journal
        journal = ""
        year = ""
        if art is not None:
            j = art.find("Journal")
            if j is not None:
                journal = _text(j.find("Title")) or _text(j.find("ISOAbbreviation"))
                y = j.find(".//PubDate/Year")
                if y is not None and y.text:
                    year = y.text.strip()
                else:
                    # Sometimes year hides in MedlineDate
                    md = j.find(".//PubDate/MedlineDate")
                    if md is not None and md.text:
                        m = re.search(r"\b(19|20)\d{2}\b", md.text)
                        if m:
                            year = m.group(0)

        # DOI and other IDs
        doi = ""
        pmc = ""
        for aid in article.findall(".//ArticleIdList/ArticleId"):
            id_type = aid.get("IdType", "")
            val = (aid.text or "").strip()
            if id_type == "doi":
                doi = val
            elif id_type == "pmc":
                pmc = val

        # MeSH terms
        mesh_terms: list[str] = []
        for mh in med.findall("MeshHeadingList/MeshHeading/DescriptorName"):
            if mh.text:
                mesh_terms.append(mh.text.strip())

        # Publication types
        pub_types: list[str] = []
        if art is not None:
            for pt in art.findall("PublicationTypeList/PublicationType"):
                if pt.text:
                    pub_types.append(pt.text.strip())

        records.append({
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "first_author": authors[0] if authors else "",
            "journal": journal,
            "year": year,
            "doi": doi,
            "pmc": pmc,
            "abstract": abstract,
            "mesh_terms": mesh_terms,
            "pub_types": pub_types,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "pubmed",
        })
    return records


# ---------- Cache layer ----------

def cache_path(pmid: str) -> Path:
    return CACHE_DIR / f"{pmid}.json"


def cache_read(pmid: str) -> dict[str, Any] | None:
    p = cache_path(pmid)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def cache_write(record: dict[str, Any]) -> None:
    pmid = record.get("pmid")
    if not pmid:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path(pmid).write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_with_cache(
    pmids: list[str],
    env: dict[str, str],
    limiter: RateLimiter,
    batch_size: int = 50,
    force_refresh: bool = False,
) -> list[dict[str, Any]]:
    """Return records for given PMIDs, using cache when possible."""
    results: list[dict[str, Any]] = []
    to_fetch: list[str] = []

    for pmid in pmids:
        if not force_refresh:
            cached = cache_read(pmid)
            if cached:
                cached["_from_cache"] = True
                results.append(cached)
                continue
        to_fetch.append(pmid)

    # Batch fetch the rest
    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i:i + batch_size]
        xml = efetch_xml(batch, env, limiter)
        recs = parse_pubmed_xml(xml)
        for r in recs:
            cache_write(r)
            r["_from_cache"] = False
            results.append(r)

    # Reorder to match input
    order = {p: i for i, p in enumerate(pmids)}
    results.sort(key=lambda r: order.get(r.get("pmid", ""), 1e9))
    return results


# ---------- Output formatters ----------

def fmt_json(records: list[dict[str, Any]]) -> str:
    return json.dumps(records, ensure_ascii=False, indent=2)


def fmt_md(records: list[dict[str, Any]]) -> str:
    if not records:
        return "_No results._\n"
    out = ["| PMID | Year | First Author | Title | Journal | DOI |",
           "|---|---|---|---|---|---|"]
    for r in records:
        title = (r.get("title", "") or "").replace("|", "\\|")
        out.append(
            f"| [{r.get('pmid','')}](https://pubmed.ncbi.nlm.nih.gov/{r.get('pmid','')}/) "
            f"| {r.get('year','')} "
            f"| {r.get('first_author','')} "
            f"| {title} "
            f"| {r.get('journal','')} "
            f"| {r.get('doi','')} |"
        )
    return "\n".join(out) + "\n"


def fmt_bibtex(records: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for r in records:
        pmid = r.get("pmid", "")
        first = r.get("first_author", "").split()[0].lower() if r.get("first_author") else "anon"
        year = r.get("year", "") or "nd"
        citekey = f"{first}{year}_pmid{pmid}"

        authors = " and ".join(r.get("authors", [])) or "Unknown"
        title = r.get("title", "").replace("{", "\\{").replace("}", "\\}")

        fields = [
            f"  author    = {{{authors}}}",
            f"  title     = {{{title}}}",
            f"  journal   = {{{r.get('journal','')}}}",
            f"  year      = {{{year}}}",
            f"  pmid      = {{{pmid}}}",
        ]
        if r.get("doi"):
            fields.append(f"  doi       = {{{r['doi']}}}")
        # Provenance fields — what makes this our skill's BibTeX, not someone else's
        fields.append(f"  verified  = {{true}}")
        fields.append(f"  verified_by = {{pubmed-eutils}}")
        fields.append(f"  verified_on = {{{r.get('fetched_at','')[:10]}}}")

        chunks.append("@article{" + citekey + ",\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(chunks) + "\n"


def fmt_csv(records: list[dict[str, Any]]) -> str:
    import io
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["pmid", "year", "first_author", "title", "journal", "doi", "pub_types"])
    for r in records:
        writer.writerow([
            r.get("pmid", ""),
            r.get("year", ""),
            r.get("first_author", ""),
            r.get("title", ""),
            r.get("journal", ""),
            r.get("doi", ""),
            "; ".join(r.get("pub_types", [])),
        ])
    return buf.getvalue()


def fmt_text(records: list[dict[str, Any]]) -> str:
    out: list[str] = []
    for r in records:
        out.append(f"PMID: {r.get('pmid','')}")
        out.append(f"Title: {r.get('title','')}")
        out.append(f"Authors: {', '.join(r.get('authors', []))}")
        out.append(f"Journal: {r.get('journal','')} ({r.get('year','')})")
        if r.get("doi"):
            out.append(f"DOI: {r['doi']}")
        if r.get("abstract"):
            out.append(f"Abstract: {r['abstract']}")
        out.append("")
    return "\n".join(out)


FORMATTERS = {
    "json": fmt_json,
    "md": fmt_md,
    "bibtex": fmt_bibtex,
    "csv": fmt_csv,
    "text": fmt_text,
}


# ---------- Commands ----------

def cmd_search(args: argparse.Namespace) -> int:
    env = load_env()
    rate = 10 if (env.get("NCBI_API_KEY") or os.getenv("NCBI_API_KEY")) else 3
    limiter = RateLimiter(rate)

    print(f"[search] query: {args.query}", file=sys.stderr)
    pmids = esearch(args.query, args.max, env, limiter)
    print(f"[search] {len(pmids)} PMIDs returned", file=sys.stderr)
    if not pmids:
        out_text = FORMATTERS[args.format]([])
        _write(args.output, out_text)
        return 0

    records = fetch_with_cache(pmids, env, limiter, force_refresh=args.refresh)
    cached_count = sum(1 for r in records if r.get("_from_cache"))
    print(f"[search] {cached_count} from cache, {len(records) - cached_count} freshly fetched",
          file=sys.stderr)

    out_text = FORMATTERS[args.format](records)
    _write(args.output, out_text)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    env = load_env()
    rate = 10 if (env.get("NCBI_API_KEY") or os.getenv("NCBI_API_KEY")) else 3
    limiter = RateLimiter(rate)

    pmids = [p.strip() for p in args.pmids if p.strip()]
    records = fetch_with_cache(pmids, env, limiter, force_refresh=args.refresh)

    # Identify any PMIDs that returned no record — potential fabrications
    found = {r["pmid"] for r in records}
    missing = [p for p in pmids if p not in found]
    if missing:
        print(f"[fetch] WARNING: {len(missing)} PMID(s) returned no record: {missing}",
              file=sys.stderr)

    out_text = FORMATTERS[args.format](records)
    _write(args.output, out_text)
    return 1 if missing else 0


def cmd_cache(args: argparse.Namespace) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if args.stats:
        files = list(CACHE_DIR.glob("*.json"))
        total_bytes = sum(f.stat().st_size for f in files)
        if files:
            mtimes = [f.stat().st_mtime for f in files]
            oldest = datetime.fromtimestamp(min(mtimes)).isoformat()
            newest = datetime.fromtimestamp(max(mtimes)).isoformat()
        else:
            oldest = newest = None
        stats = {
            "count": len(files),
            "total_bytes": total_bytes,
            "total_kb": round(total_bytes / 1024, 1),
            "oldest": oldest,
            "newest": newest,
            "cache_dir": str(CACHE_DIR),
        }
        print(json.dumps(stats, indent=2))
        return 0

    if args.show:
        rec = cache_read(args.show)
        if rec is None:
            print(f"PMID {args.show} not in cache", file=sys.stderr)
            return 1
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if args.clear:
        files = list(CACHE_DIR.glob("*.json"))
        if not files:
            print("Cache already empty.")
            return 0
        if not args.yes:
            ans = input(f"Delete {len(files)} cached abstracts? [y/N] ")
            if ans.strip().lower() not in ("y", "yes"):
                print("Aborted.")
                return 0
        for f in files:
            f.unlink()
        print(f"Deleted {len(files)} files.")
        return 0

    print("Specify one of: --stats / --show PMID / --clear", file=sys.stderr)
    return 2


# ---------- Helpers ----------

def _write(output: str | None, text: str) -> None:
    if output and output != "-":
        Path(output).write_text(text, encoding="utf-8")
        print(f"[write] {output} ({len(text)} chars)", file=sys.stderr)
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pubmed_search.py",
        description="PubMed search, fetch, and local cache.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="Run esearch then efetch")
    p_search.add_argument("query", help="PubMed query string")
    p_search.add_argument("--max", type=int, default=50, help="Max PMIDs (default 50)")
    p_search.add_argument("--output", "-o", default="-", help="Output file (default stdout)")
    p_search.add_argument("--format", choices=list(FORMATTERS), default="json")
    p_search.add_argument("--refresh", action="store_true", help="Ignore cache")
    p_search.set_defaults(func=cmd_search)

    p_fetch = sub.add_parser("fetch", help="Fetch one or more PMIDs")
    p_fetch.add_argument("pmids", nargs="+", help="PMID list")
    p_fetch.add_argument("--output", "-o", default="-")
    p_fetch.add_argument("--format", choices=list(FORMATTERS), default="json")
    p_fetch.add_argument("--refresh", action="store_true")
    p_fetch.set_defaults(func=cmd_fetch)

    p_cache = sub.add_parser("cache", help="Inspect or clear local cache")
    g = p_cache.add_mutually_exclusive_group(required=True)
    g.add_argument("--stats", action="store_true")
    g.add_argument("--show", metavar="PMID")
    g.add_argument("--clear", action="store_true")
    p_cache.add_argument("--yes", action="store_true", help="Skip confirmation on --clear")
    p_cache.set_defaults(func=cmd_cache)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
