#!/usr/bin/env bash


set -u
RACINE="$(cd "$(dirname "$0")/.." && pwd)"

# URL du QR vue par le public : IP LAN du poste (127.0.0.1 ne marche que sur place).
# En lab, l'URL du tunnel cloudflared reste la meilleure : ALPHA_VAGUE_URL la surcharge.
if [ -z "${ALPHA_VAGUE_URL:-}" ]; then
  IP_PUBLIQUE=$(hostname -I | tr ' ' '\n' | grep -E '^(10\.|192\.168\.)' | grep -v '^192\.168\.49\.' | head -1)
  [ -n "$IP_PUBLIQUE" ] && export ALPHA_VAGUE_URL="http://$IP_PUBLIQUE:${PORT:-8765}/participation"
fi
SDK="${RENPY_SDK:-$HOME/.local/opt/renpy-8.5.3-sdk}"
PORT=8765
if curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then
  echo "Un service répond déjà sur le port $PORT : j'utilise celui-là."
else
  ( cd "$RACINE/services/simulateur" && exec setsid nohup uv run uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level warning > /tmp/simulateur.log 2>&1 ) &
  for _ in $(seq 1 40); do curl -s -o /dev/null "http://127.0.0.1:$PORT/health" && break; sleep 1; done
fi
curl -s "http://127.0.0.1:$PORT/health" | head -c 200; echo
( exec setsid nohup "$SDK/renpy.sh" "$RACINE/renpy" > /tmp/jeu.log 2>&1 ) &
echo "Jeu lancé. Arrêt : scripts/arreter.sh"
