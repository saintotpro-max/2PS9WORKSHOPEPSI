# Analyse des manques (audit du 2026-10-19)

Méthode : le sujet (PDF), `graphify-v3.1` (PART 02, 10, 12, 19), le PRD et les stories ont été recoupés ; chaque sujet a été cherché dans les stories (nombre d'occurrences) et dans les fichiers réels du dépôt. Constat réel : le dépôt n'a que `services/simulateur` ; aucun Dockerfile, aucun README racine, aucun dossier `docs/`.

## 1. Manques et façon de les intégrer
| # | Manque | Pourquoi c'est attendu | Comment on l'intègre | Tickets |
|---|---|---|---|---|
| M1 | Conteneurs des services, authentification distincte | Sujet p.3 et p.4 : infrastructure conteneurisée, microservices dont un service d'authentification | Dockerfile par service + un exemple de `compose` que l'infra recopie dans son déploiement ; l'authentification devient un petit service séparé | 1.14, 1.16 |
| M2 | `/metrics` et journaux JSON | Sujet p.4 : la chaîne d'observabilité doit alimenter réellement l'analyse de l'incident | La plateforme expose `payment_requests_total{status}`, `payment_request_duration_seconds`, `payment_up` ; ses journaux sont du JSON pour Loki. L'infra n'a plus qu'à les collecter | 1.15 |
| M3 | Actions du moteur sous accès restreint | Sujet p.4 (playbooks Ansible = automatisation) et p.5 (le moteur a des droits élevés : pas d'administration accessible à tout composant) | Choix à faire avec l'infra : proxy Docker limité aux actions prévues, ou playbooks Ansible appelés par le moteur ; jamais le socket Docker en entier | 2.12 |
| M4 | Matrice attaque → détection → décision → action → vérification | Sujet p.3 : ne pas confondre restaurer la disponibilité et corriger une compromission ; attaque reproductible et expliquée | Un tableau par type (charge, connexions lentes, saturation réseau, injection, panne) : l'injection se bloque et se vérifie, elle ne se « redémarre » pas. Réutilisé dans le dossier | 2.11, 2.17 |
| M5 | Pannes non malveillantes | graphify EX-12 et sujet p.7 (chaos engineering jeudi) | Le moteur reprend aussi un conteneur tué ou ralenti par l'outil de chaos de l'infra, et vérifie par une transaction | 2.13 |
| M6 | Garde-fou de périmètre | Sujet p.5 et p.11 : toute activité offensive reste dans le SI fictif | Les scripts d'attaque refusent toute cible hors de 192.168.137.0/24 et de la machine locale, avant tout envoi | 2.14 |
| M7 | Données réelles et documents pour l'IA | graphify PART 09 (attaques → dataset ML, incidents → corpus RAG) ; sujet p.5 | Capture du trafic et des métriques pendant les vraies attaques, étiquetées par les fenêtres déclarées ; runbook, architecture et scénarios remis au collègue IA pour le corpus | 2.15, 2.16 |
| M8 | Livraison | Sujet p.8 : Code.zip sans secret, clip de 60 s sans coupe masquant une action manuelle ; p.9 : test des 5 minutes | Une commande qui produit l'archive et échoue si un secret est trouvé ; procédure écrite du clip ; build Windows du jeu testé sur les deux postes ; fiche d'une page par outil emprunté | 1.18, 1.19, 4.17, 4.18 |
| M9 | Répétition | graphify EX-12 : 10 passages de suite | Remise à zéro de la plateforme sans redéploiement + liste de contrôle avant chaque passage (réel seulement, rôles verrouillés, ports) | 1.17, 4.19 |
| M10 | Plan B React + Tailwind | Sujet p.2 et p.4 : tableau de bord en React + Tailwind | Option : une page minimale en lecture seule sur les mêmes routes, qui couvre l'exigence sans remettre en cause la salle de contrôle dans Ren'Py | 3.11 |

## 2. Points d'intégration avec vos collègues
| Avec | Ce qui passe | Sens | Contrat |
|---|---|---|---|
| IA (détecteur) | alerte avec score et recommandation ; série de scores | détecteur → moteur ; détecteur → salle | `POST /alerts` (+ `recommendation`), `GET /scores` |
| IA (assistant) | question, réponse, sources | jeu → assistant | `POST /assistant/ask` |
| Infra (supervision) | métriques et journaux de la plateforme | plateforme → Prometheus et Loki | `/metrics`, journaux JSON |
| Infra (WAF, SIEM) | flux bloqués ; alertes | WAF → salle ; SIEM → moteur | `GET /flux-bloques`, `POST /alerts` |
| Infra (déploiement) | Dockerfile et compose de la plateforme | nous → infra | exemples fournis (1.14) |
| Infra (actions) | proxy Docker restreint ou playbooks | moteur → infra | à décider (2.12) |
| Infra (chaos) | pannes injectées | outil de chaos → plateforme | scénario 2.13 |

## 3. Ordre d'intégration conseillé
1. Lundi : contrats envoyés (déjà rédigés) ; les collègues répondent par des routes qui respectent le contrat ; vous développez contre le simulateur.
2. Mardi : Dockerfile et compose (1.14), `/metrics` et journaux (1.15) : l'infra peut déjà brancher Prometheus et Loki sur la plateforme réelle.
3. Mercredi : alertes réelles et recommandation du détecteur (2.8) ; flux bloqués du WAF (1.12, 3.9) ; actions du moteur sous accès restreint (2.12).
4. Jeudi matin : chaos (2.13), remise à zéro (1.17), liste de contrôle (4.19), répétitions ; avant 17 h : arsenal gelé, archive et analyse de secrets (1.18), clip (4.18).

## 4. Décisions à prendre
1. Actions du moteur : proxy Docker restreint (plus simple à contrôler) ou playbooks Ansible (plus proche du sujet) ? Recommandation : proxy Docker restreint pour les actions simples, playbooks si l'infra les fournit déjà.
2. Poste attaquant : Windows ou Linux ? Cela change l'arrêt des outils (2.10), le build du jeu (4.17) et les outils d'attaque disponibles.
3. Plan B React + Tailwind : oui ou non (3.11) ? Recommandation : oui, si le temps le permet, car il couvre une exigence écrite du sujet pour un coût faible.
4. Qui porte le dossier de gouvernance (EBIOS, PCA/PRA, NIS2/DORA) ? Ce domaine est obligatoire (sujet p.2) et personne n'est désigné dans nos documents.
5. Qui assemble le dossier, la présentation et l'archive à la fin ? Le sujet demande aussi de rendre visible la contribution de chacun (p.8).

## 5. Ce qui est déjà bon (vérifié)
Contrats et simulateur, jeu habillé et testé (12 parcours), salle de contrôle, rôles verrouillés, épilogue, refus du mode démo, crédits des assets, commande de test en une ligne.
