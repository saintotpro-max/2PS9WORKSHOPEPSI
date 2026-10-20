


label start:
    $ pont_demarrer()
    show screen hud
    if ETAT.cfg.get("demo") and (interfaces_simulees() or not role_verrouille()):
        call screen s_demo_refusee
        return
    jump titre

label titre:
    $ choix = renpy.call_screen("s_titre")
    if choix == "hacker":
        call screen s_terminal
    elif choix == "client":
        call screen s_paiement
    elif choix == "soc":
        $ suite = renpy.call_screen("s_soc")
        if suite == "epilogue":
            call screen s_epilogue
    elif choix == "salle":
        call screen s_salle
    elif choix == "scenario":
        jump scenario
    elif choix == "repetition":
        jump repetition
    jump titre




label repetition:
    $ _passes = int(ETAT.cfg.get("repetition_passes", 10))
    $ ETAT.repetition = dict(passes=0, ok=0, en_cours=True)
    $ _i = 0
    while _i < _passes:
        $ ETAT.chrono_debut = None
        $ ETAT.chrono_fin = None
        $ http("POST", ETAT.cfg["plateforme"]["url"], "/simulation/reset")
        $ lancer_niveau(1)
        call screen scenario_salle()
        $ lancer_paiement()
        $ _t = 0
        while not paiement_fini() and _t < 40:
            pause 0.3
            $ _t += 1
        $ ETAT.repetition["passes"] += 1
        if paiement_ok():
            $ ETAT.repetition["ok"] += 1
        $ _i += 1
    $ ETAT.repetition["en_cours"] = False
    call screen intertitre("RÉPÉTITION (EX-12)", "%d/%d passages réussis, sans aucune intervention humaine." % (ETAT.repetition["ok"], ETAT.repetition["passes"]))
    jump titre




label scenario:
    # Campagne guidee lisible : les 4 types d'attaque, un par un, chacun avec son carton,
    # sa reprise mesuree et sa preuve. Le joueur regarde (ZERO-TOUCH) et avance a l'espace.
    $ ETAT.tx_ok = 0
    $ ETAT.tx_ko = 0
    $ ETAT.chrono_debut = None
    $ ETAT.chrono_fin = None
    call screen s_carton("#36f1cd", "RÉSILIENCE ALPHA", "Une banque encaisse une attaque et se relève toute seule.", "Vous regardez la salle de contrôle. Vous ne touchez à rien.")

    $ lancer_paiement()
    $ attendre(paiement_fini, 15)
    call screen s_carton("#2ea043", "AVANT", "Le client paie. Le service répond.", "Tout est vert : c'est l'état normal, avant l'attaque.")

    python:
        for _niv, _coul, _nom, _quoi, _regardez in CAMPAGNE:
            renpy.call_screen("s_carton", _coul, "ATTAQUE %d/4 — %s" % (_niv, _nom), _quoi, _regardez)
            lancer_niveau(_niv)
            son_attaque(_niv)
            if _niv == 4:
                # Injection : pas de panne a mesurer, elle est bloquee et verifiee.
                # On ne reinitialise pas le chrono (l'epilogue garde la derniere reprise reelle).
                attendre(lambda: ETAT.flux_total > 0 or reprise_confirmee() or ETAT.terminal_etat == "fini", 14)
                renpy.call_screen("s_carton", _coul, "NE TOUCHEZ À RIEN",
                                  "Le système a vu l'injection. Il la bloque, sans tomber.",
                                  "Aucun humain n'intervient. Regardez le flux se faire bloquer.")
                renpy.call_screen("scenario_salle", cap=12)
                jouer(SON_REPRISE)
                renpy.call_screen("s_carton", "#7ee787", "BLOQUÉE — %s" % _nom,
                                  "La requête piégée a été bloquée et vérifiée.",
                                  "Pas de redémarrage : le service n'est jamais tombé.")
            else:
                ETAT.chrono_debut = None
                ETAT.chrono_fin = None
                attendre(lambda: ETAT.sante in ("degraded", "down") or ETAT.terminal_etat == "fini", 14)
                renpy.call_screen("s_carton", _coul, "NE TOUCHEZ À RIEN",
                                  "Le système a vu l'attaque. Il se répare seul.",
                                  "Aucun humain n'intervient. Regardez la reprise se mesurer.")
                renpy.call_screen("scenario_salle")
                jouer(SON_REPRISE)
                renpy.call_screen("s_carton", "#7ee787", "REPRISE — %s" % _nom,
                                  "La plateforme est revenue. Reprise mesurée : %s." % libelle_chrono(),
                                  "Une transaction repasse. Zéro intervention humaine.")

    call screen s_epilogue
    jump titre


label autonomie:
    # Duel autonome depuis l'ecran du Hacker : l'attaquant enchaine ses tactiques (1 -> 4),
    # la defense reagit seule, tout se voit sur l'ecran du duel. ZERO-TOUCH.
    $ ETAT.tx_ok = 0
    $ ETAT.tx_ko = 0
    $ duel_reset()
    python:
        # Duree de lecture minimale par tour : plus longue en mode reel pour laisser le
        # modele repondre (~14 s) ; courte sinon. Reglable via cfg["duel_s"].
        _dwell = 16.0 if duel_ia_active() else float(ETAT.cfg.get("duel_s", 7.0))
        for _niv, _coul, _nom, _quoi, _regardez in CAMPAGNE:
            ETAT.duel["tour"] = _niv
            ETAT.duel["nom"] = _nom
            ETAT.duel["raison"] = duel_raison(_niv)
            ETAT.duel["def_raison"] = ""
            duel_ia_async(_niv)
            duel_defense_async(_niv)
            if _niv != 4:
                ETAT.chrono_debut = None
                ETAT.chrono_fin = None
            lancer_niveau(_niv)
            son_attaque(_niv)
            renpy.call_screen("s_duel", _coul, _niv, _dwell)
            jouer(SON_REPRISE)
        ETAT.duel["fini"] = True
    call screen s_epilogue
    jump titre
