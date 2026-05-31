---
name: pubmed-research
description: Search PubMed and verify citations end-to-end. Builds advanced PubMed queries (Boolean operators, MeSH terms, field tags, PICO), retrieves articles via NCBI E-utilities, caches abstracts locally, and verifies that claims attributed to a PMID are actually supported by the abstract. Use this skill whenever the user asks to search PubMed, find biomedical literature, look up a PMID, verify a citation, check whether a reference is real, audit references in a manuscript, or fetch abstracts. Also use this skill any time a response is going to cite a PubMed paper — pull and verify the citation rather than relying on memory, since model memory of PMIDs and exact paper claims is unreliable.
---

# PubMed Research

End-to-end PubMed search and citation verification. This skill replaces three failure modes of LLM-based literature work: weak query construction, fabricated PMIDs, and misattributed claims.

## When to use this skill

Use whenever the conversation involves PubMed or biomedical literature. Specific triggers:

- Search requests: "find recent papers on X", "look up clinical trials of Y"
- Citation retrieval: "what does PMID 12345 say?", "give me the abstract of DOI ..."
- Verification: "is this reference real?", "verify these PMIDs", "audit my bibliography"
- Cross-checking: any time the answer cites a paper — *fetch and verify, do not recall from memory*

Do **not** use this skill for: general web search on biomedical topics that don't need PubMed specifically; questions about biology concepts where no citation is needed; full-text retrieval of paywalled articles (this skill works with abstracts only).

## Architecture

Three layers, each independently usable:

1. **L1 — Query**: construct a PubMed query, run `esearch`, get PMIDs
2. **L2 — Fetch**: pull abstracts via `efetch`, parse to JSON, cache locally
3. **L3 — Verify**: given a claim + PMID, check whether the abstract supports the claim

For most search tasks, run L1 → L2 sequentially. For verification of an existing manuscript, jump straight to L3 (L3 will call L2 internally as needed).

## Setup (one-time, per user)

> **Do not assume the user has already configured a key.** A first-time user almost
> certainly has not. The very first action of this skill on any new machine is to run
> `env_check.sh` and, if `api_key_loaded` / `email_loaded` is `false`, walk the user
> through the checklist below **before** running any search. Do not silently proceed —
> an unconfigured key means NCBI may block requests outright.

### Step 0 — Run the environment check first (always)

```bash
bash scripts/env_check.sh
```

It prints JSON: which Python tier is available (biopython > requests > urllib > curl >
web_fetch fallback), whether the key/email are loaded, the resolved `env_file` path, and
the cache location. **Read `api_key_loaded`, `email_loaded`, and `env_file` from its
output** — those tell you exactly what is missing and where the file must go. Follow
whichever tier it reports; do not guess.

- Both `true` → setup is done, skip to L1.
- Either `false` → run the onboarding checklist below, then re-run `env_check.sh` to confirm.

### First-time setup checklist

```
[ ] 1. Create a free NCBI account (or sign in)
[ ] 2. Generate an NCBI API key from Account Settings
[ ] 3. Note the email registered on that NCBI account
[ ] 4. Create the .env file at the exact path for this OS (see table)
[ ] 5. Paste the key + email into .env, lock down permissions
[ ] 6. Re-run `bash scripts/env_check.sh` → confirm api_key_loaded:true, email_loaded:true
```

### Step 1–3 — Get the key from the NCBI website

The API key is free and issued instantly. Guide the user through these clicks (do **not**
ask them to paste the key into the chat — see guardrails):

1. Open **https://account.ncbi.nlm.nih.gov/** and sign in, or register (Google /
   Microsoft / institutional logins all work — no separate password needed).
2. Click the **username** at the top-right → **Account settings**
   (direct link: **https://account.ncbi.nlm.nih.gov/settings/**).
3. Scroll to the **API Key Management** section.
4. Click **Create an API Key**. A long hex string appears — that is `NCBI_API_KEY`.
   It is shown only here; the user should copy it now.
5. `NCBI_EMAIL` is simply the email address registered on this NCBI account (any valid
   contact email NCBI can reach you at if your usage misbehaves).

> Without a key, NCBI rate-limits to **3 req/sec** instead of 10 — the skill still works,
> just slower. Without an email, NCBI may **block requests entirely**. The email matters
> more than the key for basic use.

### Step 4–5 — Where the file goes (OS-specific)

Both scripts read `~/.config/pubmed-research/.env` (resolved via `$HOME` / `Path.home()`).
Use the absolute path for the user's actual system — confirm it against the `env_file`
field that `env_check.sh` printed:

| OS | Absolute path to the `.env` file |
|---|---|
| **macOS** | `/Users/<username>/.config/pubmed-research/.env` |
| **Linux** | `/home/<username>/.config/pubmed-research/.env` |
| **Windows (WSL / Git Bash)** | `/home/<username>/.config/pubmed-research/.env` — run the skill from WSL or Git Bash, since `env_check.sh` is a Bash script |

> On this machine (`$HOME` = `/Users/xiayh` per the environment), the file path is
> **`/Users/xiayh/.config/pubmed-research/.env`**. Substitute the user's real home dir if
> different; trust the `env_file` value from `env_check.sh` over this example.

Create it (macOS / Linux / WSL — uses `$HOME`, so the path is always correct for the user):

```bash
mkdir -p "$HOME/.config/pubmed-research"
chmod 700 "$HOME/.config/pubmed-research"
cat > "$HOME/.config/pubmed-research/.env" <<'EOF'
NCBI_API_KEY=paste_the_key_from_step_4_here
NCBI_EMAIL=your_account_email@example.com
EOF
chmod 600 "$HOME/.config/pubmed-research/.env"
```

The user edits the two values in that file. Have them replace the placeholder text, then
re-run the env check. (As a fallback, the scripts also read `NCBI_API_KEY` / `NCBI_EMAIL`
from real environment variables if the `.env` file is absent — but the file is the
recommended, persistent path.)

### Step 6 — Confirm

```bash
bash scripts/env_check.sh
```

Expect `"api_key_loaded": true` and `"email_loaded": true`. If still `false`, the most
common causes are: wrong path (not under the user's real `$HOME`), a blank value after the
`=`, or stray quotes/spaces around the value. Fix and re-run.

**Security:** Never write the key into any skill file, never echo it back to the user,
never include it in commit messages or logs. If the user pastes a key into the chat,
advise them to keep it out of the conversation and rotate it.

## L1 — Query construction

PubMed's power is in its query syntax. Build queries deliberately, not as keyword strings.

### Decision tree

- **Simple lookup** (PMID, DOI, author + year): one-line query, no need for the syntax reference
- **Topic search with 1-2 concepts**: use field tags, see examples below
- **Systematic review / PICO / multi-concept**: load `references/query_syntax.md` and `references/query_recipes.md` before writing the query

### Core syntax in one minute

| Tag | Meaning | Example |
|---|---|---|
| `[tiab]` | Title or abstract | `metformin[tiab]` |
| `[mh]` | MeSH heading (includes narrower terms) | `diabetes mellitus[mh]` |
| `[majr]` | MeSH major topic | `hypertension[majr]` |
| `[pt]` | Publication type | `randomized controlled trial[pt]` |
| `[dp]` | Date of publication | `2022:2024[dp]` |
| `[au]` | Author | `smith ja[au]` |
| `[ta]` | Journal | `lancet[ta]` |
| `[la]` | Language | `english[la]` |
| `[pmid]` | PubMed ID | `12345678[pmid]` |
| `[doi]` | DOI | `10.1056/NEJMoa123456[doi]` |

Boolean operators: `AND`, `OR`, `NOT` (case-sensitive, must be uppercase). Group with parentheses.

### Examples

```
# Recent RCTs on a drug
metformin[tiab] AND randomized controlled trial[pt] AND 2022:2024[dp]

# PICO: type 2 diabetes + SGLT2 inhibitor + cardiovascular outcomes, last 3 years, English
diabetes mellitus, type 2[mh] AND
(sglt2 inhibitor[tiab] OR empagliflozin[tiab] OR dapagliflozin[tiab]) AND
cardiovascular[tiab] AND
2022:2024[dp] AND english[la]

# Free full text only
crispr[tiab] AND 2024[dp] AND free full text[sb]
```

For complex strategies (proximity, wildcards, MeSH subheadings, search history), load `references/query_syntax.md`.

For ready-made templates by study type (RCT, SR/MA, cohort, case-control, etc.), load `references/query_recipes.md`.

## L2 — Fetch and cache

Once you have PMIDs, fetch the abstracts. Always cache them — caching is what makes L3 verification affordable.

### Run a search end-to-end

```bash
python scripts/pubmed_search.py search "your query here" --max 50 --output /tmp/results.json
```

This:
1. Loads `.env` and detects the best execution tier
2. Runs `esearch` to get PMIDs
3. Runs `efetch` in batches (respects rate limits)
4. Parses each record to: `{pmid, title, authors, journal, year, doi, abstract, mesh_terms, pub_types}`
5. Writes each abstract to `~/.cache/pubmed-research/abstracts/{pmid}.json`
6. Writes the combined search result to `--output`

### Fetch known PMIDs (no search)

```bash
python scripts/pubmed_search.py fetch 12345678 23456789 34567890 --output /tmp/refs.json
```

Cached PMIDs are read from disk, only new ones hit NCBI.

### Inspect the cache

```bash
python scripts/pubmed_search.py cache --stats           # count, size, oldest, newest
python scripts/pubmed_search.py cache --show 12345678   # print one record
python scripts/pubmed_search.py cache --clear           # nuke all (asks for confirmation)
```

## L3 — Citation verification

This is the anti-hallucination core. Two modes:

### Mode A: Verify a list of PMIDs exists and matches expected metadata

```bash
python scripts/verify_citation.py refs /path/to/refs.bib
```

For each entry, checks:
- PMID resolves on NCBI
- Title similarity to bibliography entry (fuzzy match)
- First author matches
- Year matches

Output is a JSON audit report with per-entry status: `VERIFIED` / `METADATA_MISMATCH` / `NOT_FOUND` / `FABRICATED`.

### Mode B: Verify a claim is supported by the cited abstract

```bash
python scripts/verify_citation.py claim \
  --pmid 12345678 \
  --claim "Metformin reduced HbA1c by 1.2% compared to placebo"
```

This pulls the abstract from cache (or fetches it), then runs a lightweight check:
- Key noun phrases from the claim must appear in the abstract (semantic overlap, not exact match)
- Numerical values in the claim are extracted and searched in the abstract
- A confidence score is returned with the verdict: `SUPPORTED` / `WEAK_SUPPORT` / `NOT_SUPPORTED` / `CONTRADICTED`

**This is a heuristic, not a proof.** A `WEAK_SUPPORT` result means "abstract probably doesn't directly state this — read the full paper." When confidence is low, present the abstract to the user and let them judge — don't silently downgrade a citation.

### When to use which mode

- Before submitting any bibliography → Mode A on the whole file
- Before stating a specific numerical or causal claim with a citation → Mode B on that claim
- When the user shows you a manuscript with citations → both, in order

## Output formats

Structured JSON is the default. Convert to other formats only when asked:

- **BibTeX** (`--format bibtex`): adds `verified = {true/false}`, `verified_by = {pubmed}`, `verified_on = {iso-date}` fields so downstream tools know what to trust
- **Markdown table** (`--format md`): human-readable summary, columns: PMID, Year, Title, Journal, First Author, DOI
- **CSV** (`--format csv`): for spreadsheets
- **Plain text** (`--format text`): one block per record, MEDLINE-like

## Common workflows

### Workflow 1: Topic search → review

```
1. Construct query (use references/query_recipes.md if PICO or systematic)
2. python scripts/pubmed_search.py search "<query>" --max 100 --output search.json
3. Skim titles, refine query, re-run with --max higher if needed
4. python scripts/pubmed_search.py search "<refined>" --format md --output review.md
5. Present markdown table to user
```

### Workflow 2: User pastes a list of PMIDs

```
1. Extract PMIDs from user's message (regex \b\d{7,8}\b is a starting filter)
2. python scripts/pubmed_search.py fetch <pmids> --output refs.json
3. Confirm each is real and present metadata
4. If any return NOT_FOUND, flag clearly — that's a potential fabrication
```

### Workflow 3: Verify Claude's own draft

```
1. Claude has just written a paragraph citing PMIDs A, B, C with specific claims
2. python scripts/verify_citation.py refs --pmids A,B,C
3. For each claim → citation pair: python scripts/verify_citation.py claim --pmid X --claim "..."
4. If any verification fails, REWRITE the paragraph, do not paper over the failure
```

### Workflow 4: Audit an external bibliography

```
1. Receive .bib or list of references from user
2. python scripts/verify_citation.py refs <file>
3. Present audit report
4. Offer to suggest replacements for FABRICATED entries (use search to find the likely intended paper)
```

## Rules and guardrails

- **Never invent a PMID.** If a search returns no hits, report zero hits — do not fall back to memory and produce a plausible-looking ID.
- **Never echo the API key.** It's loaded by scripts directly from `.env`. If a user asks "what's my key" or pastes one in chat, advise them to keep it out of conversation and rotate it.
- **Respect rate limits.** Scripts handle this, but if running ad-hoc curl, max 10 req/sec with key, 3 without. Bursty parallel queries will get the user soft-banned.
- **Cite the cache state.** When presenting verified results, note whether each was freshly fetched or read from cache — staleness is unlikely but possible for very recent papers.
- **Heuristic verification is not human judgment.** L3 catches obvious fabrications and clear mismatches. It will not catch a subtle claim that twists the conclusion. For high-stakes writing (publications, grants), tell the user to read the abstracts themselves for any claim above WEAK_SUPPORT.

## Loading references

These are loaded on demand, not at skill activation:

- `references/query_syntax.md` — full PubMed query language (field tags, operators, wildcards, proximity, automatic term mapping, MeSH subheadings, special characters)
- `references/query_recipes.md` — pre-built query templates: RCT, systematic review, meta-analysis, cohort, case-control, case report, drug-drug, drug-disease, screening accuracy
- `references/api_reference.md` — full E-utilities documentation: all 9 endpoints, parameters, response formats, batch operations, history server, error codes

When constructing a complex query, load `query_syntax.md` and `query_recipes.md`. When debugging an API call or doing something unusual (history server, batch EPost), load `api_reference.md`.
