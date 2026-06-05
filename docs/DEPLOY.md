# Deployment — CAD Trust Engine Lite (v0.1.4+)

This doc covers deploying the Streamlit demo to a Vultr (or any Linux) VPS via
Docker + Caddy reverse proxy.

## Architecture

```
              Internet
                 │
                 ▼  :80 / :443  (Caddy listens, auto-TLS via Let's Encrypt if DOMAIN set)
       ┌─────────────────────┐
       │   caddy (alpine)    │
       │   reverse proxy     │
       │   + auto-TLS        │
       └──────────┬──────────┘
                  │ :8501 over docker bridge network 'app_net'
                  ▼
       ┌─────────────────────┐
       │ cad-trust-streamlit │
       │ python:3.12-slim    │
       │ paddleocr + opencv  │
       │ Streamlit on :8501  │
       └──────────┬──────────┘
                  │
                  ▼
        named volume `audit_data` mounted at /data
        (audit.sqlite persists across compose down/up)
```

Both services run on a single VPS via `docker compose`. No CI/CD, no
Kubernetes — single-host orchestration for v0.1.4.

## Prerequisites

1. **Vultr VPS** (or any Debian 12 / Ubuntu 22.04+ Linux host)
   - **Minimum:** 1GB RAM + 2GB swap (cheap tier with bootstrap.sh swap creation)
   - **Recommended:** 2-4GB RAM (paddleocr + opencv inference comfortable)
   - 20GB+ disk (Docker images + corpus + audit DB)
2. **SSH key** — local: `~/.ssh/id_ed25519_aio_deploy` (or any ed25519 key)
3. **Domain** — *optional*. With a domain pointed at the VPS, Caddy auto-issues
   a Let's Encrypt cert. Without a domain, Caddy serves plain HTTP on `:80`
   accessed by IP. **Both modes work for the 포비콘 demo.**

## Deploy in 4 commands

### Step 1 — Add your public key to the VPS

If you provisioned the VPS with a different key, add the deploy key:

```bash
# Run this from your local machine
PUBKEY=$(cat ~/.ssh/id_ed25519_aio_deploy.pub)
ssh user@your.vps.ip "echo '$PUBKEY' >> ~/.ssh/authorized_keys"
```

### Step 2 — Bootstrap the VPS (one-shot, idempotent)

Installs Docker + ufw + creates 2GB swap + prepares `/opt/cad-tel/`:

```bash
ssh -i ~/.ssh/id_ed25519_aio_deploy user@your.vps.ip 'bash -s' \
    < deploy/bootstrap.sh
```

This is safe to re-run — the script skips anything already done.

### Step 3 — Deploy

```bash
# IP-only access (no domain, no TLS)
./deploy/deploy.sh user@your.vps.ip

# With a domain (auto-TLS via Let's Encrypt)
./deploy/deploy.sh user@your.vps.ip --domain cad-tel.example.com
```

The script:
1. `rsync`s the repo to `/opt/cad-tel/` on the VPS
2. Writes `DOMAIN` to `/opt/cad-tel/.env`
3. `docker compose up -d --build`
4. Polls the streamlit healthcheck up to 180s
5. Curls the public URL and verifies HTTP 200 + body contains `"CAD Trust Engine"`
6. Prints the final public URL

### Step 4 — Verify

Visit:

- `http://your.vps.ip` (IP-only mode), or
- `https://cad-tel.example.com` (with domain)

You should see the **CAD Trust Engine Lite** landing page with two tabs:
**Run Engine** and **Past Runs (Audit)**.

## What the deploy does NOT touch

- The mounted `audit_data` volume — audit.sqlite is **never** overwritten
- Caddy's `caddy_data` volume — TLS certs survive (no Let's Encrypt rate-limit risk)
- Existing host services (sshd, ufw rules already in place)

## Rollback

If a deploy goes wrong, the previous container image is still on the host:

```bash
ssh user@your.vps.ip
cd /opt/cad-tel
docker compose down                    # stop current
docker image ls cad-trust              # see previous tagged images
docker compose up -d --no-build        # bring back the previous image
                                        # (if no prior tag exists, run deploy.sh again with old git commit)
```

The audit volume is preserved across `down` / `up`, so historical refusal data
is not lost during rollback.

## Secrets handling

- **No `.env` is committed to the repo.** `deploy.sh` generates `/opt/cad-tel/.env`
  on the VPS at deploy time.
- The current `.env` only carries `DOMAIN`. If future features need API keys
  (e.g., VLM_Verify), add them as environment variables in `.env` on the VPS,
  reference them in `docker-compose.yml`, and update this doc.
- `.streamlit/secrets.toml` is excluded by `.dockerignore` and `.gitignore` —
  Streamlit secrets are loaded from the VPS-side file if present.

## Resource considerations

- **Memory.** `docker-compose.yml` sets `mem_limit: 2g` on the streamlit container.
  PaddleOCR + opencv inference can spike close to that on the most complex
  drawings (the audit DB shows one Wikimedia drawing produced 20,267 objects).
  If OOM kills happen, upgrade to a higher VPS tier or reduce the inference
  load via cap'd input size.
- **Swap.** `bootstrap.sh` creates a 2GB swap file. Without it, paddleocr
  install can fail mid-pip on small VPS tiers.
- **Cold-start latency.** The first OCR call after a container restart downloads
  paddleocr model weights (~500MB). Subsequent calls reuse the cached models.
  Document this as "first run is slow" for demo visitors.
- **Disk.** Docker images + corpus + audit DB easily fit in 20GB. If the audit DB
  grows large (rare in v0.1.x; we have no retention policy yet), monitor
  `du -sh /var/lib/docker/volumes/deploy_audit_data/`.

## Roadmap

- **v0.2** — CI/CD pipeline (GitHub Actions deploy on push to `main`)
- **v0.2** — Audit DB backup / restore script (cron rsync to S3 or similar)
- **v0.3** — Multi-tenant separation (per-domain audit DBs)
- **v0.3** — Auth gate (basic-auth or OAuth) for non-public demo deployments
- **v0.3** — Prometheus / Grafana metrics export

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `deploy.sh` fails at "step 1 — SSH" | Public key not in `authorized_keys` on VPS | Add via `ssh-copy-id` or `>> authorized_keys` |
| `docker compose up` OOM during build | Insufficient RAM during `pip install paddlepaddle` | Ensure 2GB swap is active (`swapon --show`) |
| Healthcheck never goes `healthy` | Streamlit failed at startup | `ssh ... docker logs cad-trust-streamlit` |
| HTTP 200 but body lacks "CAD Trust Engine" | Caddy proxying to wrong upstream | Check `Caddyfile` `reverse_proxy streamlit:8501` |
| Let's Encrypt rate-limit error | Repeated cert issuance attempts | Caddy stores certs in `caddy_data` volume — do NOT recreate it |

See [`docs/AUDIT.md`](AUDIT.md) for querying the live audit DB on the VPS.
