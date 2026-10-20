# Messages prêts à envoyer (non envoyés)

## Aux collègues infra et IA
Objet : contrats d'interface RESILIENCE-ALPHA

Voici le contrat commun (`contrats/resilience-alpha.openapi.yaml`, explications dans `contrats/LISEZ-MOI.md`).
Ce que j'attends de vous :
- IA (ML) : détecter une anomalie et envoyer `POST /alerts` au moteur de remédiation (corps : source, kind, severity, score, target, detail).
- IA (assistant) : exposer `POST /assistant/ask` (question, réponse, sources, latence). Il informe, il ne répare pas.
- Infra : collecter `/metrics` de la plateforme (`payment_requests_total{status}`, `payment_request_duration_seconds`, `payment_up`) ; WAF et SIEM peuvent aussi envoyer `POST /alerts`.
Tant que vos services ne sont pas prêts, un simulateur (`services/simulateur`) imite ces routes, et je branche le vrai par un simple fichier de configuration. Dites-moi quand vous pouvez livrer, et si un champ du contrat vous gêne.

## Au coach (trace écrite, point P7)
Objet : question sur le périmètre du SI de paiement

Bonjour, le sujet demande de « construire un SI de paiement fictif » et autorise « les bibliothèques, images et outils publics ». Pouvons-nous réutiliser un serveur de paiement open source comme cœur métier si la démarche est documentée dans le dossier et dans le README ? Pouvez-vous nous le confirmer par écrit ? Merci.

## Pour obtenir le PPTX du sujet
Objet : support PPTX du sujet RESILIENCE-ALPHA

Bonjour, le sujet PDF mentionne un support PPTX que nous n'avons pas reçu. Pouvez-vous nous l'envoyer ?
