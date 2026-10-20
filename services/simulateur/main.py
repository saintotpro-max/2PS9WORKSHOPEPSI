






import asyncio
import json
import os
import re
import threading
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
import io
import segno
import llm
from pydantic import BaseModel, Field

MODE = "simule"
JETON = "simule-demo"
ASSISTANT_LATENCE_S = float(os.environ.get("ASSISTANT_LATENCE_S", "0.3"))

app = FastAPI(title="Simulateur RESILIENCE-ALPHA", version="0.1.0")
etat: dict = {}


_verrou_participation = threading.Lock()


def reinitialiser() -> None:
    etat.clear()
    etat.update(attaque=None, transactions={}, alertes=[], evenements=[], derniere_ok=True,
                scores=[], dernier_echantillon=None, flux=[], flux_total=0,
                participation=dict(total=0, armee=False, fin=None, duree_s=0))


reinitialiser()


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


def iso(d: datetime) -> str:
    return d.isoformat()


SEUIL = 0.7
ACTIONS_VALIDES = ("restart_service", "block_source", "rate_limit", "scale_up", "none")
DESCRIPTION_NIVEAU = {1: "charge applicative : afflux de requêtes sur /transactions",
                       2: "connexions lentes qui épuisent les ressources du serveur",
                       3: "saturation du réseau par des paquets SYN depuis une seule source",
                       4: "tentatives d'injection SQL sur /transactions",
                       5: "tentatives d'authentification en force sur /auth/token (OWASP A07)",
                       6: "accès à des transactions d'autres comptes par l'identifiant (OWASP A01, IDOR)"}
SOURCE_ATTAQUANT = "192.168.137.20"
# Niveaux qui se BLOQUENT et se VÉRIFIENT sans panne du service (injection + OWASP applicatif).
SANS_PANNE = {4, 5, 6}
KIND = {1: "dos", 2: "dos", 3: "dos", 4: "injection", 5: "auth", 6: "acces"}
SEVERITE = {1: "high", 2: "high", 3: "high", 4: "medium", 5: "high", 6: "high"}
REGLE_WAF = {1: "limite de débit", 2: "connexions lentes", 3: "saturation réseau (SYN)", 4: "injection SQL",
             5: "authentification en force", 6: "contrôle d'accès (IDOR)"}
RECOMMANDATION = {
    1: dict(summary="Pic de requêtes anormal sur payment-api : saturation applicative probable",
            suggested_action="rate_limit", confidence=0.91, rationale="score 0.97 ; erreurs 5xx en hausse"),
    2: dict(summary="Connexions lentes qui épuisent les ressources de payment-api",
            suggested_action="restart_service", confidence=0.84, rationale="nombre de connexions ouvertes anormal"),
    3: dict(summary="Saturation du réseau vers payment-api",
            suggested_action="block_source", confidence=0.88, rationale="flux SYN massif depuis une seule source"),
    4: dict(summary="Tentatives d'injection sur /transactions bloquées par le WAF",
            suggested_action="block_source", confidence=0.95, rationale="motifs d'injection SQL répétés"),
    5: dict(summary="Authentification en force sur /auth/token bloquée (identifiants invalides répétés)",
            suggested_action="block_source", confidence=0.93, rationale="nombreux échecs de connexion depuis une seule source"),
    6: dict(summary="Accès refusé à des transactions d'autres comptes : contrôle d'accès appliqué",
            suggested_action="block_source", confidence=0.94, rationale="identifiants de transaction non autorisés tentés en série"),
}


def reco_modele(niveau: int) -> None:

    try:
        texte = llm.discuter([
            {"role": "system", "content": "Tu es le détecteur d'anomalies d'une plateforme de paiement fictive. "
             "Réponds UNIQUEMENT par un objet JSON avec les clés summary (une phrase en français, 20 mots au plus), "
             "suggested_action (une valeur parmi restart_service, block_source, rate_limit, scale_up, none), "
             "confidence (nombre entre 0 et 1) et rationale (une phrase courte). N'invente aucun chiffre."},
            {"role": "user", "content": "Incident sur payment-api : %s." % DESCRIPTION_NIVEAU[niveau]}], max_tokens=300)
        brut = json.loads(re.search(r"\{.*\}", texte, re.S).group(0))
        if brut["suggested_action"] in ACTIONS_VALIDES:
            etat.setdefault("reco_modele", {})[niveau] = dict(
                summary=str(brut["summary"])[:200], suggested_action=brut["suggested_action"],
                confidence=max(0.0, min(1.0, float(brut["confidence"]))), rationale=str(brut.get("rationale", ""))[:200])
    except Exception:
        pass


def phase(instant: float | None = None) -> str:

    a = etat["attaque"]
    if a is None:
        return "sain"
    maintenant_t = time.time() if instant is None else instant
    t = maintenant_t - a["t0"]
    if t < 0 or a["niveau"] in SANS_PANNE:
        return "sain"
    arret = a.get("arret_t")
    if arret is not None and maintenant_t >= arret:
        return "reprise" if maintenant_t - arret < 1.5 else "sain"
    if t < a["detection_s"]:
        return "attaque"
    if t < a["detection_s"] + a["reprise_s"]:
        return "reprise"
    return "sain"


def echantillonner() -> None:

    maintenant_s = int(time.time())
    if etat["dernier_echantillon"] is None:
        etat["dernier_echantillon"] = maintenant_s - 1
    a = etat["attaque"]
    for t in range(max(etat["dernier_echantillon"] + 1, maintenant_s - 60), maintenant_s + 1):
        p = phase(float(t))
        graine = random.Random(t)
        bruit = graine.random()
        base = {"sain": 0.12 + bruit * 0.10, "attaque": 0.78 + bruit * 0.20, "reprise": 0.55 + bruit * 0.20}[p]
        bloc_en_cours = bool(a) and a["niveau"] in SANS_PANNE and a["t0"] <= t and (a.get("arret_t") is None or t < a["arret_t"])
        if bloc_en_cours:
            base = 0.74 + bruit * 0.15
        etat["scores"].append(dict(at=iso(datetime.fromtimestamp(t, timezone.utc)), score=round(base, 3),
                                   threshold=SEUIL, label="attaque" if (p != "sain" or bloc_en_cours) else "normal"))
        en_cours = bool(a) and a["t0"] <= t and (a.get("arret_t") is None or t < a["arret_t"]) and (
            a["niveau"] in SANS_PANNE or t - a["t0"] < a["detection_s"] + a["reprise_s"])
        if en_cours:
            n = a["niveau"]
            nombre = {1: 5 + int(graine.random() * 10), 2: 1 + int(graine.random() * 3),
                      3: 15 + int(graine.random() * 26), 4: 3 + int(graine.random() * 7),
                      5: 4 + int(graine.random() * 8), 6: 2 + int(graine.random() * 5)}[n]
            etat["flux"].append(dict(at=iso(datetime.fromtimestamp(t, timezone.utc)), source_ip=SOURCE_ATTAQUANT,
                                     rule=REGLE_WAF[n], count=nombre, target="payment-api"))
            etat["flux_total"] += nombre
    etat["dernier_echantillon"] = maintenant_s
    del etat["scores"][:-300]
    del etat["flux"][:-200]


def evenement(at: str, type_: str, composant: str, detail: str, source: str) -> dict:
    return dict(at=at, type=type_, component=composant, detail=detail, source=source)


def avancer() -> None:

    echantillonner()
    a = etat["attaque"]
    if a is None:
        return
    debut = datetime.fromtimestamp(a["t0"], timezone.utc)
    detection = debut + timedelta(seconds=a["detection_s"])
    fin = detection + timedelta(seconds=a["reprise_s"])
    maintenant_t = time.time()
    ecoule = maintenant_t - a["t0"]
    arret_t = a.get("arret_t")
    arrete_avant_detection = arret_t is not None and arret_t - a["t0"] < a["detection_s"]
    injection = a["niveau"] in SANS_PANNE
    if not injection and "degrade" not in a["faits"]:
        a["faits"].add("degrade")
        etat["evenements"].append(evenement(iso(debut), "service_degraded", "payment-api",
                                            "Attaque de niveau %d" % a["niveau"], "moteur"))
    if not arrete_avant_detection and ecoule >= a["detection_s"] and "alerte" not in a["faits"]:
        a["faits"].add("alerte")
        etat["alertes"].append(dict(id=str(uuid.uuid4()), detected_at=iso(detection), source="simulateur",
                                    kind=KIND[a["niveau"]], severity=SEVERITE[a["niveau"]], score=0.97,
                                    target="payment-api", detail="Trafic anormal détecté",
                                    recommendation=etat.get("reco_modele", {}).get(a["niveau"], RECOMMANDATION[a["niveau"]])))
        etat["evenements"].append(evenement(iso(detection), "alert_received", "remediation",
                                            "Alerte reçue", "detection"))
        etat["evenements"].append(evenement(iso(detection), "action_started", "remediation",
                                            "Règle de blocage appliquée" if injection else "Redémarrage de payment-api", "moteur"))
    if not arrete_avant_detection and ecoule >= a["detection_s"] + a["reprise_s"] and "reprise" not in a["faits"]:
        a["faits"].add("reprise")
        etat["evenements"].append(evenement(iso(fin), "action_done", "remediation", "Action terminée", "moteur"))
        if not injection:
            etat["evenements"].append(evenement(iso(fin), "service_recovered", "payment-api", "Service rétabli", "moteur"))
        etat["derniere_ok"] = True
    if arret_t is not None and maintenant_t >= arret_t + 1.5 and "arret" not in a["faits"]:
        a["faits"].add("arret")
        if not injection and "reprise" not in a["faits"]:
            etat["evenements"].append(evenement(iso(datetime.fromtimestamp(arret_t + 1.5, timezone.utc)), "service_recovered",
                                                "payment-api", "Fin d'attaque : l'attaquant s'est arrêté", "moteur"))
        etat["derniere_ok"] = True


@app.middleware("http")
async def marquer_mode(request: Request, call_next):
    avancer()
    reponse = await call_next(request)
    reponse.headers["X-Mode"] = MODE
    return reponse


def erreur(code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content=dict(detail=detail, mode=MODE))


class Identifiants(BaseModel):
    username: str
    password: str


class TransactionEntree(BaseModel):
    amount_cents: int = Field(ge=1)
    currency: str
    payer: str
    payee: str
    idempotency_key: str | None = None


class AlerteEntree(BaseModel):
    source: str
    kind: str
    severity: str
    score: float | None = None
    target: str
    detail: str | None = None


class Question(BaseModel):
    question: str


class Attaque(BaseModel):
    niveau: int = Field(default=1, ge=1, le=6)
    detection_s: float = Field(default=float(os.environ.get("DELAI_DETECTION_S", "5.0")), ge=0)
    reprise_s: float = Field(default=float(os.environ.get("DELAI_REPRISE_S", "8.0")), ge=0)


@app.post("/auth/token")
def jeton(corps: Identifiants):
    if (corps.username, corps.password) != ("demo", "demo"):
        return erreur(401, "Identifiants refusés")
    return dict(access_token=JETON, token_type="bearer", mode=MODE)


@app.get("/health")
def sante():
    p = phase()
    statut = {"sain": "ok", "attaque": "degraded", "reprise": "down"}[p]
    return dict(status=statut, last_transaction_ok=etat["derniere_ok"], checked_at=iso(maintenant()), mode=MODE)


def verifier_jeton(authorization: str | None) -> JSONResponse | None:
    if authorization != "Bearer " + JETON:
        return erreur(401, "Jeton absent ou invalide")
    return None


@app.post("/transactions", status_code=201)
def creer_transaction(corps: TransactionEntree, authorization: str | None = Header(default=None)):
    refus = verifier_jeton(authorization)
    if refus:
        return refus
    if phase() != "sain":
        etat["derniere_ok"] = False
        return erreur(503, "Service indisponible (simulation)")
    tx = dict(id=str(uuid.uuid4()), amount_cents=corps.amount_cents, currency=corps.currency,
              payer=corps.payer, payee=corps.payee, status="accepted", created_at=iso(maintenant()), mode=MODE)
    etat["transactions"][tx["id"]] = tx
    etat["derniere_ok"] = True
    return tx


@app.get("/transactions/{identifiant}")
def lire_transaction(identifiant: str, authorization: str | None = Header(default=None)):
    refus = verifier_jeton(authorization)
    if refus:
        return refus
    if identifiant not in etat["transactions"]:
        return erreur(404, "Transaction inconnue")
    return etat["transactions"][identifiant]


@app.post("/alerts", status_code=202)
def recevoir_alerte(corps: AlerteEntree):
    alerte = dict(corps.model_dump(), id=str(uuid.uuid4()), detected_at=iso(maintenant()))
    etat["alertes"].append(alerte)
    etat["evenements"].append(evenement(alerte["detected_at"], "alert_received", "remediation",
                                        "Alerte reçue de %s" % corps.source, "detection"))
    return dict(id=alerte["id"], mode=MODE)


@app.get("/alerts")
def lister_alertes():
    return dict(alerts=etat["alertes"], mode=MODE)


@app.get("/events")
def lister_evenements():
    return dict(events=etat["evenements"], mode=MODE)


class EvenementEntree(BaseModel):
    type: str
    component: str
    detail: str
    source: str


@app.post("/events", status_code=202)
def declarer_evenement(corps: EvenementEntree):

    if corps.type not in ("attack_started", "attack_ended") or corps.source != "attaquant":
        return erreur(422, "Seuls attack_started et attack_ended déclarés par la source attaquant sont acceptés")
    ev = evenement(iso(maintenant()), corps.type, corps.component, corps.detail, corps.source)
    etat["evenements"].append(ev)
    return dict(id=str(uuid.uuid4()), mode=MODE)


@app.get("/scores")
def lister_scores(since: str | None = None):
    scores = [x for x in etat["scores"] if since is None or x["at"] > since]
    return dict(scores=scores, mode=MODE)


@app.get("/components")
def composants():
    p = phase()
    api = {"sain": "ok", "attaque": "degraded", "reprise": "down"}[p]
    return dict(components=[
        dict(name="payment-api", status=api, detail=""),
        dict(name="database", status="ok", detail=""),
        dict(name="remediation", status="ok", detail=""),
    ], mode=MODE)


@app.post("/assistant/ask")
async def demander(corps: Question):
    debut = time.time()
    if llm.actif():
        try:
            a = etat["attaque"]
            contexte = ("Aucune attaque en cours." if a is None else "Attaque en cours : %s. Phase du service : %s. Dernières actions du moteur : %s." % (
                DESCRIPTION_NIVEAU[a["niveau"]], phase(), "; ".join(e["detail"] for e in etat["evenements"][-3:] if e["source"] == "moteur") or "aucune"))
            texte = await asyncio.to_thread(llm.discuter, [
                {"role": "system", "content": "Tu es l'assistant du poste SOC d'une plateforme de paiement fictive. Réponds en français, "
                 "deux phrases au plus, sans inventer de chiffre. La reprise est automatique : le moteur de remédiation agit seul et "
                 "aucun humain ne répare. " + contexte},
                {"role": "user", "content": corps.question}], 200)
            return dict(answer=texte, sources=[dict(document="runbook-incident", passage="Reprise automatique, aucune intervention humaine.")],
                        latency_ms=int((time.time() - debut) * 1000), mode=MODE)
        except Exception:
            pass
    await asyncio.sleep(ASSISTANT_LATENCE_S)
    return dict(
        answer="Une attaque par déni de service est en cours ; le moteur de remédiation redémarre "
               "l'API. Ne rien faire : la reprise est automatique.",
        sources=[dict(document="runbook-incident", passage="Reprise automatique, aucune intervention humaine.")],
        latency_ms=int((time.time() - debut) * 1000), mode=MODE)


@app.post("/simulation/attaque")
def lancer_attaque(corps: Attaque = Attaque()):
    if llm.actif():
        threading.Thread(target=reco_modele, args=(corps.niveau,), daemon=True).start()
    etat["attaque"] = dict(t0=time.time(), niveau=corps.niveau, detection_s=corps.detection_s,
                           reprise_s=corps.reprise_s, faits=set())
    avancer()
    return dict(detail="Attaque simulée lancée", niveau=corps.niveau, mode=MODE)


@app.post("/simulation/arret")
def arreter_attaque():

    a = etat["attaque"]
    if a is None or a.get("arret_t") is not None:
        return dict(detail="Aucune attaque en cours", mode=MODE)
    a["arret_t"] = time.time()
    avancer()
    return dict(detail="Attaque arrêtée", mode=MODE)


@app.get("/flux-bloques")
def flux_bloques():
    return dict(blocked=etat["flux"][-30:], total=etat["flux_total"], mode=MODE)


@app.get("/verifications")
def verifications():

    p = phase()
    if p == "sain" and etat["derniere_ok"]:
        statuts = ("ok", "ok", "ok")
    elif p == "attaque":
        statuts = ("ko", "ko", "en_cours")
    else:
        statuts = ("en_cours", "ko", "en_cours")
    noms = ("api_accessible", "transaction_test", "donnees_coherentes")
    details = {"ok": "mesuré", "ko": "échec constaté", "en_cours": "contrôle en cours"}
    return dict(verifications=[dict(name=n, status=st, detail=details[st]) for n, st in zip(noms, statuts)], mode=MODE)


@app.post("/simulation/reset")
def remettre_a_zero():
    reinitialiser()
    return dict(detail="État remis à zéro", mode=MODE)


@app.get("/simulation/export.csv")
def exporter(graine: int = 42, duree: int = 300):

    g = random.Random(graine)
    debut = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fenetres = [(int(duree * 0.30), int(duree * 0.45)), (int(duree * 0.70), int(duree * 0.82))]
    lignes = ["at,requetes_par_s,taux_erreur,latence_ms,etiquette,source"]
    for sec in range(duree):
        attaque = any(a <= sec < b for a, b in fenetres)
        if attaque:
            rps, err, lat = 180 + g.random() * 120, 0.15 + g.random() * 0.25, 400 + g.random() * 500
        else:
            rps, err, lat = 18 + g.random() * 8, 0.005 + g.random() * 0.01, 70 + g.random() * 30
        lignes.append("%s,%.1f,%.4f,%.0f,%s,synthetique" % (
            iso(debut + timedelta(seconds=sec)), rps, err, lat, "attaque" if attaque else "normal"))
    return PlainTextResponse("\n".join(lignes) + "\n", media_type="text/csv")





class ArmerVague(BaseModel):
    duree_s: int = Field(default=30, ge=5, le=600)


def etat_participation() -> dict:
    p = etat["participation"]
    if p["armee"] and p["fin"] is not None:
        restant = max(0.0, p["fin"] - time.time())
        phase = "ouvert" if restant > 0 else "termine"
    else:
        restant, phase = 0.0, "repos"
    return dict(total=p["total"], phase=phase, decompte=round(restant, 1), duree_s=p["duree_s"], mode=MODE)


@app.get("/participation/etat")
def participation_etat():
    return etat_participation()


@app.post("/participation/rejoindre")
def participation_rejoindre():
    with _verrou_participation:
        etat["participation"]["total"] += 1
    return dict(total=etat["participation"]["total"], phase=etat_participation()["phase"], mode=MODE)


@app.post("/participation/armer")
def participation_armer(corps: ArmerVague = ArmerVague()):
    p = etat["participation"]
    p["armee"], p["duree_s"], p["fin"] = True, corps.duree_s, time.time() + corps.duree_s
    return dict(detail="Vague armee", duree_s=corps.duree_s, mode=MODE)


@app.post("/participation/reset")
def participation_reset():
    etat["participation"] = dict(total=0, armee=False, fin=None, duree_s=0)
    return dict(detail="Participation remise a zero", mode=MODE)


@app.get("/participation/qr.png")
def participation_qr(cible: str | None = None):

    url = cible or os.environ.get("ALPHA_VAGUE_URL") or "http://127.0.0.1:8765/participation"
    tampon = io.BytesIO()
    segno.make(url, error="m").save(tampon, kind="png", scale=8, border=2, dark="#0d1117", light="#36f1cd")
    return Response(tampon.getvalue(), media_type="image/png")


@app.get("/participation", response_class=HTMLResponse)
def participation_page():
    return PARTICIPATION_HTML


PARTICIPATION_HTML = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rejoindre la vague</title>
<style>
  :root { --noir:#0d1117; --neon:#36f1cd; --accent:#ff5d73; --txt:#e6edf3; }
  * { box-sizing:border-box; } body { margin:0; background:var(--noir); color:var(--txt);
    font:17px/1.5 ui-monospace,Menlo,Consolas,monospace; display:grid; place-items:center;
    min-height:100vh; padding:20px; text-align:center; }
  .carte { width:min(440px,100%); }
  h1 { font-size:1.5rem; color:var(--neon); letter-spacing:.03em; margin:0 0 6px; }
  .total { font-size:4rem; font-weight:700; color:var(--neon); margin:10px 0 0; line-height:1; }
  .lbl { font-size:.8rem; color:#8b97b5; letter-spacing:.14em; text-transform:uppercase; }
  .decompte { font-size:1.1rem; color:var(--accent); margin-top:14px; min-height:1.4em; }
  button { width:100%; margin-top:26px; padding:18px; background:var(--neon); color:#031312; border:0;
    border-radius:12px; font:inherit; font-size:1.15rem; font-weight:700; letter-spacing:.05em;
    cursor:pointer; transition:filter .15s, transform .05s; }
  button:hover { filter:brightness(1.12); } button:active { transform:scale(.98); }
  button:disabled { filter:grayscale(.7) brightness(.7); cursor:default; }
  .note { margin-top:22px; font-size:.78rem; color:#6b7799; line-height:1.5; }
</style></head><body>
<div class="carte">
  <h1>Rejoindre la vague</h1>
  <div class="lbl">participants</div>
  <div class="total" id="total">0</div>
  <div class="decompte" id="decompte"></div>
  <button id="btn">Je rejoins la vague</button>
  <p class="note">Votre telephone ne fait que signaler votre presence : il n'envoie aucune
  attaque. La charge est generee par notre machine, dans notre systeme fictif de laboratoire.</p>
</div>
<script>
const total = document.getElementById('total'), dec = document.getElementById('decompte'), btn = document.getElementById('btn');
async function etat() {
  try {
    const r = await fetch('/participation/etat'); const j = await r.json();
    total.textContent = j.total;
    if (j.phase === 'ouvert') dec.textContent = 'depart dans ' + Math.ceil(j.decompte) + ' s';
    else if (j.phase === 'termine') dec.textContent = 'la vague est partie';
    else dec.textContent = 'en attente du depart';
  } catch (e) { dec.textContent = 'hors ligne'; }
}
btn.addEventListener('click', async () => {
  btn.disabled = true; btn.textContent = 'Vous avez rejoint';
  try { const r = await fetch('/participation/rejoindre', {method:'POST'}); const j = await r.json(); total.textContent = j.total; }
  catch (e) { btn.disabled = false; btn.textContent = 'Reessayer'; }
});
etat(); setInterval(etat, 1000);
</script></body></html>"""
