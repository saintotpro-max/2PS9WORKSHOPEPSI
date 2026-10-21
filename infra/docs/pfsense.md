# pfSense — configuration

pfSense est piloté par **Ansible** (collection `pfsensible.core`, en SSH avec la clé de `ra-ansible`) :
playbook [`05-pfsense.yml`](../ansible/playbooks/05-pfsense.yml).

Mise en place initiale (une fois, faite le 20/10 dans l'interface web) : *System → Advanced → Admin Access* :
SSH activé en **Public Key Only** ; *System → User Manager → admin* : clé publique de `ra-ansible`.

## Accéder à l'interface web

Le PC hôte n'est pas sur le LAN. Passer par un tunnel via `ra-ansible` :

```
ssh -L 8443:10.10.10.1:443 sadmin@192.168.80.10
```

puis https://localhost:8443.

## État actuel

| Interface | Carte | Adresse |
|---|---|---|
| WAN | `vmx0` → VMnet2 (pont sur le Wi-Fi du PC hôte) | DHCP du Wi-Fi |
| LAN | `vmx1` → VMnet6 | `10.10.10.1/24`, pas de DHCP (adresses fixes) |

Le WAN bloque tout trafic entrant (règle par défaut). Le LAN sort vers Internet (NAT).

## Exposition de la plateforme (gérée par Ansible)

| Élément | Réglage |
|---|---|
| Alias `CLIENTS_AUTORISES` | IP autorisées à joindre la plateforme : variable `pfsense_allowed_clients` de [`group_vars/firewalls.yml`](../ansible/inventory/group_vars/firewalls.yml) |
| Interface WAN | réseaux privés acceptés (le Wi-Fi est un réseau privé) |
| Redirection NAT | WAN:443 → `10.10.10.20:443` (WAF), source limitée à `CLIENTS_AUTORISES`, règle de filtrage associée |

Actuellement : tout le Wi-Fi de l'école (`10.60.64.0/22`). Pour changer (ex. point d'accès du groupe) :
modifier `pfsense_allowed_clients` puis `ansible-playbook playbooks/05-pfsense.yml`.

## Procédure manuelle (si Ansible est indisponible)

> Uniquement une fois le PC hôte et le PC attaquant connectés au **point d'accès Wi-Fi du groupe**
> (`RESILIENCE-G<n>`). Ne pas exposer la plateforme sur le Wi-Fi du campus.

1. **WAN fixe** — *Interfaces → WAN* : passer en IPv4 statique sur le réseau du point d'accès
   (ex. `192.168.137.50/24`, passerelle `192.168.137.1`), pour que l'adresse de démo ne change pas.
2. **Réseaux privés** — *Interfaces → WAN* : décocher **Block private networks**
   (le point d'accès utilise un réseau privé, sinon le PC attaquant est rejeté).
3. **Redirection** — *Firewall → NAT → Port Forward* :
   - Interface `WAN`, protocole `TCP`, destination `WAN address`, port `443`
   - Redirect target `10.10.10.20`, port `443`
   - Description « WAF RESILIENCE-ALPHA »
   - Laisser pfSense créer la règle de filtrage associée.
4. *(optionnel)* Même chose pour le port `80` (redirigé vers HTTPS par le WAF).

L'adresse source du client est conservée de bout en bout (pas de NAT source) : la sonde IPS
et le WAF voient la vraie IP de l'attaquant, ce qui permet de la bloquer.

## Vérification

Depuis le PC attaquant : `curl -k https://<IP WAN pfSense>/healthz` → `OK`.
