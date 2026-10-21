"""Primitive de charge bornée — RÉUTILISÉE de l'équipe DEV (2PS9WORKSHOPEPSI,
attack/arsenal/_commun.py), avec deux ajouts d'intégration : contexte TLS pour le
certificat autosigné du WAF, et garde de périmètre strict.

Garde-fous conservés : la cible DOIT être dans ALPHA_PERIMETRE (une seule /24, la
plateforme du lab) sinon l'exécution est refusée ; le nombre de fils est borné
(plancher/plafond). Outil de démonstration de résilience, lab uniquement.
"""
import http.client
import ipaddress
import json
import os
import signal
import ssl
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

DUREE_S = float(os.environ.get("ATTAQUE_DUREE_S", "25"))
FILS = int(os.environ.get("ATTAQUE_FILS", "40"))
PLANCHER_FILS = int(os.environ.get("ATTAQUE_FILS_MIN", "20"))
PLAFOND_FILS = int(os.environ.get("ATTAQUE_FILS_MAX", "200"))
FILS_PAR_PARTICIPANT = int(os.environ.get("ATTAQUE_FILS_PAR_PARTICIPANT", "4"))
RAMPE_S = float(os.environ.get("ATTAQUE_RAMPE_S", "15"))   # montée progressive de la charge
# Garde-fou : arrêt automatique au bout de ce délai même si on oublie (sécurité).
# La vague s'arrête normalement à la demande de l'opérateur (bouton Arrêter).
DUREE_MAX_S = float(os.environ.get("ATTAQUE_DUREE_MAX_S", "600"))
CIBLE_URL = os.environ.get("ALPHA_PLATEFORME_URL", "").rstrip("/")
# Pool d'IP sources : chaque fil se lie à une de ces IP (secondaires sur l'interface WAN)
# pour que la sonde voie PLUSIEURS sources distinctes. Vide = source unique (défaut OS).
POOL_IP = [ip.strip() for ip in os.environ.get("ATTAQUE_IP_POOL", "").split(",") if ip.strip()]

_SSL = ssl._create_unverified_context()          # WAF à certificat autosigné (lab)
_arret = threading.Event()
_compteur = dict(envoyees=0, erreurs=0)
_verrou = threading.Lock()


def arreter():
    """Interrompt immédiatement une charge en cours (bouton Arrêter)."""
    _arret.set()


def fils_depuis_compteur(total) -> int:
    try:
        total = max(0, int(total))
    except (TypeError, ValueError):
        total = 0
    return max(PLANCHER_FILS, min(PLAFOND_FILS, PLANCHER_FILS + FILS_PAR_PARTICIPANT * total))


def cible_autorisee(hote: str) -> bool:
    """Vrai seulement si l'hôte est dans le périmètre autorisé (plateforme du lab)."""
    try:
        adresse = ipaddress.ip_address(hote)
    except ValueError:
        return hote == "localhost"
    reseau = ipaddress.ip_network(os.environ.get("ALPHA_PERIMETRE", "192.168.137.0/24"))
    return adresse.is_loopback or adresse in reseau


def _ouvrir(url, timeout=5):
    ctx = _SSL if url.startswith("https") else None
    return urllib.request.urlopen(url, timeout=timeout, context=ctx)


def _requete_source(url: str, src, timeout=3) -> None:
    """GET `url` en se liant à l'IP source `src` (None = source par défaut).
    http.client expose source_address, contrairement à urllib.request."""
    p = urlsplit(url)
    port = p.port or (443 if p.scheme == "https" else 80)
    chemin = p.path or "/"
    sa = (src, 0) if src else None
    if p.scheme == "https":
        c = http.client.HTTPSConnection(p.hostname, port, context=_SSL, timeout=timeout, source_address=sa)
    else:
        c = http.client.HTTPConnection(p.hostname, port, timeout=timeout, source_address=sa)
    try:
        c.request("GET", chemin)
        c.getresponse().read()
    finally:
        c.close()


def _marteau(url: str, stop: threading.Event, src=None) -> None:
    # Timeout court : à l'arrêt, le thread sort vite au lieu de rester bloqué.
    cible = url + "/health"
    while not stop.is_set():
        try:
            _requete_source(cible, src, timeout=3)
            with _verrou:
                _compteur["envoyees"] += 1
        except (http.client.HTTPException, OSError):
            with _verrou:
                _compteur["erreurs"] += 1


def normaliser_cible(valeur: str) -> str:
    """Accepte 'ip', 'ip:port' ou 'http(s)://...' et renvoie une URL https par défaut."""
    valeur = (valeur or "").strip()
    if not valeur:
        return ""
    if "://" not in valeur:
        valeur = "https://" + valeur
    return valeur.rstrip("/")


def lancer(niveau: int, nom: str, n_fils: int | None = None, cible: str | None = None) -> int:
    actifs = n_fils if n_fils else FILS
    # Cible par vague (choisie au cockpit) si fournie, sinon la cible configurée.
    # Dans tous les cas, le garde-fou de périmètre ci-dessous tranche.
    url = normaliser_cible(cible) if cible else CIBLE_URL
    hote = url.split("//")[-1].split("/")[0].split(":")[0]
    print("[REEL] niveau %d : %s" % (niveau, nom), flush=True)
    print("[REEL] cible : %s" % url, flush=True)
    if not url or not cible_autorisee(hote):
        print("ERREUR : cible hors perimetre autorise (%s) : charge refusee" % hote, flush=True)
        return 3
    try:
        t0 = time.time()
        with _ouvrir(url + "/health", timeout=3) as r:
            r.read()
    except (urllib.error.URLError, OSError) as e:
        print("ERREUR : plateforme injoignable avant la charge : %s" % e, flush=True)
        return 1
    print("[REEL] latence /health de reference : %d ms" % int((time.time() - t0) * 1000), flush=True)
    print("[REEL] montee sur %ds jusqu'a %d fils, jusqu'a l'arret (max %ds)"
          % (RAMPE_S, actifs, DUREE_MAX_S), flush=True)

    # Event d'arrêt PROPRE à cette vague : partagé avec _arret global pour le bouton,
    # mais on JOINT les threads avant de rendre la main -> aucune fuite de thread.
    _arret.clear()
    stop = threading.Event()
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
    fils = []
    debut = time.time()
    while not stop.is_set() and not _arret.is_set() and time.time() - debut < DUREE_MAX_S:
        ecoule = time.time() - debut
        # Montée linéaire : du plancher jusqu'à la cible sur RAMPE_S secondes
        cible = actifs if RAMPE_S <= 0 else PLANCHER_FILS + int(
            (actifs - PLANCHER_FILS) * min(1.0, ecoule / RAMPE_S))
        while len(fils) < cible:
            # Chaque fil se lie à une IP du pool (round-robin) -> N sources distinctes.
            src = POOL_IP[len(fils) % len(POOL_IP)] if POOL_IP else None
            t = threading.Thread(target=_marteau, args=(url, stop, src), daemon=True)
            t.start()
            fils.append(t)
        time.sleep(1.0)
        with _verrou:
            n = _compteur["envoyees"]
        print("[REEL] +%ds : %d fils actifs, %d requetes" % (int(ecoule), len(fils), n), flush=True)

    stop.set()                                   # on coupe...
    for f in fils:                               # ...et on ATTEND la fin de chaque thread
        f.join(timeout=4)
    with _verrou:
        print("[REEL] fin : %d requetes, %d erreurs, %d fils arretes"
              % (_compteur["envoyees"], _compteur["erreurs"], len(fils)), flush=True)
    return 0
