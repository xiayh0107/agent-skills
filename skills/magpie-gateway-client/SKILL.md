---
name: magpie-gateway-client
description: Configure a local Claude Code, OpenAI-compatible client, or other agent to call a remote Magpie gateway, and diagnose model IDs, authentication, provider fallback, and routing groups. Use when the subscription login stays on the server; do not use for deploying Magpie itself.
---

# Use a remote Magpie gateway locally

This skill covers the client side of an isolated deployment: the local machine sends requests to Magpie over HTTPS, while Claude/Codex subscription credentials remain on the remote server.

## Client contract

- OpenAI-compatible clients usually use `https://<SERVER_HOST>/v1` as the base URL and the Magpie gateway bearer key as the API key.
- Anthropic-compatible clients usually use `https://<SERVER_HOST>` as the base URL and the same gateway key in the client-specific auth variable. Copy the current values from Magpie's Gateway/Client setup page because names can change.
- The Magpie Web login cookie is not an API credential. A successful Web login does not prove that `/v1` is authorized.
- Never copy the server's Claude/Codex `auth.json`, `.credentials.json`, Firefox profile, or Web key to the local machine.

## Safe setup

1. Store the gateway key in the local OS keychain, a secret manager, or a mode-600 environment file. Do not put it in a shell history, repository, screenshot, or chat.
2. Set the client's base URL and auth variable. Keep `/v1` exactly where the client expects it; verify with a models request.
3. Select a model shown in Magpie's current Models page. Names normally use `provider/model` or `group/<group-id>`.
4. Send a minimal request and confirm the request is reaching the remote gateway before debugging provider quota or fallback.

## Routing semantics

- `claude/<model>` selects the Claude provider. It can use a provider-level fallback only when that fallback is configured and a supported failure condition occurs.
- `group/<group-id>` selects a Magpie routing group and lets Magpie choose among the group's members.
- A direct request to Claude bypasses both mechanisms. So does a client pointed at the upstream provider instead of the Magpie HTTPS URL.
- A fallback can change model family. For example, a Claude Sonnet request may fall back to a configured Opus model. Verify this is acceptable before using a fixed fallback.

Read [references/client-config.md](references/client-config.md) for protocol examples and diagnosis.
