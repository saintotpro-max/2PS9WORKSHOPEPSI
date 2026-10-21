"""flow-extractor — sonde IPS RESILIENCE-ALPHA.

Lit les enregistrements de flux Argus (via `ra`), reconstruit les 10 features
UNSW-NB15 attendues par le modèle, interroge `POST /predict` par lots, et bloque
l'IP source dans nftables (famille bridge) quand le modèle détecte une attaque.

Points d'attention :
- Argus émet des enregistrements intermédiaires toutes les N s ; chacun ne
  contient que les compteurs de l'intervalle. On les CUMULE par flux pour
  reproduire des valeurs de flux complètes (comme dans UNSW-NB15) tout en
  détectant les flux encore ouverts.
- ct_srv_src / ct_dst_ltm : comptés sur les 100 dernières connexions
  (définition UNSW-NB15), « service » = protocole + port destination.
- Les flux sont envoyés au modèle par lots (toutes les BATCH_INTERVAL s ou par
  BATCH_MAX flux) : un lot de 600 flux coûte à peine plus qu'un flux isolé,
  ce qui évite que la sonde prenne du retard pendant une attaque.
"""
import csv
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque, defaultdict
from ipaddress import ip_address, ip_network

from prometheus_client import Counter, Gauge, Histogram, start_http_server

# --- Configuration (variables d'environnement) -----------------------------
ARGUS_SOURCE = os.environ.get("ARGUS_SOURCE", "127.0.0.1:561")
PREDICT_URL = os.environ.get("PREDICT_URL", "http://127.0.0.1:8000/predict")
ATTACK_CLASSES = {c.strip() for c in os.environ.get("ATTACK_CLASSES", "DoS,Reconnaissance").split(",")}
THRESHOLD = float(os.environ.get("ATTACK_THRESHOLD", os.environ.get("DOS_THRESHOLD", "0.9")))
HITS_TO_BLOCK = int(os.environ.get("HITS_TO_BLOCK", "3"))      # flux suspects requis
HITS_WINDOW = int(os.environ.get("HITS_WINDOW_SECONDS", "30"))
BLOCK_ENABLED = os.environ.get("BLOCK_ENABLED", "false").lower() == "true"
BLOCK_TIMEOUT = os.environ.get("BLOCK_TIMEOUT", "10m")
NFT_TABLE = os.environ.get("NFT_TABLE", "bridge ips")
NFT_SET = os.environ.get("NFT_SET", "blocked")
ALLOWLIST = [ip_network(n.strip()) for n in
             os.environ.get("ALLOWLIST", "10.10.10.0/24").split(",") if n.strip()]
BATCH_INTERVAL = float(os.environ.get("BATCH_INTERVAL", "0.5"))
BATCH_MAX = int(os.environ.get("BATCH_MAX", "500"))
CT_WINDOW = 100                     # définition UNSW-NB15
FLOW_IDLE = 60                      # oubli d'un flux inactif (s)
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9101"))
# Export du jeu de données d'entraînement : une ligne par flux analysé, étiquetée avec
# le contenu du fichier CAPTURE_DIR/label (« off » ou absent = pas d'export).
CAPTURE_DIR = os.environ.get("CAPTURE_DIR", "")
FEATURE_NAMES = ["dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sload", "dload",
                 "ct_srv_src", "ct_dst_ltm"]
CAPTURE_HEADER = (["ts", "label", "flow_id", "srcip", "dstip", "service"] + FEATURE_NAMES
                  + ["pred_class", "p_normal", "p_dos", "p_reconnaissance"])

FIELDS = ["stime", "ltime", "proto", "saddr", "sport", "daddr", "dport",
          "spkts", "dpkts", "sbytes", "dbytes"]

logging.basicConfig(stream=sys.stdout, level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    format="%(message)s")


def log(level, message, **kw):
    """Une ligne JSON par événement (collectée par Loki)."""
    logging.log(getattr(logging, level), json.dumps(
        {"timestamp": time.time(), "level": level.lower(), "service": "flow-extractor",
         "message": message, **kw}))


# --- Métriques Prometheus ---------------------------------------------------
M_FLOWS = Counter("ips_flows_total", "Enregistrements de flux analysés")
M_PRED = Counter("ips_predictions_total", "Prédictions par classe", ["result"])
M_SUSPECT = Counter("ips_suspect_flows_total", "Flux classés attaque au-dessus du seuil", ["attack_type"])
M_PRED_ERR = Counter("ips_predict_errors_total", "Erreurs d'appel à /predict")
M_PROBA = Gauge("ips_dos_probability_max", "Probabilité DoS maximale du dernier lot")
M_ATTACK_PROBA = Gauge("ips_attack_probability_max", "Probabilité d'attaque maximale du dernier lot",
                       ["attack_type"])
M_LAT = Histogram("ips_predict_latency_seconds", "Latence d'un appel /predict (un lot)")
M_BATCH = Histogram("ips_predict_batch_size", "Nombre de flux par lot",
                    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000))
M_BLOCKS = Counter("ips_blocks_total", "IP bloquées", ["mode", "attack_type"])
M_ACTIVE = Gauge("ips_active_flows", "Flux suivis en mémoire")


# --- État ------------------------------------------------------------------
flows = {}                              # clé de flux -> cumul
recent = deque(maxlen=CT_WINDOW)        # (saddr, service, daddr) des dernières connexions
hits = defaultdict(deque)               # saddr -> horodatages de flux suspects
blocked = {}                            # saddr -> fin de blocage (indicatif)
pending = []                            # (contexte, features) en attente de prédiction
lock = threading.Lock()
wake = threading.Event()


def service_of(proto, dport):
    return f"{proto}/{dport}"


def features(f):
    dur = max(f["ltime"] - f["stime"], 0.0)
    pkts = f["spkts"] + f["dpkts"]
    safe = dur if dur > 0 else 1e-6
    return {
        "dur": round(dur, 6),
        "spkts": f["spkts"], "dpkts": f["dpkts"],
        "sbytes": f["sbytes"], "dbytes": f["dbytes"],
        "rate": round(pkts / safe, 4) if dur > 0 else 0.0,
        "sload": round(f["sbytes"] * 8 / safe, 4) if dur > 0 else 0.0,
        "dload": round(f["dbytes"] * 8 / safe, 4) if dur > 0 else 0.0,
        "ct_srv_src": sum(1 for s, srv, _ in recent if s == f["saddr"] and srv == f["service"]),
        "ct_dst_ltm": sum(1 for _, _, d in recent if d == f["daddr"]),
    }


def predict(batch):
    req = urllib.request.Request(PREDICT_URL, data=json.dumps(batch).encode(),
                                 headers={"Content-Type": "application/json"})
    with M_LAT.time(), urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def allowlisted(ip):
    try:
        a = ip_address(ip)
    except ValueError:
        return True
    return any(a in n for n in ALLOWLIST)


def block(ip, attack_type, proba):
    if ip in blocked and blocked[ip] > time.time():
        return
    if allowlisted(ip):
        log("WARNING", "IP suspecte en liste blanche, non bloquée", srcip=ip,
            attack_type=attack_type, probability=proba)
        blocked[ip] = time.time() + 60
        return
    if not BLOCK_ENABLED:
        M_BLOCKS.labels(mode="dry-run", attack_type=attack_type).inc()
        log("WARNING", "attaque détectée (mode simulation, pas de blocage)", srcip=ip,
            attack_type=attack_type, probability=proba)
        blocked[ip] = time.time() + 60
        return
    cmd = ["nft", "add", "element", *NFT_TABLE.split(), NFT_SET,
           f"{{ {ip} timeout {BLOCK_TIMEOUT} }}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        M_BLOCKS.labels(mode="enforced", attack_type=attack_type).inc()
        blocked[ip] = time.time() + 60
        log("WARNING", "IP bloquée", srcip=ip, attack_type=attack_type, probability=proba,
            timeout=BLOCK_TIMEOUT)
    else:
        log("ERROR", "échec du blocage nftables", srcip=ip, stderr=res.stderr.strip())


def handle(rec):
    """Met à jour le cumul du flux et met ses features en attente de prédiction."""
    key = (rec["proto"], rec["saddr"], rec["sport"], rec["daddr"], rec["dport"])
    with lock:
        f = flows.get(key)
        if f is None:
            f = {"stime": rec["stime"], "ltime": rec["ltime"], "saddr": rec["saddr"],
                 "daddr": rec["daddr"], "service": service_of(rec["proto"], rec["dport"]),
                 "spkts": 0, "dpkts": 0, "sbytes": 0, "dbytes": 0, "seen": time.time()}
            flows[key] = f
            recent.append((f["saddr"], f["service"], f["daddr"]))   # nouvelle connexion
        for k in ("spkts", "dpkts", "sbytes", "dbytes"):
            f[k] += rec[k]
        f["ltime"] = max(f["ltime"], rec["ltime"])
        f["seen"] = time.time()
        ctx = {"saddr": f["saddr"], "daddr": f["daddr"], "service": f["service"],
               "flow_id": f"{rec['proto']}:{rec['saddr']}:{rec['sport']}-{rec['daddr']}:{rec['dport']}@{f['stime']:.3f}"}
        pending.append((ctx, features(f)))
        full = len(pending) >= BATCH_MAX
    M_FLOWS.inc()
    if full:
        wake.set()


def decide(ctx, feat, out):
    attack_type = out.get("attack_type", "Normal")
    M_PRED.labels(result=attack_type.lower()).inc()
    if attack_type not in ATTACK_CLASSES:
        return
    proba = float(out.get("probabilities", {}).get(attack_type, out.get("dos_probability", 0.0)))
    if proba < THRESHOLD:
        return
    M_SUSPECT.labels(attack_type=attack_type).inc()
    now = time.time()
    h = hits[ctx["saddr"]]
    h.append(now)
    while h and h[0] < now - HITS_WINDOW:
        h.popleft()
    log("INFO", "flux suspect", srcip=ctx["saddr"], dstip=ctx["daddr"], flow_service=ctx["service"],
        attack_type=attack_type, probability=proba, hits=len(h), features=feat)
    if len(h) >= HITS_TO_BLOCK:
        block(ctx["saddr"], attack_type, proba)


def capture_label():
    if not CAPTURE_DIR:
        return None
    try:
        label = open(os.path.join(CAPTURE_DIR, "label"), encoding="utf-8").read().strip()
    except OSError:
        return None
    return None if label in ("", "off") else label


def capture(batch, results):
    """Ajoute le lot au CSV du jour. Un flux long apparaît plusieurs fois (valeurs
    cumulées toutes les 5 s) : garder la dernière ligne de chaque flow_id pour l'entraînement."""
    label = capture_label()
    if label is None:
        return
    path = os.path.join(CAPTURE_DIR, time.strftime("capture-%Y%m%d.csv"))
    new = not os.path.exists(path)
    now = round(time.time(), 3)
    try:
        with open(path, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(CAPTURE_HEADER)
            for (ctx, feat), out in zip(batch, results):
                p = out.get("probabilities", {})
                w.writerow([now, label, ctx["flow_id"], ctx["saddr"], ctx["daddr"], ctx["service"]]
                           + [feat[k] for k in FEATURE_NAMES]
                           + [out.get("attack_type"), p.get("Normal"), p.get("DoS"), p.get("Reconnaissance")])
    except OSError as e:
        log("ERROR", "export CSV impossible", error=str(e))


def batcher():
    """Envoie les flux en attente au modèle, par lots."""
    while True:
        wake.wait(BATCH_INTERVAL)
        wake.clear()
        with lock:
            batch, pending[:] = pending[:], []
        if not batch:
            continue
        M_BATCH.observe(len(batch))
        try:
            results = predict([feat for _, feat in batch])
        except Exception as e:  # noqa: BLE001 — la sonde ne doit jamais s'arrêter
            M_PRED_ERR.inc()
            log("ERROR", "appel /predict impossible", error=str(e), batch=len(batch))
            continue
        maxima = defaultdict(float)
        for (ctx, feat), out in zip(batch, results):
            for cls, p in out.get("probabilities", {}).items():
                maxima[cls] = max(maxima[cls], float(p))
            decide(ctx, feat, out)
        capture(batch, results)
        M_PROBA.set(maxima.get("DoS", 0.0))
        for cls in ATTACK_CLASSES:
            M_ATTACK_PROBA.labels(attack_type=cls).set(maxima.get(cls, 0.0))


def janitor():
    while True:
        time.sleep(10)
        with lock:
            limit = time.time() - FLOW_IDLE
            for k in [k for k, f in flows.items() if f["seen"] < limit]:
                del flows[k]
            M_ACTIVE.set(len(flows))


def parse(line):
    p = line.rstrip("\n").split(",")
    if len(p) != len(FIELDS):
        return None
    r = dict(zip(FIELDS, p))
    try:
        for k in ("stime", "ltime"):
            r[k] = float(r[k])
        for k in ("spkts", "dpkts", "sbytes", "dbytes"):
            r[k] = int(r[k])
    except ValueError:
        return None
    return r


def main():
    start_http_server(METRICS_PORT)
    threading.Thread(target=janitor, daemon=True).start()
    threading.Thread(target=batcher, daemon=True).start()
    log("INFO", "démarrage", predict_url=PREDICT_URL, block_enabled=BLOCK_ENABLED,
        attack_classes=sorted(ATTACK_CLASSES), threshold=THRESHOLD, hits_to_block=HITS_TO_BLOCK,
        batch_interval=BATCH_INTERVAL, batch_max=BATCH_MAX)
    # stdbuf : sans lui, ra tamponne sa sortie vers le pipe et les flux arrivent en retard
    cmd = ["stdbuf", "-oL", "ra", "-S", ARGUS_SOURCE, "-n", "-u", "-c", ",", "-L", "-1", "-s", *FIELDS]
    while True:                                   # reconnexion si argus redémarre
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
        for line in proc.stdout:
            rec = parse(line)
            if rec and rec["proto"] in ("tcp", "udp"):
                handle(rec)
        log("WARNING", "flux Argus interrompu, reconnexion", rc=proc.wait())
        time.sleep(2)


if __name__ == "__main__":
    main()
