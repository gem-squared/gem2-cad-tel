#!/usr/bin/env bash
# CAD Trust Engine Lite — VPS bootstrap (one-shot, idempotent)
#
# Invoke from local machine:
#   ssh -i ~/.ssh/id_ed25519_aio_deploy user@HOST 'bash -s' < deploy/bootstrap.sh
#
# Installs Docker + ufw, configures firewall, creates 2GB swap, prepares
# /opt/cad-tel directory tree. Idempotent — second run is a no-op.

set -euo pipefail

SWAPFILE=/swapfile
SWAP_SIZE_MB=2048
APP_DIR=/opt/cad-tel
DATA_DIR=${APP_DIR}/data

log() { printf "\033[1;34m[bootstrap]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[bootstrap WARN]\033[0m %s\n" "$*"; }
die() { printf "\033[1;31m[bootstrap FATAL]\033[0m %s\n" "$*" >&2; exit 1; }

require_sudo() {
    if [[ $EUID -ne 0 ]]; then
        if ! sudo -n true 2>/dev/null; then
            die "this script needs sudo (passwordless) — re-run as root or with passwordless sudo"
        fi
        SUDO="sudo"
    else
        SUDO=""
    fi
}

wait_for_apt_lock() {
    local max_wait=60
    while $SUDO fuser /var/lib/apt/lists/lock >/dev/null 2>&1 \
       || $SUDO fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
        log "another apt process is running; waiting (max ${max_wait}s)..."
        sleep 5
        max_wait=$((max_wait - 5))
        if [[ $max_wait -le 0 ]]; then
            die "apt lock held for >60s — aborting; re-run after the other process completes"
        fi
    done
}

install_docker() {
    if command -v docker >/dev/null 2>&1 && docker --version >/dev/null 2>&1; then
        log "Docker already installed: $(docker --version)"
        return
    fi
    log "installing Docker (docker.io + docker-compose-plugin) via apt..."
    wait_for_apt_lock
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq docker.io docker-compose-plugin
    $SUDO systemctl enable --now docker
    log "Docker installed: $(docker --version)"
}

install_utilities() {
    local need=()
    command -v ufw >/dev/null 2>&1   || need+=(ufw)
    command -v rsync >/dev/null 2>&1 || need+=(rsync)
    command -v curl >/dev/null 2>&1  || need+=(curl)
    if [[ ${#need[@]} -eq 0 ]]; then
        log "utilities already present (ufw, rsync, curl)"
        return
    fi
    log "installing utilities: ${need[*]}"
    wait_for_apt_lock
    $SUDO apt-get install -y -qq "${need[@]}"
}

configure_ufw() {
    if $SUDO ufw status | grep -q "Status: active"; then
        log "ufw already active; ensuring required ports are open"
    else
        log "configuring ufw..."
    fi
    $SUDO ufw allow 22/tcp comment 'SSH' >/dev/null 2>&1 || true
    $SUDO ufw allow 80/tcp comment 'HTTP (Caddy)' >/dev/null 2>&1 || true
    $SUDO ufw allow 443/tcp comment 'HTTPS (Caddy)' >/dev/null 2>&1 || true
    if ! $SUDO ufw status | grep -q "Status: active"; then
        log "enabling ufw (yes y will be sent automatically)"
        $SUDO ufw --force enable
    fi
    log "ufw status:"
    $SUDO ufw status numbered | sed 's/^/  /'
}

setup_swap() {
    if [[ -f $SWAPFILE ]]; then
        log "swap file already exists at $SWAPFILE"
        return
    fi
    log "creating ${SWAP_SIZE_MB}MB swap file at $SWAPFILE..."
    $SUDO fallocate -l "${SWAP_SIZE_MB}M" "$SWAPFILE"
    $SUDO chmod 600 "$SWAPFILE"
    $SUDO mkswap "$SWAPFILE"
    $SUDO swapon "$SWAPFILE"
    if ! grep -qE "^${SWAPFILE}\s" /etc/fstab; then
        log "adding fstab entry for swap..."
        echo "$SWAPFILE none swap sw 0 0" | $SUDO tee -a /etc/fstab > /dev/null
    fi
    log "swap active:"
    swapon --show | sed 's/^/  /'
}

prepare_app_dirs() {
    log "creating $APP_DIR (and child dirs)..."
    $SUDO mkdir -p "$APP_DIR" "$DATA_DIR"
    # Make the deploying user the owner so rsync can write without sudo each time
    local owner_user=${SUDO_USER:-${USER:-$(whoami)}}
    if [[ -n "$owner_user" && "$owner_user" != "root" ]]; then
        $SUDO chown -R "$owner_user":"$owner_user" "$APP_DIR"
        log "  owner: $owner_user"
    fi
}

add_user_to_docker_group() {
    local target_user=${SUDO_USER:-${USER:-$(whoami)}}
    if [[ -z "$target_user" || "$target_user" == "root" ]]; then
        log "deploy user is root; skipping docker-group add"
        return
    fi
    if groups "$target_user" | grep -qw docker; then
        log "$target_user already in docker group"
        return
    fi
    log "adding $target_user to docker group (takes effect on next login)..."
    $SUDO usermod -aG docker "$target_user"
}

summary() {
    log "=== bootstrap summary ==="
    log "Docker:         $(docker --version 2>/dev/null || echo 'NOT FOUND')"
    log "Compose plugin: $(docker compose version 2>/dev/null | head -1 || echo 'NOT FOUND')"
    log "ufw:            $($SUDO ufw status | head -1)"
    log "Swap:           $(free -m | awk '/^Swap:/ {print $2 \"MB total, \" $3 \"MB used\"}')"
    log "RAM:            $(free -m | awk '/^Mem:/ {print $2 \"MB total, \" $3 \"MB used, \" $7 \"MB available\"}')"
    log "App dir:        $APP_DIR ($(stat -c '%U:%G' "$APP_DIR" 2>/dev/null || echo 'unknown owner'))"
    log "=== bootstrap COMPLETE ==="
}

main() {
    log "starting bootstrap on $(hostname) ($(. /etc/os-release && echo \"$PRETTY_NAME\"))"
    require_sudo
    install_docker
    install_utilities
    configure_ufw
    setup_swap
    prepare_app_dirs
    add_user_to_docker_group
    summary
}

main "$@"
