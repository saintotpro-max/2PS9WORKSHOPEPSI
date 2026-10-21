# Accès aux interfaces web — RESILIENCE-ALPHA

Toutes les interfaces web du démonstrateur, comment les ouvrir et où trouver les identifiants.
Aucun mot de passe n'est écrit ici : ils sont dans les secrets chiffrés (SOPS) du dépôt.

## Vue d'ensemble

| Interface | Pour qui | Exposée sur le Wi-Fi ? | Accès |
|---|---|---|---|
| Application de paiement | utilisateurs, jury | oui (via pfSense) | `https://<IP WAN pfSense>/` |
| Dashboard de supervision | jury, équipe | oui (via pfSense), mot de passe | `https://<IP WAN pfSense>/dashboard/` |
| Grafana | équipe | non | tunnel SSH |
| Prometheus, Alertmanager, Loki | équipe | non | via Grafana |
| Interface pfSense | administrateur | non | tunnel SSH |
| API du modèle ML (`ml-detector`) | équipe IA | non | tunnel SSH |
| Moteur de remédiation | aucun accès direct | non | via le dashboard |

Les interfaces d'administration ne sont jamais exposées au réseau (exigence du sujet, § 4).

---

## 1. Interfaces publiques (via pfSense)

Prérequis : redirection WAN:443 → WAF configurée dans pfSense (cf. [pfsense.md](pfsense.md)).
Tout le trafic passe par pfSense, la sonde IPS puis le WAF (OWASP CRS).

| Chemin | Service | Authentification |
|---|---|---|
| `https://<IP WAN>/` | Caisse (application de paiement) | comptes `caissier`, `soc`, `demo` |
| `https://<IP WAN>/auth/token` | Authentification (API) | renvoie un jeton |
| `https://<IP WAN>/transactions` | Transactions (API) | jeton `Bearer` |
| `https://<IP WAN>/dashboard/` | **Dashboard de supervision** | utilisateur `jury` + mot de passe |
| `https://<IP WAN>/healthz` | Santé du WAF (renvoie `OK`) | — |

- `http://` redirige automatiquement vers `https://`.
- Certificat **autosigné** : accepter l'avertissement du navigateur une fois.
- Pendant une panne de l'application, une page « Service momentanément indisponible » s'affiche jusqu'à la reprise automatique.
- Mots de passe des comptes de l'application : `sops decrypt secrets/platform.enc.yml` (`paiement_password_*`).

**Mot de passe du dashboard** (depuis `ra-ansible`) :

```bash
sops decrypt --extract '["dashboard_password"]' ~/resilience-infra/secrets/platform.enc.yml
```

---

## 2. Interfaces d'administration (tunnel SSH)

Depuis le **PC hôte** (Windows : PowerShell ou Git Bash). Une seule commande ouvre tous les tunnels,
à laisser ouverte pendant l'utilisation :

```bash
ssh -N -L 3000:10.10.10.20:3000 -L 8443:10.10.10.1:443 -L 9443:10.10.10.20:443 sadmin@192.168.80.10
```

| Interface | Adresse locale | Identifiants |
|---|---|---|
| **Grafana** | http://localhost:3000 | `admin` + mot de passe (ci-dessous) |
| **pfSense** | https://localhost:8443 | compte admin de pfSense (défini à l'installation) |
| Plateforme sans passer par pfSense | https://localhost:9443/dashboard/ | `jury` + mot de passe (§ 1) |

**Mot de passe Grafana** (depuis `ra-ansible`) :

```bash
sops decrypt --extract '["grafana_admin_password"]' ~/resilience-infra/secrets/observability.enc.yml
```

### Dans Grafana

| Besoin | Où |
|---|---|
| Tableau de bord « Plateforme — état du service » | Dashboards → RESILIENCE-ALPHA |
| Tableau de bord « Sonde IPS — détection ML » | Dashboards → RESILIENCE-ALPHA |
| Requêtes Prometheus (métriques) | Explore → source **Prometheus** |
| Journaux Loki (WAF, sonde, remédiation…) | Explore → source **Loki**, ex. `{service="waf"}` |
| Alertes en cours (Alertmanager) | Alerting → source **Alertmanager** |

Requêtes Loki utiles :

| Journal | Requête |
|---|---|
| Requêtes bloquées par le WAF | `{service="waf"} \|= "ModSecurity: Access denied"` |
| Détections de la sonde IPS | `{service="flow-extractor"} \|= "suspect"` |
| Étapes de remédiation | `{service="remediation"}` |
| Système des VM | `{job="journal", host="ra-docker"}` |

### API du modèle ML (équipe IA)

Le service `ml-detector` n'écoute que sur `127.0.0.1` de `ra-ips` :

```bash
ssh -N -J sadmin@192.168.80.10 -L 8000:127.0.0.1:8000 sadmin@10.10.10.40
```

| Adresse locale | Rôle |
|---|---|
| http://localhost:8000/health | modèle chargé, version, classes |
| `POST` http://localhost:8000/predict | prédiction (un flux ou une liste) |

```bash
curl -s localhost:8000/predict -H 'Content-Type: application/json' -d '{"dur":0.15,"spkts":120,"dpkts":80,"sbytes":15000,"dbytes":12000,"rate":1333.33,"sload":800000,"dload":640000,"ct_srv_src":25,"ct_dst_ltm":40}'
```

---

## 3. Services internes (pas d'interface à ouvrir)

Joignables uniquement entre conteneurs ; leur état est visible dans le dashboard et Grafana.

| Service | Adresse interne | Rôle |
|---|---|---|
| Prometheus | `prometheus:9090` | métriques, règles d'alerte |
| Alertmanager | `alertmanager:9093` | envoi des alertes au moteur de remédiation |
| Loki | `loki:3100` | journaux |
| Moteur de remédiation | `remediation:8000` | `/events`, `/status` (lus par le dashboard) |
| Base de données | `db:5432` | PostgreSQL, réseau isolé `back` |

---

## 4. Machines (SSH)

| Machine | Commande (depuis le PC hôte) |
|---|---|
| `ra-ansible` | `ssh sadmin@192.168.80.10` |
| `ra-docker` | `ssh -J sadmin@192.168.80.10 sadmin@10.10.10.20` |
| `ra-ips` | `ssh -J sadmin@192.168.80.10 sadmin@10.10.10.40` |
| Console de secours | VMware Workstation → console de la VM, utilisateur `sadmin` |

SSH vers `ra-docker` et `ra-ips` n'est accepté que depuis `ra-ansible` : d'où le `-J` (rebond).

---

## Dépannage

| Symptôme | Cause probable |
|---|---|
| `https://<IP WAN>/` ne répond pas | redirection pfSense absente, ou PC pas sur le même Wi-Fi que pfSense |
| Page « Service momentanément indisponible » | service DEV non déployé ou en cours de redémarrage |
| `403 Forbidden` du WAF | requête jugée malveillante (journal : `{service="waf"}` dans Grafana) |
| Plus aucun accès depuis une machine de test | IP bloquée par la sonde IPS : `ssh … 10.10.10.40 sudo nft list set bridge ips blocked` |
| Tunnel refusé (`bind: Address already in use`) | un tunnel est déjà ouvert sur ce port local |
