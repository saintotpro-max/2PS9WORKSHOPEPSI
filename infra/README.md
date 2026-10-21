# RESILIENCE-ALPHA — Infrastructure

Pilier INFRA du démonstrateur : machines virtuelles, segmentation réseau, sonde IPS à base de
machine learning, WAF, observabilité, secrets, sauvegardes et reprise. Tout est décrit en code
(Ansible) et se redéploie à l'identique avec une seule commande.

## Architecture

```
                      Wi-Fi (point d'accès du groupe)
                                  │
                          ┌───────┴────────┐
 PC Attaquant ──────────▶ │   ra-pfsense   │  pare-feu, NAT, segmentation
                          └───────┬────────┘
                                  │ LAN 10.10.10.0/24 (VMnet6)
                 ┌────────────────┼──────────────────┐
           ra-ansible       ┌─────┴──────────────┐   │
           10.10.10.10      │      ra-ips        │   │ admin 10.10.10.40
           (contrôle)       │ pont transparent   │───┘
                            │ argus ▶ features ▶ │
                            │ modèle RF ▶ blocage│
                            └─────┬──────────────┘
                                  │ VMnet12 (côté serveurs)
                          ┌───────┴────────────────────────────────┐
                          │ ra-docker 10.10.10.20                   │
                          │  waf (OWASP CRS) ─▶ frontend/api/auth   │  réseau front
                          │  db PostgreSQL 17                       │  réseau back (isolé)
                          │  socket-proxy-ctrl ◀─ remédiation       │  réseau ctrl (isolé)
                          │  Prometheus, Grafana, Loki, Alertmanager│  réseau obs
                          └─────────────────────────────────────────┘
```

| VM | Rôle | Ressources | Adresses |
|---|---|---|---|
| `ra-pfsense` | Pare-feu, NAT, segmentation | 2 Go / 2 vCPU | WAN : Wi-Fi (pont), LAN `10.10.10.1` |
| `ra-ansible` | Nœud de contrôle : Ansible, SOPS, clé age | 2 Go / 1 vCPU | admin `192.168.80.10` (NAT VMware), LAN `10.10.10.10` |
| `ra-ips` | Sonde IPS en coupure (pont `br0` entre VMnet6 et VMnet12) | 2 Go / 2 vCPU | admin `10.10.10.40` (hors pont) |
| `ra-docker` | Plateforme conteneurisée | 8 Go / 6 vCPU | `10.10.10.20` |
| `ra-ia` | LLM local (Ollama) — **mis de côté, VM éteinte** | 8 Go / 4 vCPU | `10.10.10.30` |

VM Linux : Debian 13, utilisateur `sadmin`, connexion par clé SSH uniquement.

## Ce qui est déployé

| Domaine | Composants | Détail |
|---|---|---|
| **Sonde IPS (ML)** | `argus`, `flow-extractor`, `ml-detector` sur `ra-ips` | Capture du trafic de la plateforme, calcul des 10 features UNSW-NB15 (flux en cours remontés toutes les 5 s), prédiction par lots avec le **Random Forest de l'équipe IA** (Normal / DoS / Reconnaissance, empreinte vérifiée), blocage nftables de l'IP source avec expiration. **Blocage en mode simulation** : le modèle ne détecte pas encore nos attaques de labo (cf. contrat DEV, 4.3 bis). |
| **WAF** | nginx + ModSecurity v3 + OWASP CRS 4.30 | Seul point d'entrée (HTTPS), routage vers les services DEV, dashboard protégé par mot de passe, journal d'audit JSON. |
| **Données** | PostgreSQL 17 + exporter | Réseau `back` sans sortie. Sauvegarde chiffrée toutes les heures. |
| **Observabilité** | Prometheus, Alertmanager, Grafana, Loki, Alloy, node-exporter, cAdvisor, blackbox | Tableaux de bord « Plateforme — état du service » et « Sonde IPS — détection ML ». Alertes : cible injoignable, CPU, sonde HTTP, DoS détecté, IP bloquée, modèle injoignable, sauvegarde ancienne. |
| **Accès Docker maîtrisé** | `docker-socket-proxy` | Supervision : lecture seule. Remédiation : inspection + redémarrage uniquement. Aucun conteneur applicatif n'accède au socket Docker. |
| **Durcissement** | nftables, DOCKER-USER, SSH | Pare-feu d'entrée par hôte (SSH seulement depuis `ra-ansible`), ports publiés restreints (Grafana, Loki), SSH sans mot de passe ni root. |
| **Secrets** | SOPS + age | Fichiers `secrets/*.enc.yml` chiffrés ; clé privée uniquement sur `ra-ansible`. |
| **Reprise (PRA)** | `70-backup`, `71-restore` | Sauvegardes chiffrées avec la clé publique age, restauration testée de bout en bout. |

## Arborescence

```
ansible/
  inventory/            hôtes, variables par groupe, versions épinglées
  playbooks/            00-control … 71-restore (voir ci-dessous)
  roles/                common, hardening, docker, ips, observability, obs_agent,
                        platform, backup, ollama, sops_tools
  site.yml              déploiement complet
ips/                    code de la sonde IPS (argus, flow-extractor, faux modèle)
secrets/                secrets chiffrés (SOPS)
docs/                   contrat DEV, exploitation, pfSense
tools/                  générateurs des tableaux de bord Grafana
```

| Playbook | Effet |
|---|---|
| `00-control` | sops + age sur le nœud de contrôle |
| `10-base` | paquets, fuseau horaire, NTP |
| `15-hardening` | pare-feu d'entrée (retour arrière automatique si l'accès est perdu), SSH |
| `20-docker` | Docker Engine + Compose |
| `40-ips` | sonde IPS |
| `50-observability` | pile de supervision + agent de `ra-ips` |
| `60-platform` | WAF, base de données, accès Docker de la remédiation |
| `70-backup` | sauvegardes chiffrées horaires |
| `71-restore` | restauration de la base (PRA) |

## Déployer

Depuis `ra-ansible` :

```bash
cd ~/resilience-infra/ansible
ansible-playbook site.yml            # tout (idempotent : relançable sans risque)
ansible-playbook playbooks/60-platform.yml   # une seule brique
```

Le déploiement complet relancé sur l'infrastructure en place ne modifie rien (`changed=0`).

Exploitation courante (accès Grafana, secrets, sauvegardes, sonde IPS) : [docs/exploitation.md](docs/exploitation.md).
Intégration des services de l'équipe DEV : [docs/contrat-integration-dev.md](docs/contrat-integration-dev.md).
Configuration de pfSense : [docs/pfsense.md](docs/pfsense.md).
Schémas (Mermaid + PNG) : [docs/schemas.md](docs/schemas.md).
Accès aux interfaces web : [docs/acces-interfaces.md](docs/acces-interfaces.md).

## Reste à faire

| Sujet | Dépend de |
|---|---|
| Modèle qui détecte les attaques du labo (réentraînement sur nos flux), puis activer le blocage (`BLOCK_ENABLED`) | Équipe IA |
| Redirection pfSense WAN:443 → WAF | Point d'accès Wi-Fi dédié du groupe (pas sur le Wi-Fi du campus) |
