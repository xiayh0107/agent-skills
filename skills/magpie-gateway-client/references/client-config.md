# Local client configuration

These examples use placeholders. Keep real values in a secret manager.

## OpenAI-compatible request

```bash
export OPENAI_BASE_URL="https://<SERVER_HOST>/v1"
export OPENAI_API_KEY="<MAGPIE_GATEWAY_KEY>"
curl -fsS \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  "${OPENAI_BASE_URL}/models"
```

The expected outcomes are a model list with a valid key and `401` without it. Do not treat a Web UI cookie as a substitute for `OPENAI_API_KEY`.

## Anthropic-compatible client

A deployment used the following shape; current Magpie UI/help is authoritative:

```bash
export ANTHROPIC_BASE_URL="https://<SERVER_HOST>"
export ANTHROPIC_AUTH_TOKEN="<MAGPIE_GATEWAY_KEY>"
```

Use the exact model ID displayed by Magpie. Some clients require an Anthropic model alias even when Magpie's provider model has a different name; use the Gateway/Client setup instructions rather than guessing.

## Diagnosis matrix

| Symptom | Check |
|---|---|
| `401` from `/v1/models` | URL path, bearer header, key rotation, Nginx route |
| Models list is empty | Provider health, protocol, refresh, upstream model discovery |
| Claude quota does not fall back | Request model prefix, configured fallback, gateway path |
| Works in Web UI but not client | Separate Web and gateway authentication |
| Local login prompt appears | Client is talking directly to Claude or the wrong base URL |

Never ask for or accept the remote subscription credentials as a workaround. Fix the client endpoint and gateway authentication instead.
