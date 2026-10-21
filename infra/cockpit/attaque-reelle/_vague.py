"""Déclencheur de vague pour le cockpit Ren'Py (mode réel).

Ce script tourne sur le PC HÔTE (lancé par le jeu). Il ne génère AUCUNE charge :
il se contente d'ARMER la vague sur le service de participation de ra-attacker.
La charge, bornée et à périmètre verrouillé, est produite par ra-attacker lui-même.

Variable d'environnement : RA_PARTICIPATION (défaut http://192.168.80.50:8088).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try:                                    # accents lisibles même sur une console Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BASE = os.environ.get("RA_PARTICIPATION", "http://192.168.80.50:8088").rstrip("/")
# Cible choisie au cockpit (IP/URL de la plateforme). Vide = cible par défaut de
# ra-attacker. Le périmètre reste vérifié côté charge : hors zone => refusée.
CIBLE = os.environ.get("RA_CIBLE", "").strip()


def post(chemin):
    req = urllib.request.Request(BASE + chemin, data=b"", method="POST")
    with urllib.request.urlopen(req, timeout=4) as r:
        return json.loads(r.read().decode())


def armer():
    chemin = "/participation/armer"
    if CIBLE:
        chemin += "?" + urllib.parse.urlencode({"cible": CIBLE})
    return post(chemin)


def etat():
    with urllib.request.urlopen(BASE + "/participation/etat", timeout=4) as r:
        return json.loads(r.read().decode())


def lancer(nom):
    print(f"$ {nom}", flush=True)
    print(f"[VAGUE] service de participation : {BASE}", flush=True)
    if CIBLE:
        print(f"[VAGUE] cible choisie au cockpit : {CIBLE}", flush=True)
    try:
        armer()
    except OSError as e:
        print(f"ERREUR : participation injoignable : {e}", flush=True)
        return 1
    phase_vue = None
    while True:
        try:
            e = etat()
        except OSError:
            time.sleep(1)
            continue
        ph = e.get("phase")
        if ph != phase_vue:
            if ph == "decompte":
                print(f"[VAGUE] {e.get('total', 0)} participant(s) — départ dans {e.get('decompte')} s", flush=True)
            elif ph == "en_cours":
                print(f"[VAGUE] >>> vague en cours ({e.get('restant')} s) - charge envoyee sur la plateforme", flush=True)
            elif ph == "termine":
                print("[VAGUE] vague terminée — observez la reprise automatique sur le dashboard", flush=True)
                return 0
            phase_vue = ph
        elif ph == "en_cours":
            print(f"[VAGUE] +{e.get('restant')} s restant", flush=True)
        time.sleep(2)
