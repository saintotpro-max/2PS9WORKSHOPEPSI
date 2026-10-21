"""Moteur de remédiation RESILIENCE-ALPHA.

Chaîne : alerte (Alertmanager) -> décision (règles YAML) -> action (Docker via
socket-proxy-ctrl) -> vérification (Prometheus) -> résolution ou escalade.

Endpoints
  POST /alerts   webhook Alertmanager v4 (jeton Bearer obligatoire)
  GET  /events   chronologie des incidents (pour le dashboard)
  GET  /status   incidents en cours et derniers résultats
  GET  /health   santé
  GET  /metrics  métriques Prometheus

Garde-fous : seules les cibles de `restartable` peuvent être redémarrées, une même
cible n'est pas relancée avant `cooldown` secondes, au plus `max_attempts` actions
par incident, et aucune autre opération Docker n'est possible (le proxy les refuse).
"""
import asyncio
import re
from datetime import datetime
import hmac
import itertools
import json
import os
import time
from collections import deque

import httpx
import yaml
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

RULES_FILE = os.environ.get("RULES_FILE", "/config/rules.yml")
DOCKER_HOST = os.environ.get("DOCKER_HOST", "tcp://socket-proxy-ctrl:2375").replace("tcp://", "http://")
# Version d'API explicite : le proxy n'autorise que les chemins /v1.xx/...
DOCKER_API = DOCKER_HOST + "/v1.44"
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")
COMPOSE_PROJECT = os.environ.get("COMPOSE_PROJECT", "platform")
TOKEN = os.environ.get("REMEDIATION_TOKEN", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
STATE_FILE = os.environ.get("STATE_FILE", "/data/state.json")

CONFIG = yaml.safe_load(open(RULES_FILE, encoding="utf-8"))
S = CONFIG["settings"]
RESTARTABLE = set(CONFIG["restartable"])

M_INCIDENTS = Counter("remediation_incidents_total", "Incidents traités", ["alert", "outcome"])
M_ACTIONS = Counter("remediation_actions_total", "Actions exécutées", ["action", "target", "result"])
M_RECOVERY = Histogram("remediation_recovery_seconds", "Durée entre détection et reprise vérifiée",
                       buckets=(5, 10, 20, 30, 45, 60, 90, 120, 180, 300))
M_ACTIVE = Gauge("remediation_incidents_active", "Incidents en cours")

app = FastAPI(title="remediation", docs_url=None, redoc_url=None)
events = deque(maxlen=500)
incidents = {}          # clé -> incident
last_action = {}        # cible -> horodatage de la dernière action
ids = itertools.count(1)


def save_state():
    """Conserve chronologie et incidents (le dashboard les affiche après un redémarrage)."""
    try:
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"events": list(events), "incidents": incidents}, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
    except OSError as e:
        log("warning", "état non sauvegardé", error=str(e))


def load_state():
    global ids
    try:
        data = json.load(open(STATE_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        return
    events.extend(data.get("events", []))
    for key, inc in data.get("incidents", {}).items():
        if inc["status"] == "in_progress":          # interrompu par le redémarrage
            inc["status"] = "failed"
        incidents[key] = inc
    ids = itertools.count(max((i["id"] for i in incidents.values()), default=0) + 1)


def log(level, message, **kw):
    print(json.dumps({"timestamp": time.time(), "level": level, "service": "remediation",
                      "message": message, **kw}, ensure_ascii=False), flush=True)


def emit(incident, step, message, **kw):
    """Enregistre une étape d'incident : chronologie du dashboard + journal (SIEM)."""
    ev = {"ts": time.time(), "incident": incident["id"], "alert": incident["alert"],
          "step": step, "message": message, **kw}
    events.append(ev)
    incident["steps"].append(ev)
    log("info" if step != "escalation" else "warning", message, incident=incident["id"],
        alert=incident["alert"], step=step, **kw)
    save_state()


def find_rule(alert):
    name, labels = alert["labels"].get("alertname"), alert["labels"]
    for rule in CONFIG["rules"]:
        if rule["alert"] == name and all(labels.get(k) == v for k, v in rule.get("match", {}).items()):
            return rule
    return None


def parse_ts(value):
    """Horodatage RFC 3339 d'Alertmanager (nanosecondes tronquées) -> epoch, ou None."""
    try:
        v = re.sub(r"(\.\d{6})\d+", r"", value).replace("Z", "+00:00")
        ts = datetime.fromisoformat(v).timestamp()
        return ts if ts > 0 else None
    except (TypeError, ValueError):
        return None


def resolve_target(action, labels):
    return labels.get(action["target_label"]) if "target_label" in action else action.get("target")


# --- Docker (via socket-proxy-ctrl) ------------------------------------------
async def find_container(client, service):
    flt = json.dumps({"label": [f"com.docker.compose.service={service}",
                                f"com.docker.compose.project={COMPOSE_PROJECT}"]})
    r = await client.get(f"{DOCKER_API}/containers/json", params={"all": "1", "filters": flt})
    r.raise_for_status()
    found = r.json()
    return found[0] if found else None


async def restart(client, service):
    c = await find_container(client, service)
    if c is None:
        return False, "conteneur introuvable"
    if DRY_RUN:
        return True, f"simulation : redémarrage de {c['Names'][0].lstrip('/')} non exécuté"
    r = await client.post(f"{DOCKER_API}/containers/{c['Id']}/restart", params={"t": "5"})
    if r.status_code == 204:
        return True, f"{c['Names'][0].lstrip('/')} redémarré (était : {c['State']})"
    return False, f"refusé par le proxy Docker (HTTP {r.status_code})"


# --- Vérification (Prometheus) ---------------------------------------------
async def query(client, expr):
    r = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": expr})
    r.raise_for_status()
    return r.json()["data"]["result"]


async def service_ok(client):
    """Vrai si le service métier est utilisable. Retourne (ok, critère utilisé)."""
    for expr in (S["verify_query"], S["verify_fallback_query"]):
        res = await query(client, expr)
        if res:
            return all(float(x["value"][1]) == 1 for x in res), expr
    return False, "aucune mesure disponible"


async def failure_start(client, labels):
    """Première évaluation en échec de l'alerte (ALERTS_FOR_STATE), ou None.

    Le startsAt du webhook correspond au déclenchement, après la durée « for » :
    il sous-estimerait la coupure réelle.
    """
    sel = ",".join(f'{k}="{labels[k]}"' for k in ("alertname", "instance", "service", "job") if k in labels)
    try:
        res = await query(client, f"ALERTS_FOR_STATE{{{sel}}}")
    except httpx.HTTPError:
        return None
    return min(float(x["value"][1]) for x in res) if res else None


async def named_checks(client):
    """Vérifications nommées : un redémarrage ne prouve pas la reprise, ces preuves si.

    Chaque entrée de settings.verify_checks est une requête qui doit valoir 1. On
    ré-interroge brièvement les preuves encore KO : une sonde relevée toutes les 5 s
    peut accuser du retard alors que le service est déjà rétabli.
    """
    async def one(expr):
        try:
            res = await query(client, expr)
            return bool(res) and all(float(x["value"][1]) == 1 for x in res)
        except httpx.HTTPError:
            return False
    checks = {name: False for name in S.get("verify_checks", {})}
    for _ in range(S.get("verify_checks_retries", 4)):
        for name, expr in S.get("verify_checks", {}).items():
            if not checks[name]:
                checks[name] = await one(expr)
        if all(checks.values()):
            break
        await asyncio.sleep(S.get("verify_checks_interval", 3))
    return [{"name": n, "ok": ok} for n, ok in checks.items()]


async def verify(client, incident):
    deadline = time.time() + S["verify_timeout"]
    while time.time() < deadline:
        await asyncio.sleep(S["verify_interval"])
        ok, expr = await service_ok(client)
        if ok:
            return True, expr, await named_checks(client)
    return False, expr, await named_checks(client)


# --- Traitement d'un incident ----------------------------------------------
async def handle(incident, rule, labels):
    async with httpx.AsyncClient(timeout=10) as client:
        M_ACTIVE.inc()
        try:
            first = await failure_start(client, labels)
            if first:
                incident["failure_start"] = min(first, incident["failure_start"])
            actions = rule.get("actions", [])
            if all(a["type"] == "record" for a in actions):
                emit(incident, "decision", rule.get("description", "observation, aucune action requise"))
                incident["status"] = "observed"
                M_INCIDENTS.labels(alert=incident["alert"], outcome="observed").inc()
                return
            for attempt, action in enumerate(actions[: S["max_attempts"]], 1):
                target = resolve_target(action, labels)
                if target not in RESTARTABLE:
                    emit(incident, "decision", f"cible « {target} » non autorisée, action ignorée", target=target)
                    continue
                wait = S["cooldown"] - (time.time() - last_action.get(target, 0))
                if wait > 0:
                    emit(incident, "decision", f"{target} déjà relancé récemment, attente {int(wait)} s",
                         target=target)
                    await asyncio.sleep(wait)
                    # Un autre incident a pu déjà rétablir le service : pas d'action inutile
                    ok, expr = await service_ok(client)
                    if ok:
                        incident.update(status="resolved", resolved=time.time(),
                                        recovery_seconds=round(time.time() - incident["failure_start"], 1),
                                        remediation_seconds=round(time.time() - incident["started"], 1))
                        M_INCIDENTS.labels(alert=incident["alert"], outcome="resolved").inc()
                        emit(incident, "verification", "service déjà rétabli, aucune action supplémentaire",
                             criterion=expr, result="ok")
                        return
                emit(incident, "decision", f"tentative {attempt} : redémarrer {target}",
                     target=target, action="restart")
                ok, detail = await restart(client, target)
                last_action[target] = time.time()
                M_ACTIONS.labels(action="restart", target=target, result="ok" if ok else "error").inc()
                emit(incident, "action", detail, target=target, action="restart", result="ok" if ok else "error")
                if not ok:
                    continue
                verified, expr, checks = await verify(client, incident)
                if verified:
                    now = time.time()
                    # Durée de coupure réelle : depuis le premier constat de panne par Prometheus
                    outage = now - incident.get("failure_start", incident["started"])
                    handling = now - incident["started"]
                    incident.update(status="resolved", resolved=now, recovery_seconds=round(outage, 1),
                                    remediation_seconds=round(handling, 1))
                    M_RECOVERY.observe(outage)
                    M_INCIDENTS.labels(alert=incident["alert"], outcome="resolved").inc()
                    preuves = ", ".join(f"{c['name']}: {'OK' if c['ok'] else 'KO'}" for c in checks)
                    emit(incident, "verification",
                         f"service rétabli : coupure de {outage:.0f} s, dont {handling:.0f} s de remédiation"
                         + (f" ({preuves})" if preuves else ""),
                         criterion=expr, checks=checks, result="ok")
                    return
                emit(incident, "verification", "service toujours dégradé après l'action", criterion=expr,
                     checks=checks, result="error")
            incident["status"] = "failed"
            M_INCIDENTS.labels(alert=incident["alert"], outcome="failed").inc()
            emit(incident, "escalation", "remédiation automatique épuisée : intervention requise")
        except Exception as e:  # noqa: BLE001
            incident["status"] = "failed"
            emit(incident, "escalation", f"erreur du moteur : {e}")
        finally:
            M_ACTIVE.dec()


# --- API ---------------------------------------------------------------------
@app.post("/alerts")
async def alerts(request: Request, authorization: str = Header(default="")):
    if not TOKEN or not hmac.compare_digest(authorization, f"Bearer {TOKEN}"):
        raise HTTPException(status_code=401, detail="jeton invalide")
    payload = await request.json()
    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {})
        key = alert.get("fingerprint") or json.dumps(labels, sort_keys=True)
        current = incidents.get(key)
        if alert.get("status") == "resolved":
            if current and current["status"] in ("in_progress", "observed"):
                emit(current, "resolution", "alerte levée par la supervision")
            continue
        if current and current["status"] == "in_progress":
            continue                            # même incident déjà en traitement
        rule = find_rule(alert)
        if rule is None:
            continue
        now = time.time()
        incident = {"id": next(ids), "alert": labels.get("alertname"), "labels": labels,
                    "status": "in_progress", "started": now, "steps": [],
                    "failure_start": min(parse_ts(alert.get("startsAt")) or now, now)}
        incidents[key] = incident
        emit(incident, "detection", alert.get("annotations", {}).get("summary", incident["alert"]),
             severity=labels.get("severity"))
        asyncio.create_task(handle(incident, rule, labels))
    return {"status": "accepted"}


@app.get("/events")
async def get_events(limit: int = 100):
    return list(events)[-limit:]


@app.get("/status")
async def status():
    recent = sorted(incidents.values(), key=lambda i: i["started"], reverse=True)[:20]
    return {"dry_run": DRY_RUN,
            "active": [i for i in recent if i["status"] == "in_progress"],
            "recent": [{k: v for k, v in i.items() if k != "steps"} for i in recent]}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


load_state()
log("info", "démarrage", incidents_restaures=len(incidents), rules=len(CONFIG["rules"]), restartable=sorted(RESTARTABLE), dry_run=DRY_RUN)
