---
type: epic
title: "Un jeu raconte la démonstration, chaque bouton agit pour de vrai"
parent: initiative-resilience-alpha
covers: [FR-14, FR-15, FR-16, FR-17, FR-18, FR-23, FR-24, FR-27, FR-29, FR-32, FR-33, FR-39, FR-40]
after: []
assignee: ""
risk: medium
---

# Un jeu raconte la démonstration, chaque bouton agit pour de vrai

## Description

Jeu Ren'Py de bureau, pierre angulaire du périmètre : 6 écrans et un HUD, premier chantier en 30 minutes ou moins contre le simulateur, interface, images et projets existants réutilisés ; l'intégration finale attend la chaîne réelle.

## Outcome

La démonstration est narrée dans le jeu en 5 minutes, et chaque action du jeu est une vraie action sur la vraie plateforme.

## Requirements

- FR-14: paiement réel.
- FR-15: terminal d'attaque réel.
- FR-16: poste SOC sans réparation, intervention manuelle refusée.
- FR-17: HUD de santé, épilogue avec temps réel, écran injoignable.
- FR-18: assets libres, CREDITS.md.
- FR-23: rôle verrouillé par poste.
- FR-24: répétition automatique avec compteur.

## Done when

1. Le jeu ne montre jamais un succès simulé comme réel.
2. La boucle courte passe 3 fois de suite sans intervention.
3. Aucun bouton ne répare.
4. Le jeu se joue au clavier seul.
5. Chaque emprunt libre est dans CREDITS.md.

## Boundaries

Jeu de bureau uniquement. Il ne remplace pas le frontal web de paiement ; il porte aussi le cockpit (épopée 3).

## References

- parent — _bmad-output/initiative-resilience-alpha/prd-perimetre-dev-cyber-jeu/prd-perimetre-dev-cyber-jeu.md, section 4
- spec — Docs/graphify-jeu-v2.1.txt, PART 4 à 6
- recherche — _bmad-output/initiative-resilience-alpha/carte-de-recherche.md
- constraint — Ren'Py desktop : pas de réseau en version navigateur

## Notes

- Decision: réutiliser interfaces, images et libs libres, aucune création ni génération d'art (utilisateur, 2026-10-19).
- Decision: le Ren'Py est la pierre angulaire et le premier chantier, 30 minutes ou moins, contre le simulateur (utilisateur, 2026-10-19).
- Decision: intégration finale (entrée 6) seulement sur la chaîne réelle : entrées 2.1, 2.4 et 2.6.
- Decision: réutiliser d'abord (GitHub, GUI, assets), coder en dernier ; carte dans carte-de-recherche.md.
