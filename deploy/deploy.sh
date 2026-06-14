#!/usr/bin/env bash
# CAD Trust Engine Lite — idempotent deploy to a Vultr VPS
#
# Usage:
#   ./deploy/deploy.sh user@host [--key PATH] [--domain DOMAIN]
#
# Example:
#   ./deploy/deploy.sh root@1.2.3.4 \
#       --key ~/.ssh/id_ed25519_aio_deploy \
#       --domain cad-tel.example.com
#
# Steps:
#   1. rsync repo → /opt/cad-tel on VPS (respects deploy/.dockerignore semantics)
#   2. write DOMAIN to /opt/cad-tel/.env (or empty if --domain not provided)
#   3. ssh: docker compose -f deploy/docker-compose.yml up -d --build
#   4. wait up to 180s for streamlit healthcheck
#   5. smoke: curl the public URL, verify HTTP 200 + body contains 'CAD Trust Engine'
#   6. print live URL + container status

set -euo pipefail

# ── arg parsing ─────────────────────────────────────────────────────────────

SSH_TARGET=""
SSH_KEY="${HOME}/.ssh/id_ed25519_aio_deploy"
DOMAIN=""

usage() {
    cat >&2 <<EOF
usage: $0 user@host [--key PATH] [--domain DOMAIN]

Required:
  user@host        SSH target (e.g. root@203.0.113.42)

Options:
  --key PATH       SSH key path (default: ~/.ssh/id_ed25519_aio_deploy)
  --domain DOMAIN  Domain for auto-TLS (omitted → plain :80 access by IP)

Env:
  SSH_KEY          alternative to --key
  DOMAIN           alternative to --domain
EOF
    exit 2
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --key) SSH_KEY="$2"; shift 2;;
        --domain) DOMAIN="$2"; shift 2;;
        --help|-h) usage;;
        *)
            if [[ -z "$SSH_TARGET" && "$1" =~ ^[^-] ]]; then
                SSH_TARGET="$1"; shift
            else
                printf "unknown arg: %s\n" "$1" >&2
                usage
            fi
            ;;
    esac
done

[[ -n "$SSH_TARGET" ]] || usage
[[ "${SSH_TARGET}" =~ @ ]] || { printf "SSH_TARGET must be user@host (got: %s)\n" "$SSH_TARGET" >&2; exit 2; }

if [[ ! -f "$SSH_KEY" ]]; then
    printf "SSH key not found: %s\n" "$SSH_KEY" >&2
    exit 3
fi

HOST="${SSH_TARGET#*@}"
USER_NAME="${SSH_TARGET%@*}"
APP_DIR=/opt/cad-tel

# ── logging ─────────────────────────────────────────────────────────────────

log() { printf "\033[1;34m[deploy %s]\033[0m %s\n" "$(date +'%H:%M:%S')" "$*" >&2; }
die() { printf "\033[1;31m[deploy FATAL]\033[0m %s\n" "$*" >&2; exit 1; }

# ── derived ─────────────────────────────────────────────────────────────────

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
log "REPO_ROOT=$REPO_ROOT"
log "SSH_TARGET=$SSH_TARGET"
log "SSH_KEY=$SSH_KEY"
log "DOMAIN=${DOMAIN:-(unset — Caddy will serve plain HTTP on :80)}"

SSH_OPTS=(-i "$SSH_KEY" -o StrictHostKeyChecking=accept-new -o BatchMode=yes -o ConnectTimeout=15)
ssh_run() { ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$@"; }

# ── step 1: verify SSH ──────────────────────────────────────────────────────

log "step 1/6 — verifying SSH reachability"
if ! ssh_run "echo ok && uname -s" >/dev/null 2>&1; then
    die "SSH connection to $SSH_TARGET failed (key=$SSH_KEY). Check: (1) host reachable, (2) public key in authorized_keys, (3) firewall on :22 open"
fi
log "    SSH ok"

# ── step 2: rsync repo ──────────────────────────────────────────────────────

log "step 2/6 — rsyncing repo to ${APP_DIR}"
# Exclude heavy / unneeded paths; mirror .dockerignore semantics + a few extras
RSYNC_EXCLUDES=(
    --exclude='.git/'
    --exclude='.venv/'
    --exclude='__pycache__/'
    --exclude='.pytest_cache/'
    --exclude='.ruff_cache/'
    --exclude='.mypy_cache/'
    --exclude='.gem-squared/audit.sqlite*'
    --exclude='.gem-squared/crawl_summary.json'
    --exclude='*.pyc'
    --exclude='.DS_Store'
    --exclude='dist/'
    --exclude='build/'
    --exclude='*.egg-info/'
    --exclude='.streamlit/secrets.toml'
)

# Ensure target dir exists with right owner (bootstrap.sh already did this,
# but be defensive in case deploy runs before bootstrap)
ssh_run "mkdir -p ${APP_DIR}/data && chown -R ${USER_NAME}: ${APP_DIR} 2>/dev/null || true"

rsync -avz --delete \
    "${RSYNC_EXCLUDES[@]}" \
    -e "ssh ${SSH_OPTS[*]}" \
    "${REPO_ROOT}/" \
    "${SSH_TARGET}:${APP_DIR}/" \
    | tail -5
log "    rsync ok"

# ── step 3: write .env on VPS ───────────────────────────────────────────────

log "step 3/6 — writing /opt/cad-tel/.env (DOMAIN binding)"
ssh_run "cat > ${APP_DIR}/.env" <<EOF
DOMAIN=${DOMAIN}
EOF
log "    .env written"

# ── step 4: docker compose up ───────────────────────────────────────────────

log "step 4/6 — docker compose up -d --build (this may take 3-5 min on first deploy)"
ssh_run "cd ${APP_DIR} && docker compose -f deploy/docker-compose.yml --env-file .env up -d --build" 2>&1 | tail -20
log "    compose up ok"

# ── step 5: wait for healthcheck ────────────────────────────────────────────

log "step 5/6 — waiting for streamlit container to become healthy (up to 180s)"
HEALTHY=0
for attempt in $(seq 1 36); do
    sleep 5
    status=$(ssh_run "docker inspect --format='{{.State.Health.Status}}' cad-trust-streamlit 2>/dev/null || echo missing")
    log "    attempt $attempt/36: status=$status"
    if [[ "$status" == "healthy" ]]; then
        HEALTHY=1
        break
    fi
    if [[ "$status" == "missing" || "$status" == "unhealthy" ]]; then
        # Print last lines of container log so the failure is visible
        log "    streamlit not healthy — recent log lines:"
        ssh_run "docker logs --tail=20 cad-trust-streamlit 2>&1" | sed 's/^/        /'
    fi
done

if [[ $HEALTHY -ne 1 ]]; then
    die "streamlit container failed to become healthy within 180s"
fi
log "    healthcheck ok"

# ── step 6: smoke check public URL ──────────────────────────────────────────

if [[ -n "$DOMAIN" ]]; then
    PUBLIC_URL="https://${DOMAIN}"
else
    PUBLIC_URL="http://${HOST}"
fi

log "step 6/6 — smoke-checking public URL: $PUBLIC_URL"
# Allow up to 30s for cert provisioning when domain is set
SMOKE_OK=0
for attempt in $(seq 1 6); do
    sleep 5
    HTTP_CODE=$(curl -s -m 10 -o /tmp/cad-tel-smoke-$$ -w "%{http_code}" "$PUBLIC_URL/" 2>/dev/null || echo "000")
    log "    attempt $attempt/6: HTTP $HTTP_CODE"
    if [[ "$HTTP_CODE" == "200" ]]; then
        if grep -q "CAD Trust Engine" /tmp/cad-tel-smoke-$$; then
            SMOKE_OK=1
            break
        else
            log "    HTTP 200 but body did NOT contain 'CAD Trust Engine' — page render mismatch?"
        fi
    fi
done
rm -f /tmp/cad-tel-smoke-$$

if [[ $SMOKE_OK -ne 1 ]]; then
    die "smoke check failed — $PUBLIC_URL did not return HTTP 200 with expected body"
fi

# ── done ────────────────────────────────────────────────────────────────────

cat >&2 <<EOF

\033[1;32m[deploy SUCCESS]\033[0m

  Public URL:  $PUBLIC_URL
  Container:   docker ps on VPS → 'cad-trust-streamlit' + 'cad-trust-caddy' both running
  Audit DB:    /opt/cad-tel/data/audit.sqlite (persisted volume on VPS)
  Logs:        ssh ${SSH_TARGET} 'docker logs cad-trust-streamlit -f'

  Next:        share $PUBLIC_URL — portfolio live demo URL

EOF
