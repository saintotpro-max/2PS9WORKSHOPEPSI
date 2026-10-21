# Dossier RGPD europeen - RESILIENCE-ALPHA

Cadre : Reglement (UE) 2016/679 (RGPD). Projet pedagogique fictif presente en
workshop : plateforme de paiement SIMULEE, donnees FICTIVES, reseau local ferme.
Regle fondatrice adoptee par l'equipe : aucune donnee personnelle reelle n'est
collectee, nulle part, ni cote services ni cote jeu ni cote public.
Verification automatisee : `scripts/check-rgpd.py` (hors ligne, stdlib pur).

## 1. Principe de minimisation (art. 5 RGPD)

Le systeme est concu pour ne pas avoir besoin de donnees personnelles :

- Les payeurs et beneficiaires sont des identifiants de demonstration fictifs
  (`demo`, `caissier`, `boulangerie-fictive`). Aucun nom, prenom, mail, telephone
  ou adresse reelle n'existe dans la base, les journaux, le code ou les ecrans.
- La page publique " Rejoindre la vague " (QR code) n'enregistre qu'un COMPTEUR
  anonyme : un entier incremente a chaque clic. Pas de formulaire, pas de cookie,
  pas de traceur, pas de stockage d'adresse IP, pas de session individuelle.
- Aucune adresse IP n'est journalisee par les services (paiement, simulateur,
  moteur). Le verifier `scripts/check-rgpd.py` le controle.

## 2. Registre des traitements (art. 30, tenu a titre de bonne pratique)

| # | Traitement | Donnees | Base legale | Duree | Ou |
|---|------------|---------|-------------|-------|----|
| 1 | Transactions de paiement fictives | id, montant, devise, payer/payee (fictifs), statut, horodatage, cle d'idempotence | Demonstration pedagogique, donnees non personnelles | Base locale `services/paiement/paiement.db`, effacee par la remise a zero (M9) | services/paiement |
| 2 | Compteur de participation du public | Un entier (total de participants) | Consentement par clic volontaire ; donnee strictement non identifiante | Memoire du simulateur, remise a zero a chaque session | services/simulateur `/participation` |
| 3 | Journaux techniques JSON (stdout) | Evenements techniques, identifiant de compte de demo sur refus d'auth | Interet legitime : diagnostic pendant la demonstration | Duree de la session, rien n'est archive | services/* |

Aucun des trois traitements ne porte sur une donnee personnelle reelle.

## 3. Transferts hors Union europeenne (art. 44)

Un seul cas possible : le modele externe optionnel (NanoGPT, `SIM_LLM=1`).
- Desactive par defaut ; jamais appele par les tests ; jamais le jour de la
  demonstration ; jamais par le vrai assistant (Ollama local, sujet p.5).
- Il ne recoit que des textes du scenario de jeu (recommandations, personas).
  Aucune donnee personnelle ne lui est envoyee, et aucune n'existerait de toute facon.
- Cle et configuration dans `~/.config/alpha/nanogpt.env`, HORS du depot.

Les collegues infra/IA n'ont rien a ajouter : tant que ce principe tient
(aucune donnee reelle), aucun transfert ne peut concerner une personne.

## 4. Droits des personnes (art. 12 a 22)

Rien a exporter, rectifier ou effacer : aucune donnee personnelle n'est traitee.
Si, malgre tout, une donnee reelle entrait dans le systeme (nom cite a l'oral et
tape dans une transaction, mail colle dans un journal), la procedure est :

1. Supprimer l'enregistrement ou la ligne de journal concernee immediatement.
2. Noter l'incident dans ce fichier (section 6).
3. Relancer `scripts/check-rgpd.py` pour confirmer le retour a l'etat normal.

## 5. Securite (art. 32)

- Secrets et cles : hors depot, ignores par `.gitignore` (`*.env`, `nanogpt*`).
  `scripts/livrer.sh` echoue si un secret se glisse dans `Code.zip`.
- Perimetre reseau : scripts d'attaque verrouilles sur 192.168.137.0/24 et
  localhost. Aucune cible exterieure.
- Reseau de demonstration : local et ferme, pas de service expose sur Internet
  en dehors du tunnel de demonstration volontaire et ephemere de la page QR.
- Mots de passe de demo publics par conception (`demo`, `caisse`, `soc`) :
  comptes fictifs, aucune correspondance avec une personne reelle.

## 6. Journal de conformite

- 2026-10-21 : creation du dossier RGPD, verification automatisee ajoutee,
  mention " aucune donnee personnelle " affichee sur la page du public.

## 7. Contact

" L'equipe RESILIENCE-ALPHA " (projet etudiant EPSI). Volontairement sans nom,
sans mail et sans formulaire : il n'y a rien a traiter, donc rien a demander.
