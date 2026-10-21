#!/usr/bin/env bash
# Test automatique EX-08 sur le MIROIR : alerte -> decision -> action reelle
# (redemarrage du conteneur alpha-paiement) -> verification par VRAIE transaction.
# A jouer apres scripts/miroir-lab/lancer-miroir.sh, avec REMEDIATION_TOKEN defini.
set -u
WAF="https://127.0.0.1:8783"
REMEDIATION_TOKEN="${REMEDIATION_TOKEN:-$(cat /tmp/miroir-token 2>/dev/null)}"
if [ -z "$REMEDIATION_TOKEN" ]; then echo "KO : jeton absent"; exit 1; fi
KO=0

dire() { echo "$1"; }
verifier() { # $1 description, $2 code retour
  if [ "$2" -eq 0 ]; then dire "  ok : $1"; else dire "  ECHEC : $1"; KO=1; fi
}

dire "== 1. Santes =="
curl -sk -o /dev/null "$WAF/health"; verifier "WAF mock repond (https autosigne)" $?
curl -s -o /dev/null http://127.0.0.1:8781/health; verifier "moteur reel repond" $?

dire "== 2. Transaction de base via le point d'entree =="
TOK=$(curl -sk -X POST "$WAF/auth/token" -H 'content-type: application/json' \
  -d '{"username":"demo","password":"demo"}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("access_token",""))')
curl -sk -o /dev/null -w '%{http_code}' -X POST "$WAF/transactions" -H 'content-type: application/json' \
  -H "authorization: Bearer $TOK" \
  -d '{"amount_cents":150,"currency":"EUR","payer":"test-miroir","payee":"boutique-fictive"}' \
  | grep -q 201; verifier "transaction acceptee (201) via le WAF" $?

dire "== 3. Alerte Alertmanager -> remediatiation reelle =="
curl -sk -o /dev/null -X POST "$WAF/dashboard/api/remediation/alerts" \
  -H 'content-type: application/json' -H "authorization: Bearer $REMEDIATION_TOKEN" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"ServiceApplicatifEnPanne","service":"paiement","severity":"high"},"annotations":{"summary":"test miroir EX-08"},"startsAt":"'"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"'"}]}'
verifier "webhook accepte" $?

dire "== 4. Attente de la reprise verifiee (max 70 s) =="
RESOLU=0
for _ in $(seq 1 35); do
  curl -sk "$WAF/dashboard/api/remediation/status" -o /tmp/miroir-poll.json 2>>/tmp/miroir-poll.err
  if python3 -c 'import json, sys
try:
    d = json.load(open("/tmp/miroir-poll.json"))
    ok = any(i.get("status") == "resolved" and i.get("recovery_seconds") is not None
             for i in d.get("recent", []))
    sys.exit(0 if ok else 1)
except Exception as e:
    open("/tmp/miroir-poll.err", "a").write("poll: %s\n" % e)
    sys.exit(1)'; then RESOLU=1; break; fi
  sleep 2
done
verifier "incident resolu avec reprise mesuree" $((1 - RESOLU))

curl -sk "$WAF/dashboard/api/remediation/events" | python3 -c '
import json, sys
ev = json.load(sys.stdin)
etapes = [e.get("step") for e in ev]
print("  etapes vues :", ", ".join(sorted(set(etapes))))
print("  action :", next((e["message"] for e in reversed(ev) if e.get("step") == "action"), "?"))
print("  verification :", next((e["message"] for e in reversed(ev) if e.get("step") == "verification"), "?"))'

dire "== 5. Garde-fou : cible hors liste blanche refusee =="
curl -sk -o /dev/null -X POST "$WAF/dashboard/api/remediation/alerts" \
  -H 'content-type: application/json' -H "authorization: Bearer $REMEDIATION_TOKEN" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"ServiceApplicatifEnPanne","service":"base","severity":"high"},"annotations":{"summary":"test garde-fou"},"startsAt":"'"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"'"}]}'
sleep 4
curl -sk "$WAF/dashboard/api/remediation/events" | grep -q 'non autoris'; verifier "redemarrage de la base refuse par le moteur" $?

if [ "$KO" -eq 0 ]; then dire "EX-08 MIROIR : OK (chaine reelle locale complete)"; else dire "EX-08 MIROIR : KO"; fi
exit $KO
