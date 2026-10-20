# Clip Chrono (60 s) — procedure de capture

Reference : sujet p.8 (clip de 60 s max, sequence continue SANS coupe masquant une action
manuelle, titres autorises) ; `graphify-jeu-v2.1` PART 5 (Clip Chrono) ; `analyse-manques.md` M8.

## Principe
Une **prise reelle continue** : attaque -> anomalie (tout rougit) -> reaction du systeme
-> service retabli. Aucune coupe ne doit cacher une intervention humaine (ce serait une fraude au
sens du sujet). Le jeu PORTE le clip, mais la capture est une vraie prise d'ecran continue.

## Ce qu'on filme : la Boucle B, temps 2-3-5 (sans RAG)
Le mode **Repetition (touche R)** ou la **Demo guidee (touche D)** fournissent exactement la
sequence ; pour un clip court et nerveux, preferer une passe ciblee :
1. Partir du cockpit (LA TOUR) ou du terminal (LE CAPUCHON), plateforme saine, un paiement OK visible.
2. Lancer l'attaque (niveau 1). Le HUD/la salle rougissent : anomalie reelle.
3. NE RIEN TOUCHER. Le chrono de reprise tourne tout seul. Le moteur agit.
4. Service retabli : sante OK, un paiement repasse. Le chrono s'arrete : c'est le temps de reprise.

## Reglage pour tenir en 60 s
- Raccourcir les delais du scenario cote simulateur (detection/reprise courts) UNIQUEMENT en
  repetition ; en reel, garder les vrais delais et couper le clip au bon moment sans masquer d'action.
- Afficher en clair le **mode** (simule/reel) et le **chrono** : ce sont les preuves.
- Titres autorises : un carton d'intro ("RESILIENCE ALPHA") et un carton final (le temps de reprise)
  sont permis ; ils n'interrompent pas la prise continue de l'action.

## Capture (selon le poste)
- Linux : `wf-recorder` / OBS en capture d'ecran continue.
- Windows (PC Hote, jour J) : Xbox Game Bar (Win+Alt+R) ou OBS, une seule prise, sans montage
  qui masque une action.
- Verifier avant rendu : duree <= 60 s, une seule sequence, mode et chrono lisibles, aucune main
  humaine sur le clavier pendant la reprise.

## Honnetete (non negociable)
Si le mode est simule, il est ecrit a l'ecran pendant tout le clip. Le jour de la demonstration,
jamais le simulateur : chaine reelle (Ollama local pour l'assistant, sujet p.5).
