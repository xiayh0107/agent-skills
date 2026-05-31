#!/usr/bin/env bash
# env_check.sh — Detect available execution tier for pubmed-research skill
# Outputs JSON to stdout, exit 0 on success.
# Never prints the API key, only whether it's loaded.

set -u

ENV_FILE="${HOME}/.config/pubmed-research/.env"
CACHE_DIR="${HOME}/.cache/pubmed-research/abstracts"

# --- Load .env if present (does not pollute parent shell) ---
api_key_loaded="false"
email_loaded="false"
if [ -f "$ENV_FILE" ]; then
    # Read key existence only, never echo values
    if grep -qE '^NCBI_API_KEY=.+' "$ENV_FILE"; then
        api_key_loaded="true"
    fi
    if grep -qE '^NCBI_EMAIL=.+' "$ENV_FILE"; then
        email_loaded="true"
    fi
fi

# --- Detect Python tier ---
python_bin=""
python_version=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        python_bin="$cand"
        python_version="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"
        break
    fi
done

has_biopython="false"
has_requests="false"
has_urllib="false"
if [ -n "$python_bin" ]; then
    if "$python_bin" -c "import Bio.Entrez" 2>/dev/null; then
        has_biopython="true"
    fi
    if "$python_bin" -c "import requests" 2>/dev/null; then
        has_requests="true"
    fi
    if "$python_bin" -c "import urllib.request" 2>/dev/null; then
        has_urllib="true"
    fi
fi

has_curl="false"
if command -v curl >/dev/null 2>&1; then
    has_curl="true"
fi

# --- Decide tier ---
# Tier 1: python + biopython (best for batch)
# Tier 2: python + requests
# Tier 3: python + urllib (stdlib only)
# Tier 4: curl + shell
# Tier 5: web_fetch fallback (no local execution)
tier=""
tier_reason=""
if [ "$has_biopython" = "true" ]; then
    tier="1"
    tier_reason="python + biopython (batch-friendly)"
elif [ "$has_requests" = "true" ]; then
    tier="2"
    tier_reason="python + requests"
elif [ "$has_urllib" = "true" ]; then
    tier="3"
    tier_reason="python stdlib (urllib only)"
elif [ "$has_curl" = "true" ]; then
    tier="4"
    tier_reason="curl + shell (no python)"
else
    tier="5"
    tier_reason="no local execution available — fall back to web_fetch"
fi

# --- Ensure cache dir exists ---
mkdir -p "$CACHE_DIR" 2>/dev/null

cache_count="0"
if [ -d "$CACHE_DIR" ]; then
    cache_count="$(find "$CACHE_DIR" -maxdepth 1 -name '*.json' -type f 2>/dev/null | wc -l | tr -d ' ')"
fi

# --- Compute rate limit ---
if [ "$api_key_loaded" = "true" ]; then
    rate_limit="10 req/sec"
else
    rate_limit="3 req/sec (no API key — slower)"
fi

# --- Warnings ---
warnings="[]"
warn_list=""
add_warn() {
    if [ -z "$warn_list" ]; then
        warn_list="\"$1\""
    else
        warn_list="$warn_list, \"$1\""
    fi
}

if [ "$api_key_loaded" = "false" ]; then
    add_warn "NCBI_API_KEY not set in $ENV_FILE — rate limited to 3 req/sec"
fi
if [ "$email_loaded" = "false" ]; then
    add_warn "NCBI_EMAIL not set in $ENV_FILE — NCBI may block requests"
fi
if [ "$tier" = "5" ]; then
    add_warn "No python or curl available — only web_fetch fallback works"
fi
if [ -n "$warn_list" ]; then
    warnings="[$warn_list]"
fi

# --- Emit JSON ---
cat <<JSON
{
  "tier": $tier,
  "tier_reason": "$tier_reason",
  "python_bin": "$python_bin",
  "python_version": "$python_version",
  "has_biopython": $has_biopython,
  "has_requests": $has_requests,
  "has_urllib": $has_urllib,
  "has_curl": $has_curl,
  "api_key_loaded": $api_key_loaded,
  "email_loaded": $email_loaded,
  "rate_limit": "$rate_limit",
  "env_file": "$ENV_FILE",
  "cache_dir": "$CACHE_DIR",
  "cached_abstracts": $cache_count,
  "warnings": $warnings
}
JSON
