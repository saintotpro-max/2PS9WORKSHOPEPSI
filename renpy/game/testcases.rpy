


init python:
    def test_remise_a_zero():
        ETAT.cfg = charger_config()
        ETAT.cfg["sondage_s"] = 0.5
        ETAT.tx_ok = 0
        ETAT.tx_ko = 0
        ETAT.terminal = []
        ETAT.terminal_etat = "repos"
        ETAT.dernier_code = None
        ETAT.runs = {}
        ETAT.chrono_debut = None
        ETAT.chrono_fin = None
        ETAT.job_paiement = None
        ETAT.job_question = None
        ETAT.alerte = None
        ETAT.evenements = []
        ETAT.scores = []
        ETAT.arret_demande = False
        ETAT.flux_bloques = []
        ETAT.flux_total = 0
        os.environ["ATTAQUE_DUREE_S"] = "3"
        os.environ["ALPHA_CONFIG"] = CHEMIN_CONFIG
        http("POST", ETAT.cfg["plateforme"]["url"], "/simulation/reset")

    def test_pid_enfant():
        try:
            with open("/tmp/alpha-test-enfant.pid", encoding="utf-8") as f:
                return int(f.read())
        except (OSError, ValueError):
            return None

    def test_processus_vivant(pid):
        try:
            with open("/proc/%d/stat" % pid, encoding="utf-8") as f:
                return f.read().split()[2] != "Z"
        except OSError:
            return False

    def test_enfant_vivant():
        pid = test_pid_enfant()
        return pid is not None and test_processus_vivant(pid)

    def test_enfant_mort():
        pid = test_pid_enfant()
        return pid is not None and not test_processus_vivant(pid)

    def test_en_cours():
        return ETAT.terminal_etat == "en_cours"

    def test_arrete():
        return ETAT.terminal_etat == "arrete" and "[arrêté par l'opérateur]" in ETAT.terminal

    def test_rien_a_arreter():
        return bool(ETAT.terminal) and "rien à arrêter" in ETAT.terminal[-1]

    def test_flux_bloques():
        return ETAT.flux_total > 0

    def test_config_hors_perimetre():
        chemin = "/tmp/alpha-config-hors-perimetre.json"
        cfg = json.loads(json.dumps(ETAT.cfg))
        cfg["plateforme"]["url"] = "http://8.8.8.8:80"
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        os.environ["ALPHA_CONFIG"] = chemin

    def test_refus_perimetre():
        return ETAT.terminal_etat == "fini" and ETAT.dernier_code == 3 and any("hors périmètre" in l for l in ETAT.terminal)

    def test_alerte_avec_recommandation():
        return ETAT.alerte is not None and ETAT.alerte.get("recommendation") is not None

    def test_verifications_ok():
        return len(ETAT.verifications) == 3 and all(v["status"] == "ok" for v in ETAT.verifications)

    def test_etape(n):
        ecran = renpy.get_screen("s_soc")
        return ecran is not None and ecran.scope.get("etape") == n

    def test_tout_reel():
        for nom in ("plateforme", "moteur", "assistant", "detection", "attaque"):
            ETAT.cfg[nom]["mode"] = "reel"

    def test_attaque_sim(detection, reprise):
        http("POST", ETAT.cfg["plateforme"]["url"], "/simulation/attaque",
             dict(niveau=1, detection_s=detection, reprise_s=reprise))

    def test_paiement_ok():
        return ETAT.tx_ok == 1

    def test_paiement_refuse():
        return ETAT.tx_ko == 1 and ETAT.tx_ok == 0

    def test_sante_ok():
        return ETAT.sante == "ok" and ETAT.joignable is True

    def test_injoignable():
        return ETAT.joignable is False

    def test_script_en_echec():
        return ETAT.terminal_etat == "fini" and ETAT.dernier_code not in (0, None)

    def test_script_termine_bien():
        return ETAT.terminal_etat == "fini" and ETAT.dernier_code == 0

    def test_question_ok():
        j = ETAT.job_question
        return j is not None and j.etat == "fini" and j.resultat["code"] == 200

    def test_intervention_refusee():
        ecran = renpy.get_screen("s_soc")
        return ecran is not None and ecran.scope.get("intervention") is True

    def test_attaque_declaree():
        return any(e.get("source") == "attaquant" and e["type"] == "attack_started" for e in ETAT.evenements)

    def test_score_depasse_seuil():
        return any(x["score"] > x["threshold"] for x in ETAT.scores)

    def test_composants_presents():
        return len(ETAT.composants) > 0

    def test_reprise_mesuree():
        return ETAT.chrono_debut is not None and ETAT.chrono_fin is not None

    def test_message_observe():
        return message_soc() == "Le système observe…"

    def test_message_sait():
        return message_soc() == "Ne touchez à rien : le système réagit seul."

    def test_projection_active():
        ecran = renpy.get_screen("s_salle")
        return ecran is not None and ecran.scope.get("projection") is True

    def test_une_porte():
        return portes_autorisees() == ["hacker"]

    def test_sans_capuchon():
        return "hacker" not in portes_autorisees()

    def test_vague_ouverte():
        return vague_phase() == "ouvert"

    def test_vague_participants(n):
        return vague_total() >= n

    def test_qr_telecharge():
        return ETAT.qr_vague is not None

    def test_repetition_finie():
        r = ETAT.repetition
        return not r.get("en_cours") and r.get("passes", 0) >= 3 and r.get("ok") == r.get("passes")

testsuite jeu:
    teardown:
        exit
    before testcase:
        $ test_remise_a_zero()
        $ ETAT.cfg["carton_s"] = 0.5
        $ ETAT.cfg["duel_s"] = 0.5
        run Jump("start")
        assert screen "s_titre" timeout 8

    testcase paiement_reel_avant_attaque:
        description "S2 : PAYER envoie une vraie transaction et affiche la réponse de l'API"
        keysym "3"
        click "PAYER"
        assert eval test_paiement_ok() timeout 5
        assert eval test_sante_ok() timeout 5

    testcase attaque_panne_reprise_paiement:
        description "UC-02 puis UC-01 : attaque, paiement refusé pendant la panne, reprise seule, paiement accepté"
        keysym "1"
        click "Saturer les paiements"
        assert eval test_attaque_declaree() timeout 5
        keysym "K_ESCAPE"
        keysym "3"
        click "PAYER"
        assert eval test_paiement_refuse() timeout 4
        assert eval test_reprise_mesuree() timeout 12
        click "PAYER"
        assert eval test_paiement_ok() timeout 5

    testcase plateforme_injoignable:
        description "EC5 : santé injoignable, le jeu ne plante pas et le dit"
        $ ETAT.cfg["plateforme"]["url"] = "http://127.0.0.1:9"
        assert eval test_injoignable() timeout 8
        assert screen "s_titre"

    testcase script_en_echec_affiche_tel_quel:
        description "EC2 : un script d'attaque qui échoue n'est jamais présenté comme un succès"
        $ ETAT.cfg["attaque"]["dossier"] = "attack/inexistant"
        keysym "1"
        click "Épuiser les ressources"
        assert eval test_script_en_echec() timeout 8

    testcase soc_refuse_intervention_manuelle:
        description "UC-04 et UC-05 : vraie réponse de l'assistant, intervention manuelle refusée"
        keysym "2"
        click "Que se passe-t-il ?"
        assert eval test_question_ok() timeout 10
        click "Suite : vérifier"
        click "Suite : décider"
        click "J'interviens moi-même"
        assert eval test_intervention_refusee() timeout 3

    testcase demo_refusee_si_interface_simulee:
        description "FR-4 : en mode démo, une interface simulée bloque le lancement"
        $ ETAT.cfg["demo"] = True
        run Jump("start")
        assert screen "s_demo_refusee" timeout 5

    testcase salle_de_controle_trois_points_de_vue:
        description "S7 : l'attaque déclarée, le score en direct, les composants et le journal arrivent dans la salle de contrôle"
        keysym "1"
        click "Saturer les paiements"
        assert eval test_script_termine_bien() timeout 9
        keysym "K_ESCAPE"
        keysym "4"
        assert screen "s_salle" timeout 3
        assert eval test_attaque_declaree() timeout 6
        assert eval test_score_depasse_seuil() timeout 6
        assert eval test_composants_presents() timeout 4
        keysym "p"
        assert eval test_projection_active() timeout 3

    testcase vague_participation_cockpit:
        description "Vague : le cockpit ouvre l'écran de participation, télécharge le QR, compte les scans, arme le décompte"
        $ http("POST", ETAT.cfg["detection"]["url"], "/participation/reset")
        keysym "4"
        assert screen "s_salle" timeout 3
        keysym "v"
        assert screen "s_vague" timeout 3
        assert eval test_qr_telecharge() timeout 6
        $ http("POST", ETAT.cfg["detection"]["url"], "/participation/rejoindre")
        $ http("POST", ETAT.cfg["detection"]["url"], "/participation/rejoindre")
        assert eval test_vague_participants(2) timeout 6
        keysym "a"
        assert eval test_vague_ouverte() timeout 6
        keysym "K_ESCAPE"
        assert screen "s_salle" timeout 3

    testcase scenario_boucle_b:
        description "Boucle B : la démo guidée enchaîne avant / pendant / après jusqu'à l'épilogue, sans intervention"
        keysym "d"
        assert screen "s_epilogue" timeout 160
        assert eval test_reprise_mesuree() timeout 3

    testcase duel_autonome:
        description "AUTONOMIE : depuis l'ecran du Hacker, le duel enchaine les 4 tactiques seul jusqu'a l'epilogue"
        keysym "1"
        assert screen "s_terminal" timeout 5
        click "AUTONOMIE : LE DUEL"
        assert screen "s_duel" timeout 10
        assert screen "s_epilogue" timeout 160
        assert eval test_reprise_mesuree() timeout 3

    testcase repetition_ex12:
        description "EX-12 : la démo passe plusieurs fois de suite sans intervention humaine"
        $ ETAT.cfg["repetition_passes"] = 3
        keysym "r"
        assert eval test_repetition_finie() timeout 120

    testcase role_attaquant_une_seule_porte:
        description "FR-23 : le poste attaquant n'offre que la porte du capuchon"
        $ ETAT.cfg["role"] = "attaquant"
        run Jump("start")
        assert eval test_une_porte() timeout 3
        keysym "2"
        assert screen "s_titre"

    testcase role_hote_sans_capuchon:
        description "FR-23 : le poste hôte n'offre pas l'attaque (le jury ne peut pas attaquer)"
        $ ETAT.cfg["role"] = "hote"
        run Jump("start")
        assert eval test_sans_capuchon() timeout 3
        keysym "1"
        assert screen "s_titre"

    testcase demo_refusee_sans_role_verrouille:
        description "FR-4 et FR-23 : en démo, un rôle non verrouillé est refusé même si tout est réel"
        $ test_tout_reel()
        $ ETAT.cfg["demo"] = True
        run Jump("start")
        assert screen "s_demo_refusee" timeout 5
        $ ETAT.cfg["role"] = "hote"
        run Jump("start")
        assert screen "s_titre" timeout 5

    testcase message_soc_selon_alerte:
        description "FR-16 : « le système sait » seulement après l'alerte"
        $ test_attaque_sim(4, 8)
        assert eval test_message_observe() timeout 4
        assert eval test_message_sait() timeout 8

    testcase epilogue_apres_incident:
        description "FR-17 : épilogue ZERO-TOUCH avec la reprise mesurée"
        $ test_attaque_sim(1, 1.5)
        assert eval test_reprise_mesuree() timeout 12
        keysym "2"
        click "Suite : vérifier"
        click "Suite : décider"
        click "Je fais confiance au système"
        assert screen "s_epilogue" timeout 3

    testcase stop_arrete_l_outil_et_ses_enfants:
        description "FR-32 : STOP arrête le script ET l'outil qu'il a lancé ; le terminal dit « arrêté », pas « échec »"
        $ ETAT.cfg["attaque"]["dossier"] = "attack/test"
        keysym "1"
        click "Saturer les paiements"
        assert eval test_enfant_vivant() timeout 6
        click "STOP"
        assert eval test_arrete() timeout 6
        assert eval test_enfant_mort() timeout 6

    testcase stop_sans_script_le_dit:
        description "FR-32 : STOP sans script en cours l'indique au lieu de ne rien faire"
        keysym "1"
        click "STOP"
        assert eval test_rien_a_arreter() timeout 3

    testcase attaque_niveau_1_lancee_puis_arretee:
        description "FR-33 : saturer les paiements, lancé puis arrêté, la plateforme revient saine"
        $ os.environ["ATTAQUE_DUREE_S"] = "30"
        keysym "1"
        click "Saturer les paiements"
        assert eval test_en_cours() timeout 5
        assert eval test_attaque_declaree() timeout 5
        click "STOP"
        assert eval test_arrete() timeout 6
        assert eval test_sante_ok() timeout 10

    testcase attaque_niveau_2_lancee_puis_arretee:
        description "FR-33 : épuiser les ressources, lancé puis arrêté"
        $ os.environ["ATTAQUE_DUREE_S"] = "30"
        keysym "1"
        click "Épuiser les ressources"
        assert eval test_en_cours() timeout 5
        click "STOP"
        assert eval test_arrete() timeout 6
        assert eval test_sante_ok() timeout 10

    testcase attaque_niveau_3_lancee_puis_arretee:
        description "FR-33 : saturer le réseau, lancé puis arrêté"
        $ os.environ["ATTAQUE_DUREE_S"] = "30"
        keysym "1"
        click "Saturer le réseau"
        assert eval test_en_cours() timeout 5
        click "STOP"
        assert eval test_arrete() timeout 6
        assert eval test_sante_ok() timeout 10

    testcase attaque_niveau_4_injection_bloquee_puis_arretee:
        description "FR-33 et FR-30 : l'injection est bloquée (flux bloqués) sans dégrader le service ; lancée puis arrêtée"
        $ os.environ["ATTAQUE_DUREE_S"] = "30"
        keysym "1"
        click "Injecter une requête"
        assert eval test_en_cours() timeout 5
        assert eval test_flux_bloques() timeout 8
        assert eval test_sante_ok() timeout 3
        click "STOP"
        assert eval test_arrete() timeout 6

    testcase attaque_hors_perimetre_refusee:
        description "FR-37 : une cible hors du réseau du groupe est refusée avant tout envoi"
        $ test_config_hors_perimetre()
        keysym "1"
        click "Saturer les paiements"
        assert eval test_refus_perimetre() timeout 6
        assert eval test_sante_ok() timeout 3

    testcase soc_en_trois_etapes_avec_recommandation:
        description "FR-26 à FR-28 : comprendre (recommandation), vérifier (trois contrôles mesurés), décider"
        $ test_attaque_sim(1, 2)
        assert eval test_alerte_avec_recommandation() timeout 8
        keysym "2"
        assert eval test_etape(1) timeout 3
        click "Suite : vérifier"
        assert eval test_etape(2) timeout 3
        assert eval test_verifications_ok() timeout 12
        click "Suite : décider"
        assert eval test_etape(3) timeout 3

    testcase salle_flux_bloques_et_recommandation:
        description "FR-30 et FR-26 : l'injection fait apparaître des flux bloqués et une recommandation, sans panne"
        $ http("POST", ETAT.cfg["plateforme"]["url"], "/simulation/attaque", dict(niveau=4, detection_s=1, reprise_s=1))
        keysym "4"
        assert screen "s_salle" timeout 3
        assert eval test_flux_bloques() timeout 8
        assert eval test_alerte_avec_recommandation() timeout 8
        assert eval test_sante_ok() timeout 3

testsuite scenario_visuel:
    teardown:
        exit
    before testcase:
        $ test_remise_a_zero()
        $ ETAT.cfg["carton_s"] = 0.5
        $ ETAT.cfg["duel_s"] = 0.5
        run Jump("start")
        assert screen "s_titre" timeout 8
    testcase captures_scenario:
        description "Captures des temps forts de la démo guidée (botnet, cockpit en reprise, épilogue)"
        keysym "d"
        pause 6.0
        screenshot "../captures/07-botnet.png"
        assert screen "scenario_salle" timeout 30
        pause 1.5
        screenshot "../captures/08-cockpit-reprise.png"
        assert screen "s_epilogue" timeout 45
        screenshot "../captures/09-epilogue.png"

testsuite menu:
    teardown:
        exit
    testcase menu_principal:
        description "Le menu principal au démarrage montre le fond de ville, plus de fond noir"
        assert screen "main_menu" timeout 8
        screenshot "../captures/00-menu.png"

testsuite visuel:
    teardown:
        exit
    before testcase:
        $ test_remise_a_zero()
        $ ETAT.cfg["carton_s"] = 0.5
        $ ETAT.cfg["duel_s"] = 0.5
        run Jump("start")
        assert screen "s_titre" timeout 8

    testcase captures:
        description "Captures d'écran des écrans du jeu pour relecture visuelle (scripts/test-jeu.sh visuel)"
        screenshot "../captures/01-titre.png"
        keysym "1"
        click "Saturer les paiements"
        assert eval test_attaque_declaree() timeout 5
        screenshot "../captures/02-terminal.png"
        keysym "K_ESCAPE"
        keysym "3"
        click "PAYER"
        assert eval test_paiement_refuse() timeout 4
        screenshot "../captures/03-paiement-refuse.png"
        keysym "K_ESCAPE"
        keysym "2"
        click "Que se passe-t-il ?"
        assert eval test_question_ok() timeout 10
        assert eval test_alerte_avec_recommandation() timeout 8
        pause 1.0
        screenshot "../captures/04-soc-comprendre.png"
        click "Suite : vérifier"
        assert eval test_etape(2) timeout 3
        screenshot "../captures/04-soc-verifier.png"
        click "Suite : décider"
        click "J'interviens moi-même"
        assert eval test_intervention_refusee() timeout 3
        screenshot "../captures/04-soc.png"
        keysym "K_ESCAPE"
        keysym "4"
        assert eval test_score_depasse_seuil() timeout 6
        assert eval test_alerte_avec_recommandation() timeout 8
        pause 1.0
        screenshot "../captures/05-salle.png"
        $ http("POST", ETAT.cfg["detection"]["url"], "/participation/reset")
        $ [http("POST", ETAT.cfg["detection"]["url"], "/participation/rejoindre") for _ in range(12)]
        keysym "v"
        assert screen "s_vague" timeout 3
        keysym "a"
        assert eval test_vague_ouverte() timeout 6
        pause 1.0
        screenshot "../captures/05b-vague.png"
        keysym "K_ESCAPE"
        keysym "K_ESCAPE"
        keysym "2"
        assert eval test_reprise_mesuree() timeout 12
        click "Suite : vérifier"
        click "Suite : décider"
        click "Je fais confiance au système"
        assert screen "s_epilogue" timeout 3
        screenshot "../captures/06-epilogue.png"
        keysym "K_ESCAPE"
        assert screen "s_titre" timeout 5
        keysym "1"
        assert screen "s_terminal" timeout 5
        click "AUTONOMIE : LE DUEL"
        assert screen "s_duel" timeout 10
        pause 4.0
        screenshot "../captures/10-duel.png"


testsuite reel:
    teardown:
        exit
    testcase duel_llm:
        description "Mode reel : le modele fait parler LE HACKER dans le duel (SIM_LLM=1)"
        run Jump("start")
        assert screen "s_titre" timeout 8
        keysym "1"
        assert screen "s_terminal" timeout 5
        click "AUTONOMIE : LE DUEL"
        assert screen "s_duel" timeout 10
        pause 20.0
        screenshot "../captures/10-duel-reel.png"
