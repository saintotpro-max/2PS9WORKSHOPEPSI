# Points d'integration pour le mode reel

Voir integration-collegues.png. Vert est fait (dev, cyber, jeu). Orange est pour
l'INFRA. Bleu est pour l'IA. Le passage au reel ne change qu'un fichier de
configuration du jeu.

## INFRA

1. Mettre les services en conteneur (Dockerfile et un compose), plateforme et
   moteur, et les deployer. La base et les secrets ne sortent pas sur le reseau.
2. Collecter les metriques et les journaux. La plateforme expose /metrics et
   ecrit des journaux JSON. Brancher Prometheus et Loki dessus.
3. Fournir l'actionneur sur. Point le plus important. Le moteur decide une action
   (redemarrer un service, bloquer une source) mais n'a pas le pouvoir direct sur
   la plateforme. Donner un proxy Docker restreint, ou des playbooks Ansible, ou
   un relais HTTP (POST /dashboard/api/escalade) qui garde le jeton cote serveur
   et n'accepte qu'une action de la liste blanche.
4. Mettre le WAF ou l'IPS qui bloque les flux, et exposer la liste des flux
   bloques que le jeu lit (source, regle, nombre).
5. Donner le tunnel et la page QR du public. Le QR renvoie vers une page avec un
   bouton qui genere de la charge. Le jeu arme la vague et lit le compteur.
6. Exposer la plateforme cote WAN avec pfSense (port 443 et le tunnel). Donner
   l'adresse WAN courante et l'URL du tunnel.

## IA

1. Fournir le detecteur ML. Il voit le trafic reel, calcule un score d'anomalie
   et envoie une alerte au moteur par POST /alerts avec une recommandation. Il
   expose aussi la serie des scores pour la courbe du jeu.
2. Fournir l'assistant RAG derriere POST /assistant/ask, qui repond avec des
   sources, en local (Ollama), jamais un texte ecrit a l'avance.

## Deja fait

Plateforme de paiement, moteur de remediation (il decide et verifie la reprise
par une vraie transaction), arsenal d'attaque, jeu et cockpit avec le match des
deux IA. Les contrats d'interface existent, le simulateur les imite, et tout
passe au reel par le fichier de configuration.
