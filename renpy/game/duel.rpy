# Duel autonome : LE HACKER (attaque) contre LA SENTINELLE (defense), sur l'ecran du
# Hacker. Deterministe par defaut ; le modele reel (config/ia-duel.env) se branchera sur
# duel_raison() sans changer l'affichage. Le joueur reste sur cet ecran et voit tout.

init python:
    # Tactique de l'attaquant, tour par tour : il commence petit, monte quand ca tient,
    # change de tactique quand la force ne passe pas (injection).
    DUEL_TACTIQUE = {
        1: "Je commence petit : noyer la caisse sous les paiements.",
        2: "Ca a tenu. Je monte d'un cran : epuiser les ressources, connexions gardees ouvertes.",
        3: "Toujours debout. Je saute au reseau : saturer le lien.",
        4: "La force ne passe pas. Je change de tactique : injecter une requete piegee.",
    }

    def duel_reset():
        ETAT.duel = dict(tour=0, nom="", raison="", def_raison="", fini=False)

    def duel_actif():
        return ETAT.duel is not None

    def duel_raison(niveau):
        # Point de branchement du modele reel (persona attaquant). Deterministe pour
        # l'instant ; le connecteur IA remplira ce texte quand ia-duel.env sera actif.
        return DUEL_TACTIQUE.get(niveau, "")

    def duel_resolu(niveau):
        # Fin d'un tour : pour une panne, la plateforme est revenue et la reprise est
        # mesuree ; pour l'injection, le script a fini (bloquee et verifiee, pas de panne).
        if niveau == 4:
            return ETAT.terminal_etat in ("fini", "arrete") or reprise_confirmee()
        return ETAT.sante == "ok" and ETAT.chrono_fin is not None

    # ---- Connecteur IA reel (persona attaquant) -----------------------------------
    # Reutilise le mecanisme existant : lit ~/.config/alpha/ia-duel.env sinon nanogpt.env.
    # Actif seulement en SIM_LLM=1 (jamais en test, jamais le jour J). Threade + cache +
    # repli deterministe : si le modele tarde ou echoue, la phrase ecrite reste affichee.
    _duel_cache = {}

    PROMPT_HACKER = (
        "Tu es LE HACKER, l'attaquant d'une plateforme de paiement fictive, dans un labo "
        "ferme et autorise. Tu enchaines des attaques du plus simple au plus retors. "
        "Reponds en UNE phrase courte (max 20 mots), a la premiere personne, qui annonce ta "
        "prochaine tactique et pourquoi. Pas de consignes techniques, juste l'intention.")

    PROMPT_DEFENSE = (
        "Tu es LA SENTINELLE, l'IA de defense d'une plateforme de paiement fictive. Tu "
        "DECIDES l'action de reprise parmi : bloquer la source, redemarrer le service, "
        "limiter le debit, ajouter de la capacite, ne rien faire. Reponds en UNE phrase "
        "courte (max 20 mots) : l'action choisie et pourquoi.")

    def _duel_cfg():
        import os
        cfg = {}
        for chemin in ("~/.config/alpha/ia-duel.env", "~/.config/alpha/nanogpt.env"):
            p = os.path.expanduser(chemin)
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    for ligne in f:
                        if "=" in ligne and not ligne.startswith("#"):
                            cle, val = ligne.strip().split("=", 1)
                            cfg.setdefault(cle, val)
        cle = cfg.get("IA_API_KEY") or cfg.get("NANOGPT_API_KEY")
        url = cfg.get("IA_URL", "https://nano-gpt.com/api/v1").rstrip("/") + "/chat/completions"
        base = cfg.get("IA_MODEL") or cfg.get("NANOGPT_MODEL") or "qwen/qwen3.8-27b-cybersecurity"
        m_att = cfg.get("IA_MODEL_ATTAQUE") or base
        m_def = cfg.get("IA_MODEL_DEFENSE") or base
        return cle, url, m_att, m_def

    def duel_ia_active():
        import os
        return os.environ.get("SIM_LLM") == "1" and _duel_cfg()[0] is not None

    def _duel_discuter(messages, modele, empreinte):
        # Appel modele partage (attaque + defense). SSL tolerant (Python Ren'Py sans bundle
        # CA), gros budget de jetons (modeles a raisonnement), cache. Renvoie texte ou None.
        if empreinte in _duel_cache:
            return _duel_cache[empreinte]
        import json, re, ssl, urllib.request
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl._create_unverified_context()
        cle, url, _, _ = _duel_cfg()
        corps = {"model": modele, "messages": messages, "max_tokens": 900, "temperature": 0.6}
        req = urllib.request.Request(url, data=json.dumps(corps).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + cle})
        try:
            with urllib.request.urlopen(req, timeout=45.0, context=ctx) as r:
                texte = json.load(r)["choices"][0]["message"].get("content") or ""
            texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S).strip()
            _duel_cache[empreinte] = texte
            return texte
        except Exception:
            return None

    def duel_ia_async(niveau):
        # Persona attaquant : raconte sa prochaine tactique (modele IA_MODEL_ATTAQUE).
        if not duel_ia_active():
            return
        def run():
            _, _, m_att, _ = _duel_cfg()
            contexte = "Tour %d. Sante du service : %s. Alerte : %s." % (niveau, libelle_sante(), libelle_alerte())
            texte = _duel_discuter([{"role": "user", "content": PROMPT_HACKER + "\n\n" + contexte}],
                                   m_att, "att%d-%s" % (niveau, m_att))
            if texte and ETAT.duel and ETAT.duel.get("tour") == niveau:
                ETAT.duel["raison"] = texte
        fil = __import__("threading").Thread(target=run)
        fil.daemon = True
        fil.start()

    def duel_defense_async(niveau):
        # Persona defenseur : SEULE la defense s'appuie sur le modele pour la DECISION
        # (demande utilisateur). Repli = reco deterministe via duel_defense_raison().
        if not duel_ia_active():
            return
        def run():
            _, _, _, m_def = _duel_cfg()
            contexte = "Attaque de type : %s. Sante : %s. Alerte : %s." % (
                dict(NIVEAUX).get(niveau, "?"), libelle_sante(), libelle_alerte())
            texte = _duel_discuter([{"role": "user", "content": PROMPT_DEFENSE + "\n\n" + contexte}],
                                   m_def, "def%d-%s" % (niveau, m_def))
            if texte and ETAT.duel and ETAT.duel.get("tour") == niveau:
                ETAT.duel["def_raison"] = texte
        fil = __import__("threading").Thread(target=run)
        fil.daemon = True
        fil.start()

    def duel_defense_raison():
        # Reaction de la defense : portee par la recommandation du detecteur, sinon etat.
        r = reco()
        if r:
            return "%s -> %s" % (r["summary"], LIBELLE_ACTION.get(r["suggested_action"], r["suggested_action"]))
        if ETAT.alerte:
            return "Alerte recue, analyse en cours."
        if ETAT.sante == "ok":
            return "Rien a signaler : le service repond."
        return "Le service observe..."


screen s_duel(couleur, niveau, dwell=7.0):
    modal True
    # Duree de lecture minimale : le tour ne se ferme pas avant `dwell`, meme si la reprise
    # est deja mesuree -> on a le temps de lire l'echange (fin du "defile trop vite").
    default lisible = False
    timer dwell action SetScreenVariable("lisible", True)
    add "bg capuchon"
    add Solid("#000000b8")
    use bandeau_injoignable
    # En-tete : on est bien sur l'ecran du Hacker, en mode duel autonome.
    hbox:
        xpos 24
        ypos 48
        spacing 16
        text "AUTONOMIE — DUEL" font POLICE_TITRE size 24 color "#36f1cd"
        text ("TOUR %d / 4" % niveau) font POLICE_TITRE size 24 color couleur yalign 0.5
    hbox:
        xalign 0.5
        ypos 92
        spacing 14
        # Attaquant
        frame:
            background "#0b0f17e6"
            xsize 330
            ysize 540
            padding (14, 12)
            vbox:
                spacing 8
                use colonne_titre("#ff7b86", "LE HACKER", "l'attaquant", "visage hacker", 300)
                text sur(ETAT.duel["nom"]) font POLICE_TITRE size 22 color couleur
                text sur(ETAT.duel["raison"]) font POLICE_ETROITE size 20 color "#ffd7db" xmaximum 300
                null height 6
                for e in evenements_de("attaquant", 4):
                    text (heure(e) + "  " + sur(e["detail"])) font POLICE_TERMINAL size 15 color "#ff7b86" xmaximum 300
        # Logs au centre (le flux du duel)
        frame:
            background "#0d1117f0"
            xsize 560
            ysize 540
            padding (16, 12)
            vbox:
                spacing 4
                text "LOGS" font POLICE_ETROITE size 16 color "#6e7681"
                for ligne in ETAT.terminal[-13:]:
                    text sur(ligne) font POLICE_TERMINAL size 18 color couleur_ligne(ligne) xmaximum 524
                null height 4
                for ligne in ETAT.flux[-4:]:
                    text sur(ligne) font POLICE_TERMINAL size 16 color "#58a6ff" xmaximum 524
        # Defenseur
        frame:
            background "#0b0f17e6"
            xsize 360
            ysize 540
            padding (14, 12)
            vbox:
                spacing 8
                use colonne_titre("#e3b341", "LA SENTINELLE", "l'IA de defense", "visage badge", 332)
                text sur((ETAT.duel and ETAT.duel.get("def_raison")) or duel_defense_raison()) font POLICE_ETROITE size 19 color "#ffe9b0" xmaximum 332
                null height 4
                text ("SANTE : " + libelle_sante()) font POLICE_TERMINAL size 18 color couleur_sante()
                text ("REPRISE " + libelle_chrono()) font POLICE_TERMINAL size 22 color ("#7ee787" if ETAT.chrono_fin else "#c9d1d9")
                for v in ETAT.verifications:
                    hbox:
                        spacing 8
                        add Solid(COULEUR_VERIF.get(v["status"], "#8b949e"), xysize=(12, 12)) yalign 0.5
                        text LIBELLE_VERIF.get(v["name"], v["name"]) font POLICE_TERMINAL size 15 color "#c9d1d9" xmaximum 300
    text "Duel autonome : vous regardez. Espace pour accelerer." font POLICE_ETROITE size 19 color "#8b95c9" xalign 0.5 ypos 648
    # Avance quand le tour est resolu ET que la duree de lecture minimale est passee ;
    # espace pour avancer tout de suite ; cap de securite.
    timer 0.4 repeat True action If(lisible and duel_resolu(niveau), Return(True), NullAction())
    timer 60 action Return(True)
    key "K_SPACE" action Return(True)
    key "K_RETURN" action Return(True)
