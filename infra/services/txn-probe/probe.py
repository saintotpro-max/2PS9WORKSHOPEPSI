"""txn-probe — sonde transactionnelle RESILIENCE-ALPHA.

Toutes les INTERVAL secondes, rejoue un parcours de paiement complet par le WAF
(comme un vrai client) : authentification -> création d'une transaction fictive
de 1 centime -> relecture. Publie txn_probe_success (1 = paiement possible),
critère de reprise utilisé par le moteur de remédiation et le dashboard.
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.request
import uuid

from prometheus_client import Counter, Gauge, Histogram, start_http_server

TARGET = os.environ.get("TARGET", "https://waf:8443").rstrip("/")
USER = os.environ.get("TXN_USER", "sonde")
PASSWORD = os.environ["TXN_PASSWORD"]
INTERVAL = float(os.environ.get("INTERVAL", "5"))
TIMEOUT = float(os.environ.get("TIMEOUT", "4"))
PORT = int(os.environ.get("METRICS_PORT", "9102"))

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE          # certificat autosigné du WAF (lab)

M_OK = Gauge("txn_probe_success", "1 si la dernière transaction de test a réussi")
M_LAST = Gauge("txn_probe_last_success_timestamp_seconds", "Dernière transaction de test réussie")
M_RUNS = Counter("txn_probe_runs_total", "Transactions de test", ["result", "step"])
M_DUR = Histogram("txn_probe_duration_seconds", "Durée d'un parcours complet",
                  buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 4))


def log(level, message, **kw):
    print(json.dumps({"timestamp": time.time(), "level": level, "service": "txn-probe",
                      "message": message, **kw}, ensure_ascii=False), flush=True)


def call(method, path, body=None, token=None):
    headers = {"Content-Type": "application/json", "User-Agent": "txn-probe/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(TARGET + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
        return r.status, json.load(r)


def run_once():
    step = "auth"
    try:
        _, tok = call("POST", "/auth/token", {"username": USER, "password": PASSWORD})
        step = "create"
        status, tx = call("POST", "/transactions", {
            "amount_cents": 1, "currency": "EUR", "payer": USER, "payee": "sonde-de-reprise",
            "idempotency_key": f"probe-{uuid.uuid4()}"}, tok["access_token"])
        if status != 201 or tx.get("status") != "accepted":
            raise ValueError(f"transaction refusée : HTTP {status}, statut {tx.get('status')}")
        step = "read"
        _, back = call("GET", f"/transactions/{tx['id']}", token=tok["access_token"])
        if back.get("id") != tx["id"]:
            raise ValueError("transaction relue incohérente")
        return True, step, None
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        return False, step, str(e)


def main():
    start_http_server(PORT)
    log("info", "démarrage", target=TARGET, user=USER, interval=INTERVAL)
    previous = None
    while True:
        t0 = time.monotonic()
        ok, step, error = run_once()
        M_DUR.observe(time.monotonic() - t0)
        M_OK.set(1 if ok else 0)
        M_RUNS.labels(result="ok" if ok else "error", step="done" if ok else step).inc()
        if ok:
            M_LAST.set(time.time())
        if ok != previous:                       # journalise les changements d'état
            log("info" if ok else "error",
                "transactions de test OK" if ok else "transaction de test en échec",
                step=step, error=error)
            previous = ok
        time.sleep(max(0.0, INTERVAL - (time.monotonic() - t0)))


if __name__ == "__main__":
    main()
