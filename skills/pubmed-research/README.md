# pubmed-research — Claude Code Skill

A PubMed skill that does three things:

1. **Build proper queries** — Boolean / MeSH / field tags / PICO templates
2. **Fetch and cache abstracts** — never hits NCBI twice for the same PMID
3. **Verify citations** — catches fabricated PMIDs and claims unsupported by their abstract

Built by combining ideas from `davila7/pubmed-database` (query syntax), `K-Dense-AI/scientific-agent-skills` (progressive references loading), and `Aperivue/medsci-skills` (citation audit), with a new abstract-cache + adaptive-tier execution layer.

## Install

```bash
# 1. Drop the skill into Claude Code's skills directory
cp -r pubmed-research ~/.claude/skills/

# 2. Create your env file (one-time)
mkdir -p ~/.config/pubmed-research
chmod 700 ~/.config/pubmed-research
cat > ~/.config/pubmed-research/.env <<EOF
NCBI_API_KEY=your_key_here
NCBI_EMAIL=your_email@example.com
EOF
chmod 600 ~/.config/pubmed-research/.env
```

Get a free NCBI API key at https://www.ncbi.nlm.nih.gov/account/settings/ (raises rate limit from 3 to 10 req/sec). The skill works without one, just slower.

## Verify install

```bash
bash ~/.claude/skills/pubmed-research/scripts/env_check.sh
```

You should see JSON with `"tier": 1` or `"tier": 2` and `"api_key_loaded": true`.

## Smoke test

```bash
# Search
python3 ~/.claude/skills/pubmed-research/scripts/pubmed_search.py \
  search "metformin AND 2024[dp]" --max 5 --format md

# Fetch known PMIDs
python3 ~/.claude/skills/pubmed-research/scripts/pubmed_search.py \
  fetch 38000001 38000002 --format text

# Verify a claim (after fetching the PMID)
python3 ~/.claude/skills/pubmed-research/scripts/verify_citation.py claim \
  --pmid 38000001 --claim "your claim about the paper"
```

## Architecture

```
pubmed-research/
├── SKILL.md                      # Main instructions Claude reads
├── references/
│   ├── query_syntax.md          # Full PubMed query language
│   ├── query_recipes.md         # PICO / SR-MA / drug / cohort templates
│   └── api_reference.md         # E-utilities (9 endpoints, history server)
└── scripts/
    ├── env_check.sh             # Detects execution tier, never echoes keys
    ├── pubmed_search.py         # esearch + efetch + cache, 5 output formats
    └── verify_citation.py       # PMID audit + claim-vs-abstract check
```

The skill loads progressively: SKILL.md is always in context (~240 lines), references load only when Claude decides they're relevant, and the cache means repeated runs are nearly free.

## Limitations

- **Claim verification is heuristic.** Keyword and number overlap, not LLM semantic reasoning. A `WEAK_SUPPORT` verdict means "go read the abstract yourself" — it's a flag, not a verdict.
- **Number matching is set-based.** "78%" and "78 mg" both contain "78". For high-stakes numeric claims, read the abstract.
- **No full-text retrieval.** This skill works on abstracts. For full text, combine with a PMC fetcher.
- **Cache never expires.** Records very rarely change after publication, but corrections do happen. Use `pubmed_search.py search ... --refresh` to force re-fetch.

## License

MIT (your choice — adjust before sharing).
