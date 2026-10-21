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

    def _duel_discuter(messages, modele, empreinte=None):
        # Appel modele partage (attaque + defense). SSL tolerant (Python Ren'Py sans bundle CA).
        # empreinte falsy -> AUCUN cache (chaque replay varie). Temperature haute pour varier
        # meme a prompt identique. Renvoie texte ou None.
        if empreinte and empreinte in _duel_cache:
            return _duel_cache[empreinte]
        import json, re, ssl, urllib.request
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl._create_unverified_context()
        cle, url, _, _ = _duel_cfg()
        corps = {"model": modele, "messages": messages, "max_tokens": 150, "temperature": 0.9}
        req = urllib.request.Request(url, data=json.dumps(corps).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + cle})
        try:
            with urllib.request.urlopen(req, timeout=45.0, context=ctx) as r:
                texte = json.load(r)["choices"][0]["message"].get("content") or ""
            texte = re.sub(r"<think>.*?</think>", "", texte, flags=re.S).strip()
            if empreinte:
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
            return "%s -> %s" % (r["summary"], libelle_action(r["suggested_action"]))
        if ETAT.alerte:
            return "Alerte recue, analyse en cours."
        if ETAT.sante == "ok":
            return "Rien a signaler : le service repond."
        return "Le service observe..."

    # ---- Match in-tour : chaque persona CHOISIT et AGIT (reutilise le connecteur IA) -----
    def _contexte_flux():
        """Signaux REELS que les IA 'lisent' en temps reel : PIC de latence et charge
        mesures pendant l'attaque (pas la derniere valeur deja retombee), sante, flux."""
        import re
        bits = ["Sante: %s" % libelle_sante(), "Alerte: %s" % libelle_alerte()]
        latences, requetes = [], 0
        for l in ETAT.terminal[-8:]:
            m = re.search(r"latence /health (\d+) ms", l)
            if m:
                latences.append(int(m.group(1)))
            m2 = re.search(r"(\d+) requetes envoyees", l)
            if m2:
                requetes = max(requetes, int(m2.group(1)))
        if latences:
            bits.append("Latence /health pic %d ms (ref ~13 ms)" % max(latences))
        if requetes:
            bits.append("Charge %d requetes" % requetes)
        if ETAT.flux_total:
            bits.append("Flux bloques: %d" % ETAT.flux_total)
        return " | ".join(bits)

    def latence_pic():
        """Pic de latence /health mesure dans les dernieres lignes de charge (vrai, en ms)."""
        import re
        vals = []
        for l in ETAT.terminal[-8:]:
            m = re.search(r"latence /health (\d+) ms", l)
            if m:
                vals.append(int(m.group(1)))
        return max(vals) if vals else 0

    SEUIL_RALENTI_MS = 80
    SEUIL_SATURE_MS = 200

    def latence_actuelle():
        """Latence reelle du flux de paiements (ETAT.latences), mesure la plus recente.
        0 si aucun paiement n'a encore ete mesure (pas de match en cours)."""
        return ETAT.latences[-1] if ETAT.latences else 0

    def latence_moyenne(n=10):
        if not ETAT.latences:
            return 0
        recentes = ETAT.latences[-n:]
        return int(sum(recentes) / len(recentes))

    def statut_plateforme():
        """FLUIDE / RALENTI / SATURE selon la latence reelle des paiements. Couleur assortie."""
        lat = latence_moyenne()
        if not ETAT.latences:
            return "EN ATTENTE", "#6e7681"
        if lat >= SEUIL_SATURE_MS:
            return "SATURE", "#dc3545"
        if lat >= SEUIL_RALENTI_MS:
            return "RALENTI", "#e3b341"
        return "FLUIDE", "#2ea043"

    def hacker_prochain(tour, contre=""):
        """LE HACKER enchaine la tactique du tour (escalade 1->4, attaques distinctes) et
        RIPOSTE a la derniere contre-mesure de la Sentinelle. Renvoie (niveau=tour, phrase)."""
        nom = dict(NIVEAUX).get(tour, "")
        raison_defaut = DUEL_TACTIQUE.get(tour, "")
        if not duel_ia_active():
            return tour, raison_defaut
        _, _, m_att, _ = _duel_cfg()
        riposte = (" La defense vient de repliquer : '%s'. Contourne-la et frappe plus fort." % contre) if contre else ""
        consigne = (PROMPT_HACKER + " Ta tactique de ce tour : %s. Annonce-la en une phrase.%s\n\n%s"
                    % (nom, riposte, _contexte_flux()))
        texte = _duel_discuter([{"role": "user", "content": consigne}], m_att)  # pas de cache : varie a chaque replay
        return tour, (texte or raison_defaut)

    def _event_sentinelle_reel():
        """Dernier event de DECISION/ACTION du vrai moteur, ou None. Supporte les deux
        formes de journal : enveloppe du simulateur (type/source) et liste brute reelle
        (step/message, doc integration-infra-reelle.md 2.2)."""
        for e in reversed(ETAT.evenements):
            if e.get("step") in ("decision", "action") or e.get("type") in ("decision", "action") \
               or e.get("source") == "sentinelle":
                return e.get("message") or e.get("detail") or ""
        return None

    def sentinelle_prochain(niveau):
        """LA SENTINELLE raconte la decision. Priorite au VRAI event du moteur (zero-touch) ;
        sinon le modele si actif ; repli = recommandation deterministe."""
        reel = _event_sentinelle_reel()
        if reel:
            return reel
        if duel_ia_active():
            _, _, _, m_def = _duel_cfg()
            contexte = "Attaque : %s. %s" % (dict(NIVEAUX).get(niveau, "?"), _contexte_flux())
            texte = _duel_discuter([{"role": "user", "content": PROMPT_DEFENSE + "\n\n" + contexte}], m_def)
            if texte:
                return texte
        return duel_defense_raison()

    def sentinelle_escalade(service):
        """Mode ACTEUR (bonus) : escalade N1 via le relais INFRA, si configure. Jamais
        d'appel direct au moteur ni a Docker ; jeton cote serveur. Sans relais, no-op."""
        url = (ETAT.cfg.get("attaque") or {}).get("escalade_url")
        if not url:
            return False
        http("POST", url, "", dict(service=service, raison="escalade N1 depuis le cockpit"), timeout=4.0)
        return True
