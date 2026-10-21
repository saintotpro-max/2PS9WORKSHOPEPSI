










import json
import os
import secrets
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

MODE = "reel"
DB = os.environ.get("ALPHA_DB", os.path.join(os.path.dirname(__file__), "paiement.db"))



METRIQUES = dict(tx_ok=0, tx_refus=0, auth_ok=0, auth_refus=0, requetes=0)


def journal(evenement: str, **champs) -> None:

    ligne = dict(ts=iso(maintenant()), service="paiement", mode=MODE, event=evenement, **champs)
    print(json.dumps(ligne, ensure_ascii=False), file=sys.stdout, flush=True)



def charger_utilisateurs() -> dict:
    brut = os.environ.get("ALPHA_USERS", "demo:demo,caissier:caisse,soc:soc")
    users = {}
    for paire in brut.split(","):
        if ":" in paire:
            u, p = paire.split(":", 1)
            users[u.strip()] = p.strip()
    return users


UTILISATEURS = charger_utilisateurs()
JETONS: dict[str, str] = {}

app = FastAPI(title="Plateforme de paiement RESILIENCE-ALPHA", version="0.1.0")


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


def iso(d: datetime) -> str:
    return d.isoformat()


def connexion() -> sqlite3.Connection:
    cx = sqlite3.connect(DB, timeout=5)
    cx.row_factory = sqlite3.Row
    return cx


def init_base() -> None:
    with connexion() as cx:
        cx.execute(
            "CREATE TABLE IF NOT EXISTS transactions ("
            "id TEXT PRIMARY KEY, amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, "
            "payer TEXT NOT NULL, payee TEXT NOT NULL, status TEXT NOT NULL, "
            "created_at TEXT NOT NULL, idempotency_key TEXT UNIQUE)"
        )


init_base()


def erreur(code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=code, content=dict(detail=detail, mode=MODE))


def utilisateur_du_jeton(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return JETONS.get(authorization[len("Bearer "):])


class Identifiants(BaseModel):
    username: str
    password: str


class TransactionEntree(BaseModel):
    amount_cents: int = Field(ge=1)
    currency: str = Field(pattern="^EUR$")
    payer: str
    payee: str
    idempotency_key: str | None = None


@app.post("/auth/token")
def auth_token(corps: Identifiants):
    attendu = UTILISATEURS.get(corps.username)
    if attendu is None or not secrets.compare_digest(attendu, corps.password):
        METRIQUES["auth_refus"] += 1
        journal("auth_refus", username=corps.username)
        return erreur(401, "Identifiants refuses")
    jeton = secrets.token_urlsafe(24)
    JETONS[jeton] = corps.username
    METRIQUES["auth_ok"] += 1
    journal("auth_ok", username=corps.username)
    return dict(access_token=jeton, token_type="bearer", mode=MODE)


@app.get("/health")
def health():

    ok = False
    try:
        with connexion() as cx:
            cx.execute("CREATE TABLE IF NOT EXISTS sonde (k TEXT PRIMARY KEY, v TEXT)")
            jeton = str(uuid.uuid4())
            cx.execute("INSERT OR REPLACE INTO sonde (k, v) VALUES ('probe', ?)", (jeton,))
            relu = cx.execute("SELECT v FROM sonde WHERE k='probe'").fetchone()
            ok = relu is not None and relu["v"] == jeton
    except Exception:
        ok = False
    status = "ok" if ok else "down"
    return dict(status=status, last_transaction_ok=ok, checked_at=iso(maintenant()), mode=MODE)


@app.post("/transactions", status_code=201)
def creer_transaction(corps: TransactionEntree, authorization: str | None = Header(default=None)):
    if utilisateur_du_jeton(authorization) is None:
        return erreur(401, "Jeton absent ou invalide")
    try:
        with connexion() as cx:
            if corps.idempotency_key:
                deja = cx.execute(
                    "SELECT * FROM transactions WHERE idempotency_key=?", (corps.idempotency_key,)
                ).fetchone()
                if deja is not None:
                    return ligne_en_transaction(deja)
            tx = dict(
                id=str(uuid.uuid4()), amount_cents=corps.amount_cents, currency=corps.currency,
                payer=corps.payer, payee=corps.payee, status="accepted", created_at=iso(maintenant()),
            )
            cx.execute(
                "INSERT INTO transactions (id, amount_cents, currency, payer, payee, status, created_at, idempotency_key) "
                "VALUES (:id, :amount_cents, :currency, :payer, :payee, :status, :created_at, :k)",
                dict(tx, k=corps.idempotency_key),
            )
    except sqlite3.Error as e:
        METRIQUES["tx_refus"] += 1
        journal("tx_refus", raison=str(e))
        return erreur(503, "Service indisponible ou degrade")
    METRIQUES["tx_ok"] += 1
    journal("tx_ok", id=tx["id"], amount_cents=tx["amount_cents"], payee=tx["payee"])
    return dict(tx, mode=MODE)


def ligne_en_transaction(row: sqlite3.Row) -> dict:
    return dict(
        id=row["id"], amount_cents=row["amount_cents"], currency=row["currency"],
        payer=row["payer"], payee=row["payee"], status=row["status"],
        created_at=row["created_at"], mode=MODE,
    )


@app.get("/transactions/{identifiant}")
def lire_transaction(identifiant: str, authorization: str | None = Header(default=None)):
    if utilisateur_du_jeton(authorization) is None:
        return erreur(401, "Jeton absent ou invalide")
    with connexion() as cx:
        row = cx.execute("SELECT * FROM transactions WHERE id=?", (identifiant,)).fetchone()
    if row is None:
        return erreur(404, "Transaction inconnue")
    return ligne_en_transaction(row)


@app.middleware("http")
async def compter_requetes(request: Request, call_next):
    METRIQUES["requetes"] += 1
    return await call_next(request)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():

    lignes = [
        "# HELP alpha_transactions_total Transactions par issue",
        "# TYPE alpha_transactions_total counter",
        'alpha_transactions_total{issue="ok"} %d' % METRIQUES["tx_ok"],
        'alpha_transactions_total{issue="refus"} %d' % METRIQUES["tx_refus"],
        "# HELP alpha_auth_total Authentifications par issue",
        "# TYPE alpha_auth_total counter",
        'alpha_auth_total{issue="ok"} %d' % METRIQUES["auth_ok"],
        'alpha_auth_total{issue="refus"} %d' % METRIQUES["auth_refus"],
        "# HELP alpha_requests_total Requetes HTTP recues",
        "# TYPE alpha_requests_total counter",
        "alpha_requests_total %d" % METRIQUES["requetes"],
    ]
    return "\n".join(lignes) + "\n"


@app.get("/", response_class=HTMLResponse)
def frontal():
    return FRONTAL_HTML


FRONTAL_HTML = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Caisse RESILIENCE-ALPHA</title>
<style>
  :root { --noir:#0b0e17; --neon:#36f1cd; --accent:#ff5d73; --txt:#e6edf3; }
  * { box-sizing:border-box; } body { margin:0; background:var(--noir); color:var(--txt);
    font:16px/1.5 ui-monospace,Menlo,Consolas,monospace; display:grid; place-items:center; min-height:100vh; padding:16px; }
  .carte { width:min(420px,100%); background:#121725; border:1px solid #1e2740; border-radius:14px;
    padding:28px; box-shadow:0 20px 60px rgba(0,0,0,.5); }
  h1 { margin:0 0 4px; font-size:1.3rem; color:var(--neon); letter-spacing:.04em; }
  .mode { font-size:.75rem; color:var(--accent); text-transform:uppercase; letter-spacing:.2em; margin-bottom:20px; }
  label { display:block; font-size:.75rem; color:#8b97b5; margin:14px 0 4px; letter-spacing:.08em; }
  input { width:100%; padding:10px 12px; background:#0b0e17; border:1px solid #273153; border-radius:8px;
    color:var(--txt); font:inherit; } input:focus { outline:none; border-color:var(--neon); }
  button { width:100%; margin-top:22px; padding:12px; background:var(--neon); color:#031312; border:0;
    border-radius:8px; font:inherit; font-weight:700; letter-spacing:.06em; cursor:pointer; transition:filter .15s; }
  button:hover { filter:brightness(1.12); } button:active { filter:brightness(.9); }
  #out { margin-top:18px; font-size:.85rem; white-space:pre-wrap; word-break:break-all; min-height:3em; }
  .ok { color:var(--neon); } .ko { color:var(--accent); }
</style></head><body>
<form class="carte" id="f">
  <h1>Caisse RESILIENCE-ALPHA</h1>
  <div class="mode" id="badge">mode reel</div>
  <label>Caissier</label><input id="u" value="caissier" autocomplete="off">
  <label>Mot de passe</label><input id="p" type="password" value="caisse" autocomplete="off">
  <label>Montant (centimes)</label><input id="a" value="1999" inputmode="numeric">
  <label>Beneficiaire</label><input id="payee" value="boulangerie-fictive">
  <button type="submit">Payer</button>
  <div id="out"></div>
</form>
<script>
const out = document.getElementById('out');
document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault(); out.textContent = 'Envoi...'; out.className = '';
  try {
    const tok = await fetch('/auth/token', {method:'POST', headers:{'content-type':'application/json'},
      body: JSON.stringify({username:document.getElementById('u').value, password:document.getElementById('p').value})});
    const tj = await tok.json();
    if (!tok.ok) { out.textContent = 'Auth refusee : ' + tj.detail; out.className='ko'; return; }
    const r = await fetch('/transactions', {method:'POST', headers:{'content-type':'application/json',
      'authorization':'Bearer ' + tj.access_token},
      body: JSON.stringify({amount_cents: Number(document.getElementById('a').value), currency:'EUR',
        payer: document.getElementById('u').value, payee: document.getElementById('payee').value})});
    const j = await r.json();
    if (r.ok) { out.textContent = 'Transaction ' + j.status + '\\nid ' + j.id; out.className='ok'; }
    else { out.textContent = 'Refus (' + r.status + ') : ' + j.detail; out.className='ko'; }
  } catch (err) { out.textContent = 'Plateforme injoignable : ' + err; out.className='ko'; }
});
</script></body></html>"""
