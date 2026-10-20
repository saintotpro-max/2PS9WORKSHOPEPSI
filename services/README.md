# Services du perimetre dev (paiement, moteur, simulateur)

Trois services FastAPI, lances avec `uv`. Fausse monnaie, faux clients ; aucun secret dans le
depot. Doc d'API detaillee : `docs/api/plateforme.md`. Contrat : `contrats/resilience-alpha.openapi.yaml`.

| Service | Role | Port (dev) | Mode |
|---|---|---|---|
| `paiement` | plateforme de paiement reelle (SQLite, sante honnete) | 8770 | reel |
| `moteur` | remediation reelle (liste blanche, reprise mesuree, zero-touch) | 8772 | reel |
| `simulateur` | orchestration non encore livree par les collegues + `/simulation/*` | 8765 | simule |

## Lancer

Tout d'un coup, en mode MIXTE (plateforme reelle + simulateur pour le reste) :

```bash
scripts/lancer-reel.sh      # paiement 8770, simulateur 8765, moteur 8772, jeu en mode mixte
scripts/arreter.sh          # arret force de tout ce qui a ete lance
```

Un service seul, a la main :

```bash
cd services/paiement && uv run uvicorn main:app --port 8770
cd services/moteur   && ALPHA_PLATEFORME_URL=http://127.0.0.1:8770 ALPHA_CIBLES=alpha-paiement \
                        uv run uvicorn main:app --port 8772
cd services/simulateur && uv run uvicorn main:app --port 8765
```

En conteneur (plateforme seule, pour l'infra) : `compose.yaml` publie le paiement sur 8780
(port interne 8000).

## Bascule simule / reel : un seul fichier

Le jeu et le moteur lisent `config/interfaces.json` (ou le fichier pointe par `ALPHA_CONFIG`).
Basculer = changer ce fichier, rien d'autre :

- `config/interfaces.json` : tout en `simule` (plateforme = simulateur 8765).
- `config/interfaces.reel.json` : plateforme et moteur en `reel` (8770 / 8772), le reste simule.

`scripts/lancer-reel.sh` exporte `ALPHA_CONFIG=config/interfaces.reel.json` pour le jeu.

## Variables d'environnement

| Variable | Service | Defaut | Role |
|---|---|---|---|
| `ALPHA_DB` | paiement | `services/paiement/paiement.db` | fichier SQLite |
| `ALPHA_USERS` | paiement | `demo:demo,caissier:caisse,soc:soc` | clients de demo (fausse monnaie) |
| `ALPHA_PLATEFORME_URL` | moteur | `http://127.0.0.1:8780` | cible des verifications de reprise |
| `ALPHA_CIBLES` | moteur | `alpha-paiement` | conteneurs qu'il peut redemarrer (liste blanche) |
| `ALPHA_DEMO_USER` / `ALPHA_DEMO_PASS` | moteur | `demo` / `demo` | identifiants de la transaction de verification |
| `ALPHA_CONFIG` | jeu | `config/interfaces.json` | fichier de bascule simule/reel |
| `ATTAQUE_FILS` / `ATTAQUE_DUREE_S` | arsenal reel | `40` / `20` | intensite et duree de la charge (bornees) |
| `ALPHA_PERIMETRE` | arsenal reel | `192.168.137.0/24` | reseau autorise (plus localhost) ; hors de la, attaque refusee |

## Tests (preuve, un fichier par service)

Chacun demarre son service puis rejoue un cas reel. Resume d'une ligne, code de sortie.

```bash
# avec le service deja lance sur son port
uv run --no-project python services/paiement/smoke.py http://127.0.0.1:8770
uv run --no-project python services/moteur/smoke.py   http://127.0.0.1:8772   # moteur avec ALPHA_PLATEFORME_URL joignable
uv run --no-project python services/simulateur/smoke.py http://127.0.0.1:8765
```

Le smoke du moteur exige une plateforme joignable (il mesure la reprise contre elle) et
`ALPHA_CIBLES` contenant `alpha-paiement`. Prouve le 2026-10-19 : paiement 10/10, moteur 9/9.
