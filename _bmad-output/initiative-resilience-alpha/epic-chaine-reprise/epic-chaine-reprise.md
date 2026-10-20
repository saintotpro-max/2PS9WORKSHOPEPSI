---
type: epic
title: "Une attaque réelle est suivie d'une reprise sans humain"
parent: initiative-resilience-alpha
covers: [FR-8, FR-9, FR-10, FR-11, FR-30, FR-32, FR-33, FR-36, FR-37, FR-38]
after: []
assignee: ""
risk: high
---

# Une attaque réelle est suivie d'une reprise sans humain

## Description

Arsenal d'attaque lancé depuis le PC Attaquant, moteur de remédiation, branchement à la détection et à la supervision des collègues, fiabilisation jusqu'à 10 passages de suite.

## Outcome

Le jury voit attaque, alerte, action puis nouvelle transaction réussie sans que personne ne touche à rien.

## Requirements

- FR-8: remédiation automatique vérifiée par une transaction.
- FR-9: moteur sans interface d'administration ouverte, droits limités, journal.
- FR-10: attaque réelle depuis un poste distinct, effet observable.
- FR-11: arsenal relu, gelé avant jeudi 17 h.

## Done when

1. La boucle complète passe 10 fois de suite en mode réel.
2. Le moteur n'a que les droits des actions prévues et journalise chaque action.
3. L'arsenal est gelé et versionné, sans appel à un modèle génératif en démo.
4. L'attaque ne vise que le SI fictif.

## Boundaries

Attaque et remédiation. La détection ML et la supervision restent aux collègues ; le moteur consomme leur alerte.

## References

- parent — _bmad-output/initiative-resilience-alpha/prd-perimetre-dev-cyber-jeu/prd-perimetre-dev-cyber-jeu.md, section 4
- constraint — PDF du sujet, p.5 (3.4, privilèges du moteur) et p.9 (sanction 0/5)
- spec — Docs/graphify-v3.1.txt, PART 12 EX-06 à EX-08 et EX-12

## Notes

- Assumption: attaque principale = déni de service contrôlé, injection en second.
- Decision: niveaux d'attaque du jeu = les 3 premiers (inonder, épuiser la mémoire, couper les tuyaux), 2026-10-19.
- Unknown: date de livraison de la détection ML et de la supervision ; l'entrée 6 en dépend.
- Open question: actions de remédiation précises (redémarrer, purger, bloquer).
