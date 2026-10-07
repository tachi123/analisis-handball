import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { getAnalysisSession, getCanonicalPlayerProjection, getMatch } from '../api/client'
import ShotZoneHeatmap from '../components/ShotZoneHeatmap'
import { useYouTubeSync } from '../hooks/useYouTubeSync'
import { seekTargetForEvent, videoAnchorSeconds } from '../timelineInteractions'
import { mapVideoTime } from '../videoReview'
import type { CanonicalEvent, VideoAvailabilityState } from '../types'

const unavailable = new Set<VideoAvailabilityState>(['unavailable', 'embedding_disabled', 'restricted', 'player_error'])

export default function GoalkeeperPanel() {
  const { matchId } = useParams<{ matchId: string }>(); const id = Number(matchId); const navigate = useNavigate()
  const [playerId, setPlayerId] = useState<number | null>(null); const [period, setPeriod] = useState<number | undefined>(); const [from, setFrom] = useState<number | undefined>(); const [to, setTo] = useState<number | undefined>(); const [notice, setNotice] = useState('')
  const enabled = Number.isInteger(id) && id > 0
  const matchQuery = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id), enabled })
  const goalkeepers = useMemo(() => (matchQuery.data?.squad ?? []).filter(item => item.is_goalkeeper), [matchQuery.data])
  const selectedId = playerId ?? goalkeepers[0]?.player_id
  const projectionQuery = useQuery({ queryKey: ['canonical-player-projection', id, selectedId, period, from, to], queryFn: () => getCanonicalPlayerProjection(id, { player_id: selectedId!, period, from_regulation_seconds: from, to_regulation_seconds: to }), enabled: enabled && !!selectedId })
  const sessionQuery = useQuery({ queryKey: ['analysis-session', id], queryFn: () => getAnalysisSession(id), enabled, retry: false })
  const player = useYouTubeSync(sessionQuery.data?.source ?? null, sessionQuery.data?.video_position_seconds ?? 0)
  const projection = projectionQuery.data
  const selectEvidence = (event: CanonicalEvent) => {
    const target = seekTargetForEvent(event)
    if (target === null || player.availability !== 'ready') { setNotice('La evidencia fue seleccionada, pero no hay ancla de video reproducible.'); return }
    player.seekTo(target)
    const mapping = mapVideoTime(sessionQuery.data?.time_segments ?? [], event.payload.period, videoAnchorSeconds(event)!)
    setNotice(`Video movido a ${target.toFixed(1)} s.${mapping.clockUnverified ? ' El reloj no está verificado.' : ''}`)
  }
  if (!enabled) return <main className="p-4" role="alert">Identificador de partido inválido.</main>
  if (matchQuery.isLoading) return <main className="p-4">Cargando panel de arqueros…</main>
  if (!matchQuery.data) return <main className="p-4" role="alert">No se pudo cargar el partido.</main>
  return <main className="min-h-screen bg-gray-50 p-4"><div className="mx-auto max-w-6xl space-y-3"><header className="flex flex-wrap items-center gap-2"><button className="btn" onClick={() => navigate('/matches')}>Volver</button><div><h1 className="text-xl font-semibold">Panel de arqueros</h1><p className="text-sm text-gray-600">Vista canónica derivada por servidor; la participación es evidencia observada, no minutos ni titularidad.</p></div></header>
    {goalkeepers.length === 0 ? <p className="card">No hay arqueros elegibles en la planilla del partido.</p> : <><section className="card grid gap-2 sm:grid-cols-4"><label>Arquero<select aria-label="Seleccionar arquero" className="mt-1 w-full rounded border p-2" value={selectedId ?? ''} onChange={event => setPlayerId(Number(event.target.value))}>{goalkeepers.map(item => <option key={item.player_id} value={item.player_id}>{item.player?.name ?? `Jugador ${item.player_id}`}</option>)}</select></label><label>Período<select aria-label="Filtrar período" className="mt-1 w-full rounded border p-2" value={period ?? ''} onChange={event => setPeriod(event.target.value ? Number(event.target.value) : undefined)}><option value="">Todos</option><option value="1">1</option><option value="2">2</option></select></label><label>Desde (s)<input aria-label="Desde segundos" type="number" min="0" className="mt-1 w-full rounded border p-2" value={from ?? ''} onChange={event => setFrom(event.target.value ? Number(event.target.value) : undefined)} /></label><label>Hasta (s)<input aria-label="Hasta segundos" type="number" min="0" className="mt-1 w-full rounded border p-2" value={to ?? ''} onChange={event => setTo(event.target.value ? Number(event.target.value) : undefined)} /></label></section>
      {projectionQuery.isLoading ? <p>Cargando proyección…</p> : projectionQuery.isError ? <p role="alert">No se pudo cargar la proyección canónica.</p> : projection && <><section className="grid gap-3 sm:grid-cols-3"><article className="card"><h2 className="font-medium">Atajadas</h2><p className="text-3xl">{projection.metrics.saves}</p></article><article className="card"><h2 className="font-medium">Goles recibidos</h2><p className="text-3xl">{projection.metrics.goals_conceded}</p></article><article className="card"><h2 className="font-medium">Tasa observada</h2><p className="text-3xl">{projection.metrics.save_rate ? `${Math.round(projection.metrics.save_rate.value * 100)}%` : 'Sin base'}</p></article></section>
        <section className="card"><h2 className="font-semibold">Participación y disciplina observadas</h2><p className="text-sm">Ingresos: {projection.participation.on}; salidas: {projection.participation.off}; sustituciones: {projection.participation.substitution}. No se infieren minutos, titularidad ni presencia completa.</p><p className="text-sm">Disciplina: amarillas {projection.discipline.yellow}, dos minutos {projection.discipline.two_minute}, rojas {projection.discipline.red}.</p></section>
        <ShotZoneHeatmap zones={projection.shot_map.zones} coverage={projection.shot_map} />
        <section className="card"><h2 className="font-semibold">Cobertura y atribución</h2><p className="text-sm">Los eventos con reloj sin verificar ({projection.shot_map.clock_unverified}) están separados de la ventana precisa. Los tiros sin arquero activo observado ({projection.shot_map.goalkeeper_unknown}) no se atribuyen a este arquero.</p></section>
        <section className="card"><h2 className="font-semibold">Video y evidencia</h2>{sessionQuery.data?.source && !unavailable.has(player.availability) ? <div ref={player.playerRef} title="Video del partido" className="mt-2 aspect-video w-full" /> : <p className="text-sm text-gray-600">No hay reproducción disponible; la evidencia sigue siendo auditable.</p>}<p aria-live="polite" className="text-sm">{notice}</p><ol className="mt-2 space-y-2">{projection.evidence.map((event, index) => <li key={`${event.id}-${event.revision}-${event.bucket ?? 'selected'}-${index}`}><button className="w-full rounded border p-2 text-left" onClick={() => selectEvidence(event)}><b>Evento #{event.sequence}</b> · {event.payload.kind}{event.bucket ? ` · ${event.bucket}` : ''}<span className="block text-xs">Evento {event.id}; revisión {event.revision}; evidencia {event.evidence?.map(item => item.id).join(', ') || 'sin ID'}</span></button></li>)}</ol></section>
        <section className="card"><h2 className="font-semibold">Contexto del partido sin filtros</h2><p className="text-sm">Métricas canónicas y reconciliación oficial se muestran como referencia no filtrada: {Object.keys(projection.unfiltered_context.canonical_metrics.metrics).length} métricas; {projection.unfiltered_context.reconciliation.discrepancies.length} diferencias de marcador.</p></section>
      </>}</>}</div></main>
}
