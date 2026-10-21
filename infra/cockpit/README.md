# Cockpit Ren'Py ↔ infra réelle (Option 1)

Le cockpit Ren'Py (dépôt `2PS9WORKSHOPEPSI`) sert d'habillage narratif. La **preuve
live** (attaque → détection → remédiation → reprise) est montrée sur **notre dashboard**
(`https://<IP WAN>/dashboard/`). Ici, on câble seulement :

- **le bouton « attaque » du jeu → notre vraie vague** de charge (sur `ra-attacker`) ;
- *(optionnel)* **« payer » → notre vraie caisse**.

## Mise en route

1. **Lancer le simulateur** du jeu (pour les panneaux cockpit moteur/détection/assistant,
   qui restent en mode narratif) : `scripts/lancer.sh` côté dépôt du jeu — mais avec
   notre config :

   ```sh
   export ALPHA_CONFIG=/chemin/absolu/vers/resilience-infra/cockpit/interfaces.reel.json
   ```

2. **Adapter `interfaces.reel.json`** (dans ce dossier) :
   - `plateforme.url` → l'IP WAN actuelle de pfSense (ex. `https://10.60.64.36`) ;
   - `attaque.dossier` → le chemin **absolu** de `cockpit/attaque-reelle`.

3. **Déclenchement de la vague** : quand l'opérateur lance un niveau dans le cockpit,
   le jeu exécute `attaque-reelle/niveau-N.py`, qui **arme notre vraie vague**
   (`ra-attacker`). Le PC hôte ne génère aucune charge ; il ne fait qu'armer.
   Variable `RA_PARTICIPATION` si l'IP de `ra-attacker` change (défaut `http://192.168.80.50:8088`).

## « Payer » sur la vraie caisse (optionnel)

Le jeu appelle `plateforme.url` en HTTP simple. Notre caisse est en **HTTPS avec
certificat auto-signé** : la lib du jeu rejette le certificat. Deux options côté équipe DEV :

- **Accepter le certificat auto-signé** : dans `renpy/game/pont.rpy`, fonction
  `http_brut`, passer un contexte TLS non vérifié à `urlopen` :

  ```python
  import ssl
  _CTX = ssl._create_unverified_context()
  # ...
  with urllib.request.urlopen(requete, timeout=timeout,
                              context=_CTX if base.startswith("https") else None) as r:
  ```

  et utiliser le compte `demo` (mot de passe dans `secrets/platform.enc.yml`,
  clé `paiement_password_demo`) au lieu de `demo/demo`.

- **Ou** laisser `plateforme` en simulé et montrer la vraie caisse dans un navigateur
  (`https://<IP WAN>/`) au moment du paiement.

## Résumé du jour J

| Élément | Où |
|---|---|
| Intro / cockpit narratif | Ren'Py (simulateur) |
| Lancement de l'attaque | bouton cockpit → vraie vague `ra-attacker` |
| QR public de participation | `ra-vague url` sur `ra-attacker` (tunnel) |
| **Preuve : détection + remédiation + reprise** | **notre dashboard** `https://<IP WAN>/dashboard/` |
| Paiement avant/après | vraie caisse `https://<IP WAN>/` |
