import { fetchBlocklist, fetchCharts, fetchIncidents, fetchSnapshot, overallState } from "./data";
import usePolling from "./usePolling";
import { Banner, Blocklist, Components, Incidents, Kpi, SeriesChart, TrafficChart } from "./components/ui";

const fmt = (v, digits = 0) => (v == null || Number.isNaN(v) ? null : v.toFixed(digits));

export default function App() {
  const snap = usePolling(fetchSnapshot, 1000);
  const charts = usePolling(fetchCharts, 1000);
  const incidents = usePolling(fetchIncidents, 1000);
  const blocklist = usePolling(fetchBlocklist, 1000);
  const s = snap.data;
  const stale = snap.at != null && Date.now() - snap.at > 15000;
  const lastRecovery = (s?.status?.recent ?? []).find((i) => i.status === "resolved")?.recovery_seconds;

  return (
    <div className="mx-auto max-w-[1600px] space-y-5 p-4 md:p-6">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-extrabold tracking-tight">
          RESILIENCE-ALPHA <span className="font-semibold text-ink/60">· supervision et reprise autonome</span>
        </h1>
        <p className="text-sm italic text-ink/60">Plateforme de paiement fictive — démonstrateur EPSI 2026</p>
      </header>

      <Banner state={overallState(s)} updatedAt={snap.at} stale={stale || !!snap.error} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Disponibilité (5 min)" value={fmt(s?.availability != null ? s.availability * 100 : null, 1)}
             unit="%" tone={s?.availability >= 0.99 ? "ok" : s?.availability != null ? "bad" : "ink"} />
        <Kpi label="Requêtes / s" value={fmt(s?.flows, 0)} unit="/ s" hint="service paiement" />
        <Kpi label="Probabilité d'attaque" value={fmt(s?.attackProba != null ? s.attackProba * 100 : null)}
             unit="%" tone={s?.attackProba >= 0.9 ? "bad" : s?.attackProba >= 0.5 ? "warn" : "ok"} hint="modèle ML, max" />
        <Kpi label="IP bloquées (15 min)" value={fmt(s?.blocked)} tone={s?.blocked > 0 ? "warn" : "ink"} hint="sonde IPS" />
        <Kpi label="Requêtes bloquées (15 min)" value={fmt(s?.wafBlocked)} tone={s?.wafBlocked > 0 ? "warn" : "ink"}
             hint="WAF OWASP CRS" />
        <Kpi label="Dernière reprise" value={fmt(lastRecovery)} unit="s" tone="ok" hint="début de panne → service vérifié" />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <TrafficChart data={charts.data?.traffic ?? []} />
          <div className="grid gap-5 lg:grid-cols-2">
            <SeriesChart title="Détection ML : probabilité d'attaque" data={charts.data?.ml ?? []}
                         keys={charts.data?.mlKeys ?? []} domain={[0, 1]} threshold={0.6} />
            <SeriesChart title="CPU des serveurs" data={charts.data?.cpu ?? []} keys={charts.data?.cpuKeys ?? []}
                         domain={[0, 100]} unit="%" />
          </div>
        </div>
        <div className="space-y-5">
          <Components items={s?.components ?? []} />
          <Blocklist data={blocklist.data} />
        </div>
      </div>

      <Incidents incidents={incidents.data ?? []} />
    </div>
  );
}
