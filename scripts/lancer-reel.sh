#!/usr/bin/env bash




set -u
RACINE="$(cd "$(dirname "$0")/.." && pwd)"

# URL du QR vue par le public : IP LAN du poste (127.0.0.1 ne marche que sur place).
# En lab, l'URL du tunnel cloudflared reste la meilleure : ALPHA_VAGUE_URL la surcharge.
if [ -z "${ALPHA_VAGUE_URL:-}" ]; then
  IP_PUBLIQUE=$(hostname -I | tr ' ' '\n' | grep -E '^(10\.|192\.168\.)' | grep -v '^192\.168\.49\.' | head -1)
  [ -n "$IP_PUBLIQUE" ] && export ALPHA_VAGUE_URL="http://$IP_PUBLIQUE:${PORT_SIM:-8765}/participation"
fi
SDK="${RENPY_SDK:-$HOME/.local/opt/renpy-8.5.3-sdk}"
PORT_PAIEMENT=8770
PORT_SIM=8765
# Modele externe (cle hors depot, ~/.config/alpha) : simulateur et duel parlent pour de vrai.
# Le jour de la demonstration : SIM_LLM=0 scripts/lancer-reel.sh
export SIM_LLM="${SIM_LLM:-1}"

lancer_service() {
  local dossier="$1" port="$2" nom="$3"
  if curl -s -o /dev/null "http://127.0.0.1:$port/health"; then
    echo "$nom repond deja sur $port : je l'utilise."
  else
    ( cd "$RACINE/$dossier" && exec setsid nohup uv run uvicorn main:app --host 0.0.0.0 --port "$port" --log-level warning > "/tmp/$nom.log" 2>&1 ) &
    for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$port/health" && break; sleep 1; done
  fi
}

PORT_MOTEUR=8772
lancer_service services/paiement "$PORT_PAIEMENT" paiement
lancer_service services/simulateur "$PORT_SIM" simulateur


if curl -s -o /dev/null "http://127.0.0.1:$PORT_MOTEUR/health"; then
  echo "moteur repond deja sur $PORT_MOTEUR : je l'utilise."
else
  ( cd "$RACINE/services/moteur" && ALPHA_PLATEFORME_URL="http://127.0.0.1:$PORT_PAIEMENT" ALPHA_CIBLES="alpha-paiement" \
      exec setsid nohup uv run uvicorn main:app --port "$PORT_MOTEUR" --log-level warning > /tmp/moteur.log 2>&1 ) &
  for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT_MOTEUR/health" && break; sleep 1; done
fi
echo "paiement reel : $(curl -s http://127.0.0.1:$PORT_PAIEMENT/health | head -c 160)"

export ALPHA_CONFIG="$RACINE/config/interfaces.reel.json"
( exec setsid nohup "$SDK/renpy.sh" "$RACINE/renpy" > /tmp/jeu.log 2>&1 ) &
echo "Jeu lance en mode MIXTE (plateforme reelle). Arret : scripts/arreter.sh"
