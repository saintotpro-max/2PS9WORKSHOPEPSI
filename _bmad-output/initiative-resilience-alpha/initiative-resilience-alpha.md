---
type: initiative
title: "Une plateforme de paiement fictive qui se rétablit seule (dev, cyber, jeu)"
parent: none
covers: [FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14, FR-15, FR-16, FR-17, FR-18, FR-19, FR-20, FR-21, FR-22, FR-23, FR-24, FR-25, FR-26, FR-27, FR-28, FR-29, FR-30, FR-31, FR-32, FR-33, FR-34, FR-35, FR-36, FR-37, FR-38, FR-39, FR-40]
after: []
assignee: ""
risk: high
---

# Une plateforme de paiement fictive qui se rétablit seule (dev, cyber, jeu)

## Description

Part de l'utilisateur dans le workshop EPSI : SI de paiement, attaque, reprise automatique, cockpit dans Ren'Py et mini-jeu. Infra et IA viennent des collègues, simulées par contrats tant qu'elles ne sont pas livrées. Le PRD porte le détail.

## Outcome

Le jury voit, au passage local de vendredi, une attaque réelle suivie d'une reprise sans intervention et d'une nouvelle transaction réussie ; l'axe « démonstration en direct et remédiation autonome » n'est pas remis à 0.

## Done when

1. La boucle paiement, attaque, alerte, reprise, paiement passe 10 fois de suite sans intervention, en mode réel.
2. Toutes les interfaces des collègues sont branchées en réel avant le passage.
3. Le cockpit est compris par une personne extérieure sans explication.
4. Le jeu tient dans la démo de 5 minutes et ne montre jamais un résultat simulé comme réel.
5. L'arsenal est gelé jeudi à 17 h.

## Boundaries

Dev, cyber et jeu uniquement. Pas d'infra, pas de détection ML ni d'assistant : ce sont les collègues. Pas de gouvernance ni de rendus (partagés). Tracer path : un paiement réel passe, une attaque réelle le dégrade, le moteur le répare, un second paiement réussit.

- Touch point: détection ML et supervision (collègues) — contrat d'alerte et métriques ; owner: epic-chaine-reprise
- Touch point: assistant RAG (collègues) — contrat de question ; owner: epic-jeu-renpy

## References

- prd — _bmad-output/initiative-resilience-alpha/prd-perimetre-dev-cyber-jeu/prd-perimetre-dev-cyber-jeu.md
- spec — Docs/graphify-v3.1.txt (étapes EX-01..13, PART 12) et Docs/graphify-jeu-v2.1.txt
- constraint — PDF du sujet, p.3 (état avant, pendant, après), p.9 (sanction 0/5)

## Notes

- Decision: 4 épopées pour un seul porteur, plutôt que 7 (2026-10-19, tranché sans question).
- Decision: audit des manques du 2026-10-19 : conteneurs, métriques, actions du moteur, garde-fou de périmètre, données et corpus pour l'IA, livraison, répétition ajoutés au plan (analyse-manques.md).
- Decision: flux bloqués affichés, éléments clés mis en valeur avec de la place pour la recommandation, bouton STOP rendu fiable et tous les types d'attaque testés (utilisateur, 2026-10-19).
- Decision: refonte du poste SOC en trois étapes (comprendre, vérifier, décider) et champ « recommandation IA » fourni par le détecteur du collègue, informatif, validé par le moteur contre une liste blanche (utilisateur, 2026-10-19).
- Decision: le cockpit devient une salle de contrôle unifiée projetée sur le PC Hôte, avec score d'anomalie en direct, trafic étiqueté pour le collègue IA et rôles verrouillés par poste (utilisateur, 2026-10-19).
- Decision: dashboard et cockpit dans Ren'Py, sans React ; le sujet impose React + Tailwind (p.2, p.4), risque assumé par l'utilisateur (2026-10-19).
- Decision: Ren'Py = pierre angulaire et premier chantier, 30 minutes ou moins, contre le simulateur (2026-10-19).
- Decision: balayage de refactor final non planifié, sprint de 4 jours ; à ajouter si le temps le permet.
- Open question: trace écrite du coach sur la réutilisation d'un serveur de paiement (P7).
- Open question: contenu du PPTX du sujet, absent de Docs/.
