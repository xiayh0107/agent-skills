# Generic server runbook

Use placeholders in this file. Replace `<SERVER_HOST>`, `<SERVICE_USER>`, `<SERVICE_HOME>`, and `<WEB_KEY_FILE>` only in a local deployment note, never in a public skill with real values.

## Layout

```text
<SERVICE_HOME>/                 Magpie service user's home
127.0.0.1:3430                 Magpie Web
127.0.0.1:3425                 Magpie gateway
127.0.0.1:3431                 Optional login helper
127.0.0.1:5901/6081             VNC and noVNC backends
https://<SERVER_HOST>/          Nginx authenticated Web UI
https://<SERVER_HOST>/v1/       Nginx gateway with bearer auth
```

## Read-only checks

```bash
sudo systemctl status magpie-web.service --no-pager
sudo ss -lntp
sudo nginx -t
sudo systemctl status <CERT_RENEWAL_TIMER> --no-pager
sudo -u <SERVICE_USER> env HOME=<SERVICE_HOME> magpie --version
sudo -u <SERVICE_USER> env HOME=<SERVICE_HOME> magpie providers
free -h
swapon --show
```

For a managed host, use the host's SSH manager instead of raw `ssh`, `scp`, `rsync`, or `sshpass`.

## Nginx invariants

Keep the following properties when editing the reverse proxy:

1. Web pages and login helpers use an authenticated session check.
2. `/v1/` is a separate upstream and requires its own bearer key.
3. VNC/noVNC uses HTTP/1.1 upgrade headers and the same session check.
4. No upstream management port is opened in the firewall.
5. `nginx -t` passes before reload, followed by a status check and an unauthenticated `401` check.

## Browser login

Run Firefox and noVNC as `<SERVICE_USER>` with a private profile. Keep the browser entry behind the Web session. After the user completes login, inspect only account/provider status and model names; never read or display token files.

## Upgrade rule

Record the current version, binary path, systemd unit, listeners, and a rollback copy before upgrading. Use the current upstream release instructions. Afterward verify the service, loopback listeners, authenticated Web UI, gateway `401` without a key, and one minimal authenticated request.
