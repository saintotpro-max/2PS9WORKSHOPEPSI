# Origine du service de paiement

Code fourni par l'équipe DEV : dépôt `saintotpro-max/2PS9WORKSHOPEPSI`, commit `3aa5e94`,
dossier `services/paiement/`. Copié ici pour livrer un dépôt unique ; les évolutions
fonctionnelles se font dans le dépôt de l'équipe DEV puis sont recopiées.

Adaptations d'intégration (côté INFRA, sans toucher au code) :
- comptes fournis par `ALPHA_USERS` depuis les secrets SOPS (plus de mots de passe par défaut) ;
- conteneur durci (capacités retirées, système de fichiers en lecture seule sauf `/data`) ;
- exposé uniquement via le WAF (`/` et `/auth/`), supervisé via `/health` et `/metrics`.
