---
name: magpie-remote-server
description: Deploy and operate Magpie on a headless Linux server when subscription accounts must stay isolated on the server and local clients consume the gateway over HTTPS. Use for Magpie services, Nginx exposure, server-side browser login, noVNC troubleshooting, and provider setup; do not use for unrelated Magpie API questions.
---

# Magpie on an isolated headless server

Use this skill when the user wants a remote Magpie instance to hold Claude/Codex or another agent subscription while a local machine calls the resulting gateway. The goal is server-side account isolation and a small, reviewable public surface.

## Non-negotiable boundaries

- Treat the server's service user home, Claude/Codex auth files, Firefox profile, Web login key, and gateway bearer key as credentials. Never print, copy, or commit their values.
- Run Magpie inspection and provider commands as the service user with its real `HOME`; running as root usually reads a different configuration.
- Keep Magpie Web, gateway, VNC, and WebSocket backends on loopback. Put Nginx HTTPS and authentication in front of them.
- Protect the Web UI, server-browser startup route, and noVNC WebSocket with the same authenticated session. Protect `/v1/` with a separate bearer key.
- Complete OAuth inside a browser running on the server when the user requires complete local isolation. Do not ask the user to paste passwords, MFA codes, CAPTCHA answers, authorization codes, or auth files into chat.
- Before changing SSH authentication, establish and verify a key-based recovery path.

## Workflow

1. Inspect the current OS, Magpie version/help, service user, systemd units, listeners, Nginx routes, certificate renewal, memory, and swap. Treat old deployment facts as observations.
2. Install or upgrade Magpie using the current upstream instructions. Preserve the service user and verify the unit after restart.
3. Configure loopback listeners and Nginx HTTPS. Test authenticated and unauthenticated responses separately; an open 443 port does not imply anonymous access.
4. If a subscription login is needed, start the server-side Firefox/Xvnc/Websockify session on demand. Finish login in that remote browser, then finish the matching CLI login as the Magpie service user.
5. Refresh provider models and verify that the expected `provider/model` IDs exist. Add API-key providers through the Web UI or the current CLI help without exposing secrets in arguments or logs.
6. Explain the local client setup using `magpie-gateway-client`. Confirm a minimal request through `/v1` before claiming that the subscription is usable.

## Resource and failure guidance

On small VPSs, Firefox plus Xvnc/noVNC can trigger OOM. Use swap as a buffer, keep the browser session time-limited, and diagnose memory/OOM before changing Nginx when noVNC shows 502 or a WebSocket disconnect. A missing provider often means the CLI was run with the wrong user or `HOME`, not that OAuth failed.

Read [references/server-runbook.md](references/server-runbook.md) for the generic deployment shape and checks. For the full user-facing explanation, see [`docs/magpie-remote-claude-local.md`](../../docs/magpie-remote-claude-local.md).
