# Carte de recherche : où chercher avant de coder

Mentalité : **réutiliser d'abord** (projets GitHub existants, assets, outils, bibliothèques), coder en dernier. Cette carte dit où chercher ; la recherche se fait pendant l'exécution des stories citées, pas avant. Les pistes de la colonne « déjà vues » viennent d'une première recherche rapide : rien n'y est vérifié, il faut lire licence et dépôt avant d'adopter.

## Ren'Py (story 4.8, puis 4.2)
Règle 4C : COPIE-COLLE (config ou projet entier), RECUPERE (outil ou asset entier), ADAPTE (on étudie et on recode simplifié), CODE (seulement le fin).

| Besoin du jeu | Où chercher | Mots-clés | Déjà vues (non vérifiées) | Mode |
|---|---|---|---|---|
| Thème d'interface, deux ambiances (sombre hacker, clair SOC) | itch.io, étiquettes « renpy » + « gui », filtre gratuit | GUI kit, dark, neon, terminal, clean | « Neon Glitch GUI Kit » : licence annoncée CC BY-SA 4.0 et interdiction liée à l'IA, page non lue (accès refusé) ; « Custom GUI » cyberpunk (Kick14) : usage commercial annoncé | RECUPERE puis reskin par variables de style |
| Boutons, panneaux, jauges du HUD | OpenGameArt, kenney.nl | UI pack, panels, 9-slice | Packs UI de Kenney, annoncés CC0 | RECUPERE |
| Silhouettes (capuchon, badge, ombre) et fonds (hall, terminal, salle SOC) | OpenGameArt, itch.io (assets gratuits), kenney.nl | silhouette, office, server room, lobby, CC0 | aucune | RECUPERE ; niveau N0 typographique par défaut |
| Projets Ren'Py complets à forker ou à imiter (écrans, HUD, menus, appels réseau) | GitHub : `gh search repos` et `gh search code` (étiquettes `renpy`, `renpy-gui`, `renpy-template` ; code contenant `renpy.fetch`, `requests`, `subprocess`) ; forum Lemmasoft | renpy template, renpy gui, renpy http, renpy hud | aucune | COPIE-COLLE / ADAPTE |
| Écran terminal avec sortie qui défile | Manuel Ren'Py (écrans) ; forum Lemmasoft ; itch.io étiquette « renpy » + « tool » | terminal, console, scrolling log, laptop UI | Doc des écrans lue : `timer … repeat`, `viewport` avec molette, `input`, `side "c r"` ; défilement automatique non documenté ; « Interactive Laptop Framework » signalé comme assisté par IA | ADAPTE ; auto-défilement à écrire (CODE, quelques lignes) |
| Appels HTTP (santé toutes les 2 s, paiement, question) | Manuel officiel Ren'Py, page « HTTPS/HTTP Fetch » (`fetch.html`) ; forum Lemmasoft ; exemples GitHub | renpy.fetch, requests, invoke_in_thread, JSON | `invoke_in_thread` sans effet en version navigateur (sans impact : jeu de bureau) ; `fetch.html` non lue | RECUPERE (API du moteur) ; test d'appel réel contre le simulateur |
| Lancer un script d'attaque et lire sa sortie | Manuel Ren'Py (Python dans `init python`) ; doc Python `subprocess` | subprocess, init python | aucune | CODE, quelques lignes ; vérifier d'abord sur la console de Ren'Py |
| Bibliothèques Python tierces | Manuel Ren'Py (`game/python-packages`) | pip --target, pure Python | extensions C (numpy, pandas) : non | COPIE-COLLE de la procédure |
| Texte de l'écran « intervention refusée » | Sujet p.9 (sanction 0/5), dossier gouvernance | — | déjà dans le sujet | recopié |

## Dev et cyber (à exécuter dans les stories indiquées)
| Besoin | Où chercher | Mots-clés | Story |
|---|---|---|---|
| Simulateur des interfaces des collègues : serveur factice généré depuis les contrats OpenAPI plutôt qu'écrit à la main | GitHub, registres npm et PyPI : outils de « mock server » | openapi mock server, prism, mockoon, wiremock | 1.5 |
| Squelette de l'API de paiement (autorisation, idempotence, machine à états) | GitHub : squelettes FastAPI ; Kill Bill et Hyperswitch en modèle de conception seulement | fastapi template, payment api, idempotency | 1.2 |
| Cockpit dans Ren'Py (D16 ; le sujet impose React + Tailwind, risque assumé) | voir la carte Ren'Py : écrans, HUD, projets GitHub renpy | hud, dashboard, screen language | 3.1, 3.2 |
| Scripts d'attaque réels et reproductibles dans le laboratoire | GitHub et sources officielles : outils de test de charge et de déni de service contrôlé | locust, hping3, slowloris, wrk, sqlmap | 2.1, 2.4 |
| Moteur de remédiation (redémarrer, purger, bloquer) | doc de l'API Docker ; GitHub : exemples « self-healing » | docker sdk python, self healing, autoheal | 2.2 |

## Protocole commun avant toute adoption (P6 de graphify v3.1)
1. Licence Apache, MIT, CC0 ou CC-BY (CC-BY-SA seulement si on accepte de partager le jeu sous la même licence ; lire les interdictions d'usage, notamment liées à l'IA).
2. Santé du dépôt : étoiles, commits récents, issues ouvertes.
3. Empreinte mémoire sous contrôle (PC Hôte à 16 Go).
4. Test des 5 minutes : savoir l'expliquer devant le jury.
5. Entrée dans `CREDITS.md` (jeu) ou dans le README (reste du dépôt) : source, licence, auteur.
6. Aucune clé ni donnée embarquée.

## Résultat de l'exécution du 2026-10-19 (Ren'Py)
Retenus et intégrés : « Warped City » (fond), « Cyberpunk Portraits » (visages), « the hooded one » (fond du terminal), « UI Pack : Sci-fi » de Kenney (cartes, polices), Share Tech Mono (OFL). Écartés : dépôts GitHub Ren'Py sans licence déclarée, « Neon Glitch GUI Kit » (CC BY-SA avec restriction liée à l'IA). Aucune bibliothèque Ren'Py tierce adaptée trouvée : les fonctions du moteur suffisent. Outils à brancher en vrai dans les stories 2.1 et 2.4 : locust (charge, MIT), slowloris (connexions lentes), hping3 (saturation réseau) ; Pumba reste le chaos de jeudi côté hôte.
