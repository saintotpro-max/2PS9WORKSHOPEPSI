"""Génère le tableau de bord Grafana de la sonde IPS."""
import json
import sys

PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
panels = []
pid = 0


def add(kind, title, x, y, w, h, targets, ds=PROM, **extra):
    global pid
    pid += 1
    p = {"id": pid, "type": kind, "title": title, "datasource": ds,
         "gridPos": {"x": x, "y": y, "w": w, "h": h},
         "targets": [dict(t, refId=chr(65 + i), datasource=ds) for i, t in enumerate(targets)]}
    p.update(extra)
    panels.append(p)


def stat(title, x, expr, unit="short", red=None):
    steps = [{"color": "green", "value": None}]
    if red is not None:
        steps.append({"color": "red", "value": red})
    add("stat", title, x, 0, 6, 4, [{"expr": expr, "instant": True}],
        fieldConfig={"defaults": {"unit": unit, "decimals": 1,
                                  "thresholds": {"mode": "absolute", "steps": steps}},
                     "overrides": []},
        options={"colorMode": "background", "graphMode": "area", "reduceOptions": {"calcs": ["lastNotNull"]}})


def ts(title, x, y, w, targets, unit="short", **defaults):
    add("timeseries", title, x, y, w, 8, targets,
        fieldConfig={"defaults": {"unit": unit, **defaults}, "overrides": []},
        options={"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}})


stat("Flux analysés / s", 0, "sum(rate(ips_flows_total[1m]))", "ops")
stat("Flux suspects ≥ seuil (5 min)", 6, 'sum(increase(ips_suspect_flows_total[5m])) or vector(0)', red=1)
stat("IP bloquées (15 min)", 12, 'sum(increase(ips_blocks_total{mode="enforced"}[15m])) or vector(0)', red=1)
stat("Flux suivis", 18, "sum(ips_active_flows)")

ts("Prédictions par classe", 0, 4, 12,
   [{"expr": "sum by (result) (rate(ips_predictions_total[1m]))", "legendFormat": "{{result}}"}], "ops")
ts("Probabilité d'attaque maximale (seuil 0,9)", 12, 4, 12,
   [{"expr": "max by (attack_type) (ips_attack_probability_max)", "legendFormat": "{{attack_type}}"}], "percentunit",
   min=0, max=1,
   thresholds={"mode": "absolute", "steps": [{"color": "green", "value": None}, {"color": "red", "value": 0.9}]},
   custom={"thresholdsStyle": {"mode": "line+area"}})
ts("Latence de /predict (p95)", 0, 12, 12,
   [{"expr": "histogram_quantile(0.95, sum by (le) (rate(ips_predict_latency_seconds_bucket[1m])))",
     "legendFormat": "p95"}], "s")
ts("CPU des hôtes", 12, 12, 12,
   [{"expr": '100 - avg by (host) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100',
     "legendFormat": "{{host}}"}], "percent", min=0, max=100)
add("logs", "Événements de la sonde (détections, blocages)", 0, 20, 24, 10,
    [{"expr": '{service="flow-extractor"} |~ "suspect|bloqu|simulation|blanche|erreur|impossible|détectée"'}], LOKI,
    options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending"})

dashboard = {
    "uid": "ips", "title": "Sonde IPS — détection ML", "tags": ["resilience", "ips"],
    "timezone": "browser", "refresh": "5s", "schemaVersion": 41, "version": 1,
    "time": {"from": "now-30m", "to": "now"}, "panels": panels,
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(dashboard, f, ensure_ascii=False, indent=2)
print(f"{len(panels)} panneaux -> {sys.argv[1]}")
