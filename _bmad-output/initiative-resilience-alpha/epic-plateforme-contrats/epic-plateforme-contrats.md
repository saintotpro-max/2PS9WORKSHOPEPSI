---
type: epic
title: "La plateforme tourne, ou son simulateur à sa place"
parent: initiative-resilience-alpha
covers: [FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-19, FR-22, FR-26, FR-28, FR-30, FR-32, FR-34, FR-35, FR-39, FR-40]
after: []
assignee: ""
risk: medium
---

# La plateforme tourne, ou son simulateur à sa place

## Description

SI de paiement (API, base, authentification, frontal web), contrats d'interface pour les collègues et simulateur local, basculement simulé ou réel par un seul fichier de configuration.

## Outcome

L'équipe peut développer et démontrer la boucle complète avant que l'infra et l'IA des collègues soient livrées, puis passer en réel sans toucher au code.

## Requirements

- FR-1: un contrat OpenAPI par interface attendue des collègues.
- FR-2: un simulateur qui panne et reprend sans humain.
- FR-3: un fichier de configuration choisit simulé ou réel, le mode est affiché.
- FR-4: la démo n'utilise que le réel.
- FR-5: API de transactions authentifiée.
- FR-6: frontal web de paiement sans le jeu.
- FR-7: santé qui reflète la capacité réelle à traiter une transaction.
- FR-22: trafic normal et attaques étiquetés, export CSV pour le détecteur.
- FR-19: README, doc d'API et tests dans le dépôt livré, sans secret en clair.

## Done when

1. Une transaction réelle réussit depuis le navigateur.
2. Le simulateur répond aux contrats et reprend après une attaque simulée.
3. Passer de simulé à réel ne change qu'un fichier de configuration.
4. La santé n'est pas saine tant qu'une transaction ne réussit pas.
5. Une seule commande lance les tests ; le README suffit à relancer la plateforme.

## Boundaries

Cœur métier et simulateur. Pas la supervision, la détection ni l'assistant (collègues).

## References

- parent — _bmad-output/initiative-resilience-alpha/prd-perimetre-dev-cyber-jeu/prd-perimetre-dev-cyber-jeu.md, section 4
- constraint — PDF du sujet, p.3 (service rétabli = transaction réussie) et p.4 (microservices)

## Notes

- Decision: cœur métier maison tant que la trace du coach (P7) n'existe pas (2026-10-19).
- Assumption: interfaces simulées = ML, assistant, supervision ; base et API de paiement réelles.
