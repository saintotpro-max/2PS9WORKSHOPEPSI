#!/usr/bin/env bash
# MIROIR local du lab : rejoue la chaine reelle sur ce poste.
#   paiement conteneurise (compose, port 8780)
#   + VRAI moteur de remediation (infra/services/remediation, port 8781)
#   + sonde Prometheus de fortune (scripts/miroir-lab/prom_sonde.py, 8782)
#   + WAF mock HTTPS autosigne (scripts/miroir-lab/waf_mock.py, 8783)
# En lab, 8781 = socket-proxy-ctrl + vrai Prometheus + vrai WAF nginx/ModSecurity :
# les contrats sont identiques, seuls les tuyaux changent.
set -u
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RACINE" || exit 1

veiller() { curl -sk -o /dev/null "$1" && { echo "$2 repond deja"; return 0; }
  ( eval "$3" ) >/dev/null 2>&1 &
  for _ in $(seq 1 30); do curl -sk -o /dev/null "$1" && { echo "$2 pret"; return 0; }; sleep 1; done
  echo "ECHEC : $2"; return 1; }

# 1. Docker via TCP (le moteur parle HTTP, comme au socket-proxy du lab)
if ! curl -sk -o /dev/null http://127.0.0.1:2375/v1.44/version; then
  setsid nohup socat TCP-LISTEN:2375,bind=127.0.0.1,reuseaddr,fork \
    UNIX-CONNECT:/var/run/docker.sock >/tmp/socat.log 2>&1 &
  sleep 1
fi

# 2. Paiement conteneurise, labels compose attendus par le moteur
docker compose -p platform up -d --build >/dev/null 2>&1 || { echo "ECHEC compose"; exit 1; }

# 3. Certificat autosigne (jetable, hors depot) + jeton local (hors depot)
if [ ! -f /tmp/miroir-cert.pem ]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 7 -subj "/CN=miroir-lab" \
    -keyout /tmp/miroir-cle.pem -out /tmp/miroir-cert.pem >/dev/null 2>&1
fi
if [ -z "${REMEDIATION_TOKEN:-}" ]; then
  REMEDIATION_TOKEN="$(openssl rand -hex 16)"
  export REMEDIATION_TOKEN
  printf '%s' "$REMEDIATION_TOKEN" > /tmp/miroir-token
fi

# 4. Services du miroir
veiller http://127.0.0.1:8782/healthz sonde-prom \
  "PORT=8782 PROBE_URL=https://127.0.0.1:8783 setsid nohup python3 scripts/miroir-lab/prom_sonde.py > /tmp/miroir-prom.log 2>&1" || true
veiller http://127.0.0.1:8781/health moteur-reel \
  "RULES_FILE=infra/services/remediation/rules.yml DOCKER_HOST=tcp://127.0.0.1:2375 \
PROMETHEUS_URL=http://127.0.0.1:8782 COMPOSE_PROJECT=platform \
STATE_FILE=/tmp/miroir-remediation-state.json \
setsid nohup /tmp/remvenv/bin/uvicorn main:app --app-dir infra/services/remediation/app --host 127.0.0.1 --port 8781 > /tmp/miroir-moteur.log 2>&1"
veiller https://127.0.0.1:8783/health waf-mock \
  "PORT=8783 setsid nohup python3 scripts/miroir-lab/waf_mock.py > /tmp/miroir-waf.log 2>&1"

echo
echo "Miroir pret :"
echo "  paiement  : http://127.0.0.1:8780 (conteneur alpha-paiement)"
echo "  moteur    : http://127.0.0.1:8781 (infra/services/remediation, REEL)"
echo "  prom sonde: http://127.0.0.1:8782 (mesures reelles, tuyau emule)"
echo "  WAF mock  : https://127.0.0.1:8783 (TLS autosigne, comme le lab)"
echo "  jeton     : /tmp/miroir-token (hors depot)"
echo "Test : REMEDIATION_TOKEN=\$(cat /tmp/miroir-token) bash scripts/miroir-lab/test-ex08.sh"
