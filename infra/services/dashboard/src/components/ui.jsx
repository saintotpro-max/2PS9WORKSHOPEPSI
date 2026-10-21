// Briques visuelles du dashboard.
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const TONES = {
  ok: "bg-ok text-white",
  warn: "bg-warn text-white",
  bad: "bg-bad text-white",
  info: "bg-info text-white",
};
const PALETTE = ["#261e48", "#c2410c", "#1d4ed8", "#15803d", "#7e22ce"];
const time = (t) => new Date(t).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export function Card({ title, children, className = "" }) {
  return (
    <section className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-lilac/40 ${className}`}>
      {title && <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink/70">{title}</h2>}
      {children}
    </section>
  );
}

export function Banner({ state, updatedAt, stale }) {
  return (
    <div className={`rounded-2xl px-8 py-6 shadow-sm transition-colors duration-500 ${TONES[state.tone]}`}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest opacity-80">État du service de paiement</p>
          <p className="mt-1 text-4xl font-extrabold leading-tight md:text-5xl">{state.title}</p>
          {state.detail && <p className="mt-2 text-lg opacity-90">{state.detail}</p>}
        </div>
        <p className="text-right text-sm opacity-80">
          {stale ? "⚠ données non actualisées" : "actualisé à"}
          <br />
          <span className="text-2xl font-bold tabular-nums">{updatedAt ? time(updatedAt) : "--:--:--"}</span>
        </p>
      </div>
    </div>
  );
}

export function Kpi({ label, value, unit, tone = "ink", hint }) {
  const color = { ink: "text-ink", ok: "text-ok", warn: "text-warn", bad: "text-bad" }[tone];
  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">{label}</p>
      <p className={`mt-1 text-3xl font-extrabold tabular-nums ${color}`}>
        {value ?? "—"}
        {value != null && unit && <span className="ml-1 text-lg font-semibold">{unit}</span>}
      </p>
      {hint && <p className="mt-1 text-xs text-ink/60">{hint}</p>}
    </Card>
  );
}

const DOT = {
  ok: ["bg-ok", "opérationnel"],
  down: ["bg-bad animate-pulse", "en panne"],
  absent: ["bg-lilac", "non déployé"],
};

export function Blocklist({ data }) {
  const ips = data?.ips ?? [];
  return (
    <Card title={`IP blacklistées (${ips.length})`}>
      {ips.length === 0 ? (
        <p className="text-sm text-ink/60">Aucune IP bloquée par la sonde IPS.</p>
      ) : (
        <ul className="space-y-2">
          {ips.map((e) => (
            <li key={e.ip} className="flex items-center justify-between rounded-lg bg-paper/60 px-3 py-2">
              <span className="font-mono font-semibold text-rose">{e.ip}</span>
              <span className="text-sm text-ink/60">
                {e.expires_s != null ? `expire dans ${Math.round(e.expires_s)} s` : "bloquée"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function Components({ items }) {
  return (
    <Card title="Composants">
      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {items.map((c) => (
          <li key={c.name} className="flex items-center justify-between rounded-lg bg-paper/60 px-3 py-2">
            <span className="font-semibold">{c.name}</span>
            <span className="flex items-center gap-2 text-sm text-ink/70">
              <span className={`h-3 w-3 rounded-full ${DOT[c.state][0]}`} />
              {DOT[c.state][1]}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

const axis = { stroke: "#261e48", fontSize: 12 };

export function TrafficChart({ data }) {
  return (
    <Card title="Disponibilité et trafic (15 min)">
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#a1a6d4" strokeOpacity={0.5} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axis} />
          <YAxis yAxisId="svc" domain={[0, 1]} ticks={[0, 1]} tickFormatter={(v) => (v ? "OK" : "KO")} {...axis} />
          <YAxis yAxisId="flux" orientation="right" {...axis} />
          <Tooltip labelFormatter={time} />
          <Legend />
          <Area yAxisId="svc" type="stepAfter" dataKey="service" name="service disponible" stroke="#15803d"
                fill="#15803d" fillOpacity={0.25} isAnimationActive={false} />
          <Line yAxisId="flux" type="monotone" dataKey="flux" name="requêtes / s" stroke="#261e48"
                dot={false} strokeWidth={2} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function SeriesChart({ title, data, keys, unit, domain, threshold }) {
  return (
    <Card title={title}>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#a1a6d4" strokeOpacity={0.5} />
          <XAxis dataKey="t" type="number" domain={["dataMin", "dataMax"]} tickFormatter={time} {...axis} />
          <YAxis domain={domain} unit={unit} {...axis} />
          <Tooltip labelFormatter={time} formatter={(v) => Number(v).toFixed(2)} />
          <Legend />
          {threshold != null && (
            <ReferenceLine y={threshold} stroke="#b91c1c" strokeDasharray="6 4" label="seuil de blocage" />
          )}
          {keys.map((k, i) => (
            <Line key={k} type="monotone" dataKey={k} stroke={PALETTE[i % PALETTE.length]} dot={false}
                  strokeWidth={2} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

const STEP = {
  detection: ["Détection", "bg-warn"],
  decision: ["Décision", "bg-lilac"],
  action: ["Action", "bg-info"],
  verification: ["Vérification", "bg-ok"],
  resolution: ["Clôture", "bg-ok"],
  escalation: ["Escalade", "bg-bad"],
};
const STATUS = {
  in_progress: ["en cours", "bg-info"],
  resolved: ["rétabli", "bg-ok"],
  observed: ["tracé", "bg-lilac"],
  failed: ["échec", "bg-bad"],
};

export function Incidents({ incidents }) {
  return (
    <Card title="Incidents et remédiation automatique">
      {!incidents.length && <p className="text-ink/60">Aucun incident depuis le démarrage du moteur.</p>}
      <ol className="space-y-4">
        {incidents.map((inc) => {
          const [label, color] = STATUS[inc.status] ?? ["—", "bg-lilac"];
          return (
            <li key={inc.id} className="rounded-xl bg-paper/60 p-4">
              <div className="mb-2 flex flex-wrap items-center gap-3">
                <span className="font-bold">#{inc.id} · {inc.alert}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-bold text-white ${color}`}>{label}</span>
                {inc.recovery_seconds != null && (
                  <span className="text-sm font-semibold text-ok">
                    coupure de {Math.round(inc.recovery_seconds)} s
                    {inc.remediation_seconds != null && ` · remédiation ${Math.round(inc.remediation_seconds)} s`}
                  </span>
                )}
              </div>
              <ol className="space-y-1 border-l-2 border-lilac pl-4">
                {inc.steps.map((s, i) => {
                  const [name, dot] = STEP[s.step] ?? [s.step, "bg-lilac"];
                  return (
                    <li key={i} className="relative text-sm">
                      <span className={`absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full ${dot}`} />
                      <span className="tabular-nums text-ink/60">{time(s.ts * 1000)}</span>{" "}
                      <span className="font-semibold">{name}</span> — {s.message}
                    </li>
                  );
                })}
              </ol>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
