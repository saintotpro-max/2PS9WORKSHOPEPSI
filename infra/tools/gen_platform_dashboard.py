"""Génère le tableau de bord Grafana « Plateforme — état du service »."""
import json
import sys

PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
panels = []


def add(kind, title, grid, targets, ds=PROM, **extra):
    p = {"id": len(panels) + 1, "type": kind, "title": title, "datasource": ds,
         "gridPos": dict(zip("xywh", grid)),
         "targets": [dict(t, refId=chr(65 + i), datasource=ds) for i, t in enumerate(targets)]}
    p.update(extra)
    panels.append(p)


def stat(title, x, expr, unit="short", steps=None, mappings=None, w=4):
    steps = steps or [{"color": "green", "value": None}]
    add("stat", title, (x, 0, w, 4), [{"expr": expr, "instant": True}],
        fieldConfig={"defaults": {"unit": unit, "thresholds": {"mode": "absolute", "steps": steps},
                                  "mappings": mappings or []}, "overrides": []},
        options={"colorMode": "background", "graphMode": "none",
                 "reduceOptions": {"calcs": ["lastNotNull"]}})


UPDOWN = [{"type": "value", "options": {"0": {"text": "EN PANNE", "color": "red"},
                                        "1": {"text": "OK", "color": "green"}}}]
RED0 = [{"color": "red", "value": None}, {"color": "green", "value": 1}]

stat("WAF (point d'entrée)", 0, 'probe_success{instance="http://waf:8080/healthz"}', steps=RED0, mappings=UPDOWN)
stat("Base de données", 4, "pg_up", steps=RED0, mappings=UPDOWN)
stat("Sonde IPS", 8, 'up{job="ips"}', steps=RED0, mappings=UPDOWN)
stat("Dernière sauvegarde", 12, "time() - pg_backup_last_success_timestamp_seconds", "s",
     steps=[{"color": "green", "value": None}, {"color": "orange", "value": 3600}, {"color": "red", "value": 7200}])
stat("Alertes actives", 16, 'count(ALERTS{alertstate="firing"}) or vector(0)',
     steps=[{"color": "green", "value": None}, {"color": "red", "value": 1}])
stat("Requêtes bloquées par le WAF (15 min)", 20,
     'sum(count_over_time({service="waf"} |= "ModSecurity: Access denied" [15m])) or vector(0)',
     steps=[{"color": "green", "value": None}, {"color": "orange", "value": 1}])
panels[-1]["datasource"] = LOKI
panels[-1]["targets"][0]["datasource"] = LOKI


def ts(title, grid, targets, unit="short", ds=PROM, **defaults):
    add("timeseries", title, grid, targets, ds,
        fieldConfig={"defaults": {"unit": unit, **defaults}, "overrides": []},
        options={"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}})


ts("Requêtes HTTP par code (WAF)", (0, 4, 12, 8),
   [{"expr": 'sum by (status) (count_over_time({service="waf"} | pattern `<_> - <_> [<_>] "<_>" <status> <_>` | status=~"[0-9]+" [1m]))',
     "legendFormat": "{{status}}"}], "short", LOKI)
ts("Attaques bloquées par le WAF", (12, 4, 12, 8),
   [{"expr": 'sum(count_over_time({service="waf"} |= "ModSecurity: Access denied" [1m]))',
     "legendFormat": "requêtes bloquées"}], "short", LOKI)
ts("CPU par conteneur", (0, 12, 12, 8),
   [{"expr": 'sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[1m])) * 100',
     "legendFormat": "{{name}}"}], "percent")
ts("Mémoire par conteneur", (12, 12, 12, 8),
   [{"expr": 'sum by (name) (container_memory_working_set_bytes{name!=""})', "legendFormat": "{{name}}"}],
   "bytes")
add("logs", "Journal du WAF : requêtes bloquées", (0, 20, 24, 9),
    [{"expr": '{service="waf"} |= "ModSecurity: Access denied"'}], LOKI,
    options={"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending"})
add("text", "Sonde transactionnelle", (0, 29, 24, 3), [], options={
    "mode": "markdown",
    "content": "**À venir** : la sonde `txn-probe` rejouera une transaction fictive toutes les 5 s "
               "(preuve de reprise). En attente de la séquence d'appels de l'équipe DEV."})

dashboard = {"uid": "plateforme", "title": "Plateforme — état du service", "tags": ["resilience"],
             "timezone": "browser", "refresh": "5s", "schemaVersion": 41, "version": 1,
             "time": {"from": "now-30m", "to": "now"}, "panels": panels}
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as f:
    json.dump(dashboard, f, ensure_ascii=False, indent=2)
print(f"{len(panels)} panneaux -> {sys.argv[1]}")
