



import json
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
echecs = []


def appel(methode, chemin, corps=None, jeton=None):
    donnees = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(BASE + chemin, data=donnees, method=methode,
                                 headers={"Content-Type": "application/json"})
    if jeton:
        req.add_header("Authorization", "Bearer " + jeton)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.load(r), r.headers.get("X-Mode")
    except urllib.error.HTTPError as e:
        return e.code, json.load(e), e.headers.get("X-Mode")


def etape(nom, condition):
    print(("OK  " if condition else "KO  ") + nom)
    if not condition:
        echecs.append(nom)


TX = dict(amount_cents=1250, currency="EUR", payer="client-fictif", payee="boutique-fictive")

appel("POST", "/simulation/reset")
code, corps, mode = appel("POST", "/auth/token", dict(username="demo", password="demo"))
etape("jeton obtenu, mode simulé affiché", code == 200 and mode == "simule" and corps["mode"] == "simule")
jeton = corps["access_token"]

code, _, _ = appel("POST", "/transactions", TX)
etape("transaction sans jeton refusée (401)", code == 401)
code, _, _ = appel("POST", "/transactions", TX, jeton)
etape("transaction avant attaque acceptée (201)", code == 201)
etape("santé ok avant attaque", appel("GET", "/health")[1]["status"] == "ok")

appel("POST", "/simulation/attaque", dict(niveau=1, detection_s=1, reprise_s=2))
code, _, _ = appel("POST", "/transactions", TX, jeton)
etape("transaction pendant l'attaque refusée (503, jamais de faux succès)", code == 503)
etape("santé dégradée pendant l'attaque", appel("GET", "/health")[1]["status"] == "degraded")

time.sleep(1.5)
etape("alerte reçue après détection", len(appel("GET", "/alerts")[1]["alerts"]) == 1)
etape("santé à l'arrêt pendant la reprise", appel("GET", "/health")[1]["status"] == "down")

time.sleep(2.2)
code, _, _ = appel("POST", "/transactions", TX, jeton)
etape("transaction après reprise automatique acceptée (201)", code == 201)
etape("santé ok après reprise", appel("GET", "/health")[1]["status"] == "ok")
types = [e["type"] for e in appel("GET", "/events")[1]["events"]]
etape("journal complet : dégradation, alerte, action, rétablissement",
      types == ["service_degraded", "alert_received", "action_started", "action_done", "service_recovered"])
etape("composants tous ok après reprise",
      all(c["status"] == "ok" for c in appel("GET", "/components")[1]["components"]))
code, corps, _ = appel("POST", "/assistant/ask", dict(question="Que se passe-t-il ?"))
etape("assistant répond avec sources, mode simulé annoncé", code == 200 and corps["sources"] and corps["mode"] == "simule")

scores = appel("GET", "/scores")[1]["scores"]
etape("série de scores disponible, au-dessus du seuil pendant l'attaque",
      len(scores) > 3 and any(x["score"] > x["threshold"] and x["label"] == "attaque" for x in scores))
code, corps, _ = appel("POST", "/events", dict(type="attack_started", component="payment-api", detail="niveau 1", source="attaquant"))
etape("événement déclaré par l'attaquant accepté (202)", code == 202)
etape("événement déclaré présent dans le journal avec sa source",
      any(e["type"] == "attack_started" and e["source"] == "attaquant" for e in appel("GET", "/events")[1]["events"]))
code, _, _ = appel("POST", "/events", dict(type="alert_received", component="x", detail="x", source="attaquant"))
etape("un faux événement d'alerte déclaré est refusé (422)", code == 422)
def brut(chemin):
    with urllib.request.urlopen(BASE + chemin, timeout=10) as r:
        return r.read().decode()
c1, c2 = brut("/simulation/export.csv?graine=7&duree=60"), brut("/simulation/export.csv?graine=7&duree=60")
etape("export CSV identique pour une même graine, avec étiquettes",
      c1 == c2 and "attaque" in c1 and "normal" in c1 and c1.splitlines()[0].startswith("at,requetes_par_s"))


appel("POST", "/simulation/reset")
appel("POST", "/simulation/attaque", dict(niveau=4, detection_s=1, reprise_s=1))
time.sleep(2.2)
etape("injection : le service reste sain", appel("GET", "/health")[1]["status"] == "ok")
bloques = appel("GET", "/flux-bloques")[1]
etape("injection : des flux sont bloqués avec leur règle", bloques["total"] > 0 and bloques["blocked"][-1]["rule"] == "injection SQL")
alertes = appel("GET", "/alerts")[1]["alerts"]
etape("l'alerte porte une recommandation (action, confiance)",
      len(alertes) == 1 and alertes[0]["recommendation"]["suggested_action"] == "block_source" and alertes[0]["recommendation"]["confidence"] > 0.5)
etape("vérifications de reprise toutes ok quand le service est sain",
      all(v["status"] == "ok" for v in appel("GET", "/verifications")[1]["verifications"]))

for _niv, _regle in ((5, "authentification en force"), (6, "contrôle d'accès (IDOR)")):
    appel("POST", "/simulation/reset")
    appel("POST", "/simulation/attaque", dict(niveau=_niv, detection_s=1, reprise_s=1))
    time.sleep(2.2)
    etape("OWASP niveau %d : le service reste sain (bloqué, pas de panne)" % _niv,
          appel("GET", "/health")[1]["status"] == "ok")
    bloques = appel("GET", "/flux-bloques")[1]
    etape("OWASP niveau %d : des flux sont bloqués avec la bonne règle" % _niv,
          bloques["total"] > 0 and bloques["blocked"][-1]["rule"] == _regle)
    alertes = appel("GET", "/alerts")[1]["alerts"]
    etape("OWASP niveau %d : alerte avec recommandation" % _niv,
          len(alertes) == 1 and alertes[0]["recommendation"]["suggested_action"] in ("block_source", "rate_limit", "restart_service", "scale_up", "none"))
appel("POST", "/simulation/reset")
appel("POST", "/simulation/attaque", dict(niveau=1, detection_s=6, reprise_s=6))
time.sleep(0.5)
v = {x["name"]: x["status"] for x in appel("GET", "/verifications")[1]["verifications"]}
etape("pendant l'attaque : API et transaction en échec, jamais ok sans mesure", v["api_accessible"] == "ko" and v["transaction_test"] == "ko")
appel("POST", "/simulation/arret")
time.sleep(2.0)
etape("après l'arrêt de l'attaquant : le service revient sain sans alerte", appel("GET", "/health")[1]["status"] == "ok" and appel("GET", "/alerts")[1]["alerts"] == [])
total = appel("GET", "/flux-bloques")[1]["total"]; time.sleep(1.5)
etape("après l'arrêt : plus de nouveaux flux bloqués", appel("GET", "/flux-bloques")[1]["total"] == total)


appel("POST", "/participation/reset")
e = appel("GET", "/participation/etat")[1]
etape("participation au repos : total 0, phase repos", e["total"] == 0 and e["phase"] == "repos")
for _ in range(3):
    appel("POST", "/participation/rejoindre")
e = appel("GET", "/participation/etat")[1]
etape("trois scans comptés (le POST n'incrémente qu'un entier)", e["total"] == 3)
appel("POST", "/participation/armer", dict(duree_s=5))
e = appel("GET", "/participation/etat")[1]
etape("vague armée : décompte ouvert, compteur conservé", e["phase"] == "ouvert" and e["decompte"] > 0 and e["total"] == 3)
appel("POST", "/participation/rejoindre")
etape("on peut encore rejoindre pendant le décompte", appel("GET", "/participation/etat")[1]["total"] == 4)
with urllib.request.urlopen(BASE + "/participation/qr.png", timeout=10) as r:
    png = r.read()
etape("QR servi en PNG (segno)", r.headers.get("Content-Type") == "image/png" and png[:8] == b"\x89PNG\r\n\x1a\n")
etape("page de participation sert le bouton « Rejoindre la vague »", "Rejoindre la vague" in brut("/participation"))

print("\n%s : %d étape(s) en échec" % ("ÉCHEC" if echecs else "SUCCÈS", len(echecs)))
sys.exit(1 if echecs else 0)
