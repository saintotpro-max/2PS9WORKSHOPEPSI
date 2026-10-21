# Arsenal de charge — origine et cadre

`_commun.py` (primitive de charge bornée) est **repris de l'équipe DEV**
(`2PS9WORKSHOPEPSI`, `attack/arsenal/_commun.py`), avec deux ajouts d'intégration :
contexte TLS pour le certificat autosigné du WAF, et lecture de la cible via
`ALPHA_PLATEFORME_URL`.

**Cadre strict (démonstration de résilience, lab uniquement) :**
- `cible_autorisee()` refuse toute cible hors de `ALPHA_PERIMETRE` (une seule /24 :
  la plateforme du lab). Impossible de viser le réseau de l'école ou Internet.
- Nombre de fils borné (`ATTAQUE_FILS_MIN`..`ATTAQUE_FILS_MAX`), durée bornée
  (`ATTAQUE_DUREE_S`). Requêtes HTTP ordinaires (`GET /health`) : afflux applicatif,
  pas d'attaque bas niveau.
- Les spectateurs ne génèrent aucune charge : ils incrémentent seulement le compteur
  de participation. La charge part uniquement de `ra-attacker` vers la plateforme du lab.
