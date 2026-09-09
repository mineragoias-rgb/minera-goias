#!/bin/bash
set -euo pipefail
state=/var/lib/minera-goias-ingestion
exec 9>"$state/import.lock"
flock -n 9 || exit 0
release=$(readlink -f /srv/minera-goias/current)
commit=${release##*/}
[[ "$release" == /srv/minera-goias/releases/* && "$commit" =~ ^[0-9a-f]{40}$ ]]
if [[ -f "$state/last-successful-commit" ]] && [[ $(cat "$state/last-successful-commit") == "$commit" ]]; then
    exit 0
fi
/opt/minera-goias-ingestion/bin/python /usr/local/lib/minera-goias-ingestion/import_repository.py \
    --root "$release" --repo-id mineragoias-rgb/minera-goias --commit "$commit" \
    --mysql --report "$state/latest.json"
printf '%s\n' "$commit" > "$state/last-successful-commit.tmp"
mv "$state/last-successful-commit.tmp" "$state/last-successful-commit"
