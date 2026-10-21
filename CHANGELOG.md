# Etat du projet

Coche ce qui est fait. Trois niveaux : dev, jeu, infra et IA.

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
