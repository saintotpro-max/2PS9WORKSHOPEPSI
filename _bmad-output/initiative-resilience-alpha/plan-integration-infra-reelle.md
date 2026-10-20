# Plan d'integration — PR #1 "cockpit reel" + passage a l'infra reelle

But : integrer la PR du collegue (cible configurable + doc infra), reconcilier avec le
travail local non pousse, et corriger l'incoherence "l'IA affiche du texte sans decider".
Source de verite : `Docs/integration-infra-reelle.md` (apporte par la PR) et
`Docs/graphify-v3.1.txt` (contrat : attaque reelle -> detection autonome -> decision, zero-touch).

Etat au 2026-10-20. "On y est pas encore" : ce plan sequence, il n'execute pas tout.

## 0. Point de depart git

- `5a647f2` = base commune (origin/main).
- `cf0f40b` = travail local NON pousse (son, musique CC0, attaque niveau 1 reelle,
  SIM_LLM=1). Push bloque : `No anonymous write access` -> l'utilisateur doit pousser.
- `pr-1` (`f15b188`) = PR Thoinoo, branche depuis `5a647f2`.
- Chevauchement : les deux touchent `pont.rpy` dans des zones disjointes. Pas de conflit
  sur `interfaces.reel.json`, `options.rpy`, `attack/simule/_commun.py` (PR n'y touche pas).

## Lot 1 — Fusion mecanique (rapide, sans risque)

- AC1.1 : pousser `cf0f40b` sur `origin/main` (action utilisateur, auth requise).
- AC1.2 : `git merge pr-1` sur main -> fusion 3-way propre attendue ; verifier a la main
  la zone `pont.rpy` (`_lancer_processus` de la PR vs `_executer_niveau` local).
- AC1.3 : le jeu demarre, `scripts/test-jeu.sh` au vert (resume une ligne).
- AC1.4 : bouton "Changer la cible (C)" visible et fonctionnel sur `s_terminal`.
- Preuve : lancement local + test-jeu vert.

## Lot 2 — Coherence de la config (decision a acter)

Tension : `interfaces.reel.json` local = dev MIXTE local (plateforme 8770, niveaux 2-4 vers
le simulateur 8765). Le doc §7 decrit une config infra REELLE (WAN 443, tunnel, escalade).
Ce sont deux cibles de deploiement differentes.

- AC2.1 : separer en deux fichiers plutot que surcharger un seul :
  `interfaces.reel.json` (dev local mixte, existant) et `interfaces.infra.json` (WAN reel,
  gabarit du doc §7). Le bouton "Changer la cible" edite la plateforme.url du fichier actif.
- AC2.2 : documenter dans `services/README.md` quel fichier pour quel contexte.
- DECISION requise de l'utilisateur : garder deux fichiers (recommande) ou un seul commute.

## Lot 3 — Incoherence "l'IA ne decide pas" (le coeur)

Faire que la Sentinelle raconte la VRAIE decision autonome, pas le `reco()` simule.

- AC3.1 : en mode reel, `duel_defense_raison()` (duel.rpy) et le panneau Sentinelle sont
  alimentes par le dernier event `decision`/`action` reel
  (`…/remediation/events`), et affichent `recovery_seconds` du `…/status` (doc §3, §5.1).
- AC3.2 : `boucle_sante()` en mode reel lit les sources du doc §3 (events bruts, status,
  PromQL) au lieu des routes du simulateur (`/alerts` GET, `/verifications`, `/components`,
  `/scores`, `/flux-bloques`) qui n'existent pas sur le moteur reel.
- AC3.3 : UI — retirer ou griser "non branche" `rate_limit` et `scale_up` (doc §5.3) ;
  `block_source` presente comme observe (autonome IPS), pas commande.
- AC3.4 : `http_brut` passe un contexte TLS non verifie quand l'URL est https (WAF
  auto-signe, doc §8.1).
- Preuve : en pointant la config sur l'infra, le panneau Sentinelle affiche un message
  issu d'un vrai event moteur et le chrono de reprise reel.

## Lot 4 — Vague reelle (attaquant) via tunnel

- AC4.1 : `armer_vague` en mode reel POST sur `attaque.tunnel_url` + `?cible=`, URL lue
  depuis config ou env `RA_TUNNEL` (doc §8.3, §2.4).
- AC4.2 : garde-fous du doc §9 preserves (perimetre `10.60.64.0/22`, charge bornee, arret
  manuel). Ne rien retirer.

## Lot 5 — Mode Acteur (escalade N1) — BONUS, bloque par INFRA

- AC5.1 (optionnel) : decision Sentinelle appelle `attaque.escalade_url` (doc §6) au lieu
  d'un texte. BLOQUE tant que l'INFRA ne fournit pas le relais `/dashboard/api/escalade`.
- Jeton d'escalade cote `~/.config/alpha/*.env`, jamais commite (doc §7).
- Par defaut : mode Observateur (AC3), deja une demo honnete et complete.

## Dependances externes (a reclamer a INFRA)

- Relais d'escalade `/dashboard/api/escalade` (contrat doc §6).
- URL du tunnel courante (`ra-vague url`) et IP WAN courante.
- Confirmation des routes `…/remediation/events|status` et `…/prom/query`.

## Hors perimetre / garde-fous

- Jamais de jeton de remediation dans le jeu ni le depot.
- Jamais d'appel direct au moteur ou a Docker depuis le jeu.
- Le jour J : `SIM_LLM=0`, modele externe interdit, repli deterministe.

## Portes

- Porte Lot1 -> Lot2 : main fusionne, test-jeu vert.
- Porte Lot3 : panneau Sentinelle alimente par un vrai event en mode reel.
