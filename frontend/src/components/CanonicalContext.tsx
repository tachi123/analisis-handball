import type { CanonicalMatchState, ReviewedMetrics } from '../types'

type Reconciliation = { official: ReviewedMetrics['official']; reconciliation: ReviewedMetrics['reconciliation']; discipline: NonNullable<ReviewedMetrics['discipline']> }

export default function CanonicalContext({ state, metrics, reconciliation }: { state: CanonicalMatchState; metrics: ReviewedMetrics; reconciliation: Reconciliation }) {
  const eligibility = metrics.eligibility
  return <section className="card space-y-3" aria-label="Contexto canónico sin filtrar">
    <div><h2 className="font-semibold">Contexto canónico sin filtrar</h2><p className="text-sm text-gray-600">El estado, las métricas y la conciliación provienen del servidor para todo el partido. Los filtros de la línea de tiempo no los modifican.</p></div>
    <section><h3 className="font-medium">Cobertura y métricas canónicas</h3>{eligibility && <p className="mt-1 text-sm">Elegibles: {eligibility.eligible} · Excluidos: {eligibility.excluded} · Desconocidos: {eligibility.unknown} · No resueltos: {eligibility.unresolved} · Reloj no verificado: {eligibility.clock_unverified}</p>}<ul className="mt-2 grid gap-2 md:grid-cols-2">{Object.entries(metrics.metrics).map(([key, metric]) => <li key={key} className="rounded border p-2 text-sm"><b>{metric.name || key}</b><br />Conteo: {metric.count} · Numerador: {metric.numerator} · Denominador: {metric.denominator}</li>)}</ul></section>
    <section><h3 className="font-medium">Estado canónico</h3><dl className="mt-1 grid gap-1 text-sm"><div><dt className="inline font-medium">Marcador analítico: </dt><dd className="inline">{JSON.stringify(state.analytical_score)}</dd></div><div><dt className="inline font-medium">Posesión: </dt><dd className="inline">{state.possession ? JSON.stringify(state.possession) : 'sin posesión activa'}</dd></div><div><dt className="inline font-medium">Arqueros activos: </dt><dd className="inline">{JSON.stringify(state.active_goalkeepers)}</dd></div></dl></section>
    <section className="rounded border border-amber-200 bg-amber-50 p-2 text-sm"><h3 className="font-medium">Conciliación con planilla oficial</h3>{reconciliation.official ? <><p>Snapshot {reconciliation.official.snapshot_id}: {reconciliation.official.home_score} - {reconciliation.official.away_score}. La analítica no modifica la planilla.</p><ul>{reconciliation.reconciliation.map(item => <li key={item.side}>{item.side}: oficial {item.official} · analítico {item.analytical} · discrepancia {item.discrepancy}</li>)}</ul></> : <p>No hay snapshot oficial para conciliar.</p>}</section>
  </section>
}
