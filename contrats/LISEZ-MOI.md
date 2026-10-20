# Contrats d'interface RESILIENCE-ALPHA

Fichier de référence : `resilience-alpha.openapi.yaml` (OpenAPI 3.0.3). À transmettre aux collègues.

## Qui implémente quoi

| Interface | Routes | Implémenté par | Consommé par |
|---|---|---|---|
| Plateforme de paiement | `/auth/token`, `/health`, `/transactions` | l'utilisateur | jeu (cockpit), attaque |
| Moteur de remédiation | `/alerts`, `/events`, `/components` | l'utilisateur | jeu (cockpit) ; reçoit les alertes de la détection |
| Détection (ML, WAF, SIEM) | envoie `POST /alerts` au moteur | **collègue IA** (ML), **collègue infra** (WAF, SIEM) | moteur de remédiation |
| Assistant RAG | `/assistant/ask` | **collègue IA** | jeu |
| Recommandation IA | champ `recommendation` de l'alerte (`POST /alerts`) : résumé, action suggérée, confiance | **collègue IA** | poste SOC et salle de contrôle ; le moteur ne l'exécute que si l'action est dans sa liste blanche |
| Flux bloqués | `GET /flux-bloques` (source, règle, nombre, cible) | **collègue infra** (WAF, SIEM) | salle de contrôle |
| Vérifications de reprise | `GET /verifications` (API accessible, opération métier, données cohérentes) | l'utilisateur (moteur) | poste SOC |
| Scores d'anomalie | `/scores` | **collègue IA** | salle de contrôle (courbe en direct) |
| Événements déclarés | `POST /events` (type `attack_started` ou `attack_ended`, source `attaquant`) | le poste attaquant l'envoie, le moteur l'enregistre | salle de contrôle ; ne remplace jamais l'alerte de détection |
| Métriques | `/metrics` (format Prometheus) sur la plateforme | l'utilisateur expose, **collègue infra** collecte | Prometheus, Grafana |

## Ce que les collègues doivent respecter
- Chaque réponse porte `mode` (`simule` ou `reel`). Une vraie implémentation répond toujours `reel`.
- Pas de faux succès : un service dégradé répond 503, pas 201.
- L'assistant informe, il ne répare pas ; une réponse lente reste une attente, jamais un texte écrit à l'avance.
- Métriques exposées par la plateforme : `payment_requests_total{status}`, `payment_request_duration_seconds`, `payment_up`.

## Vérifier qu'un service respecte le contrat
Outil retenu pour les tests de conformité : Schemathesis (licence MIT, à vérifier à l'installation).
Exemple prévu : `schemathesis run contrats/resilience-alpha.openapi.yaml --url http://localhost:8080`.

## Mode simulé ou réel
Le simulateur (`services/simulateur`) imite ces routes tant que les services réels ne sont pas livrés. Il répond toujours `mode: simule` et l'affiche dans l'en-tête `X-Mode`. Démonstration, clip et jury : réel uniquement.
