# Etat du projet

Coche ce qui est fait. Trois niveaux : dev, jeu, infra et IA.

## Reste a faire — version reelle (dans l'ordre, simple)

1. [ ] Au lab : remplir 2 champs — IP WAN pfSense et URL du tunnel — dans `config/interfaces.infra-reelle.json` (l'IP se change au vol : bouton C du cockpit). 5 min.
2. [ ] Au lab : poser `ALPHA_DEMO_PASSWORD` dans `~/.config/alpha/` (valeur = cle `paiement_password_demo` de `infra/secrets/platform.enc.yml`, le collegue dechiffre). 2 min.
3. [ ] Au lab : `ALPHA_CONFIG=$PWD/config/interfaces.infra-reelle.json scripts/lancer-reel.sh` → sante affichee via le WAF reel. 5 min.
4. [ ] Preuve croisee 3 fois (avec le collegue) : attaque cockpit → detection → remediation → reprise mesuree sur le dashboard React.
5. [ ] EX-12 : 10 passages de suite sans intervention.
6. [ ] Sur le PC Hote Windows : STOP + build du jeu (code Windows jamais teste).
7. [ ] Remise a zero M9 + checklist pour rejouer a l'identique.
8. [ ] Jeudi 17 h : gel, `scripts/livrer.sh` (Code.zip), clip 60 s, fiches des emprunts.

Depend de l'exterieur : Wi-Fi dedie + redirection pfSense WAN:443 (collègue) ;
modele ML re-entraine sur flux lab (IA), sinon `BLOCK_ENABLED=off` affiche tel quel.

### Ou sont les branchements (chemins exacts)

| Branchement | Chemin | Etat |
|---|---|---|
| Jeu ↔ WAF reel (TLS, sante, evenements, PromQL) | `renpy/game/pont.rpy` | FAIT |
| Config du lab (2 champs) | `config/interfaces.infra-reelle.json` | PRET |
| Attaque reelle pilotee par le public | `infra/cockpit/attaque-reelle/niveau-N.py` | FAIT |
| Sentinelle ↔ vrais evenements du moteur | `renpy/game/duel.rpy` | FAIT |
| Compteur public + QR | tunnel cloudflared (`infra/ansible/roles/attacker/`), repli jeu `attaque.tunnel_url` | FAIT cote jeu |
| Relais d'escalade (mode Acteur) | `attaque.escalade_url` — A FOURNIR PAR INFRA | bonus, sinon Observateur |
| Mot de passe demo | variable `ALPHA_DEMO_PASSWORD` (env, hors depot) | PRET cote jeu |
| Vraie chaine testable sans le lab | `scripts/miroir-lab/` (lancer-miroir.sh + test-ex08.sh) | FAIT |

Verifications a relancer avant chaque etape : `scripts/test-jeu.sh` (25/25 attendu,
port 8799, jeu live ferme), `scripts/check-rgpd.py` (0 echec),
`bash scripts/miroir-lab/lancer-miroir.sh` + `test-ex08.sh` (chaine reelle locale).
Historique detaille : `docs/retro-2026-10-21.md` et `docs/plan-version-reelle.md`.

## Dev

- [x] Plateforme de paiement : API transactions, auth, sante honnete.
- [x] Plateforme : etat degrade sous charge (latence de la sonde, taux d'echec).
- [x] /metrics expose et journaux JSON.
- [x] Moteur de remediation : choisit l'action, verifie la reprise par une vraie transaction.
- [x] Arsenal d'attaque : niveau 1 reel sur /transactions, perimetre verrouille, STOP fiable.
- [x] Contrats d'interface + simulateur, bascule simule / reel par un seul fichier.
- [x] Boucle reelle locale : paiements en fond, attaque, detecteur seuil, alerte, decision, reprise.
- [ ] Service d'auth separe.
- [ ] Matrice attaque, detection, decision, action, verification (pour le dossier).
- [ ] Pannes non malveillantes reprises (chaos).
- [x] Commande de livraison Code.zip avec scan des secrets (scripts/livrer.sh).
- [x] Dossier RGPD europeen : docs/rgpd.md, verifications automatisees hors ligne (scripts/check-rgpd.py), mention sur la page du public.
- [x] Miroir local du lab (scripts/miroir-lab/) : la vraie chaine EX-08 rejouee sur ce poste — paiement conteneurise (compose), VRAI moteur de remediation INFRA, WAF mock HTTPS autosigne, sonde Prometheus a vraies mesures. Test automatique test-ex08.sh : alerte -> decision -> redemarrage conteneur reel -> reprise verifiee par transaction (5 s) + garde-fou liste blanche (base refusee). OK.
- [ ] Remise a zero reelle et liste de controle pour repeter a l'identique.
- [ ] Clip 60 s, build Windows, fiches des outils empruntes.

## Jeu

- [x] 6 ecrans et HUD, habille, teste (25 parcours).
- [x] Paiement reel (bouton PAYER), resultat honnete.
- [x] Terminal d'attaque, cible configurable, STOP.
- [x] Poste SOC en 3 etapes, refus de l'intervention manuelle.
- [x] Salle de controle, roles verrouilles, refus du mode demo simule, epilogue, repetition.
- [x] Match des 2 IA dans la salle : personas LLM, escalade 1 a 4, contre-mesure, un canal par IA.
- [x] La Sentinelle rapporte la vraie decision du moteur.
- [x] Son et musique CC0, credits des assets.
- [x] LLM rapide (gemma), varie a chaque replay.
- [ ] Colonne plateforme vivante (latence, debit, vert vers rouge).
- [ ] Recommandation de la Sentinelle branchee sur le vrai signal.
- [ ] Teste sur le PC Hote Windows.

## Infra et IA

- [ ] Conteneurs et deploiement (Docker, compose).
- [ ] Collecte Prometheus et Loki.
- [ ] WAF ou IPS, liste des flux bloques exposee.
- [ ] Actionneur sur : Docker restreint ou Ansible ou relais escalade.
- [ ] pfSense : WAN 443 et tunnel, adresse et URL a donner.
- [ ] Page QR du public (en cours cote infra).
- [ ] Detecteur ML : score et alertes vers le moteur, serie des scores.
- [ ] Assistant RAG derriere /assistant/ask.
