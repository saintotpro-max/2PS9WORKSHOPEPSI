




init -10 python:
    import json
    import os
    import subprocess
    import threading
    import time
    import urllib.error
    import urllib.request

    RACINE = os.path.abspath(os.path.join(config.basedir, ".."))
    CHEMIN_CONFIG = os.environ.get("ALPHA_CONFIG") or os.path.join(RACINE, "config", "interfaces.json")

    def charger_config():
        """Lit config/interfaces.json ; sans lui, retombe sur le simulateur, signalé."""
        try:
            with open(CHEMIN_CONFIG, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["_erreur"] = None
            return cfg
        except Exception as e:
            repli = dict(mode="simule", url="http://127.0.0.1:8765")
            return dict(demo=False, plateforme=repli, moteur=repli, assistant=repli,
                        attaque=dict(mode="simule", dossier="attack/simule", python="python3"),
                        _erreur="config illisible : %s" % e)

    class Etat(NoRollback):
        """État partagé avec les fils d'arrière-plan ; jamais sauvegardé ni annulé."""
        def __init__(self):
            self.cfg = charger_config()
            self.joignable = None      # None = pas encore mesuré
            self.sante = "?"
            self.mode = "?"
            self.alerte = None
            self.tx_ok = 0
            self.tx_ko = 0
            self.chrono_debut = None
            self.chrono_fin = None
            self.terminal = []
            self.terminal_etat = "repos"
            self.dernier_code = None
            self.runs = {}
            self.processus = None
            self.demarre = False
            self.job_paiement = None
            self.job_question = None
            self.flux = []             # lignes de flux, façon mitmproxy (requêtes réelles seulement)
            self.evenements = []       # journal du moteur et événements déclarés
            self.composants = []
            self.scores = []           # série du détecteur ; vide = pas de détecteur branché
            self.flux_bloques = []     # flux bloqués par le WAF ; vide = pas de WAF branché
            self.flux_total = 0
            self.verifications = []
            self.arret_demande = False
            self.vague = None          # etat du compteur de participation (jauge, decompte)
            self.qr_vague = None       # chemin relatif du QR telecharge, ou None
            self.repetition = dict(passes=0, ok=0, en_cours=False)  # EX-12 : 10 passages sans intervention
            self.duel = None           # etat du duel autonome (attaquant/defenseur, raisons)
            self.chat = {"hacker": [], "sentinelle": []}  # canal de conversation par persona
            self.match = None          # etat du match in-tour : {tour, niveau, en_cours}
            self.latences = []         # latence reelle des paiements (ms), pour la salle vivante
            # Cible de l'attaque (IP/URL de la plateforme). Choisie au cockpit, elle sert
            # a la fois a la supervision (HUD) et a la charge reelle (passee a ra-attacker).
            self.cible = (self.cfg.get("plateforme") or {}).get("url", "")

    ETAT = Etat()

    def cible_actuelle():
        return ETAT.cible or (ETAT.cfg.get("plateforme") or {}).get("url", "") or ""

    def dire(persona, texte):
        """Ajoute une ligne au canal de conversation d'une IA (hacker/sentinelle).
        Horodatee, dedoublonnee d'affilee, canal borne pour ne pas gonfler sans fin."""
        texte = (texte or "").strip()
        if not texte:
            return
        canal = ETAT.chat.setdefault(persona, [])
        if canal and canal[-1]["texte"] == texte:
            return
        canal.append(dict(at=time.strftime("%H:%M:%S"), texte=texte))
        del canal[:-30]

    def canal(persona):
        return ETAT.chat.get(persona, [])

    def definir_cible(valeur):
        """Change l'IP/URL attaquee depuis le cockpit. Normalise, met a jour la
        supervision ET la charge, puis persiste dans config/interfaces.json pour que
        le choix survive a un redemarrage (l'IP WAN de pfSense change selon le Wi-Fi)."""
        valeur = (valeur or "").strip().rstrip("/")
        if not valeur:
            return cible_actuelle()
        if "://" not in valeur:
            valeur = "https://" + valeur            # defaut HTTPS (WAF autosigne)
        ETAT.cible = valeur
        if isinstance(ETAT.cfg.get("plateforme"), dict):
            ETAT.cfg["plateforme"]["url"] = valeur   # le HUD surveille la nouvelle cible
        ETAT.chrono_debut = ETAT.chrono_fin = None   # repart proprement sur la nouvelle cible
        try:
            with open(CHEMIN_CONFIG, encoding="utf-8") as f:
                disque = json.load(f)
            if isinstance(disque.get("plateforme"), dict):
                disque["plateforme"]["url"] = valeur
            with open(CHEMIN_CONFIG, "w", encoding="utf-8") as f:
                json.dump(disque, f, indent=2, ensure_ascii=False)
        except Exception:
            pass                                     # persistance best-effort
        return valeur

    def http(methode, base, chemin, corps=None, jeton=None, timeout=3.0, trace=False):
        """Appel HTTP. Renvoie toujours un dict : code, data, mode, erreur.
        trace=True ajoute une ligne de flux (méthode, route, code, durée mesurée)."""
        debut = time.time()
        r = http_brut(methode, base, chemin, corps, jeton, timeout)
        if trace:
            ms = int((time.time() - debut) * 1000)
            ETAT.flux.append("%s %s  ->  %s  (%d ms)" % (methode, chemin, r["code"] if r["code"] is not None else "ÉCHEC", ms))
            del ETAT.flux[:-6]
        return r

    def http_brut(methode, base, chemin, corps=None, jeton=None, timeout=3.0):
        donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
        requete = urllib.request.Request(base.rstrip("/") + chemin, data=donnees, method=methode,
                                         headers={"Content-Type": "application/json"})
        if jeton:
            requete.add_header("Authorization", "Bearer " + jeton)
        try:
            with urllib.request.urlopen(requete, timeout=timeout) as r:
                brut = r.read().decode("utf-8")
                return dict(code=r.status, data=json.loads(brut) if brut else None,
                            mode=r.headers.get("X-Mode"), erreur=None)
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read().decode("utf-8"))
            except Exception:
                data = None
            return dict(code=e.code, data=data, mode=e.headers.get("X-Mode"), erreur=None)
        except Exception as e:
            return dict(code=None, data=None, mode=None, erreur=str(e))

    def boucle_sante():
        """Interroge la santé toutes les 2 s et mesure la durée réelle de la reprise."""
        while True:
            base = ETAT.cfg["plateforme"]["url"]
            r = http("GET", base, "/health", timeout=1.5)
            if r["code"] == 200 and r["data"]:
                ETAT.joignable = True
                nouveau = r["data"].get("status", "?")
                ETAT.mode = r["data"].get("mode") or r["mode"] or "?"
                if nouveau != "ok" and (ETAT.chrono_debut is None or ETAT.chrono_fin is not None):
                    ETAT.chrono_debut = time.time()
                    ETAT.chrono_fin = None
                if nouveau == "ok" and ETAT.chrono_debut is not None and ETAT.chrono_fin is None:
                    ETAT.chrono_fin = time.time()
                ETAT.sante = nouveau
                alertes = http("GET", ETAT.cfg["moteur"]["url"], "/alerts", timeout=1.5)
                if alertes["code"] == 200 and alertes["data"]:
                    liste = alertes["data"].get("alerts", [])
                    ETAT.alerte = liste[-1] if liste else None
                ev = http("GET", ETAT.cfg["moteur"]["url"], "/events", timeout=1.5)
                if ev["code"] == 200 and ev["data"]:
                    ETAT.evenements = ev["data"].get("events", [])[-40:]
                cp = http("GET", ETAT.cfg["moteur"]["url"], "/components", timeout=1.5)
                if cp["code"] == 200 and cp["data"]:
                    ETAT.composants = cp["data"].get("components", [])
                det = ETAT.cfg.get("detection", ETAT.cfg["moteur"])
                sc = http("GET", det["url"], "/scores", timeout=1.5)
                if sc["code"] == 200 and sc["data"]:
                    ETAT.scores = sc["data"].get("scores", [])[-60:]
                fb = http("GET", ETAT.cfg.get("waf", det)["url"], "/flux-bloques", timeout=1.5)
                if fb["code"] == 200 and fb["data"]:
                    ETAT.flux_bloques = fb["data"].get("blocked", [])
                    ETAT.flux_total = fb["data"].get("total", 0)
                vf = http("GET", ETAT.cfg["moteur"]["url"], "/verifications", timeout=1.5)
                if vf["code"] == 200 and vf["data"]:
                    ETAT.verifications = vf["data"].get("verifications", [])
                pa = http("GET", det["url"], "/participation/etat", timeout=1.5)
                if pa["code"] == 200 and pa["data"]:
                    ETAT.vague = pa["data"]
                    if ETAT.qr_vague is None and rafraichir_qr_vague(det["url"]):
                        ETAT.qr_vague = "cache/vague_qr.png"
            else:
                ETAT.joignable = False
            time.sleep(ETAT.cfg.get("sondage_s", 2.0))

    def rafraichir_qr_vague(base):
        """Telecharge le QR du compteur (simulateur) dans game/cache pour l'affichage au cockpit.
        Le QR encode l'URL publique a scanner (ALPHA_VAGUE_URL cote simulateur, sinon l'URL locale)."""
        try:
            dossier = os.path.join(config.gamedir, "cache")
            if not os.path.isdir(dossier):
                os.makedirs(dossier)
            with urllib.request.urlopen(base.rstrip("/") + "/participation/qr.png", timeout=3.0) as r:
                donnees = r.read()
            with open(os.path.join(dossier, "vague_qr.png"), "wb") as f:
                f.write(donnees)
            return True
        except Exception:
            return False

    def armer_vague(duree_s=30):
        """Arme le decompte : au top, l'operateur lance attack/arsenal/vague.py (machine de l'equipe)."""
        det = ETAT.cfg.get("detection", ETAT.cfg["moteur"])
        return http("POST", det["url"], "/participation/armer", dict(duree_s=duree_s), timeout=2.0)

    def reset_vague():
        det = ETAT.cfg.get("detection", ETAT.cfg["moteur"])
        ETAT.qr_vague = None
        return http("POST", det["url"], "/participation/reset", timeout=2.0)

    def pont_demarrer():
        if not ETAT.demarre:
            ETAT.demarre = True
            fil = threading.Thread(target=boucle_sante)
            fil.daemon = True
            fil.start()


    def interfaces_simulees():
        return [nom for nom, v in ETAT.cfg.items() if hasattr(v, "get") and v.get("mode") == "simule"]

    class Job(NoRollback):
        """Une action réseau en arrière-plan ; l'écran lit etat et resultat."""
        def __init__(self, fonction):
            self.etat = "en_cours"
            self.resultat = None
            self.debut = time.time()
            self.fin = None
            fil = threading.Thread(target=self._executer, args=(fonction,))
            fil.daemon = True
            fil.start()

        def _executer(self, fonction):
            try:
                self.resultat = fonction()
            except Exception as e:
                self.resultat = dict(code=None, data=None, mode=None, erreur=str(e))
            self.fin = time.time()
            self.etat = "fini"

        def duree(self):
            return (self.fin or time.time()) - self.debut

    def payer():
        base = ETAT.cfg["plateforme"]["url"]
        jeton = http("POST", base, "/auth/token", dict(username="demo", password="demo"), trace=True)
        if jeton["code"] != 200:
            ETAT.tx_ko += 1
            return jeton
        r = http("POST", base, "/transactions",
                 dict(amount_cents=1250, currency="EUR", payer="client-fictif", payee="boutique-fictive"),
                 jeton=jeton["data"]["access_token"], trace=True)
        if r["code"] == 201:
            ETAT.tx_ok += 1
        else:
            ETAT.tx_ko += 1
        return r

    def lancer_paiement():
        if ETAT.job_paiement is None or ETAT.job_paiement.etat == "fini":
            ETAT.job_paiement = Job(payer)

    def attendre(cond, timeout=25.0, pas=0.2):
        """Attend qu'une condition devienne vraie (scénario guidé), sans figer l'UI."""
        fin = time.time() + timeout
        while not cond() and time.time() < fin:
            renpy.pause(pas, hard=True)
        return cond()

    def paiement_fini():
        return ETAT.job_paiement is not None and ETAT.job_paiement.etat == "fini"

    def paiement_ok():
        return paiement_fini() and ETAT.job_paiement.resultat.get("code") == 201

    QUESTIONS_SOC = ["Que se passe-t-il ?", "Que fait le système ?", "Quelle procédure s'applique ?"]

    def poser_question(question="Que se passe-t-il ?"):
        if ETAT.job_question is None or ETAT.job_question.etat == "fini":
            ETAT.job_question = Job(lambda: http(
                "POST", ETAT.cfg["assistant"]["url"], "/assistant/ask",
                dict(question=question), timeout=60.0, trace=True))

    NIVEAUX = [(1, "Saturer les paiements"), (2, "Épuiser les ressources"), (3, "Saturer le réseau"), (4, "Injecter une requête")]

    def _lancer_processus(commande):
        """Lance l'outil dans son propre groupe de processus pour pouvoir l'arrêter avec ses enfants.
        La cible choisie au cockpit est transmise par l'environnement : RA_CIBLE (vague
        reelle via ra-attacker) et ALPHA_PLATEFORME_URL (scripts de charge directs)."""
        env = os.environ.copy()
        cible = cible_actuelle()
        if cible:
            env["RA_CIBLE"] = cible
            env["ALPHA_PLATEFORME_URL"] = cible
        options = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, cwd=RACINE, env=env)
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        return subprocess.Popen(commande, **options)

    def _tuer_arbre(p, force=False):
        """Arrête le processus ET ses enfants (Linux : groupe de processus ; Windows : taskkill /T)."""
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        import signal
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL if force else signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    def _executer_niveau(niveau):
        cfg = ETAT.cfg["attaque"]
        # Niveau reel (arsenal, vraie charge sur la plateforme) ou simule (simulateur).
        dossier = cfg["dossier"]
        if niveau in cfg.get("niveaux_reels", []):
            dossier = cfg.get("dossier_reel", dossier)
        script = os.path.join(RACINE, dossier, "niveau-%d.py" % niveau)
        code = None
        try:
            ETAT.processus = _lancer_processus([cfg.get("python", "python3"), script])
            if ETAT.arret_demande:

                _tuer_arbre(ETAT.processus)
            for ligne in ETAT.processus.stdout:
                ETAT.terminal.append(ligne.rstrip())
            code = ETAT.processus.wait()
        except Exception as e:
            ETAT.terminal.append("ERREUR : %s" % e)
            code = -1
        ETAT.dernier_code = code
        if ETAT.arret_demande:
            ETAT.terminal.append("[arrêté par l'opérateur]")
            declarer("attack_ended", "arrêt demandé par l'opérateur")
            ETAT.terminal_etat = "arrete"
        else:
            ETAT.terminal.append("[code de sortie %s]" % code)
            declarer("attack_ended", "script terminé (code %s)" % code)
            ETAT.terminal_etat = "fini"

    def declarer(type_, detail):
        """Le poste attaquant déclare son action pour l'affichage (jamais à la place de l'alerte)."""
        def envoyer():
            http("POST", ETAT.cfg["moteur"]["url"], "/events",
                 dict(type=type_, component="payment-api", detail=detail, source="attaquant"), timeout=2.0)
        fil = threading.Thread(target=envoyer)
        fil.daemon = True
        fil.start()

    def portes_autorisees():
        role = ETAT.cfg.get("role", "tous")
        if role == "attaquant":
            return ["hacker"]
        if role == "hote":
            return ["soc", "client", "salle"]
        return ["hacker", "soc", "client", "salle"]

    def role_verrouille():
        return ETAT.cfg.get("role", "tous") in ("hote", "attaquant")

    def lancer_niveau(niveau):
        if ETAT.terminal_etat == "en_cours":
            return
        ETAT.runs[niveau] = ETAT.runs.get(niveau, 0) + 1
        nom = dict(NIVEAUX)[niveau]
        ETAT.terminal = ["$ niveau %d : %s (exécution n°%d)" % (niveau, nom, ETAT.runs[niveau])]
        ETAT.terminal_etat = "en_cours"
        ETAT.dernier_code = None
        ETAT.arret_demande = False
        ETAT.processus = None
        declarer("attack_started", "niveau %d : %s" % (niveau, nom))
        fil = threading.Thread(target=_executer_niveau, args=(niveau,))
        fil.daemon = True
        fil.start()

    def arreter_script():
        """STOP : arrête l'outil et tous ses processus enfants ; le dit s'il n'y a rien à arrêter."""
        if ETAT.terminal_etat != "en_cours":
            ETAT.terminal.append("[rien à arrêter : aucun script en cours]")
            return
        ETAT.arret_demande = True
        ETAT.terminal.append("[arrêt demandé]")
        p = ETAT.processus
        if p is not None and p.poll() is None:
            _tuer_arbre(p)
            minuteur = threading.Timer(2.0, lambda: _tuer_arbre(p, force=True) if p.poll() is None else None)
            minuteur.daemon = True
            minuteur.start()

    # ---- Pilote du MATCH in-tour : les deux IA enchainent, l'operateur garde la main ------
    def match_en_cours():
        return bool(ETAT.match and ETAT.match.get("en_cours"))

    def _flux_paiements():
        """Flux de paiements legitimes en fond pendant le match (~8/s). TX OK/KO = vrais
        appels ; c'est ce flux que l'attaque fait echouer -> degradation reelle et visible."""
        base = ETAT.cfg["plateforme"]["url"]
        j = http("POST", base, "/auth/token", dict(username="demo", password="demo"))
        jeton = (j.get("data") or {}).get("access_token") if j["code"] == 200 else None
        while match_en_cours():
            t0 = time.time()
            r = http("POST", base, "/transactions",
                     dict(amount_cents=1250, currency="EUR", payer="client-fictif", payee="boutique-fictive"),
                     jeton=jeton, timeout=3.0)
            ETAT.latences.append(int((time.time() - t0) * 1000))   # latence vecue, vrai signal
            del ETAT.latences[:-60]
            if r["code"] == 201:
                ETAT.tx_ok += 1
            else:
                ETAT.tx_ko += 1
                if r["code"] in (401, None):      # jeton expire ou injoignable : re-auth
                    j = http("POST", base, "/auth/token", dict(username="demo", password="demo"))
                    jeton = (j.get("data") or {}).get("access_token") if j["code"] == 200 else None
            time.sleep(0.12)

    def _detecteur_match():
        """Detecteur-seuil local (perimetre dev, pas de ML) : quand la LATENCE paiements
        vecue monte (vrai signal : file d'attente sous charge) ou que la plateforme se
        degrade, envoie une VRAIE alerte DoS au moteur (recommande block_source, l'action
        qui reussit en local) -> le moteur decide, la Sentinelle rapporte sa vraie decision."""
        alerte_envoyee = False
        cible = (ETAT.cfg.get("moteur") or {}).get("cible", "alpha-paiement")
        while match_en_cours():
            lat = latence_pic()
            if (lat > 200 or ETAT.sante in ("degraded", "down")) and not alerte_envoyee:
                reco = dict(summary="Saturation des paiements detectee",
                            suggested_action="block_source", confidence=0.9)
                http("POST", ETAT.cfg["moteur"]["url"], "/alerts", dict(
                    source="detecteur-local", kind="dos", severity="high", score=0.9,
                    target=cible, detail="Latence paiements %d ms sous charge" % lat,
                    recommendation=reco), timeout=3.0)
                # Rebranche la reco de la Sentinelle sur le vrai signal (le moteur reel ne
                # sert pas GET /alerts : on pose l'alerte localement pour l'affichage).
                ETAT.alerte = dict(kind="dos", recommendation=reco)
                alerte_envoyee = True
            elif lat < 60 and ETAT.sante == "ok":
                alerte_envoyee = False
                ETAT.alerte = None
            time.sleep(0.5)

    def demarrer_match():
        """Lance le match des deux IA dans la tour, en tache de fond (pas d'ecran modal).
        Le HACKER choisit et lance de vraies attaques ; la SENTINELLE raconte la decision.
        En fond : un flux de vrais paiements + un detecteur-seuil (boucle reelle locale)."""
        if match_en_cours():
            return
        if ETAT.terminal_etat == "en_cours":
            arreter_script()   # un match part d'un etat propre : on coupe l'attaque en cours
        ETAT.match = dict(en_cours=True, tour=0, niveau=None)
        ETAT.chat = {"hacker": [], "sentinelle": []}
        ETAT.tx_ok = 0
        ETAT.tx_ko = 0
        for cible_fil in (_boucle_match, _flux_paiements, _detecteur_match):
            t = threading.Thread(target=cible_fil)
            t.daemon = True
            t.start()

    def arreter_match():
        """STOP du match : coupe la boucle et l'outil en cours."""
        if ETAT.match:
            ETAT.match["en_cours"] = False
        arreter_script()

    def _attendre(predicat, limite_s):
        fin = time.time() + limite_s
        while time.time() < fin and match_en_cours() and predicat():
            time.sleep(0.3)

    def _boucle_match():
        """Un tour = le Hacker choisit (LLM) -> vraie attaque -> la Sentinelle ANALYSE le flux
        PENDANT l'attaque et pose sa contre-mesure, qui COUPE l'attaque (pas une minuterie).
        S'arrete au bout des 4 tactiques ou sur STOP."""
        # Exactement 4 tours (un par tactique, escalade 1->4), puis fin nette. Le niveau
        # suggere = le numero du tour, pour que les attaques different et que ca progresse.
        derniere_defense = ""
        for tour in (1, 2, 3, 4):
            if not match_en_cours():
                break
            _attendre(lambda: ETAT.terminal_etat == "en_cours", 3.0)  # terminal libre avant le tour
            niveau, raison = hacker_prochain(tour, derniere_defense)  # le Hacker riposte a la defense
            ETAT.match["tour"] = tour
            ETAT.match["niveau"] = niveau
            dire("hacker", raison)
            lancer_niveau(niveau)
            # Laisse la charge tourner ~8 s : la latence et les requetes montent, la
            # Sentinelle a de la vraie matiere a analyser avant de decider.
            _attendre(lambda: ETAT.terminal_etat == "en_cours", 8.0)
            derniere_defense = sentinelle_prochain(niveau)   # la Sentinelle decide, en reponse
            dire("sentinelle", derniere_defense)
            if match_en_cours() and ETAT.terminal_etat == "en_cours":
                arreter_script()                 # contre-mesure : la defense coupe l'attaque
            _attendre(lambda: ETAT.terminal_etat == "en_cours", 6.0)
            _attendre(lambda: ETAT.chrono_fin is None, 3.0)   # laisse mesurer la reprise
        if ETAT.match:
            ETAT.match["en_cours"] = False
            dire("sentinelle", "Match termine : le service a tenu, zero intervention humaine.")

    def sur(texte):
        """Échappe le texte venu de l'extérieur avant affichage."""
        return str(texte).replace("[", "[[").replace("{", "{{")

    def libelle_sante():
        return {"ok": "OK", "degraded": "DÉGRADÉE", "down": "À L'ARRÊT"}.get(ETAT.sante, "inconnue")

    def couleur_sante():
        if ETAT.joignable is False:
            return "#dc3545"
        return {"ok": "#2ea043", "degraded": "#d29922", "down": "#dc3545"}.get(ETAT.sante, "#8b949e")

    def libelle_chrono():
        if ETAT.chrono_debut is None:
            return "-"
        fin = ETAT.chrono_fin or time.time()
        return "%.0f s%s" % (fin - ETAT.chrono_debut, "" if ETAT.chrono_fin else " (en cours)")

    def libelle_alerte():
        """Forme courte (HUD)."""
        a = ETAT.alerte
        if not a:
            return "aucune"
        return "%s %s sur %s" % (a.get("severity", "?").upper(), a.get("kind", "?"), a.get("target", "?"))

    NIVEAU_WAZUH = {"low": 3, "medium": 7, "high": 12}

    def libelle_alerte_longue():
        """Forme façon Wazuh (règle, niveau sur 15) avec le score du détecteur s'il existe."""
        a = ETAT.alerte
        if not a:
            return "aucune"
        score = a.get("score")
        suite = " · score %.2f" % score if score is not None else ""
        return "niveau %d/15 · %s sur %s%s" % (
            NIVEAU_WAZUH.get(a.get("severity"), 0), a.get("kind", "?"), a.get("target", "?"), suite)

    def resume_reponse(r):
        """Texte honnête d'une réponse : succès tel quel, ou échec réel."""
        if r is None:
            return ""
        if r["code"] is None:
            return "Échec réel : plateforme injoignable (%s)" % r["erreur"]
        detail = ""
        if hasattr(r["data"], "get"):
            detail = r["data"].get("detail") or r["data"].get("id") or ""
        return "Réponse de l'API : %s %s (mode %s)" % (r["code"], detail, r["mode"] or "?")
