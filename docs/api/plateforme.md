# API de la plateforme reelle (paiement + moteur)

Source de verite : `contrats/resilience-alpha.openapi.yaml`. Ce document decrit les routes
REELLES servies par les deux services de code du perimetre dev : la plateforme de paiement
(`services/paiement`) et le moteur de remediation (`services/moteur`). Le simulateur
(`services/simulateur`) expose les memes contrats plus les routes `/simulation/*` ; voir son
propre code. Prouve le 2026-10-19 par `services/paiement/smoke.py` et `services/moteur/smoke.py`
(0 echec).

Toutes les reponses portent le champ `mode` (`reel` ici). Fausse monnaie, faux clients ;
aucune vraie valeur, aucun secret dans le depot (jeton opaque, aleatoire, garde en memoire).

## Plateforme de paiement (`services/paiement`, port 8770)

Persistance reelle en SQLite. La sante est HONNETE : `ok` seulement si une ecriture puis une
lecture reelles passent dans la base ; jamais de faux `ok`.

| Methode | Chemin | Auth | Corps / parametres | Reponse |
|---|---|---|---|---|
| POST | `/auth/token` | non | `{username, password}` | 200 `{access_token, token_type, mode}` ; 401 si refuse |
| GET | `/health` | non | - | 200 `{status: ok\|down, last_transaction_ok, checked_at, mode}` |
| POST | `/transactions` | Bearer | `{amount_cents>=1, currency:"EUR", payer, payee, idempotency_key?}` | 201 transaction ; 401 sans jeton ; 503 si base degradee |
| GET | `/transactions/{id}` | Bearer | - | 200 transaction ; 401 sans jeton ; 404 si inconnue |
| GET | `/metrics` | non | - | 200 texte Prometheus (voir plus bas) |
| GET | `/` | non | - | 200 frontal HTML (caisse de demonstration) |

Transaction renvoyee : `{id, amount_cents, currency, payer, payee, status:"accepted", created_at, mode}`.

Idempotence : deux POST avec la meme `idempotency_key` renvoient la MEME transaction (pas de
doublon). Verifie par le smoke.

Metriques exposees (`/metrics`) : `alpha_transactions_total{issue="ok"|"refus"}`,
`alpha_auth_total{issue="ok"|"refus"}`, `alpha_requests_total`. Compteurs en memoire, remis a
zero au redemarrage du conteneur (evenement visible, voulu).

Clients de demonstration (fausse monnaie) : par defaut `demo:demo`, `caissier:caisse`,
`soc:soc`. Surchargeables par `ALPHA_USERS` pour ne jamais figer d'identifiant dans le depot.

## Moteur de remediation (`services/moteur`, port 8772)

Recoit une alerte, choisit une action dans une LISTE BLANCHE, l'execute sur une cible
AUTORISEE seulement, puis MESURE la reprise par de vraies verifications. Zero-touch.

| Methode | Chemin | Corps / parametres | Reponse |
|---|---|---|---|
| POST | `/alerts` | voir `AlerteEntree` | 202 compte rendu de remediation (voir plus bas) |
| GET | `/verifications` | - | 200 `{verifications, mode}` (dernieres mesures) |
| GET | `/events` | - | 200 `{events, mode}` (journal, 50 derniers) |
| GET | `/health` | - | 200 `{status, last_transaction_ok, checked_at, mode}` |
| GET | `/metrics` | - | 200 texte Prometheus |

`AlerteEntree` : `{source, kind, severity, score?, target, detail?, recommendation?}` avec
`recommendation = {summary?, suggested_action?, confidence?, rationale?}`.

Choix de l'action : la `suggested_action` du detecteur est VALIDEE contre la liste blanche
`restart_service, block_source, rate_limit, scale_up, none` ; sinon repli deterministe par
type (`dos`/`anomaly` -> `restart_service`, `injection` -> `block_source`). Une cible hors
`ALPHA_CIBLES` est REFUSEE (jamais executee) : garde-fou verifie par le smoke.

Compte rendu (202) : `{id, action, action_ok, action_detail, verifications, reprise_ok, mode}`.

Verifications de reprise (MESUREES, jamais ok sans preuve), dans l'ordre :
1. `api_accessible` : `/health` de la plateforme = `ok`.
2. `transaction_test` : une vraie transaction de test passe (auth + POST /transactions).
3. `donnees_coherentes` : la transaction ecrite est relisible.

`reprise_ok` vaut vrai seulement si les trois sont `ok` (EX-08 REPRISE_OK). Prouve par le smoke :
une alerte `injection` sur `alpha-paiement`, plateforme joignable, donne `reprise_ok = true`.

Metriques (`/metrics`) : `alpha_moteur_alertes_total`, `alpha_moteur_actions_total`,
`alpha_moteur_reprises_total{issue="ok"|"ko"}`.

Acces Docker RESTREINT : le moteur ne fait que `docker restart` sur les conteneurs listes dans
`ALPHA_CIBLES` ; aucune autre commande. `restart_service` sans Docker disponible echoue
proprement (`action_ok = false`), sans fausser la mesure de reprise.

## Bascule simule / reel

Un seul fichier change : `config/interfaces*.json`. Voir `services/README.md`.
