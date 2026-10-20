# État du projet — 19/10/2026 (fin de session, avant clear)

Situation : B/D au départ de la session, travail en continu depuis. Point d'entrée des reprises suivantes.

## Point d'arrêt
- Démonstration lancée par l'utilisateur : encore en cours (`scripts/lancer.sh` avec `SIM_LLM=1`), à arrêter avec `scripts/arreter.sh` avant de relancer des tests.
- Tout est commité. `git status --short` vide à la fin de session.
- Dernière décision : D20 (audit des manques) + poste SOC refondu (D18) + salle de contrôle étendue (D19) + modèle externe optionnel en simulation (non numéroté dans graphify, voir TODO section N).
- Plan : 66 stories dans `_bmad-output/initiative-resilience-alpha/`, 40 exigences (FR-1 à FR-40) toutes couvertes, `tickets.py status` propre.

## Ce qui est fait et vérifié (par cas réel rejoué, pas supposé)
1. **Contrats d'interface** (`contrats/resilience-alpha.openapi.yaml`) : 11 routes, recommandation IA, flux bloqués, vérifications de reprise, événements déclarés.
2. **Simulateur** (`services/simulateur/`) : 4 niveaux d'attaque (charge, connexions lentes, saturation réseau, injection), arrêt (`/simulation/arret`), flux bloqués, scores, recommandation statique ou générée par modèle externe (optionnel), vérifications de reprise. Preuve : `smoke.py`, 18+ étapes passées.
3. **Jeu Ren'Py** (`renpy/`, SDK 8.5.3 hors dépôt dans `~/.local/opt`) : titre à 4 portes selon rôle, paiement, terminal (4 niveaux), poste SOC en 3 étapes (comprendre/vérifier/décider) avec recommandation IA, salle de contrôle unifiée (3 colonnes + score + flux bloqués + journal, mode projection), épilogue ZERO-TOUCH, écran injoignable, refus du mode démo si simulé ou rôle non verrouillé. Habillage : assets CC0/OFL réutilisés (voir `renpy/CREDITS.md`), palette néon-noir pixel.
4. **STOP fiable** : arrête l'outil ET ses processus enfants (Linux testé ; code Windows écrit, non testé), affiche « arrêté », déclare l'événement de fin.
5. **Garde-fou de périmètre** : scripts d'attaque refusent toute cible hors 192.168.137.0/24 et localhost.
6. **Tests automatisés** : `scripts/test-jeu.sh` (suite, ~21 parcours, ~78 vérifications, ~26 s) et `scripts/test-jeu.sh visuel` (captures). Tournent sur le port 8799, jamais sur la démonstration (8765). Ferment de force tout ce qu'ils lancent.
7. **Modèle externe (NanoGPT, optionnel)** : clé et modèle (`qwen/qwen3.8-27b-cybersecurity`) dans `~/.config/alpha/nanogpt.env` (hors dépôt, jamais committé — vérifié). Génère réponses d'assistant et recommandations en simulation seulement (`SIM_LLM=1`), désactivé par défaut, mis en cache, jamais appelé par les tests.

## Non vérifié / en attente
- **Bloc 3 (plateforme réelle)** : API, base, authentification, frontal web, santé, doc, tests — pas commencé.
- **Bloc 4 (chaîne réelle)** : attaque réelle, moteur de remédiation réel — pas commencé.
- **Audit des manques** (`analyse-manques.md`) : conteneurs/Dockerfile, `/metrics`, Ansible ou proxy Docker pour les actions du moteur, chaos, capture de trafic réel, corpus RAG, livraison (Code.zip, clip, build Windows, fiches de défense), remise à zéro — rien codé, tout planifié en stories (M1 à M10).
- **PPTX du sujet** : toujours absent.
- **Trace écrite du coach** (P7, réutilisation d'un serveur de paiement) : jamais demandée formellement par l'utilisateur à ce stade.
- **Build Windows du jeu** et test sur le PC Attaquant : non fait (ce poste est Linux).
- **5 décisions ouvertes** dans `analyse-manques.md` §4 : actions du moteur (proxy Docker ou Ansible), OS du poste attaquant, plan B React+Tailwind (oui/non), qui porte la gouvernance, qui assemble les rendus finaux.

## Références qui font foi
- Sujet : `Docs/Workshop-2026_BAC+5_Sujet_PROJECT RESILIENCE-ALPHA .docx.pdf` (fait foi en cas de conflit).
- Spec globale : `Docs/graphify-v3.1.txt` (décisions D1 à D20). Spec jeu : `Docs/graphify-jeu-v2.1.txt`.
- Plan détaillé : `_bmad-output/initiative-resilience-alpha/` (PRD, 66 stories, `TODO.md`, `analyse-manques.md`, `plan-design-renpy.md`, `carte-de-recherche.md`).
- PRD toujours en `draft` : jamais relu par l'utilisateur ni passé en `final`.

## Risques classés
**Bloquant** : aucun. **À voir** : 5 décisions ouvertes ci-dessus ; le code Windows de STOP non testé ; React+Tailwind du sujet non respecté (choix assumé, risque noté partout). **Non vérifié** : coût et limites du fournisseur NanoGPT.

## Décisions à prendre (par l'utilisateur, au prochain démarrage)
**Décision :** par quoi reprendre — bloc 3 (plateforme réelle), ou une des 5 décisions ouvertes, ou autre chose signalé par l'utilisateur.

## Remise en ordre proposée pour la reprise
1. Lire ce fichier + `_bmad-output/initiative-resilience-alpha/TODO.md` (section « Vue d'ensemble » en tête).
2. `scripts/arreter.sh` si une ancienne démo tourne encore, avant tout nouveau test.
3. Reprendre au bloc 3 sauf avis contraire de l'utilisateur.

## Mise a jour (meme jour, session 2) -- scenario, livrables, personas

Fait et prouve (jeu 24/24 parcours, visuel OK) :
- Services reels documentes et testes : doc d'API (docs/api/plateforme.md), README (services/),
  smoke.py pour paiement (10/10) et moteur (9/9, EX-08 REPRISE_OK mesuree).
- Mecanique QR de participation (compteur simulateur + page + QR segno + ecran cockpit s_vague) ;
  pilotage d'intensite borne cote arsenal (fils_depuis_compteur) ; script tunnel cloudflared.
- Copie refondue (axe coherent) : titre RESILIENCE ALPHA, accroche, 4 niveaux, message SOC.
- Boutons lisibles (etat desactive), terminal sans debordement, menu principal theme (plus de noir).
- Scenario guide Boucle B (touche D) : avant -> botnet "Vous etes le botnet" -> ne touchez a rien
  -> reprise mesuree -> repaiement -> ZERO-TOUCH, sans clavier. Repetition EX-12 (touche R, 10x).
- Personas "le tout" : LE CAPUCHON/l'attaquant, LA VIGIE/l'analyste, LE CLIENT/paiement,
  LA TOUR/supervision (nom + role + portrait).
- Livrables : scripts/livrer.sh (Code.zip sans secret, echoue si secret) ; docs/matrice-reprise.md
  (M4) ; docs/clip-chrono.md (procedure M8).

Reste (dependances) : visuel rearrange (facette 5, a montrer avant d'elargir) ; Boucles C/D
chronometrees ; RAG reel (Ollama, collegues) ; repetition et STOP sur Windows (PC Hote) ;
remise a zero reelle M9 ; PRD en final ; 5 decisions ouvertes (analyse-manques section 4).

Rien n'est commite. Plan de reference : ~/.claude/plans/o-vas-y-doc-5-refactored-wave.md.
