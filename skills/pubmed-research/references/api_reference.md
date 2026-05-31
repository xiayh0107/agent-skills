# NCBI E-utilities API Reference

Load this file when implementing programmatic access, especially for batch
operations, history server use, or unusual endpoints. For simple search +
fetch the helper script `scripts/pubmed_search.py` is enough.

## Table of contents

1. Base URL and common parameters
2. The 9 endpoints
3. Rate limits and authentication
4. History server for large result sets
5. Response formats
6. Error handling
7. Example workflows

---

## 1. Base URL and common parameters

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

**Always include**:

| Param | Value | Why |
|---|---|---|
| `tool` | Short name of your application | NCBI uses this for support contact |
| `email` | Your contact email | Required for non-trivial usage; NCBI may block requests without it |
| `api_key` | Your NCBI API key | Raises rate limit from 3 to 10 req/sec; tracks usage to your account |

These three live in `~/.config/pubmed-research/.env` and are auto-loaded by the
skill's scripts. Never write them into the URL by hand.

---

## 2. The 9 endpoints

### `esearch.fcgi` — Find UIDs matching a query

Inputs: `db`, `term`, optional `retmax` (default 20, max 100,000), `retmode`
(`xml` default, `json` recommended).

Returns: list of UIDs (PMIDs for `db=pubmed`).

```
GET /esearch.fcgi?db=pubmed&term=metformin[tiab]+AND+2024[dp]&retmode=json&retmax=100
```

Key response fields (JSON):
- `esearchresult.count` — total matching records
- `esearchresult.idlist` — array of PMIDs (up to retmax)
- `esearchresult.translationstack` — how PubMed parsed your query (useful for
  debugging unexpected results)

---

### `efetch.fcgi` — Download full records

Inputs: `db`, `id` (comma-separated UIDs, max ~200 per request), `rettype`,
`retmode`.

Common `rettype`/`retmode` combos for PubMed:

| rettype | retmode | Output |
|---|---|---|
| `abstract` | `xml` | Full structured XML — recommended for parsing |
| `abstract` | `text` | Human-readable abstract |
| `medline` | `text` | MEDLINE flat format (for reference managers) |
| `xml` | `xml` | Same as abstract+xml |
| `uilist` | `text` | Just the PMIDs |

```
GET /efetch.fcgi?db=pubmed&id=12345,23456,34567&rettype=abstract&retmode=xml
```

**Batch size**: 200 PMIDs per call is typical. For more, use history server (section 4).

---

### `esummary.fcgi` — Lightweight document summaries

Lighter than `efetch` — returns title, authors, journal, year, but **not the
abstract**. Useful for listing search results.

```
GET /esummary.fcgi?db=pubmed&id=12345,23456&retmode=json
```

---

### `epost.fcgi` — Upload a UID list to the history server

For large lists (thousands of PMIDs) that you'll want to operate on
repeatedly without re-sending each time.

```
POST /epost.fcgi
  db=pubmed
  id=12345,23456,34567,...
```

Returns: `WebEnv` token + `query_key` integer. Use these in subsequent
`efetch` / `elink` / `esearch` calls instead of `id=`.

---

### `elink.fcgi` — Find related records

Inputs: `dbfrom`, `db`, `id`, optional `cmd`.

Common uses:

```
# Similar articles to a given PMID
elink.fcgi?dbfrom=pubmed&db=pubmed&id=12345&cmd=neighbor

# PubMed Central full text linked from a PubMed record
elink.fcgi?dbfrom=pubmed&db=pmc&id=12345

# Cited-by (articles that cite the input PMID)
elink.fcgi?dbfrom=pubmed&db=pubmed&id=12345&linkname=pubmed_pubmed_citedin
```

---

### `einfo.fcgi` — Database metadata

Returns the list of fields, links, and update info for a given database.
Useful for discovering available `[fieldtag]` values.

```
GET /einfo.fcgi?db=pubmed&retmode=json
```

---

### `ecitmatch.fcgi` — Resolve a partial citation to a PMID

Given journal/year/volume/page/author, returns the matching PMID.

```
GET /ecitmatch.fcgi?db=pubmed&retmode=xml&bdata=Science|2008|320|5880|Smith|key1|
```

Format of `bdata`: `journal|year|volume|first_page|author|key|`. Pipe-separated,
trailing pipe required. `key` is your label — echoed back so you can match
results.

---

### `egquery.fcgi` — Global search across all NCBI databases

Returns hit counts per database for a single search term. Use when you don't
know which database to start with.

```
GET /egquery.fcgi?term=BRCA1
```

---

### `espell.fcgi` — Spelling suggestions

```
GET /espell.fcgi?db=pubmed&term=mefformin
→ suggests: metformin
```

---

## 3. Rate limits and authentication

| Configuration | Limit |
|---|---|
| No API key | **3 requests/second** |
| With API key | **10 requests/second** |
| With special agreement (high-volume institutions) | Negotiable |

**Get a key**: log into your NCBI account → Settings → API Key Management →
"Create an API Key". Free, takes 30 seconds.

**Rate limiting strategy**:

- Use a token bucket (`scripts/pubmed_search.py` implements one)
- On HTTP 429 or "API rate limit exceeded" error, back off and retry once
- For very large batches (>10,000 PMIDs), use history server to reduce request count
- Do not parallelize across processes — NCBI counts per-IP, not per-process

---

## 4. History server for large result sets

When your search returns >500 results, use the history server to keep them
on NCBI's side and paginate through efficiently.

**Step 1**: search with `usehistory=y`:

```
esearch.fcgi?db=pubmed&term=<query>&usehistory=y&retmode=json
```

Response includes `WebEnv` and `QueryKey`.

**Step 2**: fetch in batches:

```
efetch.fcgi?db=pubmed&WebEnv=<env>&query_key=<key>&retstart=0&retmax=500&rettype=abstract&retmode=xml
efetch.fcgi?db=pubmed&WebEnv=<env>&query_key=<key>&retstart=500&retmax=500&rettype=abstract&retmode=xml
…
```

**History session expires** after 8 hours of inactivity. For longer
workflows, `epost` the PMID list to disk and re-upload as needed.

---

## 5. Response formats

### XML (default for `efetch`)

Structure for PubMed:

```xml
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>...</PMID>
      <Article>
        <Journal>...</Journal>
        <ArticleTitle>...</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">...</AbstractText>
          <AbstractText Label="METHODS">...</AbstractText>
          …
        </Abstract>
        <AuthorList>
          <Author><LastName>...</LastName><Initials>...</Initials></Author>
          …
        </AuthorList>
        <PublicationTypeList>...</PublicationTypeList>
      </Article>
      <MeshHeadingList>...</MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">...</ArticleId>
        <ArticleId IdType="doi">...</ArticleId>
        <ArticleId IdType="pmc">PMC...</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
  …
</PubmedArticleSet>
```

### JSON (esearch / esummary)

Simpler nesting but no abstracts.

### MEDLINE text

Flat key-value lines:

```
PMID- 12345678
TI  - Title here
AB  - Abstract here
AU  - Smith JA
AU  - Lee BB
…
```

For reference managers (Zotero, Mendeley), MEDLINE format is the most
portable.

---

## 6. Error handling

| Symptom | Cause | Fix |
|---|---|---|
| HTTP 429 "Too Many Requests" | Rate limit | Back off, retry; add API key |
| HTTP 400 "Bad Request" | Malformed query (unbalanced parens, bad field tag) | Print the URL, validate |
| Empty `idlist` with no error | Query returned 0 hits — or query failed silently | Run `egquery` to sanity-check the term |
| `efetch` returns truncated XML | Batch too large | Reduce to ≤200 PMIDs per call |
| `WebEnv` invalid | Session expired (>8 h) or wrong server | Re-run `esearch` with `usehistory=y` |
| Some PMIDs return no record | Either fabricated, withdrawn, or merged | Mark as `NOT_FOUND` and flag |

**Always include a User-Agent** that identifies your tool — NCBI's anti-abuse
heuristics deprioritize anonymous traffic.

---

## 7. Example workflows

### Workflow A: simple search + fetch

```python
# esearch
ids = esearch("metformin AND 2024[dp]", retmax=100)
# efetch in batches of 200
records = []
for batch in chunks(ids, 200):
    records.extend(parse_xml(efetch(batch)))
```

### Workflow B: large search via history server

```python
# Step 1
result = esearch_with_history("type 2 diabetes[mh] AND 2020:2024[dp]")
webenv = result["webenv"]
query_key = result["querykey"]
total = result["count"]

# Step 2: paginate
records = []
for start in range(0, total, 500):
    records.extend(parse_xml(
        efetch_history(webenv, query_key, retstart=start, retmax=500)
    ))
```

### Workflow C: resolve a partial citation

```python
# User has: "Smith et al, Science 2008, vol 320, p1185"
match = ecitmatch("Science|2008|320|1185|Smith|q1|")
# match → "q1|Science|2008|320|1185|Smith|18687908"
pmid = match.split("|")[-1].strip()
records = efetch([pmid])
```

### Workflow D: find similar articles

```python
similar = elink(dbfrom="pubmed", db="pubmed", id="12345", cmd="neighbor")
# Returns ranked list of related PMIDs based on PubMed's similar-articles algorithm
```

---

## References

- E-utilities documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- API key signup: https://www.ncbi.nlm.nih.gov/account/settings/
- Usage policy: https://www.ncbi.nlm.nih.gov/books/NBK25497/
- PubMed help: https://pubmed.ncbi.nlm.nih.gov/help/
