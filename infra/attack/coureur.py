"""Pilote de la vague : surveille le compteur de participation et déclenche une
charge BORNÉE quand l'opérateur arme la vague. La charge (fils bornés, périmètre
verrouillé) est dans _commun.lancer. Lab uniquement, cible = plateforme du lab.

L'opérateur peut arrêter la vague en cours (bouton Arrêter) : la phase repasse à
« termine »/« repos », ce pilote coupe alors la charge immédiatement.
"""
import json
import os
import threading
import time
import urllib.error
import urllib.request

import _commun
from _commun import arreter, fils_depuis_compteur, lancer

COMPTEUR = os.environ.get("ALPHA_VAGUE_COMPTEUR", "http://127.0.0.1:8088/participation/etat")


def etat():
    try:
        with urllib.request.urlopen(COMPTEUR, timeout=4) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def main():
    print(json.dumps({"service": "coureur-vague", "message": "en attente d'armement",
                      "compteur": COMPTEUR}), flush=True)
    armee = False
    charge = None
    while True:
        e = etat()
        if e is None:
            time.sleep(2)
            continue
        phase = e.get("phase")
        if phase == "en_cours" and not armee:
            armee = True
            n = fils_depuis_compteur(e.get("total", 0))
            cible = e.get("cible")                 # cible choisie au cockpit (None = cible par défaut)
            print(json.dumps({"service": "coureur-vague", "message": "vague déclenchée",
                              "participants": e.get("total", 0), "fils": n,
                              "cible": cible or "(defaut)"}), flush=True)
            charge = threading.Thread(target=lancer,
                                      args=(1, "Vague pilotée par le public (charge bornée)", n, cible),
                                      daemon=True)
            charge.start()
        elif phase in ("repos", "termine"):
            if armee:                              # arrêt (naturel ou opérateur) : on coupe
                arreter()                          # lancer() joint ses threads avant de rendre la main
                if charge:
                    charge.join(timeout=10)
                print(json.dumps({"service": "coureur-vague", "message": "vague arrêtée"}), flush=True)
            armee = False
            charge = None
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
