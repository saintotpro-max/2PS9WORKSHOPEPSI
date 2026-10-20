# Adapter le cockpit Ren'Py à l'infra RÉELLE

> **Pour l'équipe DEV du jeu.** Ce document explique comment faire en sorte que les
> deux personas du duel (**LE HACKER** / **LA SENTINELLE**) ne soient plus de simples
> narrateurs, mais déclenchent de **vraies actions sur l'infrastructure réelle** du lab
> RESILIENCE-ALPHA : l'attaquant lance la vraie vague de charge bornée, la sentinelle
> observe — et, en escalade, déclenche — la vraie remédiation.
>
> Contexte : **lab fermé et autorisé**, fausse monnaie, faux clients. L'« attaque » est
> un générateur de charge **borné et verrouillé sur le périmètre du lab** (voir § 9). Tout
> l'intérêt pédagogique est sur la **défense** : montrer que la plateforme se répare seule.

---

## 0. Hypothèse de déploiement : le jeu tourne sur un PC tiers, côté WAN

On suppose que **le PC qui lance le jeu et le poste attaquant sont du côté WAN** du
pfSense (même Wi-Fi que l'IP WAN de la plateforme). Conséquence directe :

> **Le jeu ne peut joindre QUE ce que pfSense expose côté WAN.**
> Aujourd'hui = le **port 443 (WAF)** + le **tunnel public** du compteur de participation.
> Le LAN (`10.10.10.0/24`), les services internes (Grafana, base, moteur en direct,
> socket Docker) sont **injoignables** depuis le WAN, par conception.

Tout ce qui suit est donc conçu pour passer **uniquement par 443 et par le tunnel**.

| Besoin du jeu | Chemin réel depuis un PC WAN | Exposé ? |
|---|---|---|
| Santé plateforme / payer | `https://<IP_WAN>/health`, `/auth/token`, `/transactions` | ✅ WAF 443 |
| Lire les événements du moteur | `GET https://<IP_WAN>/dashboard/api/remediation/events` | ✅ WAF 443 (GET) |
| Lire l'état des incidents | `GET https://<IP_WAN>/dashboard/api/remediation/status` | ✅ WAF 443 (GET) |
| Lire les métriques (IPS, repro, santé) | `GET https://<IP_WAN>/dashboard/api/prom/query?query=…` | ✅ WAF 443 (GET) |
| Lire les logs | `GET https://<IP_WAN>/dashboard/api/loki/query?query=…` | ✅ WAF 443 (GET) |
| **Armer la vraie vague** (attaquant) | `POST <URL_TUNNEL>/participation/armer?cible=…` | ✅ tunnel |
| Compteur de participation | `GET <URL_TUNNEL>/participation/etat` | ✅ tunnel |
| **Déclencher un vrai redémarrage** (sentinelle) | relais d'escalade (§ 6) | ⛔ **à fournir par INFRA** |

---

## 1. La vérité terrain : il y a DEUX moteurs, contrats différents

Le jeu a été écrit contre **le moteur de votre simulateur** (`services/moteur`, voir
`Docs/api/plateforme.md`). L'infra réelle déploie un **autre** moteur
(`resilience-infra/services/remediation`). **Leurs contrats ne sont pas identiques.**
C'est le point n°1 à comprendre avant d'adapter le code.

| | Moteur du simulateur (ce que le jeu attend) | Moteur RÉEL (`services/remediation`) |
|---|---|---|
| `POST /alerts` | corps `AlerteEntree`, **réponse 202 synchrone** avec compte rendu complet (`action`, `reprise_ok`, `verifications`) | corps **format Alertmanager**, Bearer obligatoire, **réponse async** `{status:"accepted"}` — aucun compte rendu immédiat |
| `GET /events` | `{events:[…], mode}` | **liste brute** `[…]` (pas d'enveloppe `events`/`mode`) |
| `GET /verifications` | existe | **n'existe pas** (les vérifs sont dans les `events`, étape `verification`) |
| `GET /components` | existe | **n'existe pas** |
| `GET /scores` (détecteur) | existe | **n'existe pas** en REST → métriques Prometheus `ips_*` |
| `GET /flux-bloques` (WAF) | existe | **n'existe pas** en REST → métrique `ips_blocks_total` + events `IpsIpBloquee` |
| `GET /status` | — | existe : incidents actifs + récents (avec `recovery_seconds`) |
| Actions | `restart_service, block_source, rate_limit, scale_up, none` | **`restart`** et **`record`** uniquement (cibles : `paiement`, `waf`, `dashboard`) |

**Conséquence concrète** : la boucle `boucle_sante()` de `pont.rpy` interroge en réel des
routes qui n'existent pas (`/alerts` GET, `/verifications`, `/components`, `/scores`,
`/flux-bloques`). En mode réel il faut les **remplacer** par les sources du tableau du § 3.

---

## 2. Surface d'API RÉELLE, joignable depuis le WAN

### 2.1 Plateforme de paiement (via le WAF, `/`)
- `GET /health` → `{status: "ok"|"down", mode}` — **santé honnête** (écriture+lecture en base).
- `POST /auth/token` `{username,password}` → `{access_token}`.
- `POST /transactions` (Bearer) `{amount_cents,currency:"EUR",payer,payee}` → `201`.

> ⚠️ Le WAF est en **HTTPS auto-signé**. Voir § 5 pour le contexte TLS.

### 2.2 Moteur de remédiation — en LECTURE, via les proxies du dashboard (GET, 443)
- `GET /dashboard/api/remediation/events` → **liste** d'étapes. Types d'étape :
  `detection`, `decision`, `action`, `verification`, `escalation`, `resolution`.
  Chaque étape : `{id, at, incident, step, message, …}` (+ `target`, `action`, `result`,
  `checks` selon l'étape). C'est **le flux réel du moteur** : c'est ça que la Sentinelle doit raconter.
- `GET /dashboard/api/remediation/status` → `{dry_run, active:[…], recent:[…]}` ;
  chaque incident récent porte `status` (`in_progress`/`resolved`/`failed`/`observed`),
  `recovery_seconds` (coupure réelle), `remediation_seconds`.

### 2.3 Détecteur IPS + WAF — via Prometheus (GET, 443)
Pas de REST dédié : on lit les métriques via `GET /dashboard/api/prom/query?query=<PromQL>`.
Métriques utiles (format JSON Prometheus `{data:{result:[{value:[ts,"v"]}]}}`) :

| Panneau Sentinelle | PromQL |
|---|---|
| Probabilité d'attaque (score détecteur) | `ips_attack_probability_max` |
| Flux suspects détectés | `ips_suspect_flows_total` |
| IP bloquées par la sonde | `ips_blocks_total` |
| Transaction de bout en bout OK | `min(txn_probe_success)` |
| Point d'entrée up | `probe_success{instance="http://waf:8080/healthz"}` |

### 2.4 Compteur de participation (attaquant) — via le tunnel
- `POST <URL_TUNNEL>/participation/armer?cible=<ip|url>` → arme la vague.
- `GET  <URL_TUNNEL>/participation/etat` → `{total, phase, ecoule, cible, …}`.
- `POST <URL_TUNNEL>/participation/stop` → arrêt **manuel** (c'est l'opérateur qui décide).
- L'URL du tunnel est affichée par `ra-vague url` côté `ra-attacker` (elle change à chaque
  régénération). Le jeu doit la lire depuis sa config (clé `attaque.tunnel_url`) ou l'env `RA_TUNNEL`.

---

## 3. Correspondance « panneau du jeu » → source réelle (mode réel)

Remplacer, dans `boucle_sante()`, les appels inexistants par ceux-ci :

| Champ `ETAT` | Avant (simulateur) | En réel |
|---|---|---|
| `sante`, `mode` | `plateforme/health` | **inchangé** (`/health` via WAF) |
| `evenements` | `moteur/events` → `data.events` | `…/remediation/events` → **la liste brute** |
| `alerte` | `moteur/alerts` (GET) | dérivée du dernier event `detection`/`escalation`, ou `null` |
| `verifications` | `moteur/verifications` | les `checks` du dernier event `verification` (`…/status`) |
| `composants` | `moteur/components` | `…/remediation/status` → `active`/`recent` |
| `scores` | `detection/scores` | `prom/query?query=ips_attack_probability_max` (série via `query_range`) |
| `flux_bloques`, `flux_total` | `waf/flux-bloques` | `prom/query?query=ips_blocks_total` |
| `chrono` (reprise) | calculé local | `recent[].recovery_seconds` du `status` |
| `vague` | `detection/participation/etat` | `<URL_TUNNEL>/participation/etat` |

---

## 4. Persona ATTAQUANT → impact réel (déjà câblé)

Rien de nouveau à écrire côté charge : l'INFRA fournit déjà le lévier, **borné et
verrouillé** (§ 9). Depuis le WAN, la seule chose à faire est d'**armer** via le tunnel :

```
POST <URL_TUNNEL>/participation/armer?cible=<ip de la plateforme>
```

- `cible` est **optionnelle** (défaut = cible configurée sur `ra-attacker`) et permet de
  changer l'IP attaquée depuis le cockpit (bouton « Changer la cible (C) », déjà présent).
- La charge réelle est produite par `ra-attacker` lui-même (pas par le PC du jeu).
- Garde-fou : une cible hors `10.60.64.0/22` est **refusée** côté charge (voir § 9).

C'est ce que font déjà `cockpit/attaque-reelle/niveau-1.py` → `_vague.py` (dépôt infra),
que `interfaces.reel.json` branche sur le bouton d'attaque du cockpit.

---

## 5. Persona SENTINELLE → impact réel

### 5.1 Mode OBSERVATEUR (recommandé par défaut)
La Sentinelle **lit** le flux réel (§ 2.2–2.3) et **raconte les vraies décisions** que le
moteur et l'IPS prennent **tout seuls**. C'est le mode le plus fidèle au sujet : la
reprise est **autonome**, personne ne la commande. `duel_defense_raison()` doit alors
être alimentée par le dernier event `decision`/`action` réel, pas par `reco()` simulé.

### 5.2 Mode ACTEUR (escalade N1 — impact réel, sous garde-fou)
Si l'on veut que la Sentinelle **déclenche** vraiment une reprise (posture « support N1 qui
escalade »), elle appelle un **relais d'escalade** (§ 6). Elle **ne parle jamais en direct**
au moteur ni à Docker : le jeton reste côté serveur, et seule une action **whitelistée et
réversible** (redémarrage d'un service autorisé) est possible.

### 5.3 Correspondance des 5 actions du jeu avec le réel

| Action affichée | Réalité infra | À faire côté jeu |
|---|---|---|
| `restart_service` | ✅ le moteur redémarre `paiement`/`waf`/`dashboard` + vérifie 3 preuves | appeler le relais (§ 6) |
| `block_source` | ⚠️ **autonome** : c'est l'IPS/ML qui bloque, pas commandable à la demande | **observer** (`ips_blocks_total`), ne pas prétendre le commander |
| `rate_limit` | ❌ non implémenté dans l'infra | retirer de l'affichage **ou** demander à INFRA de l'implémenter |
| `scale_up` | ❌ non implémenté dans l'infra | idem |
| `none` | ✅ cas « rien à faire » | inchangé |

> Pour rester crédible devant un jury technique : la décision réelle est **à règles**
> (moteur) + **ML** (IPS). Le LLM de la Sentinelle **explique** et, au plus, **escalade** ;
> il ne « décide » pas à la place du système. C'est plus solide, pas moins.

---

## 6. Contrat du RELAIS D'ESCALADE — ⛔ à fournir par l'équipe INFRA

Pour que la Sentinelle agisse depuis le WAN **sans** exposer le moteur ni son jeton, l'INFRA
doit ajouter un petit relais derrière le WAF (ex. `POST /dashboard/api/escalade`), qui :

- n'accepte qu'un corps **fermé** (pas de payload arbitraire) :
  `{"service": "paiement"|"waf"|"dashboard", "raison": "<texte court>"}` ;
- est **restreint à la source** (clients pfSense autorisés) et **rate-limité** ;
- détient le `REMEDIATION_TOKEN` **côté serveur** et forge lui-même l'alerte Alertmanager
  envoyée au moteur réel, par ex. :

```json
{ "alerts": [ {
  "status": "firing",
  "labels": { "alertname": "ServiceApplicatifEnPanne", "service": "paiement",
              "severity": "high", "source": "escalade-cockpit" },
  "annotations": { "summary": "Escalade N1 depuis le cockpit : <raison>" },
  "startsAt": "<ISO8601>"
} ] }
```

- répond `{accepted:true, incident_hint:"voir /remediation/events"}` (le compte rendu réel
  se lit ensuite sur `…/remediation/events` et `…/status`).

> Tant que ce relais n'existe pas, la Sentinelle reste en **mode Observateur** (§ 5.1),
> ce qui est déjà une démo honnête et complète. Le mode Acteur est un **bonus**.

---

## 7. Bascule simulé → réel (config)

Un seul fichier change : `config/interfaces.json` (voir `interfaces.reel.json` fourni par
l'INFRA dans `resilience-infra/cockpit/`). Points d'attention en réel :

```jsonc
{
  "demo": false, "role": "tous",
  "plateforme": { "mode": "reel", "url": "https://<IP_WAN>" },
  "moteur":     { "mode": "reel", "url": "https://<IP_WAN>/dashboard/api/remediation" },
  "detection":  { "mode": "reel", "url": "https://<IP_WAN>/dashboard/api/prom" },
  "attaque":    { "mode": "reel", "tunnel_url": "<URL_TUNNEL>",
                  "escalade_url": "https://<IP_WAN>/dashboard/api/escalade" }
}
```

- `<IP_WAN>` = IP WAN courante de pfSense (change selon le Wi-Fi). Le bouton **« Changer la
  cible (C) »** du cockpit met déjà à jour `plateforme.url` et persiste dans ce fichier.
- Le **jeton** du relais, s'il en faut un côté client, se lit comme `ia-duel.env` :
  dans `~/.config/alpha/*.env`, **jamais commité**, jamais embarqué dans le build du jeu.

---

## 8. Ce que le DEV doit changer dans le code du jeu

1. `pont.rpy` → `http_brut` : passer un **contexte TLS non vérifié** quand l'URL est en
   `https` (WAF auto-signé) — cf. `resilience-infra/cockpit/README.md`.
2. `pont.rpy` → `boucle_sante` : en mode réel, utiliser les sources du § 3 (events bruts,
   `status`, PromQL) au lieu des routes du simulateur.
3. `pont.rpy` → `armer_vague` : en mode réel, POST sur `attaque.tunnel_url` + `?cible=`
   (et non `detection.url`). Lire l'URL du tunnel depuis la config / `RA_TUNNEL`.
4. `duel.rpy` → `duel_defense_raison` / panneau Sentinelle : alimenter depuis le dernier
   event `decision`/`action` **réel** ; afficher `recovery_seconds` du `status`.
5. `duel.rpy` → action Sentinelle (optionnel, mode Acteur) : bouton/décision qui appelle
   `attaque.escalade_url` (§ 6) au lieu de n'être qu'un texte.
6. UI : retirer (ou griser « non branché ») `rate_limit` et `scale_up` tant que l'INFRA ne
   les implémente pas, pour ne pas afficher d'action sans effet.

---

## 9. Garde-fous (à ne pas retirer)

- **Périmètre de charge verrouillé** : la vague ne frappe que `10.60.64.0/22` (le lab) ;
  toute autre cible est refusée côté `ra-attacker`. Le cockpit ne peut pas pointer ailleurs.
- **Charge bornée** : nombre de connexions plafonné, montée progressive, arrêt **manuel**
  par l'opérateur + garde-fou d'arrêt auto à 10 min.
- **Jeton server-side** : le `REMEDIATION_TOKEN` n'est jamais dans le jeu ni dans un dépôt ;
  le relais d'escalade le détient côté serveur.
- **Action réversible et whitelistée** : la Sentinelle ne peut, au plus, que demander le
  **redémarrage** d'un service autorisé (`paiement`/`waf`/`dashboard`). Jamais la base,
  jamais une commande Docker arbitraire.
- **Autonomie préservée** : le mode Observateur est le défaut ; le mode Acteur est une
  **escalade N1**, pas la boucle de reprise — celle-ci reste pilotée par la supervision.
