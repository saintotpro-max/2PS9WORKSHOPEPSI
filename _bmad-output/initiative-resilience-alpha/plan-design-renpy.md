# Plan renforcé : habillage et intégration du jeu (graphify × assets)

Idée directrice : chaque écran du jeu emprunte sa forme à un outil ou une source déjà cités dans `graphify` (règle 4C, PART 10 et 11, PART 13 et 19) et à un asset libre vérifié. Rien n'est inventé quand un équivalent existe. Mode simulé toujours affiché.

## Direction artistique « néon-noir pixel »
- Palette : marine profond, magenta et cyan de la ville, orange du couchant ; rouge alerte `#dc3545` pour le danger, vert `#2ea043` pour le rétabli ; base `#0d1117`.
- Typographie : Kenney Future (titres, boutons), Share Tech Mono (terminal, HUD, flux) ; toutes deux libres.
- Mouvement (ATL du moteur, aucune bibliothèque en plus) : panorama lent du fond de ville, respiration des portraits, fondu d'entrée.

## Carte écran → source graphify → asset
| Écran | Inspiré de (graphify ou carte de recherche) | Asset libre | Honnêteté |
|---|---|---|---|
| Titre | trois personas PJ-1 à PJ-3 (jeu v2.1) | fond de ville « Warped City » (CC0), visages « Cyberpunk Portraits » (CC0), cartes Kenney (CC0) | rien de décoratif ne simule un résultat |
| Terminal (S3) | arsenal et niveaux (graphify PART 13 et 19) : niveau 1 charge applicative (locust, MIT), niveau 2 connexions lentes (slowloris), niveau 3 saturation réseau (hping3) ; chaos de jeudi : Pumba | visage casqué, portrait capuchonné « the hooded one » (CC0), Share Tech Mono | scripts simulés étiquetés `[SIMULE]`, imitation d'une commande, aucun chiffre inventé |
| Paiement (S2) | mitmproxy (graphify PART 11) : vue de flux requête → réponse | silhouette « L'Ombre » (visage CC0 passé en noir) | lignes de flux réelles : méthode, route, code, durée mesurée |
| Poste SOC (S4) | Wazuh (règle, niveau sur 15) et PyOD (score) | visage « Le Badge » | alerte reçue telle quelle, niveau déduit de la gravité |
| HUD | Prometheus et Grafana des collègues (graphify PART 02) | polices libres | santé, mode, reprise mesurée toutes les 2 s |

## Étapes
1. Assets : fabriqués depuis les archives vérifiées (licences lues sur les pages sources) → `renpy/game/assets`.
2. Habillage : `00_habillage.rpy` (polices, images, transformations, cartes Kenney).
3. Écrans : titre en cartes avec visages, terminal avec fond capuchon, flux mitmproxy-style, alerte Wazuh-style.
4. Scripts d'attaque simulés : sortie qui imite la commande de l'outil réel (sans chiffres inventés).
5. Preuve : suite de 6 parcours + captures relues ; crédits complétés dans `renpy/CREDITS.md`.
6. Plus tard (stories 2.1 et 2.4) : remplacer les scripts simulés par les vrais outils (locust, slowloris, hping3), toujours depuis le PC Attaquant.

## Ce que cette recherche a écarté
- Aucune bibliothèque Ren'Py tierce sous licence libre adaptée (les dépôts trouvés n'ont pas de licence déclarée, ou ne concernent pas l'interface) : les fonctions du moteur (ATL, `Frame`, `Transform`) suffisent.
- « Neon Glitch GUI Kit » (CC BY-SA 4.0 avec interdiction liée à l'IA) non adopté.
