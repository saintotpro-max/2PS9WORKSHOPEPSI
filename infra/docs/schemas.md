# Schémas — RESILIENCE-ALPHA

Légende commune : les éléments en **pointillés** sont fournis par l'équipe DEV et pas encore intégrés.

Versions images (pour le dossier et la présentation) : [docs/schemas/](schemas/).

1. [Architecture technique](#1-architecture-technique)
2. [Services et réseaux Docker de la plateforme](#2-services-et-réseaux-docker-de-la-plateforme)
3. [Chaîne de défense en profondeur](#3-chaîne-de-défense-en-profondeur)
4. [Scénario d'incident : détection et reprise automatique](#4-scénario-dincident--détection-et-reprise-automatique)
5. [Pipeline de la sonde IPS](#5-pipeline-de-la-sonde-ips)
6. [Observabilité : métriques, journaux, alertes](#6-observabilité--métriques-journaux-alertes)
7. [Flux réseau autorisés](#7-flux-réseau-autorisés)
8. [Déploiement et gestion des secrets](#8-déploiement-et-gestion-des-secrets)
9. [Sauvegarde et restauration (PRA)](#9-sauvegarde-et-restauration-pra)

---

## 1. Architecture technique

Machines virtuelles VMware Workstation sur le PC hôte, réseaux virtuels et plan d'adressage.

```mermaid
flowchart TB
    subgraph WIFI["Wi-Fi — point d'accès du groupe"]
        ATT["PC Attaquant"]
        HOTE["PC Hôte Windows<br/>VMware Workstation"]
    end

    subgraph VMNET2["VMnet2 — pont sur le Wi-Fi"]
        PFW["ra-pfsense · WAN vmx0<br/>DHCP du Wi-Fi"]
    end

    subgraph VMNET4["VMnet4 — NAT VMware 192.168.80.0/24"]
        ANSA["ra-ansible · nic0<br/>192.168.80.10"]
    end

    subgraph VMNET6["VMnet6 — LAN 10.10.10.0/24"]
        PFL["ra-pfsense · LAN vmx1<br/>10.10.10.1"]
        ANSL["ra-ansible · nic1<br/>10.10.10.10"]
        IPSA["ra-ips · nic0 admin<br/>10.10.10.40"]
        IPS1["ra-ips · nic1<br/>port du pont"]
    end

    subgraph VMNET12["VMnet12 — segment serveurs"]
        IPS2["ra-ips · nic2<br/>port du pont, capture Argus"]
        DOCK["ra-docker<br/>10.10.10.20"]
    end

    IA["ra-ia · 10.10.10.30<br/>Ollama — VM éteinte, mise de côté"]

    ATT -- "HTTPS vers l'IP WAN" --> PFW
    HOTE -- "SSH admin" --> ANSA
    PFW --- PFL
    ANSA --- ANSL
    PFL --- IPS1
    IPS1 <== "br0 : pont transparent" ==> IPS2
    IPS2 --- DOCK
    ANSL -. "SSH Ansible" .-> IPSA
    ANSL -. "SSH Ansible, via le pont" .-> DOCK
    IA -.- VMNET6

    classDef off fill:#eee,stroke:#999,color:#777,stroke-dasharray: 5 5
    class IA off
```

| VM | Rôle | RAM / vCPU |
|---|---|---|
| `ra-pfsense` | Pare-feu, NAT, segmentation | 2 Go / 2 |
| `ra-ansible` | Nœud de contrôle (Ansible, SOPS, clé age) | 2 Go / 1 |
| `ra-ips` | Sonde IPS en coupure | 2 Go / 2 |
| `ra-docker` | Plateforme conteneurisée | 8 Go / 6 |

---

## 2. Services et réseaux Docker de la plateforme

Sur `ra-docker`. Les réseaux `back` et `ctrl` sont internes : aucun accès à Internet.

```mermaid
flowchart TB
    IN(["Trafic entrant · 10.10.10.20:443"])

    subgraph FRONT["réseau front"]
        WAF["waf<br/>nginx + ModSecurity · OWASP CRS 4.30"]
        FE["frontend"]
        API["api-payment"]
        AUTH["auth"]
        DASH["dashboard"]
    end

    subgraph BACK["réseau back — interne, sans Internet"]
        DB[("db · PostgreSQL 17")]
        PGX["postgres-exporter"]
    end

    subgraph CTRL["réseau ctrl — interne, sans Internet"]
        REM["remediation"]
        SPC["socket-proxy-ctrl<br/>inspection + redémarrage"]
    end

    subgraph OBS["réseau obs"]
        STACK["Prometheus · Alertmanager<br/>Grafana · Loki"]
        ALLOY["Alloy"]
        SPO["socket-proxy<br/>lecture seule"]
    end

    SOCK[["socket Docker de l'hôte"]]

    IN --> WAF
    WAF -- "/" --> FE
    WAF -- "/api/" --> API
    WAF -- "/auth/" --> AUTH
    WAF -- "/dashboard/ · mot de passe" --> DASH
    API & AUTH --> DB
    PGX --> DB
    STACK -. "relève" .-> PGX
    STACK -. "webhook d'alerte" .-> REM
    REM --> SPC --> SOCK
    ALLOY --> SPO --> SOCK

    classDef dev stroke-dasharray: 5 5
    class FE,API,AUTH,DASH,REM dev
```

---

## 3. Chaîne de défense en profondeur

Chaque couche traite une menace différente ; une attaque doit les traverser toutes.

```mermaid
flowchart LR
    A(["Attaquant"]) --> L1
    L1["1 · pfSense<br/>filtrage WAN<br/>seul le port 443 redirigé"] --> L2
    L2["2 · Sonde IPS ML<br/>Random Forest sur les flux<br/>blocage de l'IP source"] --> L3
    L3["3 · WAF OWASP CRS<br/>injections, XSS, scanners<br/>réponse 403"] --> L4
    L4["4 · Segmentation Docker<br/>base sur réseau interne<br/>accès Docker filtré"] --> L5
    L5[("5 · Données<br/>sauvegardes chiffrées<br/>restauration testée")]

    L2 -. "DoS / saturation" .-> X1["IP bloquée 10 min<br/>nftables"]
    L3 -. "requête malveillante" .-> X2["403 + journal d'audit"]
```

| Couche | Menace traitée | Mécanisme |
|---|---|---|
| pfSense | Exposition inutile | Seul le 443 est redirigé vers le WAF |
| Sonde IPS | Déni de service, saturation | Classification ML des flux, blocage nftables avec expiration |
| WAF | Attaques applicatives | Règles OWASP CRS, score d'anomalie |
| Segmentation | Rebond après compromission | Réseaux internes, proxys Docker à droits minimaux, pare-feu des hôtes |
| Données | Perte ou corruption | Sauvegarde chiffrée toutes les heures, PRA testé |

---

## 4. Scénario d'incident : détection et reprise automatique

Déroulé visé pour la démonstration (aucune intervention humaine).

```mermaid
sequenceDiagram
    autonumber
    actor ATT as PC Attaquant
    participant PF as pfSense
    participant IPS as Sonde IPS (ra-ips)
    participant ML as ml-detector (RF)
    participant API as WAF + API (ra-docker)
    participant PROM as Prometheus / Alertmanager
    participant REM as Remédiation
    participant PROBE as txn-probe

    PROBE->>API: transaction fictive toutes les 5 s
    API-->>PROBE: OK — service sain
    ATT->>PF: flood HTTP
    PF->>IPS: trafic redirigé vers 443
    IPS->>API: trafic transmis (pont)
    Note over API: saturation, transactions en échec
    API-->>PROBE: erreur / délai dépassé
    loop toutes les 5 s, par flux
        IPS->>ML: POST /predict (10 features)
        ML-->>IPS: DoS, probabilité 0,97
    end
    IPS->>IPS: 3 flux suspects : IP bloquée
    ATT-xIPS: paquets rejetés
    IPS->>PROM: ips_blocks_total, journal JSON
    PROM->>REM: alerte (webhook)
    REM->>API: redémarrage du conteneur dégradé (socket-proxy-ctrl)
    PROBE->>API: nouvelle transaction
    API-->>PROBE: OK
    PROBE->>PROM: txn_probe_success = 1
    REM->>PROM: reprise confirmée
```

---

## 5. Pipeline de la sonde IPS

Fonctionnement interne de `ra-ips`.

```mermaid
flowchart LR
    NIC["nic2<br/>port serveurs du pont"] --> ARGUS["argus<br/>enregistrement de flux<br/>toutes les 5 s"]
    ARGUS -- "ra : CSV" --> AGG

    subgraph FX["flow-extractor"]
        AGG["Cumul par flux<br/>paquets, octets, durée"]
        FEAT["10 features UNSW-NB15<br/>dur, spkts, dpkts, sbytes, dbytes,<br/>rate, sload, dload,<br/>ct_srv_src, ct_dst_ltm"]
        WIN["Fenêtre des<br/>100 dernières connexions"]
        DEC{"DoS ≥ 0,9<br/>et 3 flux en 30 s ?"}
        AGG --> FEAT
        WIN --> FEAT
    end

    FEAT -- "POST /predict" --> ML["ml-detector<br/>Random Forest"]
    ML -- "prediction, probabilité" --> DEC
    DEC -- "non" --> OK(["flux laissé passer"])
    DEC -- "oui" --> AL{"IP en liste<br/>blanche ?"}
    AL -- "oui" --> LOG(["journalisé seulement"])
    AL -- "non" --> NFT["nftables bridge ips<br/>set blocked, expiration 10 min"]
    FX --> OUT["Prometheus : métriques :9101<br/>Loki : journaux JSON"]

```

---

## 6. Observabilité : métriques, journaux, alertes

```mermaid
flowchart LR
    subgraph SRC["Sources"]
        NE1["node-exporter<br/>ra-docker"]
        NE2["node-exporter<br/>ra-ips"]
        CAD["cAdvisor<br/>conteneurs"]
        PGX["postgres-exporter"]
        IPSM["sonde IPS :9101"]
        BB["blackbox<br/>sondes HTTP"]
        BK["sauvegardes<br/>métrique textfile"]
        CT["journaux des<br/>conteneurs + journald"]
    end

    PROM["Prometheus<br/>rétention 7 j"]
    LOKI["Loki<br/>rétention 7 j"]
    AL1["Alloy ra-docker"]
    AL2["Alloy ra-ips"]
    AM["Alertmanager"]
    GRAF["Grafana<br/>Plateforme · Sonde IPS"]
    REM["Remédiation"]

    NE1 & NE2 & CAD & PGX & IPSM & BB --> PROM
    BK --> NE1
    CT --> AL1 & AL2
    AL1 & AL2 --> LOKI
    PROM -- "règles d'alerte" --> AM
    AM -. "webhook" .-> REM
    PROM & LOKI & AM --> GRAF

    classDef dev stroke-dasharray: 5 5
    class REM dev
```

| Alerte | Déclencheur |
|---|---|
| CibleInjoignable | une cible ne répond plus depuis 1 min |
| CpuSature | CPU d'un hôte > 90 % pendant 2 min |
| SondeHttpEnEchec | sonde HTTP en échec |
| IpsDosDetecte | flux classés DoS par le modèle |
| IpsIpBloquee | IP bloquée par la sonde |
| IpsModeleInjoignable | `/predict` ne répond plus |
| SauvegardeBaseAncienne | dernière sauvegarde > 2 h |

---

## 7. Flux réseau autorisés

Tout flux absent de ce schéma est refusé par les pare-feu des hôtes.

```mermaid
flowchart LR
    ATT["Clients Wi-Fi<br/>dont PC Attaquant"]
    HOTE["PC Hôte"]
    PF["pfSense<br/>10.10.10.1"]
    ANS["ra-ansible<br/>10.10.10.10"]
    IPS["ra-ips<br/>10.10.10.40"]
    DOCK["ra-docker<br/>10.10.10.20"]
    NET(["Internet"])

    ATT -- "443" --> PF
    PF -- "443 redirigé · traverse la sonde IPS" --> DOCK
    HOTE -- "22 SSH" --> ANS
    ANS -- "22 SSH" --> IPS
    ANS -- "22 SSH" --> DOCK
    ANS -- "3000 Grafana · tunnel" --> DOCK
    DOCK -- "9100, 9101 · relevé Prometheus" --> IPS
    IPS -- "3100 · envoi des journaux Loki" --> DOCK
    ANS & IPS & DOCK -- "sortie via NAT" --> PF
    PF --> NET
```

| Règle | Où |
|---|---|
| SSH accepté uniquement depuis `ra-ansible` | pare-feu `hostfw` de `ra-docker` et `ra-ips` |
| Grafana (3000) : `ra-ansible` uniquement | chaîne `DOCKER-USER` de `ra-docker` |
| Loki (3100) : `ra-ips` uniquement | chaîne `DOCKER-USER` de `ra-docker` |
| Métriques de `ra-ips` : `ra-docker` uniquement | pare-feu `hostfw` de `ra-ips` |
| WAN pfSense : tout bloqué sauf 443 | pfSense (redirection à activer le jour de la démo) |

---

## 8. Déploiement et gestion des secrets

Infrastructure décrite en code, secrets chiffrés dans le dépôt.

```mermaid
flowchart LR
    DEV(["Dépôt Git<br/>resilience-infra"]) -- "synchronisation" --> ANS

    subgraph ANS["ra-ansible — nœud de contrôle"]
        PB["Playbooks Ansible<br/>site.yml"]
        SOPS["SOPS"]
        KEY[["Clé privée age<br/>~/.config/sops/age"]]
        ENC["secrets/*.enc.yml<br/>chiffrés"]
        ENC --> SOPS
        KEY --> SOPS
        SOPS -- "valeurs en mémoire" --> PB
    end

    PB -- "SSH" --> IPS["ra-ips<br/>sonde IPS, agent obs"]
    PB -- "SSH" --> DOCK["ra-docker<br/>observabilité, plateforme,<br/>sauvegardes"]
    PB -- ".env 0600" --> DOCK
```

| Playbook | Rôle |
|---|---|
| `00-control` | outils SOPS et age |
| `10-base` | socle commun |
| `15-hardening` | pare-feu, SSH |
| `20-docker` | moteur Docker |
| `40-ips` | sonde IPS |
| `50-observability` | supervision |
| `60-platform` | WAF, base, accès Docker de la remédiation |
| `70-backup` / `71-restore` | sauvegardes / PRA |

Relancer `site.yml` sur l'infrastructure en place ne modifie rien : le déploiement est reproductible.

---

## 9. Sauvegarde et restauration (PRA)

`ra-docker` chiffre avec la clé **publique** : il ne peut pas relire ses propres sauvegardes. Seul `ra-ansible` peut déchiffrer.

```mermaid
sequenceDiagram
    autonumber
    participant T as Minuterie (toutes les heures)
    participant D as ra-docker
    participant DB as PostgreSQL
    participant P as Prometheus
    participant A as ra-ansible

    rect rgb(235, 240, 250)
    Note over T,P: Sauvegarde
    T->>D: pg-backup.sh
    D->>DB: pg_dump
    DB-->>D: dump
    D->>D: chiffrement age (clé publique), rotation 48
    D->>P: pg_backup_last_success_timestamp_seconds
    Note over P: alerte si > 2 h
    end

    rect rgb(250, 240, 235)
    Note over D,A: Restauration (playbook 71-restore)
    A->>D: récupère la sauvegarde chiffrée
    A->>A: déchiffrement age (clé privée)
    A->>D: dump en clair, 0600, temporaire
    D->>DB: pg_restore --clean
    A->>D: effacement du clair (toujours, même en cas d'échec)
    A->>A: effacement des copies locales
    end
```
