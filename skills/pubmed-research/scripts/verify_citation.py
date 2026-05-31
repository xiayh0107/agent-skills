#!/usr/bin/env python3
"""
verify_citation.py — citation audit for pubmed-research skill.

Two modes:

  refs   Verify a bibliography (.bib, .json from this skill, or plain PMID list).
         Per-entry status: VERIFIED / METADATA_MISMATCH / NOT_FOUND / FABRICATED.

  claim  Verify a specific factual claim against an abstract.
         Per-claim verdict: SUPPORTED / WEAK_SUPPORT / NOT_SUPPORTED.

Both modes reuse pubmed_search.py's cache, so a claim check on a recently
searched PMID is free.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# Reuse fetch/cache/parse from sibling script
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
import pubmed_search as ps  # noqa: E402

# ---------- Text utilities ----------

STOPWORDS = {
    "a", "an", "and", "or", "but", "the", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "this", "that", "these", "those",
    "it", "its", "they", "them", "their", "we", "our", "you", "your", "i", "me",
    "than", "vs", "versus", "between", "after", "before", "during", "while",
    "compared", "compared to", "associated", "associated with", "may", "can",
    "could", "would", "should", "also", "however", "therefore", "thus", "hence",
    "study", "studies", "trial", "trials", "patients", "participants", "subjects",
    "group", "groups", "showed", "found", "reported", "observed", "demonstrated",
    "results", "result", "conclusion", "conclusions", "method", "methods",
    "p", "n", "ci", "se", "sd", "ie", "eg", "etc",
}

NUMERIC_RE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)(\s*%)?(?![\w.])")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]+")


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def keywords(text: str) -> set[str]:
    """Extract content-bearing keywords (lowercased, stopwords removed, len >= 3)."""
    out: set[str] = set()
    for m in WORD_RE.findall(text.lower()):
        w = m.strip("-")
        if len(w) >= 3 and w not in STOPWORDS:
            out.add(w)
    return out


def numbers_in(text: str) -> list[str]:
    """Extract numeric tokens (with optional %), canonicalized."""
    nums: list[str] = []
    for m in NUMERIC_RE.finditer(text or ""):
        val = m.group(1).replace(",", "")
        pct = "%" if m.group(2) else ""
        nums.append(val + pct)
    return nums


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


# ---------- Bibliography parsers ----------

PMID_RE = re.compile(r"\b(\d{7,9})\b")


def parse_bibtex(text: str) -> list[dict[str, str]]:
    """Very forgiving .bib parser. Returns list of {citekey, title, author, year, pmid, doi}."""
    entries: list[dict[str, str]] = []
    # Split by @article-like entries
    for chunk in re.split(r"(?=@\w+\s*\{)", text):
        chunk = chunk.strip()
        if not chunk.startswith("@"):
            continue
        head = re.match(r"@\w+\s*\{\s*([^,]+),", chunk)
        citekey = head.group(1).strip() if head else ""
        entry: dict[str, str] = {"citekey": citekey, "raw": chunk}
        for field in ("title", "author", "year", "pmid", "doi", "journal"):
            # Match field = {value} or field = "value"
            pat = re.compile(
                rf"\b{field}\s*=\s*[{{\"]([^{{}}\"]*(?:{{[^{{}}]*}}[^{{}}\"]*)*)[}}\"]",
                re.IGNORECASE | re.DOTALL,
            )
            m = pat.search(chunk)
            if m:
                entry[field] = re.sub(r"\s+", " ", m.group(1)).strip()
        entries.append(entry)
    return entries


def parse_input(path: Path) -> list[dict[str, str]]:
    """Detect file type and parse to list of entries with at minimum a pmid where possible."""
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()

    if suffix == ".bib":
        return parse_bibtex(text)

    if suffix == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            # Already in our format
            out: list[dict[str, str]] = []
            for r in data:
                out.append({
                    "citekey": r.get("pmid", ""),
                    "title": r.get("title", ""),
                    "author": r.get("first_author", ""),
                    "year": r.get("year", ""),
                    "pmid": r.get("pmid", ""),
                    "doi": r.get("doi", ""),
                })
            return out

    # Fallback: extract PMIDs from arbitrary text
    pmids = sorted(set(PMID_RE.findall(text)))
    return [{"citekey": p, "pmid": p, "title": "", "author": "", "year": ""} for p in pmids]


# ---------- Verification core ----------

def verify_one_ref(entry: dict[str, str], env: dict[str, str], limiter) -> dict[str, Any]:
    """Verify a single bibliography entry. Returns audit record."""
    audit: dict[str, Any] = {
        "citekey": entry.get("citekey", ""),
        "pmid_input": entry.get("pmid", ""),
        "title_input": entry.get("title", ""),
        "author_input": entry.get("author", ""),
        "year_input": entry.get("year", ""),
    }

    pmid = entry.get("pmid", "").strip()
    if not pmid:
        audit["status"] = "NO_PMID"
        audit["reason"] = "Entry has no PMID; cannot verify via this skill."
        return audit

    # Fetch
    try:
        records = ps.fetch_with_cache([pmid], env, limiter)
    except Exception as e:
        audit["status"] = "FETCH_ERROR"
        audit["reason"] = str(e)
        return audit

    if not records:
        audit["status"] = "FABRICATED"
        audit["reason"] = f"PMID {pmid} does not resolve on NCBI."
        return audit

    rec = records[0]
    audit["pmid_resolved"] = rec.get("pmid", "")
    audit["title_actual"] = rec.get("title", "")
    audit["first_author_actual"] = rec.get("first_author", "")
    audit["year_actual"] = rec.get("year", "")
    audit["doi_actual"] = rec.get("doi", "")
    audit["journal_actual"] = rec.get("journal", "")
    audit["from_cache"] = rec.get("_from_cache", False)

    mismatches: list[str] = []

    # Title (fuzzy)
    if entry.get("title"):
        sim = similarity(entry["title"], rec.get("title", ""))
        audit["title_similarity"] = round(sim, 3)
        if sim < 0.6:
            mismatches.append(f"title (similarity {sim:.2f})")

    # First author (last name match is enough)
    if entry.get("author"):
        a_input = normalize(entry["author"]).split()
        a_actual = normalize(rec.get("first_author", "")).split()
        # Compare last names — first token of each
        if a_input and a_actual:
            if a_input[0] != a_actual[0] and a_input[-1] != a_actual[-1]:
                mismatches.append(f"author ({entry['author']!r} vs {rec.get('first_author','')!r})")

    # Year (allow ±0)
    if entry.get("year") and rec.get("year"):
        if str(entry["year"]).strip() != str(rec["year"]).strip():
            mismatches.append(f"year ({entry['year']} vs {rec['year']})")

    if mismatches:
        audit["status"] = "METADATA_MISMATCH"
        audit["mismatches"] = mismatches
    else:
        audit["status"] = "VERIFIED"

    return audit


def verify_claim(pmid: str, claim: str, env: dict[str, str], limiter) -> dict[str, Any]:
    """Heuristic check: does the abstract of `pmid` support `claim`?"""
    audit: dict[str, Any] = {
        "pmid": pmid,
        "claim": claim,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        records = ps.fetch_with_cache([pmid], env, limiter)
    except Exception as e:
        audit["verdict"] = "FETCH_ERROR"
        audit["reason"] = str(e)
        return audit

    if not records:
        audit["verdict"] = "PMID_NOT_FOUND"
        audit["reason"] = f"PMID {pmid} does not resolve."
        return audit

    rec = records[0]
    abstract = (rec.get("abstract") or "") + " " + (rec.get("title") or "")
    audit["title"] = rec.get("title", "")
    audit["abstract_chars"] = len(rec.get("abstract", ""))

    if not abstract.strip():
        audit["verdict"] = "NO_ABSTRACT"
        audit["reason"] = "Record has no abstract to check against."
        return audit

    # Keyword overlap
    claim_kw = keywords(claim)
    abs_kw = keywords(abstract)
    if not claim_kw:
        audit["verdict"] = "EMPTY_CLAIM"
        return audit

    overlap = claim_kw & abs_kw
    kw_ratio = len(overlap) / len(claim_kw)

    # Number overlap (these matter more — a misstated stat is the worst kind of hallucination)
    claim_nums = set(numbers_in(claim))
    abs_nums = set(numbers_in(abstract))
    if claim_nums:
        num_overlap = claim_nums & abs_nums
        num_ratio = len(num_overlap) / len(claim_nums)
    else:
        num_overlap = set()
        num_ratio = None  # no claim numbers means we can't penalize

    audit["keyword_overlap_count"] = len(overlap)
    audit["keyword_total_in_claim"] = len(claim_kw)
    audit["keyword_overlap_ratio"] = round(kw_ratio, 3)
    audit["keywords_matched"] = sorted(overlap)
    audit["keywords_missing"] = sorted(claim_kw - abs_kw)
    audit["numbers_in_claim"] = sorted(claim_nums)
    audit["numbers_matched"] = sorted(num_overlap)
    audit["numbers_missing"] = sorted(claim_nums - abs_nums)
    if num_ratio is not None:
        audit["number_overlap_ratio"] = round(num_ratio, 3)

    # Verdict logic
    #  - Numbers present and all missing from abstract → NOT_SUPPORTED (strong signal of fabrication)
    #  - Numbers present and partially matched → WEAK_SUPPORT
    #  - No numbers: rely on keyword overlap thresholds
    if claim_nums and num_ratio == 0:
        audit["verdict"] = "NOT_SUPPORTED"
        audit["reason"] = "Claim contains specific numbers, none found in abstract."
    elif claim_nums and num_ratio is not None and num_ratio < 1.0:
        if kw_ratio >= 0.5:
            audit["verdict"] = "WEAK_SUPPORT"
            audit["reason"] = "Some numbers in claim are missing from abstract; keyword overlap moderate."
        else:
            audit["verdict"] = "NOT_SUPPORTED"
            audit["reason"] = "Numbers and keywords both poorly matched."
    else:
        # No numbers OR all numbers matched — use keyword threshold
        if kw_ratio >= 0.65:
            audit["verdict"] = "SUPPORTED"
            audit["reason"] = f"Keyword overlap {kw_ratio:.0%}" + (
                "; all claim numbers found in abstract" if claim_nums else ""
            )
        elif kw_ratio >= 0.35:
            audit["verdict"] = "WEAK_SUPPORT"
            audit["reason"] = f"Keyword overlap only {kw_ratio:.0%}; verify by reading the abstract."
        else:
            audit["verdict"] = "NOT_SUPPORTED"
            audit["reason"] = f"Keyword overlap {kw_ratio:.0%} too low to consider the claim supported."

    # Always include the abstract for the user to judge
    audit["abstract_excerpt"] = (rec.get("abstract") or "")[:600]
    return audit


# ---------- Commands ----------

def cmd_refs(args: argparse.Namespace) -> int:
    env = ps.load_env()
    rate = 10 if (env.get("NCBI_API_KEY") or __import__("os").getenv("NCBI_API_KEY")) else 3
    limiter = ps.RateLimiter(rate)

    if args.pmids:
        entries = [{"citekey": p, "pmid": p} for p in args.pmids]
    elif args.input:
        entries = parse_input(Path(args.input))
    else:
        print("Provide either --pmids or an input file as positional arg.", file=sys.stderr)
        return 2

    print(f"[refs] auditing {len(entries)} entries", file=sys.stderr)
    audits = [verify_one_ref(e, env, limiter) for e in entries]

    summary = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "n_total": len(audits),
        "n_verified": sum(1 for a in audits if a.get("status") == "VERIFIED"),
        "n_mismatch": sum(1 for a in audits if a.get("status") == "METADATA_MISMATCH"),
        "n_fabricated": sum(1 for a in audits if a.get("status") == "FABRICATED"),
        "n_no_pmid": sum(1 for a in audits if a.get("status") == "NO_PMID"),
        "n_error": sum(1 for a in audits if a.get("status") == "FETCH_ERROR"),
    }
    summary["submission_safe"] = (
        summary["n_fabricated"] == 0
        and summary["n_mismatch"] == 0
        and summary["n_error"] == 0
    )

    report = {"summary": summary, "records": audits}
    out_text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output and args.output != "-":
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"[refs] report written to {args.output}", file=sys.stderr)
    else:
        print(out_text)

    # Console summary
    print(
        f"[refs] verified={summary['n_verified']} "
        f"mismatch={summary['n_mismatch']} "
        f"fabricated={summary['n_fabricated']} "
        f"submission_safe={summary['submission_safe']}",
        file=sys.stderr,
    )
    return 0 if summary["submission_safe"] else 1


def cmd_claim(args: argparse.Namespace) -> int:
    env = ps.load_env()
    rate = 10 if (env.get("NCBI_API_KEY") or __import__("os").getenv("NCBI_API_KEY")) else 3
    limiter = ps.RateLimiter(rate)

    audit = verify_claim(args.pmid, args.claim, env, limiter)
    out_text = json.dumps(audit, ensure_ascii=False, indent=2)
    if args.output and args.output != "-":
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"[claim] report written to {args.output}", file=sys.stderr)
    else:
        print(out_text)

    verdict = audit.get("verdict", "")
    print(f"[claim] verdict={verdict}", file=sys.stderr)
    return 0 if verdict == "SUPPORTED" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_citation.py",
        description="Verify PubMed citations: existence, metadata, claim support.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_refs = sub.add_parser("refs", help="Audit a bibliography or PMID list")
    p_refs.add_argument("input", nargs="?", help=".bib / .json / .txt file with refs")
    p_refs.add_argument("--pmids", nargs="+", help="Inline PMID list")
    p_refs.add_argument("--output", "-o", default="-")
    p_refs.set_defaults(func=cmd_refs)

    p_claim = sub.add_parser("claim", help="Verify a single claim against an abstract")
    p_claim.add_argument("--pmid", required=True)
    p_claim.add_argument("--claim", required=True)
    p_claim.add_argument("--output", "-o", default="-")
    p_claim.set_defaults(func=cmd_claim)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
