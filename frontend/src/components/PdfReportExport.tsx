import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCanonicalEvents, getCanonicalMetrics, getCanonicalPlayerProjection, getCanonicalReconciliation, getCanonicalState, getMatch, getWarningsSummary } from '../api/client'

export default function PdfReportExport({ matchId }: { matchId: number }) {
  const [goalkeeperId, setGoalkeeperId] = useState<number | null>(null)
  const enabled = Number.isInteger(matchId) && matchId > 0
  const match = useQuery({ queryKey: ['match', matchId], queryFn: () => getMatch(matchId), enabled, retry: false })
  const state = useQuery({ queryKey: ['canonical-state', matchId], queryFn: () => getCanonicalState(matchId), enabled, retry: false })
  const metrics = useQuery({ queryKey: ['canonical-metrics', matchId], queryFn: () => getCanonicalMetrics(matchId), enabled, retry: false })
  const reconciliation = useQuery({ queryKey: ['canonical-reconciliation', matchId], queryFn: () => getCanonicalReconciliation(matchId), enabled, retry: false })
  const warnings = useQuery({ queryKey: ['warnings-summary', matchId], queryFn: () => getWarningsSummary(matchId), enabled, retry: false })
  const events = useQuery({ queryKey: ['canonical-events', matchId], queryFn: () => getCanonicalEvents(matchId), enabled, retry: false })
  const goalkeeper = useQuery({ queryKey: ['canonical-player-projection', matchId, goalkeeperId], queryFn: () => getCanonicalPlayerProjection(matchId, { player_id: goalkeeperId! }), enabled: enabled && goalkeeperId !== null, retry: false })
  const required = [match, state, metrics, reconciliation, warnings, events]
  const requiredError = required.some(query => query.isError)
  const loading = required.some(query => query.isLoading) || (goalkeeperId !== null && goalkeeper.isLoading)
  const blocked = requiredError || loading || (goalkeeperId !== null && goalkeeper.isError)
  const goalkeepers = (match.data?.squad ?? []).filter(member => member.is_goalkeeper)
  const exportReport = async () => {
    if (blocked || !match.data || !state.data || !metrics.data || !reconciliation.data || !warnings.data || !events.data) return
    const { buildPdfReport } = await import('../pdf/reportPdf')
    buildPdfReport({ match: match.data, state: state.data, metrics: metrics.data, reconciliation: reconciliation.data, warnings: warnings.data, events: events.data, goalkeeper: goalkeeperId === null ? undefined : goalkeeper.data }).save()
  }
  return <section className="ml-auto space-y-1 text-right" aria-label="Exportar reporte PDF">
    <label className="block text-xs text-gray-600">Arquero opcional<select aria-label="Arquero opcional para PDF" className="ml-2 rounded border p-1" value={goalkeeperId ?? ''} onChange={event => setGoalkeeperId(event.target.value ? Number(event.target.value) : null)}><option value="">Sin arquero</option>{goalkeepers.map(member => <option key={member.player_id} value={member.player_id}>{member.player?.name ?? `Jugador ${member.player_id}`}</option>)}</select></label>
    <button type="button" className="btn btn-primary" disabled={blocked} onClick={() => void exportReport()}>{loading ? 'Preparando reporte…' : 'Exportar reporte PDF'}</button>
    {requiredError && <p role="alert" className="text-xs text-red-700">No se pudo cargar la información canónica requerida. Reintentá antes de exportar.</p>}
    {goalkeeperId !== null && goalkeeper.isError && <p role="alert" className="text-xs text-red-700">No se pudo cargar la proyección del arquero seleccionado.</p>}
  </section>
}
