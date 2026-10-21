# Plan — version réelle complète

> Persona dev (Amelia), généré le 21/10. Source : état des lieux 21/10 + Docs/integration-infra-reelle.md + collègue/workshop2026-main.
> Règle du jeu : une case se coche UNIQUEMENT après une preuve re-jouée. Rien n'est commité sans accord.

## Phase 0 — Hygiène du dépôt (aujourd'hui, 15 min) — FAIT
- [x] Commiter l'existant validé : `CHANGELOG.md`, `docs/rgpd.md`, `scripts/check-rgpd.py`, mention page publique simulateur → `78c4370`
- [x] Intégrer `collègue/workshop2026-main` → `infra/` (vendor en 1 commit, ORIGINE.md gardé, secrets SOPS chiffrés OK, clé age JAMAIS) → `257ad2a`
- [x] `scripts/check-rgpd.py` : 0 échec après l'ajout (403 fichiers) ; `scripts/livrer.sh` : scan secrets vert (370 fichiers après exclusion du doublon) ; `collègue/` ignoré

## Phase 1 — Jeu en mode réel (aujourd'hui, 60–90 min) — FAIT
- [x] `renpy/game/pont.rpy` `http_brut` : contexte TLS non vérifié si URL https (WAF auto-signé)
- [x] `renpy/game/pont.rpy` `boucle_sante` : adaptateurs réels — `/events` liste brute, `/status`, PromQL `ips_attack_probability_max` / `ips_blocks_total` ; `/components` et `/verifications` absents en réel → no-op propre
- [x] `renpy/game/pont.rpy` `armer_vague` : repli tunnel `attaque.tunnel_url` (armer, reset, QR)
- [x] `renpy/game/duel.rpy` : Sentinelle sur events réels — DÉJÀ EN PLACE (f15b188), vérifié
- [x] UI : `libelle_action()` grise `rate_limit`/`scale_up` en réel
- [x] `config/interfaces.infra-reelle.json` créée (URLs jour J à remplacer)
- [x] Preuve : `scripts/test-jeu.sh` 25/25 parcours, 95 vérifications (re-joué) → `6765da3`

## Phase 2 — Test sur CETTE machine (Linux) — FAIT (partie locale)
- [x] Suite `scripts/test-jeu.sh` : 25/25 (port 8799)
- [x] API simulateur vérifiée à la main : token + transaction 201
- [x] JSON des 3 configs validés
- [x] Limites notées en rétro : chemin HTTPS réel et rôle cockpit WAN → Phase 3 (lab)

## Phase 3 — Intégration lab (jeudi matin, avec le collègue)
- [ ] Wi-Fi dédié du groupe monté ; IP WAN relevée ; redirection `pfSense WAN:443 → WAF` (leur reste à faire)
- [ ] `ansible-playbook site.yml` relancé sur l'infra en place (`changed=0` attendu) ; Grafana + dashboard React visibles
- [ ] `BLOCK_ENABLED` sonde IPS : activé seulement si le modèle ré-entraîné (IA) détecte nos attaques — sinon alertes de charge seules (honnête, affiché tel quel)
- [ ] Relais d'escalade côté INFRA (mode Acteur Sentinelle) — sinon rester en Observateur (défaut, démo complète)
- [ ] Preuve croisée : 3 passages complets attaque → détection → remédiation → reprise mesurée (`txn_probe_success == 1`) sans intervention
- [ ] Côté jeu : `ALPHA_CONFIG=$PWD/config/interfaces.infra-reelle.json scripts/lancer.sh` + IP WAN via bouton C + `ALPHA_DEMO_PASSWORD` depuis `~/.config/alpha/`

## Phase 4 — FIABILISER (jeudi, avant 17 h)
- [ ] EX-12 : répétition du passage 10 fois de suite sans intervention (cible du sujet)
- [ ] STOP testé sur le PC Hôte Windows + build Windows du jeu
- [ ] Remise à zéro M9 : checklist de répétition à l'identique
- [ ] `scripts/livrer.sh` → `Code.zip` sans secret ; clip 60 s (procédure `docs/clip-chrono.md`) ; fiches des emprunts dans `CREDITS.md`

## Phase 5 — Vendredi, jury
- [ ] Passage 10 min : intro Ren'Py → attaque (ra-attacker) → détection ML → remédiation réelle → reprise mesurée → paiement sur la vraie caisse
- [ ] Dossier : matrice attaque/détection/decision/action/verification + phrases de gouvernance

## Dépendances hors de notre contrôle (à afficher honnêtement)
1. Wi-Fi dédié du groupe (redirection 443) — sinon demo en LAN limité, tableau avant/pendant/après quand même
2. Ré-entraînement du modèle sur flux lab (IA) — sinon `BLOCK_ENABLED=off`, la détection reste montrée « en cours d'entraînement »
3. Relais d'escalade INFRA — sinon Sentinelle en Observateur (complet et honnête)

## Réponses
- Version réelle à la fin : OUI — les 6 briques (plateforme, attaque, détection, remédiation, reprise mesurée, dashboard) sont déjà livrées et testées séparément ; il ne reste qu'à les câbler (Phases 1–3) et répéter (Phase 4).
- Testable sur cette machine : OUI pour le jeu, les tests et le rôle de cockpit/testeur (Wi-Fi du groupe, côté WAN) ; NON pour héberger les VMs du lab (elles tournent chez le collègue/PC VMware).
