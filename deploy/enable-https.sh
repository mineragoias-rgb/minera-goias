#!/bin/bash
set -euo pipefail
# Use the existing Let's Encrypt account. Do not request a certificate until
# both names resolve exclusively to this VPS.
python3 - <<'PY'
import socket
for name in ['labfgv.com.br', 'www.labfgv.com.br']:
    try:
        addresses = {x[4][0] for x in socket.getaddrinfo(name, 80)}
    except socket.gaierror:
        print('Waiting for DNS:', name)
        raise SystemExit(1)
    if addresses != {'187.77.3.27'}:
        print('Waiting for correct DNS:', name)
        raise SystemExit(1)
PY
certbot --nginx --non-interactive --redirect --cert-name labfgv.com.br -d labfgv.com.br -d www.labfgv.com.br
nginx -t
curl -fsS --resolve labfgv.com.br:443:127.0.0.1 https://labfgv.com.br/ >/dev/null
systemctl disable --now minera-goias-https.timer
