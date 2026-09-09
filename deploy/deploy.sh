#!/bin/bash
set -euo pipefail
exec 9>/run/lock/minera-goias-deploy.lock
flock -n 9 || exit 0
base=/srv/minera-goias
previous=$(readlink "$base/current" || true)
# DB credentials are supplied by the systemd unit, never stored in Git.
runuser -u minera-goias -- /usr/bin/python3 /usr/local/lib/minera-goias/prepare-release.py
next=$(readlink "$base/current")
if [[ "$next" == "$previous" ]] && systemctl is-active --quiet minera-goias; then
    exit 0
fi
systemctl restart minera-goias || true
healthy=false
for attempt in $(seq 1 30); do
    if curl -fsS --max-time 5 http://127.0.0.1:18141/api/projetos >/dev/null &&
       curl -fsS --max-time 5 http://127.0.0.1:18141/api/projecoes >/dev/null &&
       curl -fsS --max-time 5 http://127.0.0.1:18141/api/fontes >/dev/null; then
        healthy=true
        break
    fi
    sleep 1
done
if [[ "$healthy" != true ]]; then
    if [[ "$previous" == "$base/releases/"* ]] && [[ -d "$previous" ]]; then
        runuser -u minera-goias -- ln -sfn "$previous" "$base/rollback"
        runuser -u minera-goias -- mv -Tf "$base/rollback" "$base/current"
        systemctl restart minera-goias
        echo 'Health check failed; previous release restored' >&2
    else
        systemctl stop minera-goias
    fi
    exit 1
fi
printf 'Published %s\n' "$next"
