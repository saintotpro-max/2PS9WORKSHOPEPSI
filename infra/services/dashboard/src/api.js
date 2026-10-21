// Accès en lecture seule aux données, relayées par le nginx du dashboard :
//   /dashboard/api/prom/*         -> Prometheus (query, query_range)
//   /dashboard/api/loki/query     -> Loki (requête instantanée)
//   /dashboard/api/remediation/*  -> moteur de remédiation (events, status)
const BASE = `${import.meta.env.BASE_URL}api`;

async function getJson(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(`${url} : HTTP ${r.status}`);
  return r.json();
}

/** Valeur scalaire d'une requête PromQL (première série), ou null si absente. */
export async function promValue(expr) {
  const d = await getJson(`${BASE}/prom/query?query=${encodeURIComponent(expr)}`);
  const res = d.data?.result ?? [];
  return res.length ? Number(res[0].value[1]) : null;
}

/** Toutes les séries d'une requête PromQL : [{ labels, value }]. */
export async function promVector(expr) {
  const d = await getJson(`${BASE}/prom/query?query=${encodeURIComponent(expr)}`);
  return (d.data?.result ?? []).map((s) => ({ labels: s.metric, value: Number(s.value[1]) }));
}

/** Séries temporelles sur les `minutes` dernières minutes : [{ labels, points: [[ts, v]] }]. */
export async function promRange(expr, minutes = 15, step = 1) {
  // Bornes alignées sur le pas : toutes les séries partagent les mêmes instants
  const end = Math.floor(Date.now() / 1000 / step) * step;
  const start = end - minutes * 60;
  const q = `query=${encodeURIComponent(expr)}&start=${start}&end=${end}&step=${step}`;
  const d = await getJson(`${BASE}/prom/query_range?${q}`);
  return (d.data?.result ?? []).map((s) => ({
    labels: s.metric,
    points: s.values.map(([t, v]) => [t * 1000, Number(v)]),
  }));
}

/** Valeur scalaire d'une requête LogQL métrique. */
export async function lokiValue(expr) {
  const d = await getJson(`${BASE}/loki/query?query=${encodeURIComponent(expr)}`);
  const res = d.data?.result ?? [];
  return res.length ? Number(res[0].value[1]) : 0;
}

export const remediationEvents = () => getJson(`${BASE}/remediation/events?limit=200`);
export const remediationStatus = () => getJson(`${BASE}/remediation/status`);

/** Liste des IP blacklistées par la sonde IPS (via le WAF -> service de contrôle ra-ips). */
export const ipsBlocklist = () => getJson("/ipsctl/blocklist");

/**
 * Fusionne plusieurs séries en lignes { t, clé1, clé2… } pour Recharts.
 * entries : [[clé, séries]] ; la clé peut être une fonction (labels) => nom.
 */
export function mergeSeries(entries) {
  const rows = new Map();
  for (const [key, series] of entries) {
    for (const s of series) {
      const k = typeof key === "function" ? key(s.labels) : key;
      for (const [t, v] of s.points) {
        const row = rows.get(t) ?? { t };
        row[k] = v;
        rows.set(t, row);
      }
    }
  }
  return [...rows.values()].sort((a, b) => a.t - b.t);
}
