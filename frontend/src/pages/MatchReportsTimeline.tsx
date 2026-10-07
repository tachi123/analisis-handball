import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { getAnalysisSession, getCanonicalEvents, getCanonicalMetrics, getCanonicalReconciliation, getCanonicalState, getMatch } from '../api/client'
import CanonicalContext from '../components/CanonicalContext'
import ReportEventTimeline from '../components/ReportEventTimeline'
import { useYouTubeSync } from '../hooks/useYouTubeSync'
import { emptyReportFilters, timelineRows, type ReportFilters } from '../reportTimeline'
import { seekTargetForEvent, videoAnchorSeconds } from '../timelineInteractions'
import { mapVideoTime } from '../videoReview'
import type { CanonicalEvent, VideoAvailabilityState } from '../types'

const unavailable = new Set<VideoAvailabilityState>(['unavailable', 'embedding_disabled', 'restricted', 'player_error'])
const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Error de red o validación'

export default function MatchReportsTimeline() {
  const { matchId } = useParams<{ matchId: string }>(); const id = Number(matchId); const navigate = useNavigate()
  const [filters, setFilters] = useState<ReportFilters>(emptyReportFilters); const [selected, setSelected] = useState<CanonicalEvent | null>(null); const [notice, setNotice] = useState('')
  const enabled = Number.isInteger(id) && id > 0
  const matchQuery = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id), enabled })
  const eventsQuery = useQuery({ queryKey: ['canonical-events', id], queryFn: () => getCanonicalEvents(id), enabled })
  const stateQuery = useQuery({ queryKey: ['canonical-state', id], queryFn: () => getCanonicalState(id), enabled })
  const metricsQuery = useQuery({ queryKey: ['canonical-metrics', id], queryFn: () => getCanonicalMetrics(id), enabled })
  const reconciliationQuery = useQuery({ queryKey: ['canonical-reconciliation', id], queryFn: () => getCanonicalReconciliation(id), enabled })
  const sessionQuery = useQuery({ queryKey: ['analysis-session', id], queryFn: () => getAnalysisSession(id), enabled, retry: false })
  const player = useYouTubeSync(sessionQuery.data?.source ?? null, sessionQuery.data?.video_position_seconds ?? 0)
  const rows = useMemo(() => timelineRows(eventsQuery.data ?? [], filters), [eventsQuery.data, filters])
  const playerLabels = useMemo(() => Object.fromEntries((matchQuery.data?.squad ?? []).flatMap(item => item.player ? [[item.player_id, `#${item.jersey_number} ${item.player.name}`]] : [])), [matchQuery.data]) as Record<number, string>
  const teamLabels = useMemo(() => ({ [matchQuery.data?.home_team?.id ?? -1]: matchQuery.data?.home_team?.name ?? 'Local', [matchQuery.data?.away_team?.id ?? -2]: matchQuery.data?.away_team?.name ?? 'Visitante' }), [matchQuery.data])
  const loading = matchQuery.isLoading || eventsQuery.isLoading || stateQuery.isLoading || metricsQuery.isLoading || reconciliationQuery.isLoading
  const selectEvent = (event: CanonicalEvent) => {
    setSelected(event)
    const target = seekTargetForEvent(event)
    if (target === null) { setNotice(`Evento #${event.sequence} seleccionado. No se movió el video: no tiene un ancla utilizable.`); return }
    if (player.availability !== 'ready') { setNotice(`Evento #${event.sequence} seleccionado. No se movió el video: el reproductor no está disponible.`); return }
    player.seekTo(target)
    const mapping = mapVideoTime(sessionQuery.data?.time_segments ?? [], event.payload.period, videoAnchorSeconds(event)!)
    setNotice(`Evento #${event.sequence} seleccionado. Video movido a ${target.toFixed(1)} s.${mapping.clockUnverified ? ' La cobertura de reloj no está verificada.' : ''}`)
  }
  if (!enabled) return <main className="p-4" role="alert">Identificador de partido inválido.</main>
  if (matchQuery.isLoading) return <main className="p-4">Cargando línea de tiempo…</main>
  if (matchQuery.isError || !matchQuery.data) return <main className="p-4 text-red-700" role="alert">No se pudo cargar el partido: {errorMessage(matchQuery.error)}</main>
  return <main className="min-h-screen bg-gray-50 p-4"><div className="mx-auto max-w-7xl space-y-3"><header className="flex flex-wrap items-center gap-2"><button className="btn" onClick={() => navigate('/matches')}>Volver</button><div><h1 className="text-xl font-semibold">Línea de tiempo: {matchQuery.data.home_team?.name ?? 'Local'} vs {matchQuery.data.away_team?.name ?? 'Visitante'}</h1><p className="text-sm text-gray-600">Vista de solo lectura de observaciones canónicas actuales.</p></div></header>
     {loading ? <p>Cargando contexto canónico…</p> : <>{eventsQuery.isError || stateQuery.isError || metricsQuery.isError || reconciliationQuery.isError ? <p role="alert" className="text-red-700">No se pudo cargar todo el contexto canónico.</p> : <><section className="card" aria-label="Video de referencia"><h2 className="font-semibold">Video de referencia</h2>{sessionQuery.data?.source && !unavailable.has(player.availability) ? <div ref={player.playerRef} className="mt-2 aspect-video w-full" title="Video del partido" /> : <p className="mt-1 text-sm text-gray-600">No hay reproducción disponible. La línea de tiempo y sus detalles siguen disponibles.</p>}</section><ReportEventTimeline rows={rows} filters={filters} allEvents={eventsQuery.data ?? []} selected={selected} playerLabels={playerLabels} teamLabels={teamLabels} notice={notice} onFiltersChange={setFilters} onSelect={selectEvent} /><CanonicalContext state={stateQuery.data!} metrics={metricsQuery.data!} reconciliation={reconciliationQuery.data!} /></>}</>}
  </div></main>
}
