# Matrice attaque -> detection -> decision -> action -> verification

Reference : sujet p.3 (ne pas confondre *restaurer la disponibilite* et *corriger une
compromission* ; attaque reproductible et expliquee) ; `analyse-manques.md` M4. Source de
comportement : simulateur (`services/simulateur/main.py`, `RECOMMANDATION`/`REGLE_WAF`) et moteur
reel (`services/moteur/main.py`, liste blanche + `verifier_reprise`). Chaque ligne est rejouee par
le jeu (menu attaquant) et par les tests.

Les trois verifications de reprise sont les memes pour toutes les lignes (moteur, mesurees,
jamais ok sans preuve) : **API accessible** (`/health` = ok), **transaction de test** reussie,
**donnees coherentes** (la transaction ecrite est relisible). `reprise_ok` seulement si les trois.

| Attaque (jeu) | Type | Detection (detecteur IA) | Decision (reco, confiance) | Action moteur (liste blanche) | Verification / nuance |
|---|---|---|---|---|---|
| Saturer les paiements | dos (charge applicative) | pic de requetes, 5xx en hausse, score > seuil | `rate_limit` (0.91) | `rate_limit` ou `restart_service` | 3 verifications ; disponibilite restauree |
| Epuiser les ressources | dos (connexions lentes) | connexions ouvertes anormales | `restart_service` (0.84) | `restart_service` | 3 verifications ; disponibilite restauree |
| Saturer le reseau | dos (SYN flood) | flux SYN massif depuis une seule source | `block_source` (0.88) | `block_source` | 3 verifications ; source isolee |
| Injecter une requete | injection (SQL/HTTP) | motifs d'injection repetes, WAF bloque | `block_source` (0.95) | `block_source` (regle WAF) | **ne PAS redemarrer** : on BLOQUE et on VERIFIE (correction de compromission, pas restauration) ; le service reste sain |
| Panne non malveillante | chaos (conteneur tue/ralenti) | sante degradee sans signature d'attaque | `restart_service` | `restart_service` | 3 verifications ; reprise d'une panne, pas d'une attaque |

Garde-fous : cible hors `ALPHA_CIBLES` -> action refusee (jamais executee) ; perimetre des scripts
d'attaque limite a 192.168.137.0/24 + localhost ; zero intervention humaine (R-01) ; mode simule
toujours affiche. La distinction cle du sujet (p.3) est la ligne **injection** : restaurer la
disponibilite (redemarrer) ne corrige pas une compromission ; on bloque la source et on verifie.
