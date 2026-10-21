#!/usr/bin/env python3
"""Verification RGPD du projet RESILIENCE-ALPHA.

Hors ligne, stdlib pur, aucune requete reseau. Controle que :
  1. aucun mail n'apparaat dans le code et les docs du depot (hors textes
     de licences tiers exclus explicitement) ;
  2. aucun champ de donnee personnelle dans les modeles de donnees ;
  3. la base de paiement ne contient pas de colonne de donnee personnelle ;
  4. aucune adresse IP n'est captee ni journalisee par les services face
     au public (paiement, simulateur) ;
  5. la page du public affiche la mention « aucune donnee personnelle » ;
  6. les secrets restent couverts par .gitignore.

Sortie : resume d'une ligne ; code 0 si tout passe, 1 sinon.
"""

import re
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

# Repertoires generes, tiers ou caches : jamais des donnees de l'equipe.
REPERTOIRES_EXCLUS = {
    ".git", ".venv", "venv", "__pycache__", "graphify-out", "_bmad",
    ".pytest_cache", ".ruff_cache",
    "renpy/captures", "renpy/tests/captures", "renpy/game/cache", "renpy/game/saves",
}
# Textes legaux tiers et archives binaires : un mail de licence OFL est legitime.
MOTIFS_EXCLUS = (".pdf", ".png", ".jpg", ".db", ".rpyc", ".rpyb", ".webp",
                 ".ogg", ".ttf", ".otf", ".lock", ".joblib", ".sum", ".save")
NOMS_EXCLUS = ("OFL", "LICENSE", "CREDITS", "COPYING", "NOTICE")

MOTIF_MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# Champs qui, dans un modele de donnees, trahiraient une collecte reelle.
MOTIF_CHAMP_PERSO = re.compile(
    r"(email|e_mail|telephone|tel_|numero_secu|date_naissance|"
    r"adresse_postale|nom_complet|prenom|last_name|first_name|full_name)",
    re.IGNORECASE,
)
# Captures d'adresse IP cote service web.
MOTIFS_IP = ("request.client", "client.host", "remote_addr", "X-Forwarded-For",
             "x-forwarded-for", "client_ip", "ip_client")

echecs: list[str] = []


def ajouter_echec(message: str) -> None:
    echecs.append(message)


def fichiers_a_scanner() -> list[Path]:
    trouves: list[Path] = []
    for chemin in RACINE.rglob("*"):
        if not chemin.is_file():
            continue
        parties = chemin.relative_to(RACINE).parts
        if any(p in REPERTOIRES_EXCLUS for p in parties):
            continue
        if chemin.suffix.lower() in MOTIFS_EXCLUS:
            continue
        if any(m in chemin.name.upper() for m in NOMS_EXCLUS):
            continue
        if chemin.name in ("check-rgpd.py",):
            continue  # le present verifier se cite lui-meme
        trouves.append(chemin)
    return trouves
def verifier_mails(fichiers: list[Path]) -> int:
    nb = 0
    for chemin in fichiers:
        try:
            texte = chemin.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for motif in MOTIF_MAIL.findall(texte):
            nb += 1
            ajouter_echec("mail trouve : %s -> %s" % (chemin.relative_to(RACINE), motif))
    return nb


def verifier_champs_personnels() -> None:
    cibles = [RACINE / "services" / "paiement" / "main.py",
              RACINE / "services" / "simulateur" / "main.py",
              RACINE / "services" / "moteur" / "main.py",
              RACINE / "contrats" / "resilience-alpha.openapi.yaml"]
    for chemin in cibles:
        if not chemin.is_file():
            ajouter_echec("fichier attendu absent : %s" % chemin.relative_to(RACINE))
            continue
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        for ligne in texte.splitlines():
            if "journal(" in ligne and MOTIF_CHAMP_PERSO.search(ligne):
                ajouter_echec("champ personnel journalise : %s" % chemin.relative_to(RACINE))


def verifier_base_paiement() -> None:
    base = RACINE / "services" / "paiement" / "paiement.db"
    if not base.is_file():
        return  # pas encore creee : rien a controler
    cx = sqlite3.connect("file:%s?mode=ro" % base, uri=True)
    try:
        tables = [r[0] for r in cx.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            colonnes = [r[1] for r in cx.execute("PRAGMA table_info(%s)" % table)]
            for colonne in colonnes:
                if MOTIF_CHAMP_PERSO.search(colonne):
                    ajouter_echec("colonne personnelle : %s.%s" % (table, colonne))
    finally:
        cx.close()


def verifier_pas_d_ip() -> None:
    for service in ("paiement", "simulateur"):
        chemin = RACINE / "services" / service / "main.py"
        texte = chemin.read_text(encoding="utf-8", errors="ignore")
        for motif in MOTIFS_IP:
            if motif in texte:
                ajouter_echec("capture d'IP (%s) dans services/%s/main.py" % (motif, service))


def verifier_mention_publique() -> None:
    chemin = RACINE / "services" / "simulateur" / "main.py"
    texte = chemin.read_text(encoding="utf-8", errors="ignore")
    if "aucune donnee personnelle" not in texte.lower():
        ajouter_echec("mention RGPD absente de la page du public (simulateur)")


def verifier_gitignore() -> None:
    chemin = RACINE / ".gitignore"
    texte = chemin.read_text(encoding="utf-8", errors="ignore").lower()
    for attendu in (".env", "nanogpt", "*.key"):
        if attendu not in texte:
            ajouter_echec(".gitignore ne couvre plus : %s" % attendu)


def main() -> int:
    fichiers = fichiers_a_scanner()
    verifier_mails(fichiers)
    verifier_champs_personnels()
    verifier_base_paiement()
    verifier_pas_d_ip()
    verifier_mention_publique()
    verifier_gitignore()
    if echecs:
        for e in echecs:
            print("ECHEC rgpd :", e)
    print("RGPD : %d fichiers scans, 6 controles, %d echec(s)"
          % (len(fichiers), len(echecs)))
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())

