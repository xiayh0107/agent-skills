# PubMed Query Recipes

Pre-built query templates by research scenario. Load this file when starting
a new search and the question fits one of the patterns below. Adapt the
placeholders (`<…>`) to the specific topic.

## Table of contents

1. Study-type filters
2. PICO templates
3. Systematic review / meta-analysis
4. Drug-related searches
5. Disease epidemiology
6. Diagnostic accuracy
7. Cohort / case-control / case report
8. Author-centric searches
9. Monitoring / surveillance

---

## 1. Study-type filters

Drop these into any query as building blocks.

```
randomized controlled trial[pt]
clinical trial[pt]
meta-analysis[pt]
systematic review[pt]
review[pt]
case reports[pt]
practice guideline[pt]
observational study[pt]
comparative study[pt]
multicenter study[pt]
```

**High-evidence filter** (Cochrane-style):

```
(randomized controlled trial[pt]
 OR controlled clinical trial[pt]
 OR systematic review[pt]
 OR meta-analysis[pt])
```

---

## 2. PICO templates

PICO = Population, Intervention, Comparison, Outcome. Build each component
separately, then combine with AND.

**Template**:

```
(<population MeSH>[mh] OR <population synonym>[tiab])
AND
(<intervention>[tiab] OR <intervention MeSH>[mh])
AND
(<comparator>[tiab])
AND
(<outcome>[tiab] OR <outcome MeSH>[mh])
AND
<study-type filter>
AND
<date>[dp]
AND
english[la]
```

**Example** — SGLT2 inhibitors vs placebo for cardiovascular outcomes in T2DM:

```
(diabetes mellitus, type 2[mh] OR "type 2 diabetes"[tiab])
AND
(sglt2 inhibitor*[tiab] OR empagliflozin[tiab] OR dapagliflozin[tiab]
 OR canagliflozin[tiab] OR ertugliflozin[tiab])
AND
(placebo[tiab] OR "standard care"[tiab])
AND
(cardiovascular[tiab] OR "major adverse cardiovascular events"[tiab]
 OR mortality[tiab] OR "heart failure"[tiab])
AND
randomized controlled trial[pt]
AND
2018:2024[dp]
AND
english[la]
```

---

## 3. Systematic review / meta-analysis

**Find existing SRs/MAs on a topic**:

```
<topic>[tiab]
AND
(systematic review[pt] OR meta-analysis[pt]
 OR "systematic review"[tiab] OR "meta-analysis"[tiab])
AND
2020:2024[dp]
```

**Find primary studies for your own SR/MA** (broader):

```
(<concept-1 MeSH>[mh] OR <concept-1 synonym>[tiab])
AND
(<concept-2 MeSH>[mh] OR <concept-2 synonym>[tiab])
AND
(randomized controlled trial[pt] OR controlled clinical trial[pt]
 OR clinical trial[pt])
AND
humans[mh]
```

**PRISMA flag** — papers that report PRISMA-compliant SRs:

```
prisma[tiab] OR "preferred reporting items"[tiab]
```

---

## 4. Drug-related searches

**Drug efficacy** — RCTs of a specific drug:

```
<drug name>[nm]
AND
randomized controlled trial[pt]
AND
<indication>[mh]
AND
2020:2024[dp]
```

**Drug-drug comparison**:

```
(<drug A>[tiab] AND <drug B>[tiab])
AND
(versus[tiab] OR comparison[tiab] OR "head to head"[tiab])
AND
randomized controlled trial[pt]
```

**Adverse effects**:

```
<drug name>[nm]/adverse effects[mh]
OR
(<drug name>[tiab] AND ("adverse effect*"[tiab] OR "side effect*"[tiab]
                        OR toxicity[tiab] OR safety[tiab]))
```

**Pharmacovigilance / post-marketing**:

```
<drug name>[nm]
AND
(pharmacovigilance[tiab] OR "post-marketing"[tiab]
 OR "real-world evidence"[tiab] OR "spontaneous reports"[tiab])
```

---

## 5. Disease epidemiology

**Prevalence / incidence**:

```
<disease>[mh]/epidemiology
AND
(prevalence[tiab] OR incidence[tiab])
AND
<region/country>[tiab]
AND
2020:2024[dp]
```

**Burden of disease**:

```
<disease>[mh]
AND
("global burden"[tiab] OR "disability adjusted life years"[tiab]
 OR DALYs[tiab] OR "years of life lost"[tiab])
```

**Risk factors**:

```
<disease>[mh]/etiology
AND
("risk factor*"[tiab] OR "risk assessment"[tiab])
AND
(cohort stud*[tiab] OR case-control[tiab] OR cross-sectional[tiab])
```

---

## 6. Diagnostic accuracy

**Standard DTA query**:

```
<index test>[tiab]
AND
<reference standard>[tiab]
AND
(sensitivity[tiab] OR specificity[tiab] OR "diagnostic accuracy"[tiab]
 OR "ROC curve"[tiab] OR "area under curve"[tiab])
AND
<target condition>[mh]
```

**AI / ML diagnostic studies** (TRIPOD-AI / STARD-AI relevant):

```
(<target condition>[mh])
AND
(("deep learning"[tiab] OR "machine learning"[tiab]
  OR "artificial intelligence"[tiab] OR "neural network*"[tiab]
  OR "convolutional"[tiab]))
AND
(diagnos*[tiab] OR classif*[tiab] OR detect*[tiab])
AND
2020:2024[dp]
```

---

## 7. Cohort / case-control / case report

**Cohort study**:

```
(<exposure>[tiab] OR <exposure MeSH>[mh])
AND
(<outcome>[tiab] OR <outcome MeSH>[mh])
AND
("cohort stud*"[tiab] OR "prospective stud*"[tiab]
 OR "follow-up stud*"[tiab] OR "longitudinal"[tiab])
AND
humans[mh]
```

**Case-control study**:

```
<exposure>[tiab]
AND
<outcome>[tiab]
AND
("case-control"[tiab] OR "case control"[tiab] OR "matched study"[tiab])
```

**Case reports**:

```
<condition>[tiab]
AND
case reports[pt]
AND
2020:2024[dp]
```

**Population-based registry**:

```
<condition>[mh]
AND
(registry[tiab] OR "national database"[tiab] OR "population-based"[tiab]
 OR NHANES[tiab] OR "UK Biobank"[tiab] OR "Surveillance Epidemiology and End Results"[tiab])
```

---

## 8. Author-centric searches

**An author's complete output**:

```
<lastname> <initials>[au]
```

**An author at a specific institution**:

```
<lastname> <initials>[au]
AND
<institution>[ad]
```

**An author's recent work**:

```
<lastname> <initials>[au]
AND
2022:2024[dp]
```

**Senior author** (last position):

```
<lastname> <initials>[lastau]
```

**Author with research topic**:

```
<lastname> <initials>[au]
AND
<topic>[tiab]
```

---

## 9. Monitoring / surveillance

**New papers since last check** — use `[edat]` not `[dp]`:

```
<topic>[tiab]
AND
"last 30 days"[edat]
```

**Pre-print or just-online** — `[ppdt]` catches articles before formal `[dp]`:

```
<topic>[tiab]
AND
2024/12/01:2025/01/31[ppdt]
```

**RSS / saved-search style** — for ongoing monitoring, save and re-run:

```
(<concept-1>[mh] OR <concept-1 synonym>[tiab])
AND
(<concept-2>[mh] OR <concept-2 synonym>[tiab])
AND
"last 7 days"[edat]
```

---

## Tips for writing your own template

1. **Build one concept at a time**, test it in isolation, then AND them together.
2. **Always use synonyms** — `(metformin OR glucophage OR biguanide)` catches
   more than `metformin` alone.
3. **MeSH + tiab is the golden pair**: MeSH for controlled vocabulary,
   `[tiab]` for terms not yet indexed (esp. very recent papers).
4. **Test broad first, narrow second**. If your first version returns 5 hits,
   widen synonyms. If it returns 50,000, add date / study-type filters.
5. **Save the query in the project notes** — reproducibility matters for any
   systematic work.
