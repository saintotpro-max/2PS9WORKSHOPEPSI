---
type: epic
title: "Le jury comprend la démonstration en regardant l'écran"
parent: initiative-resilience-alpha
covers: [FR-12, FR-13, FR-20, FR-21, FR-25, FR-30, FR-31]
after: []
assignee: ""
risk: low
---

# Le jury comprend la démonstration en regardant l'écran

## Description

Cockpit dans le moteur Ren'Py (écran S7 du jeu) : état du service avant, pendant et après, composants, événements, alertes, frise de reprise ; la vue Red Crew est le terminal du jeu.

## Outcome

Une personne extérieure comprend la démonstration sans explication.

## Requirements

- FR-12: vues avant, pendant, après, avec composants, événements, alertes et temps de reprise réel.
- FR-20: salle de contrôle unifiée à trois colonnes, journal défilant, cartes de personnages.
- FR-21: courbe du score d'anomalie en direct.
- FR-25: mode projection plein écran.
- FR-13: le terminal du jeu, vue Red Crew, lance un script gelé par niveau.

## Done when

1. Les trois états du service sont visibles en direct.
2. Le temps de reprise affiché est le temps réel mesuré.
3. Chaque niveau lance un script gelé de l'arsenal.
4. Une personne extérieure comprend l'écran sans aide.

## Boundaries

Écrans de supervision dans le moteur Ren'Py. Pas Grafana (collègues).

## References

- parent — _bmad-output/initiative-resilience-alpha/prd-perimetre-dev-cyber-jeu/prd-perimetre-dev-cyber-jeu.md, section 4
- constraint — PDF du sujet, p.2 et p.4 : React + Tailwind imposé ; écarté par décision de l'utilisateur, risque assumé

## Notes

- Decision: le cockpit est fait dans Ren'Py, sans React (utilisateur, 2026-10-19) ; risque : perte possible sur l'axe « Clip Chrono et dashboard ».
- Decision: distinct de Grafana ; il lit l'état de la plateforme et les événements du moteur.
- Unknown: budget des 4 stories, hors des 30 minutes du jeu ; à estimer par l'utilisateur.
