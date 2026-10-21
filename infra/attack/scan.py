"""Générateur de trafic de RECONNAISSANCE (scan) — LAB AUTORISÉ UNIQUEMENT.

But : produire des flux de SCAN *étiquetés* pour (ré)entraîner le détecteur IPS à
reconnaître la reconnaissance — une classe que le modèle attend (`Reconnaissance`)
mais que le jeu de données actuel ne contient pas. Ce script ne sert qu'à générer du
trafic contre la plateforme DU LAB, pendant que la sonde `ra-ips` capture en
`ips-label reconnaissance`.

Méthode : connect-scan TCP en pur Python (pas de nmap, pas de root). Pour chaque port
d'une liste BORNÉE, on ouvre une connexion brève puis on la ferme. Un port joignable
(ex. 443 exposé) donne un flux court « SYN → SYN/ACK → RST/FIN » ; un port filtré par
pfSense donne un SYN sans réponse (timeout) — les deux sont des signatures de recon,
bien distinctes d'un flood HTTP (peu de paquets, peu d'octets, pas de charge utile).

Garde-fous (comme la vague) : la cible DOIT être dans ALPHA_PERIMETRE sinon refus ;
liste de ports bornée ; nombre de passes borné ; cadence lente (un scan, pas un flood).
"""
import os
import random
import socket
import struct
import sys
import time

import _commun

try:                                    # accents lisibles même sur une console Windows
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

CIBLE = _commun.normaliser_cible(os.environ.get("ALPHA_PLATEFORME_URL", ""))
# Ports du lab à sonder (bornés) : point d'entrée + ports d'admin/observabilité typiques
# qu'un attaquant testerait. Seuls les ports réellement joignables génèrent un flux complet.
PORTS = [int(p) for p in os.environ.get(
    "SCAN_PORTS", "22,80,443,3000,3100,5432,8080,9090,9100,9101").split(",") if p.strip()]
PASSES = int(os.environ.get("SCAN_PASSES", "40"))          # nb de passes (borné)
PASSES = max(1, min(PASSES, 200))                          # plafond dur
DELAI_MS = int(os.environ.get("SCAN_DELAI_MS", "150"))     # cadence : un scan, pas un flood
TIMEOUT = float(os.environ.get("SCAN_TIMEOUT", "1.0"))     # timeout court par port


def hote_de(url: str) -> str:
    return url.split("//")[-1].split("/")[0].split(":")[0]


# Styles de sonde : chacun laisse une empreinte de flux DIFFÉRENTE (nb de paquets,
# octets, drapeaux) pour produire un jeu de reconnaissance VARIÉ, pas 38 lignes
# identiques. Tous bénins : aucune charge d'exploitation, juste des formes de connexion.
STYLES = ["connect", "donnees", "tls_hello", "rst", "trickle"]


def sonder(hote: str, port: int, style: str) -> str:
    """Une connexion brève (style variable) : 'ouvert', 'ferme' (RST) ou 'filtre'."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(TIMEOUT)
    try:
        r = s.connect_ex((hote, port))
        if r != 0:
            return "filtre" if r in (10060, 110) else "ferme"
        try:
            if style == "donnees":                     # envoi d'octets aléatoires -> sbytes variable
                s.sendall(os.urandom(random.randint(40, 500)))
                s.recv(256)
            elif style == "tls_hello":                 # début de ClientHello TLS tronqué
                n = random.randint(20, 200)
                s.sendall(b"\x16\x03\x01" + struct.pack(">H", n) + os.urandom(n))
                s.recv(512)
            elif style == "trickle":                   # quelques octets espacés -> dur plus longue
                for _ in range(random.randint(2, 5)):
                    s.sendall(os.urandom(random.randint(8, 40)))
                    time.sleep(random.uniform(0.05, 0.2))
            elif style == "rst":                        # fermeture par RST (SO_LINGER 0)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            # style "connect" : on ne fait rien, fermeture propre (FIN)
        except OSError:
            pass
        return "ouvert"
    except OSError:
        return "filtre"
    finally:
        try:
            s.close()
        except OSError:
            pass


def main() -> int:
    hote = hote_de(CIBLE)
    print("[SCAN] cible : %s (hote %s)" % (CIBLE, hote), flush=True)
    if not CIBLE or not _commun.cible_autorisee(hote):
        print("ERREUR : cible hors perimetre autorise (%s) : scan refuse" % hote, flush=True)
        return 3
    print("[SCAN] %d passes x %d ports, cadence %d ms — lab uniquement" % (PASSES, len(PORTS), DELAI_MS),
          flush=True)
    total = 0
    for passe in range(1, PASSES + 1):
        if _commun._arret.is_set():                        # bouton Arrêter partagé avec la vague
            print("[SCAN] arret demande", flush=True)
            break
        etats = {}
        for port in PORTS:
            etat = sonder(hote, port, random.choice(STYLES))   # style varié -> flux divers
            etats[etat] = etats.get(etat, 0) + 1
            total += 1
            time.sleep(DELAI_MS / 1000.0)
        print("[SCAN] passe %d/%d : %s" % (passe, PASSES, etats), flush=True)
    print("[SCAN] fin : %d connexions de reconnaissance emises" % total, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
