# TODO : RESILIENCE-ALPHA, votre part (dev, cyber, jeu)

Règle de rythme : on coche seulement à la fin d'un bloc, en une ligne, après sa preuve (cas réel rejoué), puis on enchaîne.
Les numéros sont ceux des tickets (`epic.entrée`). Calendrier [D] aligné sur le sujet p.7, à recaler selon la livraison des collègues.
Mentalité : réutiliser d'abord, coder en dernier : `carte-de-recherche.md`.

## Vue d'ensemble (mise à jour du 2026-10-19)
| Bloc | Contenu | État | Reste |
|---|---|---|---|
| 0 | Sécuriser et corriger | fait, sauf relecture | relecture du PRD par vous, puis passage en `final` |
| 1 | Contrats + simulateur | fait, sauf envois | envoyer `contrats/messages-a-envoyer.md` |
| 2 | Jeu Ren'Py + simulateur étendus | **fait** : rôles, épilogue, poste SOC en 3 étapes, recommandation IA, flux bloqués, STOP fiable, 4 types d'attaque, périmètre ; 21 parcours validés | mode répétition n / 10 (4.11), options 4.12 et 4.14, plan B React (3.11) |
| 3 | Plateforme réelle | **fait côté code** (API, base, auth, frontal, santé honnête, conteneur, /metrics, bascule) ; prouvé 2026-10-19 | doc d'API, README, tests du service |
| 4 | Chaîne attaque → reprise | **fait côté code** : attaque réelle niveau 1 + moteur (EX-08 REPRISE_OK) ; prouvé 2026-10-19 | niveaux 2-3 réels, vrai détecteur IA (collègues), doc matrice |
| 5 | Salle de contrôle unifiée | **fait côté code**, 12 parcours validés | relecture par une personne extérieure (3.4) |
| 6 | Passage au réel, fin du jeu | à faire | dépend des collègues |
| 7 à 8 | Gel, remise, jury | à faire | jeudi 17 h, vendredi |

Vérification en une commande : `scripts/test-jeu.sh` (résumé d'une ligne, environ 25 s, port 8799 : la démonstration sur 8765 n'est pas touchée). Prochaine action recommandée : bloc 3 (plateforme réelle) : conteneurs, métriques, moteur.

## Bloc 0 : Sécuriser et corriger
- [x] Corrections appliquées (statut du Ren'Py, FR-19 et 1.8, dashboard, citation p.3/p.5/p.6)
- [x] `tickets.py status` propre, grep des divergences vide
- [x] Commit de `AGENTS.md`, `_bmad/`, `_bmad-output/`
- [ ] PRD relu par vous, passé en `final`

## Bloc 1 : Socle minimal pour que le jeu démarre (1.1, 1.5)
- [ ] Contrats d'interface envoyés aux collègues ; trace du coach (P7) et PPTX demandés (rédigés dans `contrats/messages-a-envoyer.md`, à envoyer par vous)
- [x] Contrats rédigés (`contrats/`) ; simulateur : santé, transactions, alerte, question, panne et reprise (`services/simulateur`)
- [x] Preuve : `smoke.py` 13 étapes sur 13 ; les 9 routes du contrat sont couvertes par le simulateur
- [x] Ajouts du 2026-10-19 : série de scores et événements déclarés (1.10), trafic étiqueté et export CSV (1.9) : `smoke.py` 18 étapes sur 18

## Bloc 2 : Ren'Py, pierre angulaire, 30 minutes ou moins, contre le simulateur (4.8, 4.2, 4.1, 4.3, 4.5, 4.4)
- [x] Recherche faite sur la carte, choix et licences dans `renpy/CREDITS.md` (4.8, 4.2) : modèle d'interface du SDK, aucun asset externe
- [x] Scaffold, pont de santé, écran « injoignable » (4.1)
- [x] Titre, HUD, paiement, refus du mode démo si simulé (4.3)
- [x] Poste SOC sans réparation (4.5) ; terminal avec script factice étiqueté « simulé » (4.4)
- [x] Habillage « néon-noir pixel » : fond de ville, visages, cartes, polices libres (CC0 et OFL), flux façon mitmproxy, alerte façon Wazuh, scripts d'attaque qui imitent locust, slowloris, hping3 : plan dans `plan-design-renpy.md`, sources dans `renpy/CREDITS.md`
- [x] Preuve : `scripts/test-jeu.sh` : 6 parcours, 14 vérifications passées ; `scripts/test-jeu.sh visuel` produit les captures (`renpy/tests/captures`), relues
- Hors budget des 30 min, à venir : épilogue (4.6, après la chaîne réelle), cockpit S7 (épopée 3)
- Durée réelle : non chronométrée ; le temps de la session n'est pas une mesure fiable.

## Bloc 2 bis : Corrections de scénario du jeu (4.9, 4.10, épilogue 4.6)
- [x] « Le système sait » seulement après l'alerte (4.10)
- [x] Rôle verrouillé par poste (4.9)
- [x] Épilogue « ZERO-TOUCH » : temps de reprise mesuré, avant et après (part de 4.6)
- [x] Preuve : parcours de test pour chacun

## Bloc 2 ter : Poste SOC refondu et recommandation IA (D18)
- [x] Simulateur : recommandation dans l'alerte et `/verifications` (1.11)
- [x] Poste SOC en trois étapes : comprendre, vérifier, décider (4.13)
- [x] Recommandation IA dans la colonne Badge de la salle de contrôle (3.8)
- [ ] Moteur : action suggérée validée par liste blanche, vérifications mesurées (2.8, avec le bloc 4)
- [ ] Option : consigner l'incident (4.14)
- [ ] Envoyer au collègue IA le nouveau champ `recommendation` (`contrats/`)

## Bloc 2 quater : Flux bloqués, mise en valeur, attaquant fiable (D19)
Constat vérifié le 2026-10-19 (avant correction) : STOP est branché sur `arreter_script`, mais (1) aucun test ne le couvre ; (2) les scripts simulés finissent en 0,05 s, il n'y a donc rien à arrêter ; (3) `terminate()` ne tue que le script, pas l'outil enfant (vérifié : l'enfant survit ; l'arrêt du groupe de processus le tue) ; (4) après STOP le terminal afficherait « ÉCHEC du script (code -15) » ; (5) l'effet de l'attaque continue côté plateforme ; (6) Windows non géré. Les niveaux 1 à 3 se lancent (code 0, plateforme dégradée) ; seul le niveau 1 est couvert par un test de bout en bout.
- [x] S1 Flux bloqués : simulateur (1.12), panneau dans la salle (3.9), attaque d'injection qui les déclenche (2.9, simulée ; à refaire avec le vrai WAF)
- [x] S2 Mise en valeur : agrandir santé, reprise, recommandation ; place pour la recommandation (3.10, avec 3.8) : captures relues
- [x] S3 STOP fiable : arrêt de l'arbre de processus, état « arrêté », événement de fin, message s'il n'y a rien à arrêter (4.15, 2.10) : testé sous Linux, code Windows (taskkill) non testé ; une course corrigée (STOP juste après le lancement)
- [x] S4 Attaque simulée de longue durée et `/simulation/arret`, pour que STOP ait un effet (1.13)
- [x] S5 Chaque type d'attaque (niveaux 1 à 3 et injection) lancé puis arrêté, vérifié par test (4.16)
- [ ] S6 Droits particuliers (saturation réseau hping3) signalés avant le lancement ; Windows pris en compte (2.10)

## Bloc 2 quinquies : Manques trouvés par l'audit du 2026-10-19 (D20)
Absents des 49 stories avant l'audit (zéro occurrence) : métriques Prometheus, Ansible, chaos, capture du trafic réel, corpus de l'assistant, fiche de défense des emprunts, remise à zéro. Cités sans story : Dockerfile, authentification distincte, archive Code.zip et analyse de secrets, procédure du clip, build Windows, garde-fou de périmètre, matrice de remédiation. Détail et intégration : `analyse-manques.md`.
- [x] M1 Conteneurs : `services/paiement/Dockerfile` + `compose.yaml`, authentification distincte (jeton par rôle) (1.14, 1.16). Preuve 2026-10-19 : `docker compose up -d --build` → santé `ok`, transaction et `/metrics` via le conteneur, journal JSON via `docker logs` ; port hôte 8780 (8000 pris par un service tiers)
- [x] M2 Métriques `/metrics` (format Prometheus, sans dépendance) et journaux JSON (stdout, pour Loki) côté paiement (1.15). Preuve : `/metrics` montre tx_ok/auth_refus qui bougent
- [ ] M2b Côté simulateur et moteur : `/metrics` et journaux JSON (à faire avec le moteur, bloc 4)
- [x] M3 Actions du moteur : accès restreint, **proxy Docker** (décision de l'utilisateur, 2026-10-19), redémarrage + cibles en liste blanche ; playbooks Ansible écartés (dépendance infra) (2.12). Implémenté dans `services/moteur/`, prouvé par la chaîne complète
- [~] M4 Matrice attaque → détection → décision → action → vérification : implémentée dans le code du moteur (choisir_action + verifier_reprise) ; reste à écrire le tableau documentaire et la doc d'attaque (2.11, 2.17)
- [ ] M5 Pannes non malveillantes (chaos de jeudi) reprises par le moteur (2.13)
- [x] M6 Garde-fou de périmètre des scripts d'attaque (2.14) : fait sur les scripts simulés et testé ; à reprendre dans l'arsenal réel
- [ ] M7 Données réelles pour le détecteur : capture étiquetée (2.15) ; documents du corpus de l'assistant (2.16)
- [ ] M8 Livraison : archive et analyse de secrets (1.18), fiche de défense (1.19), build Windows (4.17), procédure du clip (4.18)
- [ ] M9 Répétition : remise à zéro (1.17) et liste de contrôle de passage (4.19)
- [ ] M10 Option plan B React + Tailwind minimale (3.11), à décider

## Bloc 3 : Plateforme réelle (1.2, 1.3, 1.4, 1.6, 1.8)
- [x] API + base + authentification : une transaction réelle ; frontal web ; santé honnête (`services/paiement/`, SQLite, jeton opaque par rôle, idempotence, `/health` qui écrit puis relit une sonde). Preuve 2026-10-19 : cas réel rejoué (santé, jeton bon/mauvais, transaction, idempotence, lecture 404) + paiement accepté depuis le navigateur (capture relue, badge MODE REEL)
- [x] Bascule simulé/réel (`config/interfaces.reel.json` + `scripts/lancer-reel.sh`, mode MIXTE : plateforme réelle, orchestration simulée). Preuve : route du jeu (`demo/demo`) acceptée en réel ; `scripts/test-jeu.sh` reste 21/21 parcours, 78 vérifications
- [ ] doc d'API, README, tests du service paiement
- [ ] Une phrase par décision technique au dossier gouvernance (récurrent)

## Bloc 4 : Chaîne attaque → reprise, EX-06 et EX-08 (2.1 à 2.4)
- [x] Attaque réelle niveau 1 (`attack/arsenal/niveau-1.py`, charge réelle multi-fils sur la plateforme, garde-fou de périmètre, arrêt propre sur SIGTERM) (2.1, EX-06). Preuve 2026-10-19 : ~4000 requêtes réelles en 4 s, `/metrics` passe de 2 à 4035 ; cible hors périmètre (8.8.8.8) refusée. Latence `/health` reste basse (route légère) : dégradation visible à obtenir en martelant `/transactions` ou derrière la vraie pile
- [x] Moteur de remédiation réel (`services/moteur/`) : reçoit l'alerte (contrat), choisit une action en LISTE BLANCHE (recommandation IA validée, sinon repli par type d'incident), agit sur cible AUTORISÉE seulement, puis MESURE la reprise (API joignable, transaction de test réelle, données cohérentes). Accès Docker restreint (décision M3 : **proxy Docker**, redémarrage + cibles en liste blanche) (EX-08, 2.2 à 2.4, 2.8, M4)
- [x] Preuve 2026-10-19 (jalon central) : alerte dos → `docker restart alpha-paiement` → API ok → transaction de test acceptée → données cohérentes → **REPRISE_OK**, sans intervention ; cible hors liste blanche refusée. Câblé dans `config/interfaces.reel.json` (moteur réel, port 8772) et `scripts/lancer-reel.sh`
- [ ] Niveaux 2 et 3 réels + branchement du vrai détecteur IA (dépend des collègues) ; `/metrics` et journaux JSON du simulateur (M2b)

## Bloc 5 : Salle de contrôle unifiée dans Ren'Py, EX-11 (3.1 à 3.7) : budget à estimer par vous
- [x] Salle de contrôle : trois colonnes, santé et mode, frise avant/pendant/après, composants, événements, alertes, colonne Capuchon (3.1, 3.2, 3.3), courbe du score (3.5), journal et cartes (3.6), mode projection touche P (3.7)
- [ ] Relecture par une personne extérieure

## Bloc 6 : Passage au réel et fin du jeu (2.5, 2.6, 2.7, 1.7, 4.6, 4.7)
- [ ] Collègues livrés ; branchement réel (2.6) ; contrôle « réel seulement » (1.7)
- [ ] Arsenal relu et gelé avant 17 h jeudi (2.5)
- [ ] Jeu : boucle courte 3 fois en réel sous 5 minutes (4.6) ; option 4.7
- [ ] Preuve : 10 passages de suite sans intervention (2.7)

## Bloc 7 : Jeudi, gel et remise
- [ ] Code gelé à 17 h, `Code.zip` sans secret ; clip 60 s continu ; remise avant 23h59
- [ ] Répétition du passage de 5 minutes et de la version nationale de 3 minutes

## Bloc 8 : Vendredi, jury local
- [ ] Toutes les interfaces en réel ; passage de 10 minutes ; aucune intervention

## Idées retenues au plan (2026-10-19) : tickets et cases
- [x] I1 Salle de contrôle unifiée (3.1, 3.2, 3.3)
- [x] I2 Courbe du score d'anomalie en direct (3.5, données 1.10)
- [x] I3 Trafic normal et attaques étiquetés, export CSV (1.9)
- [x] I4 et I5 Journal défilant et cartes de personnages vivantes (3.6)
- [x] I6 Rôle verrouillé par poste (4.9)
- [ ] I7 Mode répétition automatique n / 10 (4.11)
- [x] I8 Mode projection plein écran (3.7)
- [x] I9 Épilogue « ZERO-TOUCH » avec avant et après (4.6)
- [x] I10 « Le système sait » seulement après l'alerte (4.10)
- [ ] I11 Option : barre d'état propre à chaque personnage (4.12, faible priorité)

## Idée à valider : simulation par un modèle externe (NanoGPT), 2026-10-19
Vérifié : API au format chat completions d'OpenAI (`POST https://nano-gpt.com/api/v1/chat/completions`, clé en en-tête Bearer). Non vérifié : tarif, limites, conservation des données.
Cadre : pour la SIMULATION et la génération EN AMONT seulement. Jamais pour le vrai assistant (sujet p.5 : Ollama + LangChain, modèle local de 8 Md au plus), jamais le jour J (graphify R-14), clé jamais dans le dépôt ni dans `Code.zip` (R-15, sujet p.7).
- [x] N1 Clé et modèle (`qwen/qwen3.8-27b-cybersecurity`) en place hors dépôt (`~/.config/alpha/nanogpt.env`), vérifiés par un appel réel
- [x] N2 Simulateur : réponses de l'assistant (ancrées sur l'état simulé) et recommandations générées par le modèle ; activé par `SIM_LLM=1 scripts/lancer.sh`, désactivé par défaut, mis en cache, jamais appelé par les tests ; repli sur la version statique en cas d'échec. Constat : le filtre du service refuse parfois les consignes en rôle « système » sur ces sujets : elles sont fusionnées dans le message utilisateur
- [ ] N3 Génération en amont de scénarios d'attaque (Attack Composer), relus puis gelés
- [ ] N4 Brouillons du runbook et des scénarios pour le corpus du collègue IA, à relire

## Nettoyage de l'écran unifié (2026-10-19)
- [x] Un seul marqueur de mode (SIMULÉ, RÉEL ou MIXTE) au lieu d'une mention par ligne ; légendes et suffixes « simulé » retirés ; journal et composants épurés ; recommandation compacte (captures relues)
