# PubMed Query Syntax Reference

Load this file when constructing a non-trivial PubMed query. For simple keyword
or PMID lookups, the table in SKILL.md is enough.

## Table of contents

1. Field tags
2. Boolean operators
3. Phrases, wildcards, proximity
4. MeSH terms and subheadings
5. Filters and limits
6. Automatic term mapping (and how to override it)
7. Special characters
8. Date ranges
9. Common pitfalls

---

## 1. Field tags

A query term followed by `[tag]` limits search to that record field. Without a
tag, PubMed applies automatic term mapping (see section 6) — usually but not
always what you want.

### Frequently used

| Tag | Field | Notes |
|---|---|---|
| `[tiab]` | Title or abstract | Most-used freetext tag |
| `[ti]` | Title only | Stricter than `[tiab]` |
| `[ab]` | Abstract only | Rarely used alone |
| `[mh]` | MeSH terms (explodes to narrower) | Use for controlled vocabulary |
| `[majr]` | MeSH major topic | Article is *about* the topic, not just mentions it |
| `[pt]` | Publication type | RCT, review, meta-analysis, case report, etc. |
| `[dp]` | Date of publication | `2024[dp]`, `2020:2024[dp]`, `2024/03/15[dp]` |
| `[edat]` | Entrez date | Date PubMed added the record (use for "new in last N days") |
| `[au]` | Author | `smith ja[au]` matches last + initials |
| `[1au]` | First author only | |
| `[lastau]` | Last author only | Useful for senior-author searches |
| `[ad]` | Affiliation | E.g. `harvard[ad]` |
| `[ta]` | Journal title abbreviation | `lancet[ta]`, `n engl j med[ta]` |
| `[vi]` | Volume | |
| `[ip]` | Issue | |
| `[pg]` | Pagination | First page or page range |
| `[la]` | Language | `english[la]` |
| `[pmid]` | PubMed ID | Direct lookup |
| `[doi]` | DOI | `10.xxxx/yyyy[doi]` — use slashes as-is |
| `[pmc]` | PMC ID | `PMC123456[pmc]` |
| `[nm]` | Substance name (Pharmacological Action) | `metformin[nm]` |
| `[grant]` | Grant number | NIH-funded etc. |

### Less common but useful

| Tag | Field |
|---|---|
| `[sb]` | Subset / filter (free full text, MEDLINE, etc.) |
| `[ot]` | Other term (often author-supplied keywords) |
| `[crdt]` | Create date |
| `[ppdt]` | PubMed publication date (preferred over `[dp]` for very recent papers) |
| `[text]` | Free-text fields combined |

---

## 2. Boolean operators

`AND`, `OR`, `NOT` — **must be uppercase** to be parsed as operators.

```
diabetes AND metformin       # both terms required
diabetes OR hyperglycemia    # either term
diabetes NOT type 1          # diabetes but not "type 1"
```

Use parentheses for grouping:

```
(metformin[tiab] OR insulin[tiab]) AND diabetes[mh]
```

Default operator between bare terms is `AND`. So `diabetes metformin` is
equivalent to `diabetes AND metformin`. But quoted phrases bypass this.

---

## 3. Phrases, wildcards, proximity

**Exact phrase**: wrap in double quotes.

```
"heart failure"           # exact phrase, no automatic term mapping
"covid-19"                # phrase including hyphen
```

**Wildcard (truncation)**: `*` at end of stem, **minimum 4 characters before** the wildcard.

```
diab*                     # diabetes, diabetic, diabetics, etc.
neuro*                    # neurology, neuroscience, neuropathy, ...
```

PubMed turns off automatic term mapping when you use a wildcard. Truncation
expands to up to 600 variants — be specific or the expansion may fail.

**Proximity**: terms within N words of each other. Syntax is
`"term1 term2"[field:~N]`.

```
"hip fracture"[tiab:~3]   # hip and fracture within 3 words in title/abstract
"breast cancer"[ti:~5]    # same for title
```

Only works on `[tiab]`, `[ti]`, `[ab]`, `[ad]`. Word order doesn't matter.

---

## 4. MeSH terms and subheadings

MeSH (Medical Subject Headings) is a controlled vocabulary. Searching `[mh]`
**automatically explodes** to include all narrower terms. E.g.
`cardiovascular diseases[mh]` includes heart failure, MI, stroke, etc.

To **disable explosion**, use `[mh:noexp]`:

```
cardiovascular diseases[mh:noexp]   # only the parent term
```

**Subheadings** (qualifiers) limit a MeSH term to an aspect:

| Subheading | Use for |
|---|---|
| `/diagnosis` | Diagnostic methods, criteria |
| `/drug therapy` | Pharmaceutical treatment |
| `/etiology` | Causes |
| `/epidemiology` | Prevalence, incidence |
| `/prevention & control` | Prevention |
| `/therapy` | All treatments |
| `/surgery` | Surgical management |
| `/genetics` | Genetic factors |
| `/adverse effects` | Side effects |
| `/mortality` | Death/survival outcomes |

Syntax: `mesh_term/subheading[mh]`.

```
diabetes mellitus, type 2/drug therapy[mh]
hypertension/diagnosis[mh:noexp]
```

**Major topic**: use `[majr]` instead of `[mh]` to require the term as a major
focus.

```
metformin[majr]   # papers primarily about metformin, not just mentioning it
```

---

## 5. Filters and limits

PubMed filters can be applied as `[sb]` (subset) clauses:

| Filter | Query fragment |
|---|---|
| Free full text | `free full text[sb]` |
| Full text available | `full text[sb]` |
| Has abstract | `hasabstract[text]` |
| Humans | `humans[mh]` |
| Animals | `animals[mh]` |
| Female / Male | `female[mh]` / `male[mh]` |
| Adult / Child / Aged | `adult[mh]`, `child[mh]`, `aged[mh]` |
| English language | `english[la]` |
| Last 5 years | `"last 5 years"[dp]` |
| Last 90 days | `"last 90 days"[edat]` |

---

## 6. Automatic term mapping (and how to override it)

When you search a bare word, PubMed tries to map it to MeSH headings,
journal names, authors, etc. This is usually helpful but sometimes too
aggressive.

**Example of mapping**:

```
heart attack
→ "myocardial infarction"[MeSH Terms] OR ("heart"[All Fields] AND "attack"[All Fields]) OR "heart attack"[All Fields]
```

**To see what PubMed did with your query**, run it on the web and click
"Search details" / "Translations" in the right panel.

**To turn off mapping**, use field tags or quoted phrases:

```
"heart attack"            # only the literal phrase
heart attack[tiab]        # field-restricted, no MeSH mapping
```

---

## 7. Special characters

| Character | Behavior |
|---|---|
| `()` | Grouping |
| `""` | Phrase / disable mapping |
| `[]` | Field tag |
| `*` | Wildcard (min 4 chars stem) |
| `:` | Date range, e.g. `2020:2024[dp]` |
| `/` | MeSH subheading separator |
| `#` | Search history reference (web UI only) |

Avoid: `&`, `+`, `?`, `^`, `~`, `!`. They are either ignored or break parsing.

For non-ASCII characters (umlauts, Cyrillic, CJK), PubMed normalizes to ASCII
in most fields. Use the romanized form.

---

## 8. Date ranges

Several date fields exist, each with subtly different meanings:

| Tag | Meaning | When to use |
|---|---|---|
| `[dp]` | Publication date | Most common; "papers published in 2024" |
| `[ppdt]` | PubMed pub date | Use for very recent papers (more current than `[dp]`) |
| `[edat]` | Entrez date | "Indexed by PubMed since…"; use for monitoring |
| `[mhda]` | MeSH date | When MeSH terms were assigned |
| `[crdt]` | Create date | Initial record creation |

Range syntax: `start:end[tag]`.

```
2020:2024[dp]                  # publication years 2020 through 2024
2024/01/01:2024/06/30[dp]     # first half of 2024
"last 7 days"[edat]           # papers indexed in last week
"last 1 year"[dp]             # published in last 12 months
```

---

## 9. Common pitfalls

- **Lowercase boolean operators are ignored.** `cancer and metformin` searches
  the words "cancer", "and", "metformin" — not a Boolean AND. Always uppercase.

- **Wildcards disable MeSH mapping.** `diabet*` won't include MeSH `Diabetes
  Mellitus`. Use `diabetes[mh] OR diabet*[tiab]` for both.

- **Too-broad MeSH explosion.** `cardiovascular diseases[mh]` includes 50+
  child terms. Add `[mh:noexp]` if you want the parent only, or use a more
  specific child term.

- **`[au]` requires last-name + initials format.** Not "John Smith" but
  `smith j[au]` or `smith ja[au]`.

- **`[dp]` lags by weeks for new papers.** For "this week's papers" use
  `[edat]` or `[ppdt]`, not `[dp]`.

- **Quoted phrases inside `[tiab]`**: `"heart failure"[tiab]` works.
  `heart failure[tiab]` also works (interpreted as a phrase by default).
  But `heart-failure[tiab]` matches only when hyphenated in the source.

- **Display cap is 10,000 results.** For larger sets use the history server
  (see `api_reference.md`).
