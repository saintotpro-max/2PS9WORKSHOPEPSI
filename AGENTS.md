<!-- bmad:context -->
<!-- Verified 2026-10-19 against 4118213. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## WORKSHOP EPSI — PROJECT RESILIENCE-ALPHA

Workshop EPSI Bac+5 (octobre 2026) : plateforme de paiement fictive qui se rétablit seule après une attaque. Pour l'instant dossier documentaire sans code. Périmètre de l'utilisateur : dev, cyber et jeu Ren'Py ; infra et IA sont faites par ses collègues.

## Policy

- Le PDF du sujet dans `Docs/` fait foi ; en cas de conflit avec `graphify-v3.1.txt`, corriger le graphify, jamais le sujet.
- Ne jamais montrer, dans une démo, un clip ou un écran de jury, un résultat simulé comme réel : le mode simulé est affiché en clair.
- Aucun code d'attaque ni action offensive hors du SI fictif et des machines de l'équipe.
- Aucun secret ni clé d'API dans le dépôt ni dans `Code.zip`.
- Rien n'est commité ni installé sans accord de l'utilisateur.

## Where things are

- Spec globale : `Docs/graphify-v3.1.txt` (plan en PART 00, étapes EX-01..13 en PART 12). Spec du jeu : `Docs/graphify-jeu-v2.1.txt`.
- Les fichiers v3.0 et v2.0 sont périmés : ne pas les modifier ni s'y référer.
- Point d'entrée des reprises : `Docs/etat-projet-2026-10-19.md`.

## Running and verifying

- Le CLI `graphify` ne lit que du code : sur ce dossier il ne trouve rien, ne pas le relancer pour cartographier les Docs.
- Modèle externe pour la simulation seulement : `SIM_LLM=1 scripts/lancer.sh` ; clé et modèle dans `~/.config/alpha/nanogpt.env` (hors dépôt). Jamais pour le vrai assistant (Ollama local, sujet p.5), jamais le jour de la démonstration.
- Vérifier le jeu : `scripts/test-jeu.sh` (résumé d'une ligne, environ 15 s, ferme de force tout ce qu'il lance) ; captures : `scripts/test-jeu.sh visuel`. Simulateur : `services/simulateur/smoke.py`.
- Le PC Hôte du workshop est sous Windows ; ce poste est sous Linux. Tester le jeu et le labo sur Windows avant la démo.

## Conventions that differ from defaults

- Pas de sous-agents : John (`bmad-agent-pm`) mène, un autre persona seulement si un point technique l'exige.
- Les interfaces des collègues (infra, IA) se simulent par des contrats d'interface et un simulateur local ; le passage au réel ne change qu'un fichier de configuration.
- Ren'Py = pierre angulaire (« angularité » de l'utilisateur ne veut pas dire Angular), premier chantier, 30 minutes ou moins. Réutiliser d'abord (projets GitHub, GUI, assets, outils) et coder en dernier, carte dans `_bmad-output/initiative-resilience-alpha/carte-de-recherche.md` ; chaque emprunt dans `CREDITS.md` ; ne pas créer ni générer d'art si un équivalent existe.
- Tableau de bord : tout est fait dans le moteur Ren'Py, sans React (décision de l'utilisateur, 2026-10-19) alors que le sujet impose React + Tailwind (p.2, p.4) : risque assumé, ne pas le « corriger » sans demande.
- Téléchargements et installations du projet : automatiques, sans validation de l'utilisateur ; vérifier tout de même source, licence et santé du dépôt (carte de recherche).
- Les fichiers de `Docs/` sont en ASCII sans accents ; garder ce format.

## Known pitfalls

- Le mot « graphify » désigne le fichier de spec, pas l'outil CLI (voir le glossaire en mémoire projet).
- Le PPTX du sujet est absent de `Docs/` : ne pas citer son contenu comme vérifié.

<!-- /bmad:context -->
