# Contrat d'intégration DEV ↔ INFRA — RESILIENCE-ALPHA

> **Pour l'équipe DEV.** L'INFRA déploie vos services dans la plateforme (Docker Compose sur `ra-docker`, piloté par Ansible).
> Pour chaque service que vous livrez, complétez la fiche de la section 3, puis répondez aux **questions de la section 6** : elles sont bloquantes pour l'intégration.

## 1. Ce que l'INFRA fournit / ce que le DEV fournit

| INFRA fournit | DEV fournit |
|---|---|
| PostgreSQL 17 (base, utilisateur, mot de passe injectés) | `frontend` (React) |
| WAF / reverse proxy TLS, seul point d'entrée | `api-payment` (API métier, transactions) |
| Prometheus, Grafana, Loki, Alertmanager | `auth` (authentification, JWT) |
| Sonde IPS `ra-ips` : `argus` + `flow-extractor` (10 features UNSW-NB15, appel de `POST /predict`) + blocage nftables de l'IP source | `ml-detector` (modèle Random Forest + `POST /predict`), **déployé sur `ra-ips`** |
| `txn-probe` : sonde transactionnelle synthétique | `remediation` (moteur de remédiation) |
| `socket-proxy-ctrl` : accès restreint à Docker pour la remédiation | `dashboard` (React + Tailwind) |
| Secrets chiffrés (SOPS) injectés en variables d'environnement | Schéma de base / migrations |

> L'assistant LLM (Ollama / RAG) est **mis de côté** pour l'instant.

### Architecture réseau

```
Attaquant ─▶ pfSense ─▶ [ ra-ips : pont transparent ] ─▶ ra-docker (WAF ─▶ frontend / api / auth / db …)
                          argus ▶ flow-extractor ▶ ml-detector ▶ blocage
```

Tout le trafic vers la plateforme traverse physiquement la sonde `ra-ips`. Elle tourne sur une VM séparée : un DoS qui sature `ra-docker` ne la prive pas de ressources.

## 2. Règles communes à tous les services

1. **Livraison** : un `Dockerfile` dans votre dépôt (chemin à indiquer), ou une image taguée (`nom:version`, jamais `latest`).
2. **Configuration uniquement par variables d'environnement.** Aucun secret dans le code, l'image ou le dépôt : l'INFRA les injecte.
3. **Santé** : une route `GET /health` qui renvoie `200` uniquement si le service est **réellement utilisable** (ex. l'API vérifie sa connexion à la base). Elle sert au `healthcheck` Docker et à la vérification de reprise.
4. **Métriques** (fortement recommandé) : `GET /metrics` au format Prometheus (nombre de requêtes, latence, erreurs). Bibliothèques : `prometheus-fastapi-instrumentator` (FastAPI), `prom-client` (Node.js), `client_golang` (Go).
5. **Journaux** sur la sortie standard, **une ligne JSON par événement** (`timestamp`, `level`, `service`, `message`, + `request_id` si possible). Loki les collecte automatiquement.
6. **Utilisateur non-root** dans l'image, et un seul processus par conteneur.
7. **Démarrage tolérant** : si la base n'est pas encore prête, le service réessaie au lieu de planter définitivement.
8. **Ports internes** fixes (ci-dessous). Aucun service n'est publié directement : tout passe par le WAF.

### Routage via le WAF (proposition)

| Chemin public | Service | Port interne |
|---|---|---|
| `/` | `frontend` | 8080 |
| `/api/` | `api-payment` | 8000 |
| `/auth/` | `auth` | 8001 |
| `/dashboard/` | `dashboard` (accès restreint) | 8080 |

Le préfixe est **conservé** jusqu'au service (ex. `/api/transactions` arrive tel quel sur `api-payment`).

Le WAF (OWASP CRS, paranoïa 1) bloque les requêtes jugées malveillantes avec un `403`. Si une requête légitime de votre application est bloquée, signalez-le : nous ajouterons une exclusion ciblée plutôt que de baisser la protection.

### Réseaux Docker (déjà créés sur `ra-docker`)

| Réseau | Contenu | Accès Internet |
|---|---|---|
| `front` | WAF ↔ `frontend`, `api-payment`, `auth`, `dashboard` | oui |
| `back` | `api-payment`, `auth` ↔ `db` | **non** (isolé) |
| `ctrl` | `remediation` ↔ `socket-proxy-ctrl` (et `dashboard` si besoin des événements) | **non** (isolé) |
| `obs` | Prometheus, Loki, Alertmanager : à rejoindre par tout service qui expose `/metrics` ou lit Prometheus | oui |

Le nom du service dans Compose doit être exactement celui de la colonne « Service » du routage (le WAF le résout par ce nom).

### Variables injectées par l'INFRA

| Variable | Destinataires | Exemple |
|---|---|---|
| `DATABASE_URL` | api-payment, auth | `postgresql://payment:***@db:5432/payment` |
| `JWT_SECRET` (ou `JWT_PUBLIC_KEY` / `JWT_PRIVATE_KEY`) | auth, api-payment | (secret SOPS) |
| `AUTH_URL` | api-payment, frontend | `http://auth:8001` |
| `PREDICT_URL` | flow-extractor (INFRA, sur `ra-ips`) | `http://ml-detector:8000/predict` |
| `PROMETHEUS_URL` | remediation, dashboard | `http://prometheus:9090` |
| `DOCKER_HOST` | remediation | `tcp://socket-proxy-ctrl:2375` |
| `LOG_LEVEL` | tous | `info` |

## 3. Fiche par service — à compléter

Recopiez ce bloc pour chaque service.

```yaml
service: api-payment
responsable:
source:                 # dépôt Git + chemin du Dockerfile, ou image:tag
langage:                # Node.js / Python-FastAPI / Go
port_interne: 8000
health: GET /health
metrics: GET /metrics   # oui / non
variables_requises:     # liste des noms (les valeurs secrètes sont fournies par l'INFRA)
depend_de: [db, auth]
volumes_persistants:    # chemins à conserver entre redémarrages, ou "aucun"
memoire_estimee:        # ex. 256 Mo
```

## 4. Points spécifiques

### 4.1 Base de données
- PostgreSQL **17**, déjà déployé : service `db`, base `payment`, utilisateur `payment`, réseau `back`. Mot de passe fourni dans `DATABASE_URL`.
- Sauvegarde chiffrée toutes les heures et restauration testée (PRA) : rien à prévoir de votre côté.

### 4.2 Transaction de test (sonde `txn-probe`) — indispensable pour prouver la reprise
La sonde rejoue en boucle (toutes les 5 s) une transaction fictive complète, via un compte de test dédié dont le mot de passe est stocké dans SOPS. Exemple de séquence : `POST /auth/login` → jeton → `POST /api/transactions` → `GET /api/transactions/{id}`.

### 4.3 `ml-detector` — modèle Random Forest (UNSW-NB15)
- **Déployé sur `ra-ips`**, à côté de la capture, pour limiter la latence. Il n'est joignable que par `flow-extractor` (aucune exposition).
- **Le modèle classe, l'INFRA agit** : `ml-detector` renvoie seulement une prédiction. C'est `flow-extractor` qui connaît l'IP source du flux et déclenche le blocage (nftables, avec expiration automatique et liste blanche).
- Les prédictions sont publiées dans Prometheus et Loki par l'INFRA (dashboard, SIEM).

Contrat repris de la demande ML, côté INFRA nous appelons :

```http
POST /predict
Content-Type: application/json

{"dur": 0.15, "spkts": 120, "dpkts": 80, "sbytes": 15000, "dbytes": 12000,
 "rate": 1333.33, "sload": 800000, "dload": 640000, "ct_srv_src": 25, "ct_dst_ltm": 40}
```

Réponse attendue :

```json
{"prediction": 1, "attack_type": "DoS", "dos_probability": 0.97, "model_version": "1.0"}
```

- Fréquence proposée par l'INFRA : flux **en cours** remontés toutes les **5 s** (enregistrements intermédiaires Argus), pas seulement à leur fermeture.
- `ct_srv_src` / `ct_dst_ltm` : calculés par l'INFRA sur les **100 dernières connexions**, selon la définition UNSW-NB15.

### 4.3 bis État de l'intégration du modèle (19/10)

Le modèle `attack_detector_rf_3classes.joblib` (version `experiment-e-rf-3classes`) est **intégré et en service** sur `ra-ips` :

- Classes : `Normal` (0), `DoS` (1), `Reconnaissance` (2). Les deux dernières peuvent déclencher un blocage.
- Servi par `ml-detector` (scikit-learn 1.7.2, identique à l'entraînement). L'empreinte SHA-256 du fichier est vérifiée au démarrage : un modèle modifié est refusé.
- `POST /predict` accepte un flux **ou une liste de flux** ; la sonde envoie des lots (toutes les 0,5 s) et la réponse ajoute `probabilities` pour chaque classe.
- Aucun prétraitement : les 10 features brutes, dans l'ordre de `features`.

**Résultat des essais sur la plateforme** (trafic réel traversant la sonde) :

| Scénario | Flux | Résultat |
|---|---|---|
| Trafic normal | 20 requêtes | classé `Normal` |
| Balayage de 1 500 ports | ~1 500 | **non détecté** : probabilité `Reconnaissance` max 0,014 |
| Flood HTTP (4 000 requêtes, 64 en parallèle) | ~4 000 | 5 flux classés `DoS`, probabilité max **0,37** : sous le seuil de 0,9, **aucune alerte** |

Le modèle, entraîné sur UNSW-NB15, ne reconnaît pas encore les attaques de notre laboratoire. **Demande à l'équipe IA** : réentraîner ou calibrer le modèle avec des flux capturés sur notre plateforme. L'INFRA peut fournir un export CSV des 10 features calculées par la sonde, étiquetées par scénario (normal, flood, scan), pour constituer ce jeu de données.

### 4.4 `remediation` — moteur de remédiation
- **Partage des rôles** : la sonde IPS **bloque l'attaquant** ; le moteur de remédiation **rétablit le service** (redémarrage d'un conteneur dégradé, vérification par `txn-probe`).
- **Entrées** possibles : webhooks Alertmanager (`POST /alerts`, format Alertmanager v4) et/ou événements de blocage publiés par la sonde IPS.
- **Accès Docker** : uniquement via `DOCKER_HOST=tcp://socket-proxy-ctrl:2375` (réseau `ctrl`). Le proxy n'autorise que : lister / inspecter les conteneurs, les redémarrer (`POST /containers/{id}/restart`). Toute autre requête reçoit un `403`.
- **Alertes** : Alertmanager enverra ses alertes en `POST` (format webhook Alertmanager v4) à l'URL que vous indiquerez.
- **Vérification** : la reprise est confirmée quand `txn-probe` repasse au vert (métrique `txn_probe_success == 1` dans Prometheus).
- **Événements** : merci d'exposer `GET /events` (historique horodaté : détection, décision, action, vérification) pour le dashboard, et d'écrire chaque étape dans les journaux JSON (traçabilité SIEM).

### 4.5 `dashboard`
- Sources : API Prometheus (`PROMETHEUS_URL`) + `GET /events` du moteur de remédiation.
- Doit montrer l'état du service **avant / pendant / après** l'incident (Clip Chrono) : statut de `txn-probe`, score ML, actions de remédiation.

## 5. Calendrier
- **Mardi midi** : fiches de la section 3 complétées + premières images, même incomplètes, pour câbler le déploiement.
- **Mardi soir** : `/health` fonctionnels, transaction de test utilisable par la sonde.
- **Mercredi** : branchement `ml-detector` + `remediation`, premiers tests de reprise.

## 6. Questions à l'équipe DEV

Merci de répondre directement sous chaque question.

**Général**
1. Souhaitez-vous que le WAF conserve le préfixe de chemin (`/api/…` arrive tel quel sur `api-payment`) ou qu'il le retire ?

**Base de données**

2. Comment le schéma est-il créé : script SQL d'initialisation, migrations (Alembic, Prisma…) lancées au démarrage ?
3. Quel jeu de données fictif initial (comptes, marchands) faut-il charger ?

**Transaction de test (`txn-probe`)**

4. Quel compte de test dédié la sonde doit-elle utiliser (identifiant) ?
5. Quelle est la séquence exacte d'appels pour une transaction complète ?
6. Quel est le critère de succès : code HTTP attendu et statut de la transaction dans la réponse ?

**`ml-detector`**

7. ~~Envoi unitaire ou par lot ?~~ **Réglé par l'INFRA** : le service accepte les deux, la sonde envoie des lots.
8. Quel **seuil de décision** déclenche le blocage (ex. `dos_probability >= 0.9`), et faut-il plusieurs flux suspects consécutifs pour la même IP avant de bloquer (limite les faux positifs) ?
9. Unités : confirmez-vous `sload` / `dload` en **bits/s** et `rate` en **paquets/s** (calcul actuel de la sonde) ? Le modèle n'a pas de prétraitement embarqué : une normalisation faite à l'entraînement serait à nous transmettre.
10. ~~Livraison de `ml-detector` ?~~ **Réglé** : modèle reçu, servi par l'INFRA (11 ms en moyenne par lot).
13. **Nouveau** : pouvez-vous réentraîner le modèle sur des flux capturés dans notre laboratoire (cf. 4.3 bis) ? Le format du fichier livré (dictionnaire `model`, `features`, `classes`, `class_to_id`, `version`) est parfait : merci de le conserver.

**`remediation`**

11. Quelle(s) entrée(s) utilisez-vous : webhooks Alertmanager, événements de blocage de la sonde IPS, ou les deux ?
12. Avez-vous besoin d'actions Docker autres que lister / inspecter / redémarrer ?
