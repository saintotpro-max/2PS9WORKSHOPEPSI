



style carte_bouton is button:
    background carte("carte_grise")
    hover_background carte("carte_grise", True)
    insensitive_background carte("carte_grise", False, True)
    padding (20, 36, 20, 8)
    xminimum 260
    xsize None
    ysize None
    yminimum 0

style carte_bouton_text is text:
    font POLICE_ETROITE
    size 23
    color "#1b2433"
    hover_color "#000000"
    insensitive_color "#2b323d"
    text_align 0.5
    xalign 0.5

style bouton_rouge is carte_bouton:
    background carte("carte_rouge")
    hover_background carte("carte_rouge", True)
    insensitive_background carte("carte_rouge", False, True)

style bouton_rouge_text is carte_bouton_text

style bouton_clair is carte_bouton:
    background carte("carte_bleue")
    hover_background carte("carte_bleue", True)
    insensitive_background carte("carte_bleue", False, True)

style bouton_clair_text is carte_bouton_text

style bouton_petit is carte_bouton:
    padding (16, 36, 16, 6)
    xminimum 340

style bouton_petit_text is carte_bouton_text:
    size 22

style bouton_stop is bouton_rouge:
    padding (16, 36, 16, 10)
    xminimum 340

style bouton_stop_text is carte_bouton_text:
    size 26
    color "#2b0b0e"
    hover_color "#000000"

style bouton_court is bouton_clair:
    xminimum 0

style bouton_court_text is carte_bouton_text:
    size 17

style bouton_petit_rouge is bouton_rouge:
    padding (16, 40, 16, 8)
    xminimum 340

style bouton_petit_rouge_text is carte_bouton_text:
    size 18

style hud_texte is text:
    font POLICE_TERMINAL
    size 19

init python:
    PORTES = [
        ("1", "LE HACKER", "l'attaquant", "visage hacker", "carte_rouge", "hacker"),
        ("2", "LA SENTINELLE", "l'IA de défense", "visage badge", "carte_bleue", "soc"),
        ("3", "LE CLIENT", "le paiement", "visage ombre", "carte_grise", "client"),
        ("4", "LA TOUR", "la supervision", "visage salle", "carte_verte", "salle"),
    ]

    COULEUR_SOURCE = {"moteur": "#58a6ff", "detection": "#e3b341", "attaquant": "#ff7b86"}

    def message_soc():
        """Le système ne « sait » qu'après réception de l'alerte."""
        if ETAT.alerte:
            return "Ne touchez à rien : le système réagit seul."
        if ETAT.sante in ("degraded", "down"):
            return "Le système observe…"
        return ""

    def evenements_de(source, n):
        return [e for e in ETAT.evenements if e.get("source") == source][-n:]

    def etat_capuchon():
        ev = evenements_de("attaquant", 1)
        if not ev:
            return "en attente"
        return "attaque en cours" if ev[0]["type"] == "attack_started" else "attaque terminée"

    def etat_badge():
        if ETAT.alerte:
            return "alerte reçue" if ETAT.sante != "ok" else "alerte traitée"
        return "observe"

    def etat_ombre():
        if ETAT.tx_ok + ETAT.tx_ko == 0:
            return "aucun paiement"
        return "OK %d · KO %d" % (ETAT.tx_ok, ETAT.tx_ko)

    def phase_frise():
        if ETAT.chrono_debut is None:
            return "avant"
        return "pendant" if ETAT.chrono_fin is None else "après"

    def couleur_composant(statut):
        return {"ok": "#2ea043", "degraded": "#d29922", "down": "#dc3545"}.get(statut, "#8b949e")

    def barres_score():
        return [(max(2, int(x["score"] * 100)), "#ff4d5e" if x["score"] > x["threshold"] else "#39c5cf")
                for x in ETAT.scores[-60:]]

    LIBELLE_ACTION = {"restart_service": "redémarrer le service", "block_source": "bloquer la source",
                      "rate_limit": "limiter le débit", "scale_up": "ajouter de la capacité", "none": "ne rien faire"}
    LIBELLE_VERIF = {"api_accessible": "L'API répond", "transaction_test": "Une opération métier réussit",
                     "donnees_coherentes": "Les données sont cohérentes"}
    COULEUR_VERIF = {"ok": "#2ea043", "ko": "#dc3545", "en_cours": "#d29922"}

    def reco():
        """Recommandation du détecteur portée par l'alerte, ou None."""
        a = ETAT.alerte
        return a.get("recommendation") if a else None

    def reprise_confirmee():
        return len(ETAT.verifications) == 3 and all(v["status"] == "ok" for v in ETAT.verifications)

    def mode_global():
        """Un seul marqueur de mode pour toute la salle : SIMULÉ, RÉEL ou MIXTE."""
        modes = [v.get("mode") for v in ETAT.cfg.values() if hasattr(v, "get") and v.get("mode")]
        if modes and all(m == "simule" for m in modes):
            return ("SIMULÉ", "#ff7b86")
        if modes and all(m == "reel" for m in modes):
            return ("RÉEL", "#7ee787")
        return ("MIXTE", "#e3b341")

    def heure(e):
        return e.get("at", "")[11:19]

    def couleur_ligne(ligne):
        if ligne.startswith("ERREUR") or ligne.startswith("[code de sortie") and ETAT.dernier_code not in (0, None):
            return "#ff7b86"
        if ligne.startswith("[SIMULE]"):
            return "#e3b341"
        if ligne.startswith("$"):
            return "#ffffff"
        return "#7ee787"

    def attente_libre(job):
        return job is None or job.etat == "fini"

    def porte_refermee():
        return (len(ETAT.runs) > 0 and ETAT.sante == "ok" and ETAT.chrono_debut is not None
                and ETAT.chrono_fin is not None)


screen hud():
    zorder 100
    frame:
        xfill True
        background "#0d1117e6"
        padding (14, 7)
        hbox:
            spacing 20
            text ("SANTÉ : " + libelle_sante()) style "hud_texte" color couleur_sante()
            text ("TX  OK " + str(ETAT.tx_ok) + " / KO " + str(ETAT.tx_ko)) style "hud_texte" color "#c9d1d9"
            text ("ALERTE : " + sur(libelle_alerte())) style "hud_texte" color ("#ff7b86" if ETAT.alerte else "#8b949e")
            text ("REPRISE : " + libelle_chrono()) style "hud_texte" color "#c9d1d9"
            if ETAT.joignable is False:
                text "INJOIGNABLE" style "hud_texte" color "#ff7b86"
            elif ETAT.mode == "simule":
                text "MODE SIMULÉ" style "hud_texte" color "#ff7b86" bold True
            elif ETAT.mode == "reel":
                text "MODE RÉEL" style "hud_texte" color "#2ea043" bold True
    timer 0.5 repeat True action Function(renpy.restart_interaction)


screen bandeau_injoignable():
    if ETAT.joignable is False:
        frame:
            xalign 0.5
            ypos 80
            background "#5c1a22"
            padding (26, 12)
            text "PLATEFORME INJOIGNABLE : le jeu continue, rien n'est simulé à la place." size 22 color "#ffb3ba"


screen carte_acteur(touche, nom, role, visage, fond, retour, largeur=300):
    button:
        background carte(fond)
        hover_background carte(fond, True)
        padding (18, 44, 18, 14)
        xsize largeur
        ysize None
        action Return(retour)
        vbox:
            spacing 4
            xalign 0.5
            add visage xalign 0.5 at respiration
            text (touche + "  " + nom) font POLICE_TITRE size 20 color "#1b2433" xalign 0.5
            text role font POLICE_ETROITE size 21 color "#44505f" xalign 0.5


screen s_titre():
    modal True
    add "bg ville" at panorama
    use bandeau_injoignable
    $ ouvertes = portes_autorisees()
    $ largeur = 270 if len(ouvertes) > 3 else 300
    text "RÉSILIENCE ALPHA" font POLICE_TITRE size 54 color "#ffffff" outlines [(3, "#000000bb", 0, 0)] xalign 0.5 ypos 46
    text "Une banque qui se remet debout toute seule." font POLICE_ETROITE size 28 color "#d6dcff" outlines [(2, "#000000bb", 0, 0)] xalign 0.5 ypos 116
    hbox:
        xalign 0.5
        ypos 190
        spacing 24
        for touche, nom, role, visage, fond, retour in PORTES:
            if retour in ouvertes:
                use carte_acteur(touche, nom, role, visage, fond, retour, largeur)
    text ("Clavier : touches " + ", ".join([p[0] for p in PORTES if p[5] in ouvertes]) + "  ·  Tab et Entrée pour naviguer") font POLICE_ETROITE size 22 color "#d6dcff" outlines [(2, "#000000bb", 0, 0)] xalign 0.5 ypos 672
    if role_verrouille():
        text ("Poste verrouillé : rôle " + ETAT.cfg.get("role", "tous")) font POLICE_ETROITE size 20 color "#e3b341" outlines [(2, "#000000bb", 0, 0)] xalign 0.5 ypos 640
    else:
        text "D : démo guidée (5 min)   ·   R : répétition (EX-12)" font POLICE_ETROITE size 22 color "#36f1cd" outlines [(2, "#000000bb", 0, 0)] xalign 0.5 ypos 636
        key "d" action Return("scenario")
        key "r" action Return("repetition")
    for touche, nom, role, visage, fond, retour in PORTES:
        if retour in ouvertes:
            key touche action Return(retour)


screen s_paiement():
    modal True
    add "bg ville" at panorama
    add Solid("#05061acc")
    use bandeau_injoignable
    $ job = ETAT.job_paiement
    hbox:
        xalign 0.5
        ypos 90
        spacing 40
        vbox:
            spacing 8
            add "visage ombre" at respiration
            text "LE CLIENT" font POLICE_TITRE size 22 color "#d6dcff" xalign 0.5
            text "paiement" font POLICE_ETROITE size 20 color "#8b949e" xalign 0.5
        vbox:
            spacing 20
            xsize 760
            text "Caisse de la Banque Alpha (fictive)" font POLICE_TITRE size 26 color "#ffffff"
            text "Montant : 12,50 EUR (fictif)" font POLICE_ETROITE size 30 color "#c9d1d9"
            textbutton "PAYER" style "bouton_rouge" action Function(lancer_paiement) sensitive attente_libre(job)
            if job is not None and job.etat == "en_cours":
                text "Paiement en cours…" size 24 color "#e3b341"
            elif job is not None:
                text sur(resume_reponse(job.resultat)) size 22 color ("#7ee787" if job.resultat["code"] == 201 else "#ff7b86")
            frame:
                background "#0d1117dd"
                padding (16, 12)
                xsize 760
                vbox:
                    spacing 3
                    text "FLUX (requêtes réelles, façon mitmproxy)" font POLICE_TERMINAL size 16 color "#6e7681"
                    if not ETAT.flux:
                        text "aucune requête pour l'instant" font POLICE_TERMINAL size 18 color "#6e7681"
                    for ligne in ETAT.flux:
                        text sur(ligne) font POLICE_TERMINAL size 19 color "#7ee787"
            textbutton "Retour" style "bouton_clair" action Return("titre")
    key "K_ESCAPE" action Return("titre")


screen s_terminal():
    modal True
    add "bg capuchon"
    add Solid("#000000b0")
    use bandeau_injoignable
    hbox:
        xalign 0.5
        ypos 72
        spacing 24
        vbox:
            spacing 6
            xsize 340
            hbox:
                spacing 14
                add "visage hacker" zoom 0.5 at respiration
                vbox:
                    yalign 0.5
                    text "LE HACKER" font POLICE_TITRE size 20 color "#ff7b86"
                    text "l'attaquant" font POLICE_ETROITE size 20 color "#8b949e"
            for numero, nom in NIVEAUX:
                textbutton nom style "bouton_petit_rouge" action Function(lancer_niveau, numero) sensitive (ETAT.terminal_etat != "en_cours")
            null height 8
            textbutton "AUTONOMIE : LE DUEL" style "bouton_petit" action Jump("autonomie") sensitive (ETAT.terminal_etat != "en_cours")
            null height 6
            textbutton "STOP" style "bouton_stop" action Function(arreter_script)
            textbutton "Retour" style "bouton_petit" action Return("titre")
        vbox:
            spacing 10
            frame:
                background "#0d1117e6"
                xsize 860
                ysize 440
                padding (18, 14)
                vbox:
                    spacing 4
                    xsize 820
                    if not ETAT.terminal:
                        text "Choisissez un niveau d'attaque." font POLICE_TERMINAL size 20 color "#6e7681"
                    for ligne in ETAT.terminal[-15:]:
                        text sur(ligne) font POLICE_TERMINAL size 20 color couleur_ligne(ligne)
            if ETAT.terminal_etat == "en_cours":
                text "Script en cours…" size 22 color "#e3b341"
            elif ETAT.terminal_etat == "arrete":
                text "Arrêté par l'opérateur : l'attaque a cessé." size 22 color "#e3b341"
            elif ETAT.terminal_etat == "fini" and ETAT.dernier_code != 0:
                text ("ÉCHEC du script (code " + str(ETAT.dernier_code) + ")") size 22 color "#ff7b86"
            elif ETAT.terminal_etat == "fini":
                text "Script terminé (code 0). Le résultat sur la plateforme se lit dans le HUD." size 20 color "#c9d1d9"
            if porte_refermee():
                text ("La porte se referme : la plateforme est revenue à l'état OK. Reprise mesurée : " + libelle_chrono() + " (relevé toutes les 2 s).") size 20 color "#7ee787" xmaximum 860
    key "K_ESCAPE" action Return("titre")


screen bloc_recommandation(grand=False):
    $ r = reco()
    frame:
        background "#1b2538"
        padding (16, 10)
        xfill True
        vbox:
            spacing 4
            hbox:
                spacing 12
                text "RECOMMANDATION IA" font POLICE_TITRE size (18 if grand else 15) color "#e3b341"
                text ("informative, aucune action humaine" if grand else "informative") font (POLICE_ETROITE if grand else POLICE_TERMINAL) size (16 if grand else 14) color "#8b949e" yalign 0.5
            if r:
                text sur(r["summary"]) font (POLICE_ETROITE if grand else POLICE_TERMINAL) size (26 if grand else 18) color "#ffffff"
                text ("Action : " + LIBELLE_ACTION.get(r["suggested_action"], r["suggested_action"]) + "  ·  confiance " + str(int(r["confidence"] * 100)) + " %") font (POLICE_ETROITE if grand else POLICE_TERMINAL) size (22 if grand else 17) color "#58a6ff"
                add Solid("#39c5cf", xysize=(int(300 * r["confidence"]), 5))
            else:
                text "pas de recommandation reçue" font POLICE_ETROITE size 20 color "#6e7681"


screen s_soc():
    modal True
    default intervention = False
    default etape = 1
    add "#eef1f6"
    use bandeau_injoignable
    $ q = ETAT.job_question
    hbox:
        xalign 0.5
        ypos 56
        spacing 26
        vbox:
            spacing 6
            xsize 200
            add "visage badge" xalign 0.5 at respiration
            text "LA SENTINELLE" font POLICE_TITRE size 20 color "#1b2433" xalign 0.5
            text "l'IA de défense" font POLICE_ETROITE size 20 color "#57606a" xalign 0.5
            text "lecture seule" font POLICE_ETROITE size 17 color "#8f1d2a" xalign 0.5
        vbox:
            spacing 10
            xsize 980
            hbox:
                spacing 8
                for n, nom in ((1, "1  Comprendre"), (2, "2  Vérifier"), (3, "3  Décider")):
                    frame:
                        background ("#1b2433" if etape == n else "#d7dde5")
                        padding (16, 5)
                        text nom font POLICE_TITRE size 17 color ("#ffffff" if etape == n else "#57606a")
            if etape == 1:
                frame:
                    background ("#fbe3e6" if ETAT.alerte else "#e0e5ec")
                    padding (18, 8)
                    xfill True
                    text ("ALERTE : " + sur(libelle_alerte_longue())) size 21 color ("#8f1d2a" if ETAT.alerte else "#57606a")
                if message_soc():
                    text message_soc() font POLICE_TITRE size 28 color "#0d1117" xalign 0.5
                use bloc_recommandation(True)
                hbox:
                    spacing 14
                    for texte in QUESTIONS_SOC:
                        textbutton texte style "bouton_court" action Function(poser_question, texte) sensitive attente_libre(q)
                if q is not None and q.etat == "en_cours":
                    text ("L'assistant réfléchit… " + str(int(q.duree())) + " s") size 20 color "#57606a"
                elif q is not None:
                    if q.resultat["code"] == 200:
                        text sur(q.resultat["data"]["answer"]) size 20 color "#0d1117"
                        for s in q.resultat["data"]["sources"]:
                            text ("Source : " + sur(s["document"]) + " : " + sur(s["passage"])) size 16 color "#57606a"
                    else:
                        text sur(resume_reponse(q.resultat)) size 21 color "#8f1d2a"
                textbutton "Suite : vérifier" style "bouton_court" action SetScreenVariable("etape", 2)
            elif etape == 2:
                text "Reprise : trois contrôles mesurés" font POLICE_TITRE size 20 color "#1b2433"
                if not ETAT.verifications:
                    text "aucun contrôle reçu du moteur" size 22 color "#57606a"
                for v in ETAT.verifications:
                    frame:
                        background "#ffffff"
                        padding (16, 8)
                        xfill True
                        hbox:
                            spacing 14
                            add Solid(COULEUR_VERIF.get(v["status"], "#8b949e"), xysize=(16, 16)) yalign 0.5
                            text LIBELLE_VERIF.get(v["name"], v["name"]) font POLICE_ETROITE size 26 color "#0d1117" xminimum 420
                            text sur(v["status"].upper()) font POLICE_TERMINAL size 22 color COULEUR_VERIF.get(v["status"], "#8b949e") xminimum 120
                            text sur(v["detail"]) font POLICE_TERMINAL size 17 color "#57606a" yalign 0.5
                if reprise_confirmee():
                    text "REPRISE CONFIRMÉE : les trois contrôles sont ok." font POLICE_TITRE size 22 color "#2ea043"
                else:
                    text "En attente des trois contrôles" font POLICE_ETROITE size 22 color "#57606a"
                hbox:
                    spacing 14
                    textbutton "Retour : comprendre" style "bouton_court" action SetScreenVariable("etape", 1)
                    textbutton "Suite : décider" style "bouton_court" action SetScreenVariable("etape", 3)
            else:
                text "Décider : le Badge ne répare jamais." font POLICE_TITRE size 22 color "#1b2433"
                hbox:
                    spacing 14
                    textbutton "J'interviens moi-même" style "bouton_court" action SetScreenVariable("intervention", True)
                    textbutton "Je fais confiance au système" style "bouton_court" action Return("epilogue")
                    textbutton "Retour : vérifier" style "bouton_court" action SetScreenVariable("etape", 2)
                if intervention:
                    frame:
                        background "#fbe3e6"
                        padding (20, 10)
                        xfill True
                        vbox:
                            spacing 6
                            text "REFUSÉ. Aucune réparation n'est possible depuis le jeu : le jeu n'a rien modifié." size 22 color "#8f1d2a"
                            text "Sujet, p.9 : « Si le service ne se rétablit pas automatiquement et qu'une intervention corrective humaine devient nécessaire pendant le live, l'axe consacré à la remédiation reçoit 0 sur 5. »" size 17 color "#0d1117"
                textbutton "Retour au titre" style "bouton_court" action Return("titre")
    key "K_ESCAPE" action Return("titre")


screen s_demo_refusee():
    modal True
    add "bg capuchon"
    add Solid("#000000c0")
    vbox:
        align (0.5, 0.45)
        spacing 24
        text "MODE DÉMO REFUSÉ" font POLICE_TITRE size 46 color "#ff7b86" xalign 0.5
        if interfaces_simulees():
            text ("Interfaces encore simulées : " + ", ".join(interfaces_simulees())) size 26 color "#c9d1d9" xalign 0.5
        if not role_verrouille():
            text "Rôle du poste non verrouillé (role = tous) : choisissez hote ou attaquant." size 26 color "#c9d1d9" xalign 0.5
        text "Démonstration, clip et jury : réel uniquement, un rôle par poste. Corrigez config/interfaces.json." size 22 color "#8b949e" xalign 0.5
        textbutton "Quitter" style "bouton_clair" xalign 0.5 action Return(True)


screen s_epilogue():
    modal True
    add "bg ville" at panorama
    add Solid("#05061acc")
    vbox:
        align (0.5, 0.45)
        spacing 20
        xsize 940
        text "ZERO-TOUCH" font POLICE_TITRE size 64 color "#7ee787" xalign 0.5 outlines [(3, "#000000aa", 0, 0)]
        if ETAT.chrono_debut is not None and ETAT.chrono_fin is not None:
            text ("La plateforme s'est rétablie en " + libelle_chrono() + " (mesure toutes les 2 s).") size 30 color "#ffffff" xalign 0.5 text_align 0.5
            text ("Transactions de cette session : OK " + str(ETAT.tx_ok) + " / KO " + str(ETAT.tx_ko) + ".") size 24 color "#c9d1d9" xalign 0.5
            text "Aucune réparation n'a été demandée depuis le jeu : le moteur de remédiation a agi seul." size 24 color "#c9d1d9" xalign 0.5 text_align 0.5
        elif ETAT.chrono_debut is not None:
            text "La reprise est encore en cours…" size 30 color "#e3b341" xalign 0.5
        else:
            text "Aucun incident mesuré pour l'instant : lancez une attaque d'abord." size 28 color "#c9d1d9" xalign 0.5
        if ETAT.mode == "simule":
            text "MODE SIMULÉ : cette reprise est simulée, elle ne vaut pas preuve." size 22 color "#ff7b86" xalign 0.5
        textbutton "Retour" style "bouton_clair" xalign 0.5 action Return("titre")
    key "K_ESCAPE" action Return("titre")


screen colonne_titre(couleur, titre, sous_titre, visage=None, largeur=376):
    add Solid(couleur, xysize=(largeur, 4))
    hbox:
        spacing 12
        if visage:
            add visage zoom 0.42
        vbox:
            yalign 0.5
            text titre font POLICE_TITRE size 18 color couleur
            text sous_titre font POLICE_ETROITE size 19 color "#c9d1d9"


screen s_salle():
    modal True
    default projection = False
    add "bg ville" at panorama
    add Solid("#05061ab8")
    use bandeau_injoignable
    text "SALLE DE CONTRÔLE" font POLICE_TITRE size 24 color "#ffffff" xpos 24 ypos 44
    $ marque, couleur_marque = mode_global()
    text marque font POLICE_TITRE size 22 color couleur_marque xalign 1.0 xoffset -24 ypos 46
    hbox:
        xalign 0.5
        ypos 84
        spacing 12
        frame:
            background "#0b0f17e6"
            xsize 330
            ysize 324
            padding (14, 12)
            vbox:
                spacing 6
                use colonne_titre("#ff7b86", "LE HACKER", etat_capuchon(), "visage hacker", 300)
                for e in evenements_de("attaquant", 5):
                    text (heure(e) + "  " + sur(e["detail"])) font POLICE_TERMINAL size 16 color "#ff7b86"
        frame:
            background "#0b0f17e6"
            xsize 420
            ysize 324
            padding (16, 12)
            vbox:
                spacing 6
                add Solid("#58a6ff", xysize=(388, 4))
                text ("PLATEFORME : " + libelle_sante()) font POLICE_TITRE size 22 color couleur_sante()
                hbox:
                    spacing 6
                    for moment in ("avant", "pendant", "après"):
                        frame:
                            background ("#58a6ff" if phase_frise() == moment else "#161b22")
                            padding (12, 4)
                            text moment font POLICE_ETROITE size 19 color ("#0b0f17" if phase_frise() == moment else "#6e7681")
                text ("REPRISE " + libelle_chrono()) font POLICE_TERMINAL size 30 color ("#7ee787" if phase_frise() == "après" else "#ffffff")
                for c in ETAT.composants:
                    hbox:
                        spacing 8
                        add Solid(couleur_composant(c["status"]), xysize=(10, 10)) yalign 0.5
                        text sur(c["name"]) font POLICE_TERMINAL size 17 color "#c9d1d9"
                text ("Client  " + etat_ombre()) font POLICE_TERMINAL size 17 color "#8b949e"
        frame:
            background "#0b0f17e6"
            xsize 480
            ysize 324
            padding (16, 12)
            vbox:
                spacing 6
                use colonne_titre("#e3b341", "LA SENTINELLE", etat_badge(), "visage badge", 446)
                use bloc_recommandation(False)
                text sur("Alerte  " + libelle_alerte_longue()) font POLICE_TERMINAL size 16 color ("#ff7b86" if ETAT.alerte else "#6e7681") xmaximum 448
                for e in evenements_de("moteur", 2):
                    text (heure(e) + "  " + sur(e["detail"])) font POLICE_TERMINAL size 15 color "#58a6ff"
    hbox:
        xalign 0.5
        ypos 420
        spacing 12
        frame:
            background "#0b0f17e6"
            xsize 500
            ysize 196
            padding (16, 10)
            vbox:
                spacing 4
                if ETAT.scores:
                    text "SCORE D'ANOMALIE" font POLICE_ETROITE size 18 color "#8b949e"
                    fixed:
                        xysize (468, 108)
                        hbox:
                            spacing 1
                            yalign 1.0
                            for h, couleur in barres_score()[-46:]:
                                add Solid(couleur, xysize=(9, h)) yalign 1.0
                        add Solid("#ffffff99", xysize=(468, 1)) ypos 38
                        text "seuil" font POLICE_TERMINAL size 13 color "#8b949e" xalign 1.0 ypos 20
                else:
                    text "SCORE D'ANOMALIE : pas de détecteur branché" font POLICE_ETROITE size 19 color "#6e7681"
        frame:
            background "#0b0f17e6"
            xsize 330
            ysize 196
            padding (16, 10)
            vbox:
                spacing 3
                text "FLUX BLOQUÉS" font POLICE_ETROITE size 18 color "#8b949e"
                text str(ETAT.flux_total) font POLICE_TERMINAL size 40 color ("#e3b341" if ETAT.flux_total else "#6e7681")
                for f in reversed(ETAT.flux_bloques[-3:]):
                    text (heure(f) + "  " + sur(f["rule"]) + "  x" + str(f["count"])) font POLICE_TERMINAL size 15 color "#e3b341"
        frame:
            background "#0b0f17e6"
            xsize 400
            ysize 196
            padding (14, 10)
            vbox:
                spacing 3
                text "JOURNAL" font POLICE_ETROITE size 17 color "#8b949e"
                for e in reversed(ETAT.evenements[-7:]):
                    text (heure(e) + "  " + sur(e["detail"])) font POLICE_TERMINAL size 15 color COULEUR_SOURCE.get(e.get("source"), "#c9d1d9")
    if not projection:
        text "P projection  ·  V vague  ·  Échap retour" font POLICE_ETROITE size 19 color "#8b95c9" xalign 0.5 ypos 664
    key "p" action ToggleScreenVariable("projection")
    key "v" action Show("s_vague")
    key "K_ESCAPE" action Return("titre")



init python:
    PARTICIPANTS_PLEIN = 50  # jauge pleine a ce nombre (affichage seulement)

    def vague_total():
        return (ETAT.vague or {}).get("total", 0)

    def vague_phase():
        return (ETAT.vague or {}).get("phase", "repos")

    def vague_decompte():
        return (ETAT.vague or {}).get("decompte", 0)

    def vague_fraction():
        return max(0.0, min(1.0, vague_total() / float(PARTICIPANTS_PLEIN)))

    def _qr_vague(st, at):
        if ETAT.qr_vague and renpy.loadable(ETAT.qr_vague):
            return Transform(ETAT.qr_vague, fit="contain", xysize=(320, 320)), 1.0
        return Text("QR en attente\nlancer scripts/tunnel.sh", font=POLICE_ETROITE, size=22,
                    color="#6e7681", xalign=0.5), 1.0



    def ui_armer_vague():
        armer_vague(30)

    def ui_reset_vague():
        reset_vague()


screen s_vague():
    modal True
    add "bg ville" at panorama
    add Solid("#05061ad8")
    $ frac = vague_fraction()
    $ phase = vague_phase()
    text "REJOINDRE LA VAGUE" font POLICE_TITRE size 34 color "#36f1cd" xalign 0.5 ypos 40
    hbox:
        xalign 0.5
        ypos 134
        spacing 56
        vbox:
            spacing 12
            xalign 0.5
            add DynamicDisplayable(_qr_vague) xalign 0.5
            text "Scannez pour rejoindre" font POLICE_ETROITE size 22 color "#c9d1d9" xalign 0.5
        vbox:
            spacing 16
            yalign 0.5
            text "PARTICIPANTS" font POLICE_ETROITE size 20 color "#8b949e"
            text str(vague_total()) font POLICE_TITRE size 96 color "#36f1cd"
            frame:
                background "#161b22"
                xsize 360
                ysize 26
                padding (0, 0)
                add Solid("#36f1cd", xysize=(int(360 * frac), 26))
            if phase == "ouvert":
                text ("DÉPART DANS " + str(int(vague_decompte() + 0.999)) + " s") font POLICE_TITRE size 34 color "#ff5d73"
            elif phase == "termine":
                text "LA VAGUE EST PARTIE" font POLICE_TITRE size 34 color "#ff5d73"
            else:
                text "EN ATTENTE DU DÉPART" font POLICE_ETROITE size 26 color "#8b949e"
    text "Les scans ne font que signaler. La charge part de notre machine, dans le SI fictif." font POLICE_ETROITE size 20 color "#8b95c9" xalign 0.5 ypos 600
    text "A armer 30 s  ·  R remettre à zéro  ·  Échap retour" font POLICE_ETROITE size 19 color "#6e7681" xalign 0.5 ypos 648
    key "a" action Function(ui_armer_vague)
    key "r" action Function(ui_reset_vague)
    key "K_ESCAPE" action Hide("s_vague")



init python:
    # Campagne : les 4 types d'attaque mis en scene, un par palier, du plus simple au
    # plus retors. (niveau, couleur, nom, ce que ca casse, ce qu'il faut regarder)
    CAMPAGNE = [
        (1, "#ff7b86", "SATURER LES PAIEMENTS",
         "Des milliers de faux clients paient en meme temps.",
         "La caisse sature. Regardez la sante virer et les paiements echouer."),
        (2, "#e3b341", "EPUISER LES RESSOURCES",
         "Des connexions tenues ouvertes, jamais relachees.",
         "Le service etouffe lentement, sans un paquet de trop."),
        (3, "#d29922", "SATURER LE RESEAU",
         "Un flot de paquets noie le lien reseau.",
         "Le reseau se bouche : la plateforme devient injoignable."),
        (4, "#58a6ff", "INJECTER UNE REQUETE",
         "Une requete piegee tente de tromper l'API.",
         "Celle-la ne se redemarre pas : elle se bloque et se verifie."),
    ]


# Carton de campagne : lisible, ne defile JAMAIS tout seul (espace pour avancer).
# C'est la correction du reproche "ca va trop vite, on comprend rien".
screen s_carton(couleur, titre, quoi="", regardez=""):
    modal True
    zorder 150
    add "bg ville" at panorama
    add Solid("#05060ff2")
    vbox:
        xalign 0.5
        yalign 0.5
        spacing 20
        xsize 1040
        add Solid(couleur, xysize=(1040, 5))
        text titre font POLICE_TITRE size 50 color couleur xalign 0.5 text_align 0.5
        if quoi:
            text quoi font POLICE_ETROITE size 30 color "#ffffff" xalign 0.5 text_align 0.5 xmaximum 1000
        if regardez:
            text regardez font POLICE_ETROITE size 24 color "#9fb0d8" xalign 0.5 text_align 0.5 xmaximum 1000
    text "espace pour continuer" font POLICE_ETROITE size 18 color "#6e7681" xalign 0.5 ypos 656
    key "K_SPACE" action Return(True)
    key "K_RETURN" action Return(True)
    # Avance seule apres un delai lisible (regle par carton_s) : l'humain a le temps de
    # lire ou saute a l'espace ; en projection ou en test, ca progresse sans clavier.
    timer ETAT.cfg.get("carton_s", 8.0) action Return(True)


screen intertitre(titre, sous=""):
    modal True
    zorder 150
    add "bg ville" at panorama
    add Solid("#05060ff2")
    vbox:
        xalign 0.5
        yalign 0.5
        spacing 18
        text titre font POLICE_TITRE size 46 color "#36f1cd" xalign 0.5
        if sous:
            text sous font POLICE_ETROITE size 27 color "#d6dcff" xalign 0.5 xmaximum 980 text_align 0.5
    text "espace pour continuer" font POLICE_ETROITE size 18 color "#6e7681" xalign 0.5 ypos 648
    key "K_SPACE" action Return(True)
    key "K_RETURN" action Return(True)
    timer 7.0 action Return(True)



screen s_vague_auto(duree=6.0):
    use s_vague
    timer duree action Return(True)

screen scenario_salle(cap=50.0):
    use s_salle
    timer 0.4 repeat True action If(ETAT.sante == "ok" and ETAT.chrono_fin is not None, Return(True), NullAction())
    timer cap action Return(True)
