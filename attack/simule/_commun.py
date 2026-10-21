





import ipaddress
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DUREE_S = float(os.environ.get("ATTAQUE_DUREE_S", "20"))



COMMANDES = {
    1: "locust --headless --users 200 --spawn-rate 50 -H {url}",
    2: "slowloris {hote} -s 500 --sleeptime 5",
    3: "hping3 -S --flood -p {port} {hote}",
    4: "sqlmap -u {url}/transactions --batch --level 3",
    5: "hydra -l demo -P rockyou.txt {hote} http-post-form '/auth/token'",
    6: "ffuf -u {url}/transactions/FUZZ -w ids.txt -mc 200",
}


def cible_autorisee(hote: str) -> bool:

    try:
        adresse = ipaddress.ip_address(hote)
    except ValueError:
        return hote == "localhost"
    reseau = ipaddress.ip_network(os.environ.get("ALPHA_PERIMETRE", "192.168.137.0/24"))
    return adresse.is_loopback or adresse in reseau


def _poster(base: str, chemin: str, corps: dict) -> None:
    requete = urllib.request.Request(base.rstrip("/") + chemin, data=json.dumps(corps).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(requete, timeout=5) as r:
        print("[SIMULE] %s -> %d" % (chemin, r.status), flush=True)


def lancer(niveau: int, nom: str) -> int:
    chemin = os.environ.get("ALPHA_CONFIG") or os.path.join(RACINE, "config", "interfaces.json")
    with open(chemin, encoding="utf-8") as f:
        conf = json.load(f)
    # L'attaque simulee vise le simulateur (routes /simulation/*), pas la vraie plateforme.
    url = conf.get("attaque", {}).get("cible_simulee") or conf["plateforme"]["url"]
    hote_port = url.split("//")[-1].split("/")[0]
    hote, _, port = hote_port.partition(":")
    print("[SIMULE] niveau %d : %s" % (niveau, nom), flush=True)
    print("[SIMULE] cible : %s" % url, flush=True)
    if not cible_autorisee(hote):
        print("ERREUR : cible hors périmètre autorisé (%s) : attaque refusée" % hote, flush=True)
        return 3
    commande = COMMANDES[niveau].format(url=url, hote=hote, port=port or "80")
    print("[SIMULE] $ %s   (imitation : aucun outil lancé)" % commande, flush=True)

    def arreter(*_):
        print("[SIMULE] arrêt reçu : l'attaque cesse", flush=True)
        try:
            _poster(url, "/simulation/arret", {})
        except (urllib.error.URLError, OSError):
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, arreter)
    try:
        _poster(url, "/simulation/attaque", {"niveau": niveau})
    except (urllib.error.URLError, OSError) as e:
        print("ERREUR : plateforme injoignable : %s" % e, flush=True)
        return 1
    debut = time.time()
    while time.time() - debut < DUREE_S:
        time.sleep(min(2.0, max(0.1, DUREE_S - (time.time() - debut))))
        print("[SIMULE] attaque en cours depuis %d s" % (time.time() - debut), flush=True)
    try:
        _poster(url, "/simulation/arret", {})
    except (urllib.error.URLError, OSError):
        pass
    print("[SIMULE] fin de l'outil (durée prévue atteinte)", flush=True)
    return 0


def principal(niveau: int, nom: str) -> None:
    sys.exit(lancer(niveau, nom))
