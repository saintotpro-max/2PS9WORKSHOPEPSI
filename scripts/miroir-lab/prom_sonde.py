#!/usr/bin/env python3
"""Sonde Prometheus de fortune pour le MIROIR local du lab.

Ce service joue le role de l'API Prometheus (meme format JSON) mais chaque
requete declenche une VRAIE sonde : une transaction reelle bout-en-bout pour
txn_probe_success, un vrai GET /health pour probe_success. En lab, ces mesures
viennent du vrai Prometheus et de la sonde txn-probe : ici on emule le tuyau,
pas le resultat (le resultat est mesure pour de vrai).

Routes : GET /api/v1/query?query=<expr>
Mode SIMULE affiche dans chaque reponse (champ metric.source=miroir).
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8782"))
# La sonde passe par le point d'entree du miroir (WAF mock, TLS autosigne).
CIBLE = os.environ.get("PROBE_URL", "https://127.0.0.1:8783")
UTILISATEUR = os.environ.get("PROBE_USER", "demo")
MOT_DE_PASSE = os.environ.get("PROBE_PASSWORD", "demo")
_CTX = ssl._create_unverified_context()


def _appel(chemin, corps=None, jeton=None):
    donnees = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(CIBLE + chemin, data=donnees, method="POST" if corps is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    if jeton:
        req.add_header("Authorization", "Bearer " + jeton)
    with urllib.request.urlopen(req, timeout=6, context=_CTX) as r:
        return r.status, json.loads(r.read().decode() or "{}")


def txn_probe():
    """Vraie transaction bout-en-bout via le point d'entree. 1 si acceptee."""
    try:
        code, j = _appel("/auth/token", dict(username=UTILISATEUR, password=MOT_DE_PASSE))
        if code != 200:
            return "0"
        code, j = _appel("/transactions", dict(amount_cents=105, currency="EUR",
                                               payer="sonde-miroir", payee="boutique-fictive",
                                               idempotency_key="miroir-%d" % int(time.time() * 1000)),
                         jeton=j.get("access_token"))
        return "1" if code == 201 and j.get("status") == "accepted" else "0"
    except Exception:
        return "0"


def health_probe():
    try:
        code, _ = _appel("/health")
        return "1" if code == 200 else "0"
    except Exception:
        return "0"


def evaluer(expr):
    e = expr.strip()
    if "txn_probe_success" in e:
        return [dict(metric=dict(source="miroir", probe="transaction"), value=[int(time.time()), txn_probe()])]
    if "probe_success" in e:
        return [dict(metric=dict(source="miroir", probe="http"), value=[int(time.time()), health_probe()])]
    if "ips_attack_probability_max" in e:
        return [dict(metric=dict(source="miroir"), value=[int(time.time()), "0.12"])]
    if "ips_blocks_total" in e:
        return [dict(metric=dict(source="miroir"), value=[int(time.time()), "0"])]
    return []          # ALERTS_FOR_STATE et inconnues : resultat vide (honnete)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/api/v1/query":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(u.query).get("query", [""])[0]
        corps = dict(status="success", data=dict(resultType="vector", result=evaluer(q)))
        brut = json.dumps(corps).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(brut)))
        self.end_headers()
        self.wfile.write(brut)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("prom_sonde miroir sur %d, cible %s" % (PORT, CIBLE), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
