---
title: RESILIENCE-ALPHA, périmètre dev, cyber et jeu
status: draft
created: 2026-10-19
updated: 2026-10-19
---

# PRD : RESILIENCE-ALPHA, périmètre dev, cyber et jeu
*Titre de travail, à confirmer.*

## 0. Document Purpose
Ce PRD couvre la part de l'utilisateur dans le workshop EPSI : développement (SI de paiement, moteur de remédiation, cockpit dans Ren'Py), cybersécurité offensive (arsenal d'attaque) et mini-jeu Ren'Py. L'infrastructure et l'IA sont portées par les collègues ; ici elles sont des dépendances décrites par des contrats d'interface et remplacées par un simulateur tant qu'elles ne sont pas livrées. Il s'appuie sur le sujet PDF (fait foi), `Docs/graphify-v3.1.txt` et `Docs/graphify-jeu-v2.1.txt`, sans les dupliquer. Les hypothèses sont taguées `[ASSUMPTION]` et indexées en §9.

## 1. Vision
Une plateforme de paiement fictive subit une attaque réelle lancée depuis un second ordinateur, se détecte et se répare seule, et une nouvelle transaction réussit sans qu'aucun humain n'intervienne. Le jury doit voir l'état du service avant, pendant et après l'incident.

Le périmètre de l'utilisateur fournit le cœur métier attaqué et réparé, l'attaque elle-même, l'écran qui rend la démonstration lisible, et un jeu qui la raconte. Tant que l'infrastructure et l'IA des collègues ne sont pas prêtes, un simulateur permet d'avancer sans attendre ; le passage au réel ne demande qu'un changement de configuration.

Ce qui compte pour la note : démonstration en direct et remédiation autonome (5 points au jury local, 25 en finale nationale). Une intervention humaine pendant le live ramène cet axe à 0.

## 2. Target User

### 2.1 Jobs To Be Done
- Jury : comprendre en quelques minutes que le service s'est rétabli seul, preuve à l'appui.
- Équipe : répéter la démonstration en boucle et la rendre fiable (10 passages de suite sans intervention).
- Utilisateur (développeur/cyber) : avancer sans attendre l'infra ni l'IA des collègues, puis brancher le réel sans réécriture.

### 2.2 Non-Users (v1)
Aucun client réel ni donnée bancaire réelle. Le jury local joue au plus le rôle de client dans le jeu.

### 2.3 Key User Journeys

- **UJ-1. Camille, du jury, paie avant et après l'attaque.**
  - **Persona + context :** Camille évalue le passage local de 10 minutes ; elle n'a jamais vu la plateforme.
  - **Entry state :** plateforme en mode réel, jeu et cockpit ouverts sur le PC Hôte.
  - **Path :** elle clique PAYER et la transaction réussit ; l'attaque démarre ; le cockpit passe au rouge ; la reprise s'affiche seule ; elle clique PAYER une seconde fois.
  - **Climax :** la deuxième transaction réussit sans que personne ait touché à rien.
  - **Resolution :** l'écran de fin affiche le temps de reprise réel et l'avant/après.
  - **Edge case :** si l'API est encore indisponible au second paiement, l'échec réel est affiché, sans faux succès.

- **UJ-2. Malik lance l'attaque depuis le PC Attaquant.**
  - **Persona + context :** Malik, côté Red Crew, répète l'attaque de jeudi.
  - **Entry state :** arsenal gelé, plateforme joignable depuis le réseau du groupe.
  - **Path :** il choisit un niveau d'attaque ; le script réel s'exécute ; la sortie du script s'affiche ; le trafic anormal monte sur la plateforme.
  - **Climax :** la dégradation est visible sur le cockpit.
  - **Resolution :** la reprise automatique ramène la plateforme à l'état sain.
  - **Edge case :** si le script échoue, l'erreur est affichée telle quelle.

- **UJ-3. Inès, opératrice SOC, regarde sans toucher.**
  - **Persona + context :** Inès incarne la sagesse du zero-touch.
  - **Entry state :** attaque en cours, alerte de détection reçue.
  - **Path :** elle lit l'alerte, pose une question à l'assistant, tente d'intervenir à la main.
  - **Climax :** l'intervention manuelle est refusée avec l'explication de la sanction.
  - **Resolution :** elle laisse le système finir.
  - **Edge case :** réponse de l'assistant lente (plus de 10 s) : un indicateur d'attente honnête s'affiche, jamais un texte écrit à l'avance.

- **UJ-4. Sam, de l'équipe, développe sans attendre les collègues.**
  - **Persona + context :** Sam travaille mardi alors que la détection ML et la supervision ne sont pas livrées.
  - **Entry state :** simulateur lancé en local, configuration en mode simulé.
  - **Path :** il joue la boucle complète (paiement, attaque, alerte, reprise, paiement) contre le simulateur.
  - **Climax :** la boucle passe de bout en bout, le mode simulé étant affiché.
  - **Resolution :** quand les collègues livrent, il change la configuration en réel et rejoue la même boucle.

## 3. Glossary
- **Plateforme** — le SI de paiement fictif : base de données, API métier, service d'authentification, frontal web.
- **Mode simulé / mode réel** — origine des réponses : simulateur local ou vraie plateforme. Toujours affiché.
- **Contrat d'interface** — description courte (OpenAPI) de ce que les collègues doivent exposer et que le simulateur imite.
- **Simulateur** — service local qui répond selon les contrats, avec pannes et reprise simulées.
- **PC Hôte / PC Attaquant** — poste qui exécute les services ; poste distinct d'où part l'attaque.
- **Arsenal** — scripts d'attaque générés puis relus puis gelés dans Git.
- **Attack Composer** — vue qui génère des scénarios d'attaque en amont ; jamais utilisé en direct (R-14).
- **Moteur de remédiation** — composant qui reçoit l'alerte, exécute l'action et vérifie le retour à l'état sain.
- **Zero-touch** — reprise sans aucune intervention corrective humaine.
- **Cockpit (dashboard jury)** — écrans de supervision (avant, pendant, après) réalisés dans le moteur Ren'Py, par décision de l'utilisateur ; le sujet impose React + Tailwind (p.2, p.4) : risque assumé.
- **Jeu** — mini-jeu Ren'Py « Double Face », application de bureau qui narre la démonstration.
- **HUD** — bandeau permanent du jeu : santé, transactions, alerte, chrono de reprise.

## 4. Features

### 4.1 Contrats d'interface et simulateur
**Description :** les collègues et l'utilisateur partagent des contrats courts pour santé, transactions, alerte de détection, question à l'assistant et métriques. Le simulateur les imite pour permettre le développement. Réalise UJ-4.

**Functional Requirements :**

#### FR-1 : Contrats d'interface
L'équipe dispose d'un contrat OpenAPI par interface attendue des collègues. Réalise UJ-4.

**Consequences (testable) :**
- Les contrats couvrent au minimum : santé, transactions, alerte de détection, question à l'assistant, métriques.
- Un collègue peut implémenter un contrat sans lire le code de l'utilisateur.

#### FR-2 : Simulateur
Le simulateur répond conformément aux contrats et rejoue une panne puis une reprise après une attaque simulée. Réalise UJ-4.

**Consequences (testable) :**
- Une transaction envoyée au simulateur renvoie la réponse prévue par le contrat.
- Après une attaque simulée, la santé passe à dégradée puis revient à saine sans action humaine.

#### FR-3 : Basculement par configuration
Un seul fichier de configuration choisit simulé ou réel pour chaque interface. Réalise UJ-4.

**Consequences (testable) :**
- Passer de simulé à réel ne modifie aucun code.
- Le mode actif de chaque interface est affiché dans le jeu et son cockpit.

#### FR-4 : Interdiction de démo simulée
La démonstration, le clip et le passage jury n'utilisent que le mode réel. Réalise UJ-1.

**Consequences (testable) :**
- La liste de contrôle avant le jury vérifie que toutes les interfaces sont en réel.
- Une interface restée simulée bloque le lancement du jeu en mode démo.

**Notes :** `[ASSUMPTION: les interfaces simulées sont ML, assistant, supervision ; la base et l'API de paiement sont réelles dès le départ.]`

### 4.2 SI de paiement (cœur métier)
**Description :** microservices conteneurisés en base, API métier, authentification et frontal web, avec transactions fictives. Le sujet impose de le construire ; les outils publics sont autorisés. Réalise UJ-1.

#### FR-5 : API de transactions
Un client authentifié peut créer et consulter une transaction fictive. Réalise UJ-1.

**Consequences (testable) :**
- Une transaction valide est enregistrée dans la vraie base et renvoie son identifiant.
- Un appel non authentifié est refusé.
- La base et les secrets ne sont pas exposés au réseau pédagogique.
- Les journaux sont structurés et exploitables pour l'investigation (sujet p.5).

#### FR-6 : Frontal web de paiement
Le client peut payer depuis une interface web, sans le jeu. Réalise UJ-1.

**Consequences (testable) :**
- Le paiement fonctionne dans un navigateur lorsque le jeu est fermé.

#### FR-7 : Santé du service
La plateforme expose un état de santé qui reflète la capacité réelle à traiter une transaction. Réalise UJ-1, UJ-2.

**Consequences (testable) :**
- Un conteneur qui redémarre sans que l'API réponde n'est pas déclaré sain.
- Le retour à l'état sain exige qu'une nouvelle transaction réussisse.

**Notes :** `[NOTE FOR PM: l'option « serveur de paiement réutilisé » dépend d'une trace écrite du coach (P7) ; sans elle, le cœur métier est maison.]`

### 4.3 Moteur de remédiation
**Description :** reçoit l'alerte, exécute l'action prévue, vérifie la reprise. Terrain commun de l'équipe (EX-08). Réalise UJ-1, UJ-3.

#### FR-8 : Remédiation automatique
À réception d'une alerte, le moteur exécute l'action adaptée sans intervention. Réalise UJ-1.

**Consequences (testable) :**
- Attaque, alerte, action puis nouvelle transaction réussie s'enchaînent sans intervention.
- Le résultat est vérifié par une transaction, pas par le seul redémarrage d'un conteneur.

#### FR-9 : Surface d'attaque maîtrisée
Le moteur n'offre aucune interface d'administration accessible à un composant quelconque. Réalise UJ-3.

**Consequences (testable) :**
- Ses droits sont limités aux actions prévues.
- Toute action est journalisée.

### 4.4 Arsenal d'attaque
**Description :** attaque réelle depuis le PC Attaquant, reproductible, compatible avec une réponse automatique. Réalise UJ-2.

#### FR-10 : Attaque réelle depuis un poste distinct
L'attaque part du PC Attaquant et produit un effet observable sur la plateforme. Réalise UJ-2.

**Consequences (testable) :**
- Le trafic anormal est visible dans les métriques de la plateforme.
- L'attaque ne vise que le SI fictif et les machines de l'équipe.

#### FR-11 : Arsenal gelé
Les scripts d'attaque sont relus, versionnés et gelés avant jeudi 17 h. Réalise UJ-2.

**Consequences (testable) :**
- Aucun appel à un modèle génératif n'a lieu pendant la démonstration.
- Un script relancé donne le même effet à chaque passage.

**Notes :** `[ASSUMPTION: attaque principale = déni de service contrôlé ; injection en second pour montrer le WAF.]`

### 4.5 Cockpit jury (dans Ren'Py)
**Description :** écrans du jeu Ren'Py (décision de l'utilisateur ; le sujet impose React + Tailwind, risque assumé) montrant composants, événements, alertes et avancement de la reprise. Réalise UJ-1.

#### FR-12 : Vues avant, pendant, après
Le cockpit présente l'état du service aux trois moments. Réalise UJ-1.

**Consequences (testable) :**
- Une personne extérieure comprend la démonstration en regardant l'écran seul.
- Une frise de la reprise affiche le temps de reprise réel.
- Les composants, les événements et les alertes sont listés, avec l'avancement de la reprise (sujet p.4).

#### FR-13 : Vue Red Crew
Le cockpit (terminal du jeu) permet de choisir un niveau d'attaque. Réalise UJ-2.

**Consequences (testable) :**
- Chaque niveau lance un script gelé de l'arsenal.

#### FR-20 : Salle de contrôle unifiée
Un écran projeté sur le PC Hôte regroupe les trois points de vue : colonne Capuchon (niveau et événements d'attaque déclarés par le poste attaquant), colonne Plateforme (santé en frise avant, pendant, après ; composants ; flux), colonne Badge (alerte, assistant, mention zero-touch), journal défilant et chronomètre de reprise. Réalise UJ-1, UJ-2, UJ-3.

**Consequences (testable) :**
- Un événement déclaré par le poste attaquant porte sa source ; il ne remplace jamais l'alerte de détection.
- Le mode simulé ou réel de chaque interface reste affiché.
- Les cartes de personnages indiquent l'état de chacun en direct.

#### FR-21 : Score d'anomalie en direct
Une courbe affiche le score du détecteur, son seuil et les fenêtres d'attaque déclarées. Réalise UJ-2, UJ-4.

**Consequences (testable) :**
- Sans détecteur branché, l'emplacement affiche « pas de détecteur branché », jamais une courbe inventée.
- En simulation, la courbe est étiquetée « simulé ».

#### FR-25 : Mode projection
Un mode plein écran, sans boutons, affiche la salle de contrôle pour le clip de 60 s. Réalise UJ-1.

**Consequences (testable) :**
- Ce mode ne remplace pas la capture réelle continue exigée pour le clip.

### 4.6 Mini-jeu Ren'Py
**Description :** application de bureau qui narre la démonstration ; chaque bouton déclenche une action réelle. 6 écrans et un HUD ; pierre angulaire et premier chantier, 30 minutes ou moins en réutilisant l'existant, contre le simulateur ; intégration finale sur la chaîne réelle. Réalise UJ-1, UJ-2, UJ-3.

#### FR-14 : Paiement réel dans le jeu
Le bouton PAYER envoie une vraie transaction. Réalise UJ-1.

**Consequences (testable) :**
- Le résultat affiché est la réponse de l'API, telle quelle.
- API indisponible : l'échec réel est affiché, sans faux succès.

#### FR-15 : Terminal d'attaque
Le jeu lance un script gelé et affiche sa sortie. Réalise UJ-2.

**Consequences (testable) :**
- Un script qui échoue affiche son erreur, jamais « succès ».
- Un niveau peut être relancé avec un compteur d'exécutions.

#### FR-16 : Poste SOC sans réparation
Le jeu affiche l'alerte réelle, une question à l'assistant et refuse l'intervention manuelle. Réalise UJ-3.

**Consequences (testable) :**
- Aucun bouton du jeu ne répare quoi que ce soit.
- « Attendez. Le système sait. » n'apparaît qu'après réception de l'alerte.
- La réponse de l'assistant vient du vrai point d'accès ; lente, elle affiche une attente honnête.

#### FR-17 : Santé et épilogue
Le HUD interroge la santé toutes les 2 secondes ; l'épilogue affiche le temps de reprise réel et l'avant/après. Réalise UJ-1.

**Consequences (testable) :**
- Santé injoignable : écran « injoignable », le jeu ne plante pas.
- Aucun chiffre n'est inventé.

#### FR-18 : Réutilisation d'assets
Interfaces, images et bibliothèques proviennent de sources libres vérifiées. Réalise UJ-1.

**Consequences (testable) :**
- Chaque emprunt figure dans `CREDITS.md` avec source, licence et auteur.
- Le jeu fonctionne au clavier seul.

### 4.7 Livrables de code
**Description :** le sujet exige dans `Code.zip` des tests, une documentation d'API et un README de déploiement, sans secret en clair (p.8). Réalise UJ-4.

#### FR-19 : Code livrable et vérifiable
Le dépôt permet de comprendre comment installer, relancer et vérifier la partie de l'utilisateur. Réalise UJ-4.

**Consequences (testable) :**
- Un README décrit l'installation et la relance ; la doc d'API est générée depuis les contrats.
- Des tests couvrent les routes de l'API et la bascule simulé/réel ; ils passent d'une seule commande.
- Aucun secret n'apparaît en clair dans l'archive.

### 4.8 Données pour la détection
**Description :** le collègue IA doit voir et tester son détecteur avant le vrai trafic ; le simulateur lui fournit des données synthétiques étiquetées. Réalise UJ-4.

#### FR-22 : Trafic normal et attaques étiquetés
Le simulateur génère du trafic normal et des attaques annoncées avec leurs étiquettes et les exporte en CSV. Réalise UJ-4.

**Consequences (testable) :**
- Colonnes : horodatage, requêtes par seconde, taux d'erreur, latence, étiquette.
- Une même graine donne le même fichier.
- Le fichier porte la mention « synthétique » : il ne remplace pas les données issues de vraies attaques.

### 4.9 Rôles et répétition
**Description :** chaque poste joue un seul rôle, et la démonstration peut se rejouer seule. Réalise UJ-1, UJ-2.

#### FR-23 : Rôle verrouillé par poste
Chaque poste a un rôle (hôte ou attaquant) et le jeu n'offre que les portes de ce rôle. Réalise UJ-1, UJ-2.

**Consequences (testable) :**
- Rôle attaquant : seule la porte du capuchon ; rôle hôte : badge et ombre ; le jury sur l'hôte ne peut pas lancer d'attaque.
- Mode démo avec un rôle non verrouillé : lancement refusé.

#### FR-24 : Répétition automatique
Un mode rejoue la boucle complète avec un compteur « n / 10 » et s'arrête au premier échec. Réalise UJ-4.

**Consequences (testable) :**
- Le compteur est visible ; le mode est étiqueté simulé ou réel.

### 4.10 Poste SOC en trois étapes et recommandation IA
**Description :** le poste du Badge sert à comprendre, vérifier puis décider de faire confiance, en lecture seule. La détection fournit une recommandation sur l'incident ; elle informe, elle ne répare pas (le sujet distingue l'assistant de l'automate de remédiation, p.5). Réalise UJ-3.

#### FR-26 : Recommandation IA
L'alerte porte une recommandation du détecteur (résumé, action suggérée, confiance), affichée au poste SOC et dans la salle de contrôle. Réalise UJ-3.

**Consequences (testable) :**
- Sans recommandation, l'emplacement indique « pas de recommandation », jamais un texte inventé.
- Elle est étiquetée « informative : aucune action humaine » et « simulée » en mode simulé.
- Le moteur n'applique une action suggérée que si elle figure dans sa liste blanche ; sinon il applique son action par défaut et le journal le dit.

#### FR-27 : Poste SOC en trois étapes
Le poste SOC enchaîne Comprendre, Vérifier, Décider. Réalise UJ-3.

**Consequences (testable) :**
- Comprendre : alerte, recommandation IA, une question à l'assistant choisie parmi trois (que se passe-t-il, que fait le système, quelle procédure).
- Vérifier : liste de reprise lue sur le moteur, en lecture seule.
- Décider : « J'interviens » est refusé avec le texte du sujet ; « Je fais confiance » ouvre l'épilogue.
- Aucun bouton ne répare.

#### FR-28 : Vérifications de reprise
Le moteur expose trois vérifications mesurées : API accessible, une opération métier réussit, données cohérentes (sujet p.3). Réalise UJ-1, UJ-3.

**Consequences (testable) :**
- Une vérification n'est jamais « ok » sans mesure ; pendant la panne elles sont ko ou en cours.
- La reprise n'est déclarée qu'une fois les trois vérifications ok.

#### FR-29 : Consigner l'incident (option)
Le Badge peut ajouter une note au journal d'incident, qui alimente le dossier de gouvernance. Réalise UJ-3.

**Consequences (testable) :**
- La note porte la source « badge » ; elle ne modifie aucun système.

### 4.11 Flux bloqués, mise en valeur et arrêt des attaques
**Description :** la salle de contrôle montre ce que la défense bloque, met en avant l'essentiel et laisse la place à la recommandation ; côté attaquant, chaque type d'attaque se lance et s'arrête vraiment. Réalise UJ-1, UJ-2, UJ-3.

#### FR-30 : Flux bloqués
La salle de contrôle affiche les flux bloqués par le WAF ou le SIEM (source, règle, nombre, cible). Réalise UJ-2, UJ-3.

**Consequences (testable) :**
- Sans WAF branché, la salle affiche « pas de WAF branché », jamais des blocages inventés.
- Une attaque de type injection fait apparaître des flux bloqués sans dégrader le service.

#### FR-31 : Mise en valeur
La santé, la durée de reprise et la recommandation IA sont plus grandes que le reste, et la colonne Badge laisse la place à la recommandation. Réalise UJ-1, UJ-3.

**Consequences (testable) :**
- Les trois éléments mis en avant restent lisibles à 3 mètres sur un écran projeté (corps de texte au moins deux fois plus grand que le journal).
- Aucun texte ne déborde de son cadre à 1280 par 720.

#### FR-32 : Arrêt fiable d'une attaque
Le bouton STOP arrête l'outil d'attaque et tous ses processus enfants, sur Linux comme sur Windows. Réalise UJ-2.

**Consequences (testable) :**
- Après STOP, aucun processus enfant ne survit et l'effet de l'attaque cesse sur la plateforme.
- Le terminal affiche « arrêté par l'opérateur », pas « échec du script » ; un événement `attack_ended` « arrêt demandé » est déclaré.
- STOP sans script en cours l'indique au lieu de ne rien faire.

#### FR-33 : Chaque type d'attaque lançable et arrêtable
Chaque niveau (inonder, épuiser, couper) et l'attaque de type injection se lancent puis s'arrêtent, vérifiés par un test. Réalise UJ-2.

**Consequences (testable) :**
- Un test lance puis arrête chaque niveau et vérifie l'état final.
- Les outils qui exigent des droits particuliers (saturation réseau) le disent avant le lancement.

### 4.12 Intégration, données pour l'IA et livraison
**Description :** ce qui relie la part de l'utilisateur à l'infra, à l'IA et aux rendus : conteneurs, métriques, actions du moteur, périmètre des attaques, données et documents pour le détecteur et l'assistant, archive et clip. Réalise UJ-1, UJ-2, UJ-4.

#### FR-34 : Conteneurs et déploiement
Chaque service de l'utilisateur a un Dockerfile et un exemple de compose que l'infra intègre à son déploiement. Réalise UJ-4.

**Consequences (testable) :**
- Les services démarrent par `docker compose up` ; la base et les secrets ne sont pas exposés au réseau pédagogique.
- L'authentification est un service distinct, comme le demande le sujet (p.4).

#### FR-35 : Métriques et journaux exploitables
La plateforme expose `/metrics` (Prometheus) et écrit des journaux JSON structurés pour Loki. Réalise UJ-4.

**Consequences (testable) :**
- `payment_requests_total{status}`, `payment_request_duration_seconds` et `payment_up` existent et évoluent pendant une attaque.
- Chaque ligne de journal est du JSON avec horodatage, service et niveau.

#### FR-36 : Remédiation selon le type d'incident
Le moteur choisit son action selon le type d'attaque ou de panne, et le sujet est expliqué dans une matrice attaque, détection, décision, action, vérification. Réalise UJ-1, UJ-3.

**Consequences (testable) :**
- La restauration de disponibilité n'est pas confondue avec la correction d'une compromission (sujet p.3) : l'injection est bloquée et vérifiée, pas seulement « redémarrée ».
- Une panne non malveillante (conteneur tué ou ralenti, chaos de jeudi) est aussi reprise.
- Les actions passent par un accès restreint (proxy Docker limité ou playbooks Ansible de l'infra), jamais par un accès total.
- L'attaque principale est décrite de façon reproductible et expliquée.

#### FR-37 : Garde-fou de périmètre
Les scripts d'attaque refusent toute cible hors du réseau du groupe. Réalise UJ-2.

**Consequences (testable) :**
- Une cible hors du réseau du groupe (192.168.137.0/24) ou de la machine locale est refusée avec un message clair (sujet p.5 et p.11).

#### FR-38 : Données et documents pour l'IA
Les attaques réelles produisent des données étiquetées pour le détecteur, et l'équipe fournit les documents du corpus de l'assistant. Réalise UJ-4.

**Consequences (testable) :**
- Le trafic et les métriques des attaques réelles sont capturés avec les fenêtres d'attaque déclarées comme étiquettes.
- Le corpus contient au moins le runbook d'incident, la description d'architecture et les scénarios d'attaque testés, sans donnée réelle ni secret.

#### FR-39 : Livraison
L'archive `Code.zip`, la procédure du clip, le build du jeu et la fiche de défense des emprunts sont prêts avant le gel. Réalise UJ-1.

**Consequences (testable) :**
- Une commande produit `Workshop2026-M2-G<n>-Code.zip` sans secret en clair (analyse de secrets passée).
- Le clip de 60 s se refait par une procédure écrite, en une prise, sans coupe masquant une action manuelle.
- Le jeu se lance sur le PC Hôte et le PC Attaquant (Windows inclus).
- Chaque outil emprunté a une fiche : pourquoi, licence, comment il fonctionne (test des 5 minutes).

#### FR-40 : Répétition
Une remise à zéro et une liste de contrôle permettent de répéter la démonstration à l'identique. Réalise UJ-1, UJ-4.

**Consequences (testable) :**
- La remise à zéro rend la plateforme à son état initial sans redéployer.
- La liste de contrôle vérifie réel seulement, rôles verrouillés, ports et accès avant chaque passage.

## 5. Non-Goals (Explicit)
- Pas de plateforme de paiement industrielle ni de vraie donnée bancaire.
- Pas d'infrastructure, de supervision ni de détection ML dans ce périmètre : ce sont les collègues.
- Le jeu n'est pas un jeu vidéo : pas de score, sauvegardes, inventaire, expressions animées ni version navigateur.
- Le jeu ne remplace pas le frontal web de paiement ; il porte le cockpit (décision de l'utilisateur).
- Aucun appel à un modèle génératif pendant la démonstration.

## 6. MVP Scope

### 6.1 In Scope
- Contrats et simulateur (FR-1 à FR-4), SI de paiement (FR-5 à FR-7), remédiation (FR-8, FR-9), arsenal (FR-10, FR-11), dashboard (FR-12, FR-13).
- Jeu (FR-14 à FR-18), premier chantier ; livrables de code (FR-19) ; salle de contrôle, score en direct, mode projection (FR-20, FR-21, FR-25) ; données pour la détection (FR-22) ; rôles et répétition (FR-23, FR-24) ; poste SOC, recommandation IA et vérifications de reprise (FR-26 à FR-28, option FR-29) ; flux bloqués, mise en valeur et arrêt fiable des attaques (FR-30 à FR-33) ; intégration, données pour l'IA, livraison et répétition (FR-34 à FR-40).

### 6.2 Out of Scope for MVP
- Rejouabilité rapide de l'autre route (G-6 du jeu) : seulement si le temps le permet.
- Art original : jamais ; seuls des assets libres réutilisés (FR-18).
- Dossier de gouvernance, rendus et clip : partagés avec l'équipe, hors de ce PRD.

## 7. Success Metrics

**Primary**
- **SM-1** : la boucle complète passe 10 fois de suite sans intervention (EX-12). Valide FR-8, FR-10.
- **SM-2** : après chaque reprise, une nouvelle transaction réussit. Valide FR-5, FR-7.
- **SM-3** : le passage tient en 5 minutes (jury local) et 3 minutes de démo (finale nationale). Valide FR-12, FR-14 à FR-17.

**Secondary**
- **SM-4** : le jeu est livré en 30 minutes ou moins, en réutilisant l'existant, avant le reste du développement. Valide FR-14 à FR-18.
- **SM-5** : le passage de simulé à réel ne change qu'un fichier de configuration. Valide FR-3.

**Counter-metrics (do not optimize)**
- **SM-C1** : vitesse de reprise obtenue en masquant un échec ou en simulant. Contrebalance SM-1 et SM-2.
- **SM-C2** : habillage du jeu au détriment de la fiabilité. Contrebalance SM-4.

## 8. Open Questions
1. Réutilisation d'un serveur de paiement : trace écrite du coach (P7) ?
2. Le PPTX du sujet est absent : qu'apporte-t-il de plus que le PDF ?
3. Quels 3 niveaux d'attaque, parmi les 5 de l'Attack Composer, pour le jeu ?
4. Qui implémente chaque contrat côté collègues, et pour quelle date ?
5. Quelles actions de remédiation précises (redémarrer, purger, bloquer) ?
6. Les tests du jeu et du labo sont-ils possibles sur un PC Hôte Windows avant mercredi ?
7. Conformité : le sujet impose React + Tailwind pour le tableau de bord (p.2, p.4) ; l'utilisateur a choisi de tout faire dans Ren'Py (2026-10-19). Risque de perte sur l'axe « Clip Chrono et dashboard » (4 points au jury local, 15 en finale) : à relire avec le coach ?

## 8 bis. Choix d'intégration à confirmer
- Actions du moteur : proxy Docker restreint ou playbooks Ansible de l'infra (le sujet fait des playbooks le vecteur d'automatisation, p.4).
- Authentification : service distinct (sujet p.4), minimal.
- Plan B : page React + Tailwind minimale en lecture seule, lisant les mêmes routes, pour couvrir l'exigence du sujet sans changer le choix de tout faire dans Ren'Py. Option, à décider.

## 9. Assumptions Index
- §4.1 : interfaces simulées = ML, assistant, supervision ; base et API de paiement réelles.
- §4.2 : cœur métier maison tant que la trace du coach n'existe pas.
- §4.4 : attaque principale = déni de service contrôlé, injection en second.
- §4.8 : le trafic synthétique du simulateur sert à voir et régler le détecteur ; le vrai jeu de données vient des vraies attaques (EX-07).
- §4.5 : cockpit dans Ren'Py, sans React (décision de l'utilisateur) ; budget propre, non estimé.
- §4.6 : 30 minutes suffisent parce qu'on réutilise l'existant (décision de l'utilisateur, 2026-10-19).
