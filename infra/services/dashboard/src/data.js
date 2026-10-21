// Lecture et interprétation de l'état de la plateforme.
import { ipsBlocklist, lokiValue, mergeSeries, promRange, promValue, promVector, remediationEvents, remediationStatus } from "./api";

// Reprise prouvée par une transaction de test (txn-probe) ; à défaut, le point d'entrée répond.
const SERVICE_OK = 'min(txn_probe_success) or probe_success{instance="http://waf:8080/healthz"}';
const AVAILABILITY_5M =
  'avg_over_time(min(txn_probe_success)[5m:15s]) or avg_over_time(probe_success{instance="http://waf:8080/healthz"}[5m])';

const safe = (p, fallback = null) => p.catch(() => fallback);

/** IP blacklistées par la sonde IPS : { ips: [{ip, expires_s}], count }. */
export async function fetchBlocklist() {
  return (await safe(ipsBlocklist(), { ips: [], count: 0 })) ?? { ips: [], count: 0 };
}

/** Instantané : bandeau d'état, indicateurs, état des composants. */
export async function fetchSnapshot() {
  const [serviceOk, availability, flows, attackProba, attacks, blocked, wafBlocked, backupAge, components, status] =
    await Promise.all([
      safe(promValue(SERVICE_OK)),
      safe(promValue(AVAILABILITY_5M)),
      safe(promValue("sum(rate(alpha_requests_total[1m]))")),
      safe(promValue("max(ips_attack_probability_max)")),
      safe(promValue("sum(increase(ips_suspect_flows_total[1m]))")),
      safe(promValue('sum(increase(ips_blocks_total{mode="enforced"}[15m]))')),
      safe(lokiValue('sum(count_over_time({service="waf"} |= "ModSecurity: Access denied" [15m]))'), 0),
      safe(promValue("time() - pg_backup_last_success_timestamp_seconds")),
      safe(fetchComponents(), []),
      safe(remediationStatus(), null),
    ]);
  return { serviceOk, availability, flows, attackProba, attacks, blocked, wafBlocked, backupAge, components, status };
}

const APP_SERVICES = [["paiement", "Plateforme de paiement"]];

async function fetchComponents() {
  const [up, probes, appProbes] = await Promise.all([
    promVector('up{job=~"ips|remediation|postgres"}'),
    promVector('probe_success{instance="http://waf:8080/healthz"}'),
    safe(promVector('probe_success{job="blackbox-services"}'), []),
  ]);
  const byJob = Object.fromEntries(up.map((s) => [s.labels.job, s.value]));
  const pg = await safe(promValue("pg_up"));
  const model = await safe(promValue("increase(ips_predict_errors_total[2m])"));
  const backup = await safe(promValue("time() - pg_backup_last_success_timestamp_seconds"));
  const txn = await safe(promValue("min(txn_probe_success)"));
  const app = Object.fromEntries(appProbes.map((s) => [s.labels.service, s.value]));
  const state = (v) => (v == null ? "absent" : v >= 1 ? "ok" : "down");
  return [
    { name: "Point d'entrée (WAF)", state: state(probes[0]?.value) },
    ...APP_SERVICES.map(([svc, name]) => ({ name, state: state(app[svc]) })),
    { name: "Transactions de test", state: state(txn) },
    { name: "Base de données", state: state(pg) },
    { name: "Sonde IPS", state: state(byJob.ips) },
    { name: "Modèle ML", state: byJob.ips == null ? "absent" : model > 0 ? "down" : "ok" },
    { name: "Moteur de remédiation", state: state(byJob.remediation) },
    { name: "Sauvegardes", state: backup == null ? "absent" : backup < 7200 ? "ok" : "down" },
  ];
}

/** Séries des graphiques (15 dernières minutes). */
export async function fetchCharts() {
  const [svc, flows, proba, cpu] = await Promise.all([
    safe(promRange(SERVICE_OK), []),
    safe(promRange("sum(rate(alpha_requests_total[1m]))"), []),
    safe(promRange("max by (attack_type) (ips_attack_probability_max)"), []),
    safe(promRange('100 - avg by (host) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100'), []),
  ]);
  return {
    traffic: mergeSeries([["service", svc.slice(0, 1)], ["flux", flows]]),
    ml: mergeSeries([[(l) => l.attack_type, proba]]),
    mlKeys: proba.map((s) => s.labels.attack_type),
    cpu: mergeSeries([[(l) => l.host, cpu]]),
    cpuKeys: cpu.map((s) => s.labels.host),
  };
}

/** Incidents reconstitués à partir de la chronologie du moteur de remédiation. */
export async function fetchIncidents() {
  const [events, status] = await Promise.all([remediationEvents(), remediationStatus()]);
  const meta = Object.fromEntries((status.recent ?? []).map((i) => [i.id, i]));
  const groups = new Map();
  for (const ev of events) {
    const g = groups.get(ev.incident) ?? { id: ev.incident, alert: ev.alert, steps: [] };
    g.steps.push(ev);
    groups.set(ev.incident, g);
  }
  return [...groups.values()]
    .map((g) => ({ ...g, ...meta[g.id] }))
    .sort((a, b) => b.id - a.id)
    .slice(0, 5);
}

/** Bandeau principal : priorité reprise > panne > attaque > rétabli récemment > nominal. */
export function overallState(snap) {
  if (!snap) return { tone: "info", title: "Connexion à la supervision…", detail: "" };
  const active = snap.status?.active ?? [];
  const lastResolved = (snap.status?.recent ?? []).find((i) => i.status === "resolved");
  const sinceResolved = lastResolved ? Date.now() / 1000 - lastResolved.resolved : Infinity;
  if (active.length)
    return { tone: "info", title: "REPRISE AUTOMATIQUE EN COURS", detail: `${active[0].alert} — remédiation engagée` };
  if (snap.serviceOk === 0)
    return { tone: "bad", title: "SERVICE DÉGRADÉ", detail: "les transactions de test échouent" };
  if (snap.attacks > 0 || snap.blocked > 0)
    return { tone: "warn", title: "ATTAQUE DÉTECTÉE — SERVICE MAINTENU", detail: "la sonde IPS traite l'attaque" };
  if (sinceResolved < 180)
    return {
      tone: "ok",
      title: `SERVICE RÉTABLI EN ${Math.round(lastResolved.recovery_seconds)} s`,
      detail: `reprise vérifiée automatiquement, sans intervention humaine (remédiation : ${Math.round(
        lastResolved.remediation_seconds ?? lastResolved.recovery_seconds,
      )} s)`,
    };
  if (snap.serviceOk == null) return { tone: "info", title: "ÉTAT INCONNU", detail: "aucune mesure de disponibilité" };
  return { tone: "ok", title: "SERVICE OPÉRATIONNEL", detail: "transactions de paiement nominales" };
}
