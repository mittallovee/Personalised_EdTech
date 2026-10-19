# Opening the local app on your own domain (Cloudflare Tunnel)

Use this to reach the app running on your PC from anywhere, e.g. at `https://qb.loveemittal.online`.
A Cloudflare Tunnel (`cloudflared`) on the PC connects out to Cloudflare, so no router ports are opened.

> This is still a development setup. Put **Cloudflare Access** in front (step 4) so only you can reach it.

## 1. Start the app on the PC
```bash
docker compose up --build -d
docker compose run --rm migrate qbank create-platform-admin --email you@example.com --name "Your Name"
```
Check `http://localhost:3000` works on the PC first.

## 2. Route the subdomain to the web app
The web app forwards `/api/v1/*` and `/health/*` to the API itself (ADR-0014), so the tunnel only
needs **one** rule: `qb.loveemittal.online` → `http://localhost:3000`.

- **Tunnel managed in the Cloudflare dashboard:** Zero Trust → Networks → Tunnels → your tunnel →
  Public Hostname → Add: subdomain `qb`, domain `loveemittal.online`, service `HTTP` `localhost:3000`.
- **Tunnel with a `config.yml`:** add above the final catch-all rule, then restart `cloudflared`:
  ```yaml
    - hostname: qb.loveemittal.online
      service: http://localhost:3000
  ```
  and create the DNS record: `cloudflared tunnel route dns <tunnel-name> qb.loveemittal.online`.
- If `cloudflared` itself runs in Docker, use `http://host.docker.internal:3000` instead of `localhost`.

## 3. Tell the app about the address
In `.env` next to `compose.yaml` (keep the single quotes), then `docker compose up -d`:
```env
ALLOWED_ORIGINS='["http://localhost:3000","https://qb.loveemittal.online"]'
SESSION_COOKIE_SECURE=true
CLIENT_IP_HEADER=CF-Connecting-IP
```
- `ALLOWED_ORIGINS`: changes are accepted only from these web addresses (Origin check).
- `SESSION_COOKIE_SECURE=true`: the site is https through Cloudflare; browsers still accept secure
  cookies on `http://localhost`.
- `CLIENT_IP_HEADER`: Cloudflare puts the visitor's real IP in this header, so sign-in limits apply
  per visitor instead of to everyone together. Only set it when traffic comes through Cloudflare.

## 4. Keep it private: Cloudflare Access
Zero Trust → Access → Applications → Add → Self-hosted: application domain `qb.loveemittal.online`;
policy *Allow* with *Emails* = your address. Visitors then prove their email with a one-time code
before Cloudflare lets them through to the app's own sign-in.

## 5. Check
1. `https://qb.loveemittal.online/health/ready` → `{"status":"ok",...}`
2. `https://qb.loveemittal.online/` → sign-in page → sign in → home page shows your name and health.
3. Sign out → back to sign-in.
