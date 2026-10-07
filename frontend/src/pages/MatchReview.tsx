import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { createCanonicalEvent, deactivateCanonicalEvent, deactivateLastCanonicalEvent, enableCanonicalAnalysis, getAnalysisSession, getCanonicalEvents, getMatch, getOfficialSheet, resetCanonicalAnalysis, reviseCanonicalEvent, saveAnalysisSession } from '../api/client'
import EventTimeline from '../components/EventTimeline'
import EvidenceModal from '../components/EvidenceModal'
import IncidentWizard from '../components/IncidentWizard'
import { VideoSection } from './MatchReviewVideoSection'
import { MatchClock } from './MatchReviewMatchClock'
import { IncidentCapture } from './MatchReviewIncidentCapture'
import { Sidebar } from './MatchReviewSidebar'
import { useYouTubeSync } from '../hooks/useYouTubeSync'
import { dispatchReviewShortcut } from '../reviewShortcuts'
import { derivePlayableSegments, mapVideoTime } from '../videoReview'
import { closestEventId, videoAnchorSeconds } from '../timelineInteractions'
import type { AnalysisSession, AnalysisSessionUpdate, CanonicalEvent, CanonicalEventCommand, CanonicalEventRevisionInput, TimeAnchor, TimeSegment, VideoAvailabilityState } from '../types'

const unavailable = new Set<VideoAvailabilityState>(['unavailable', 'embedding_disabled', 'restricted', 'player_error'])
const message = (error: unknown) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : error instanceof Error ? error.message : 'Error de red o validación'
}
const isNotFound = (error: unknown) => (error as { response?: { status?: number } })?.response?.status === 404
const supportedYouTubeUrl = (value: string) => {
  try {
    const parsed = new URL(value)
    const host = parsed.hostname.toLowerCase().replace(/^www\./, '')
    if (!['youtube.com', 'youtu.be', 'youtube-nocookie.com'].includes(host)) return false
    const videoId = host === 'youtube.com' ? parsed.searchParams.get('v') : host === 'youtu.be' ? parsed.pathname.split('/').filter(Boolean)[0] : parsed.pathname.split('/').filter(Boolean)[1]
    return Boolean(videoId && /^[A-Za-z0-9_-]{6,}$/.test(videoId))
  } catch { return false }
}

export function checkpoint(session: AnalysisSession | undefined, patch: Partial<AnalysisSessionUpdate>): AnalysisSessionUpdate {
  return { mode: 'video' as const, profile: session?.profile ?? 'complete', source: session?.source ? { url: session.source.original_url, availability_state: session.source.availability_state } : null,
    video_position_seconds: session?.video_position_seconds ?? null, clock_start_video_seconds: session?.clock_start_video_seconds ?? null, angle: session?.angle ?? null, filters: session?.filters ?? {}, draft: session?.draft ?? {}, queue: session?.queue ?? [],
    anchors: (session?.anchors ?? []).map(anchor => ({ period: anchor.period, video_seconds: anchor.video_seconds, regulation_seconds: anchor.regulation_seconds, uncertainty_seconds: anchor.uncertainty_seconds })),
    time_segments: (session?.time_segments ?? []).map(segment => ({ period: segment.period, video_start_seconds: segment.video_start_seconds, video_end_seconds: segment.video_end_seconds, regulation_start_seconds: segment.regulation_start_seconds, regulation_end_seconds: segment.regulation_end_seconds, uncertainty_seconds: segment.uncertainty_seconds, coverage: segment.coverage, clock_unverified: segment.clock_unverified })), ...patch }
}

export function replaceVideoSource(session: AnalysisSession, url: string): AnalysisSessionUpdate {
  return checkpoint(session, {
    source: { url, availability_state: 'unknown' },
    video_position_seconds: null,
    clock_start_video_seconds: null,
    anchors: [],
    time_segments: [],
  })
}

export { message, supportedYouTubeUrl, isNotFound }

export function remapAnchoredEvents(events: CanonicalEvent[], segments: Array<Omit<TimeSegment, 'id'>>, periods: Set<number>): Array<{ id: number; input: CanonicalEventRevisionInput }> {
  return events.flatMap(event => {
    const videoSeconds = event.evidence?.find(item => item.kind === 'video')?.video_anchor_seconds
    if (!periods.has(event.payload.period) || videoSeconds === null || videoSeconds === undefined) return []
    const mapping = mapVideoTime(segments as TimeSegment[], event.payload.period, videoSeconds)
    if (event.payload.regulation_seconds === mapping.regulationSeconds && event.payload.clock_unverified === mapping.clockUnverified) return []
    const evidence = event.evidence?.map(({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty }) => ({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty })) ?? []
    return [{ id: event.id, input: { ...event.payload, regulation_seconds: mapping.regulationSeconds, clock_unverified: mapping.clockUnverified, evidence, reason: 'Recalibración de anclajes de video' } }]
  })
}

export default function MatchReview() {
  const { matchId } = useParams<{ matchId: string }>(); const id = Number(matchId); const navigate = useNavigate(); const client = useQueryClient()
  const [selected, setSelected] = useState<CanonicalEvent | null>(null); const [period, setPeriod] = useState(1); const [modal, setModal] = useState(false); const [focusNotes, setFocusNotes] = useState(false); const [anchorsOpen, setAnchorsOpen] = useState(false); const [helpOpen, setHelpOpen] = useState(false); const [notice, setNotice] = useState(''); const [sourceUrl, setSourceUrl] = useState(''); const [sourceError, setSourceError] = useState(''); const [teamId, setTeamId] = useState<number | null>(null); const [wizardOpen, setWizardOpen] = useState(false); const [recoveryAction, setRecoveryAction] = useState<'last' | 'reset' | null>(null)
  const matchQuery = useQuery({ queryKey: ['match', id], queryFn: () => getMatch(id), enabled: Number.isFinite(id) })
  const sessionQuery = useQuery({ queryKey: ['analysis-session', id], queryFn: () => getAnalysisSession(id), enabled: Number.isFinite(id), retry: false })
  const eventsQuery = useQuery({ queryKey: ['canonical-events', id], queryFn: () => getCanonicalEvents(id), enabled: Number.isFinite(id) && matchQuery.data?.canonical_analysis_enabled === true, retry: false })
  const officialQuery = useQuery({ queryKey: ['official-sheet', id], queryFn: () => getOfficialSheet(id), enabled: Number.isFinite(id), retry: false })
  const session = sessionQuery.data
  useEffect(() => { if (session?.source) setSourceUrl(session.source.original_url) }, [session?.source])
  const player = useYouTubeSync(session?.source ?? null, session?.video_position_seconds ?? 0)
  const highlightedId = useMemo(() => closestEventId(eventsQuery.data ?? [], player.currentTime), [eventsQuery.data, player.currentTime])
  const saveSession = useMutation({ mutationFn: (data: ReturnType<typeof checkpoint>) => saveAnalysisSession(id, data), onSuccess: saved => { client.setQueryData(['analysis-session', id], saved); setNotice('Sesión guardada.') } })
  const enable = useMutation({
    mutationFn: async () => {
      await enableCanonicalAnalysis(id)
      try {
        return await getAnalysisSession(id)
      } catch (error) {
        if (!isNotFound(error)) throw error
        return saveAnalysisSession(id, checkpoint(undefined, { source: null }))
      }
    },
    onSuccess: async () => {
      await Promise.all([client.invalidateQueries({ queryKey: ['match', id] }), client.invalidateQueries({ queryKey: ['analysis-session', id] }), client.invalidateQueries({ queryKey: ['canonical-events', id] })])
      setNotice('Análisis iniciado. Prepará el video y registrá el saque inicial.')
    },
    onError: error => setNotice(`No se pudo iniciar el análisis: ${message(error)}`),
  })
  const revise = useMutation({ mutationFn: (data: Parameters<typeof reviseCanonicalEvent>[1]) => reviseCanonicalEvent(selected!.id, data), onSuccess: saved => { client.invalidateQueries({ queryKey: ['canonical-events', id] }); setSelected(saved); setModal(false); setNotice('Revisión guardada.') } })
  const mark = useMutation({ mutationFn: (data: CanonicalEventCommand) => createCanonicalEvent(id, data), onSuccess: saved => { client.invalidateQueries({ queryKey: ['canonical-events', id] }); setSelected(saved); setNotice('Incidente marcado en la posición actual.') } })
  const kickoff = useMutation({
    mutationFn: async () => {
      const source = session?.source
      const validTeamIds = [matchQuery.data?.home_team?.id, matchQuery.data?.away_team?.id]
      if (!source || teamId === null || !validTeamIds.includes(teamId)) throw new Error('Seleccioná un equipo válido del partido para el saque inicial.')
      const anchor = await player.pauseAndReadCurrentTime()
      return createCanonicalEvent(id, {
        kind: 'other', period, regulation_seconds: null, clock_unverified: true, team_id: teamId,
        player_id: null, related_player_id: null, outcome: 'kickoff', fact_kind: 'observed', evidence_state: 'confirmed',
        uncertainty: ['clock_unverified'], note: null,
        evidence: [{ kind: 'video', reference: source.original_url, video_source_id: source.id, video_anchor_seconds: anchor, uncertainty: [] }],
      })
    },
    onSuccess: saved => {
      client.invalidateQueries({ queryKey: ['canonical-events', id] })
      setSelected(saved)
      setNotice('Saque inicial y posesión registrados. Declaralo como 00:00 para habilitar incidencias.')
    },
  })
  const anchorSave = useMutation({
    mutationFn: async (anchors: Array<Omit<TimeAnchor, 'id'>>) => {
      const segments = derivePlayableSegments(anchors.map((anchor, index) => ({ ...anchor, id: index })))
      const saved = await saveAnalysisSession(id, checkpoint(session, { anchors, time_segments: segments }))
      const revisions = remapAnchoredEvents(eventsQuery.data ?? [], segments, new Set(anchors.map(anchor => anchor.period)))
      await Promise.all(revisions.map(revision => reviseCanonicalEvent(revision.id, revision.input)))
      return { saved, revisions: revisions.length }
    },
    onSuccess: async ({ saved, revisions }) => {
      client.setQueryData(['analysis-session', id], saved)
      await client.invalidateQueries({ queryKey: ['canonical-events', id] })
      setNotice(revisions ? 'Anclajes guardados y eventos con video recalibrados.' : 'Anclajes guardados.')
    },
  })

  const deleteEvent = useMutation({
    mutationFn: (eventId: number) => deactivateCanonicalEvent(eventId, 'Eliminado por el analista'),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['canonical-events', id] })
      if (selected) setSelected(null)
      setModal(false)
      setNotice('Incidente eliminado.')
    },
    onError: (error) => setNotice(`No se pudo eliminar: ${message(error)}`),
  })

  const deleteLast = useMutation({ mutationFn: () => deactivateLastCanonicalEvent(id, 'Eliminación de la última incidencia por el analista'), onSuccess: () => { client.invalidateQueries({ queryKey: ['canonical-events', id] }); setSelected(null); setRecoveryAction(null); setNotice('Última incidencia eliminada. No existe restauración.') }, onError: error => setNotice(`No se pudo eliminar la última incidencia: ${message(error)}`) })
  const resetReview = useMutation({ mutationFn: () => resetCanonicalAnalysis(id, 'Reinicio completo solicitado por el analista'), onSuccess: async result => { await Promise.all([client.invalidateQueries({ queryKey: ['canonical-events', id] }), client.invalidateQueries({ queryKey: ['analysis-session', id] })]); setSelected(null); setRecoveryAction(null); setNotice(`Análisis reiniciado: ${result.deactivated_events} incidencias quedaron desactivadas de forma auditable.`) }, onError: error => setNotice(`No se pudo reiniciar el análisis: ${message(error)}`) })
  
  const selectEvent = (event: CanonicalEvent) => {
    setSelected(event)
    setPeriod(event.payload.period)
    const target = videoAnchorSeconds(event)
    if (target === null) setNotice('Evidencia de video no disponible para este incidente.')
    else {
      player.pause()
      player.seekTo(target)
      setNotice(`Video ubicado en ${target.toFixed(1)} s para la incidencia #${event.sequence}.`)
    }
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => dispatchReviewShortcut(event, { togglePlayback: () => player.isPlaying ? player.pause() : player.play(), seek: delta => player.seekTo(player.currentTime + delta), navigateEvents: direction => { const events = eventsQuery.data ?? []; const index = selected ? events.findIndex(item => item.id === selected.id) : -1; const next = events[index + direction] ?? events[direction > 0 ? 0 : events.length - 1]; if (next) selectEvent(next) }, addAnchor: () => setAnchorsOpen(open => !open), tag: () => selected && setModal(true), save: () => session && saveSession.mutate(checkpoint(session, { video_position_seconds: player.currentTime })), focusNotes: () => { if (selected) { setFocusNotes(true); setModal(true) } }, undo: () => setNotice('Deshacer no está disponible: el contrato canónico no expone restauración.'), redo: () => setNotice('Rehacer no está disponible: el contrato canónico no expone restauración.'), showHelp: () => setHelpOpen(true) })
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey)
  })

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setHelpOpen(false)
      setFocusNotes(false)
      setModal(false)
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])

  useEffect(() => {
    if (!session?.source || !unavailable.has(player.availability) || player.availability === session.source.availability_state || saveSession.isPending) return
    saveSession.mutate(checkpoint(session, { source: { url: session.source.original_url, availability_state: player.availability } }))
  }, [player.availability, saveSession, session])

  const handleWizardSubmit = (command: CanonicalEventCommand) => {
    mark.mutate(command)
    setWizardOpen(false)
  }

  const needsSetup = !session && !sessionQuery.isLoading && (!sessionQuery.isError || isNotFound(sessionQuery.error))
  const canonicalEnabled = matchQuery.data?.canonical_analysis_enabled === true
  const playerUnavailable = !session?.source || unavailable.has(player.availability)
  
  const profile = (session?.profile ?? 'complete') as 'complete' | 'classic' | 'goalkeepers'
  const profileLabel = { complete: 'Completo', classic: 'Clásico', goalkeepers: 'Arqueros' }[profile]
  const activeSourceId = session?.source?.id
  const pendingKickoffs = useMemo(() => (eventsQuery.data ?? []).filter(event =>
    event.active && event.payload.kind === 'other' && event.payload.outcome === 'kickoff' &&
    event.payload.period === period &&
    event.payload.regulation_seconds === null && event.payload.clock_unverified &&
    activeSourceId !== undefined && event.evidence?.some(item => item.kind === 'video' && item.video_source_id === activeSourceId && item.video_anchor_seconds !== null && item.video_anchor_seconds !== undefined),
  ), [activeSourceId, eventsQuery.data, period])
  const [selectedPendingKickoffId, setSelectedPendingKickoffId] = useState<number | null>(null)
  const pendingKickoff = pendingKickoffs.length === 1
    ? pendingKickoffs[0]
    : pendingKickoffs.find(event => event.id === selectedPendingKickoffId) ?? null
  const hasCalibratedKickoff = useMemo(() => (eventsQuery.data ?? []).some(event =>
    event.active && event.payload.kind === 'other' && event.payload.outcome === 'kickoff' &&
    event.payload.period === period && event.payload.regulation_seconds === 0 && !event.payload.clock_unverified &&
    activeSourceId !== undefined && event.evidence?.some(item => item.kind === 'video' && item.video_source_id === activeSourceId),
  ), [activeSourceId, eventsQuery.data, period])
  const hasValidClockStart = hasCalibratedKickoff && session?.clock_start_video_seconds !== null && session?.clock_start_video_seconds !== undefined
  const ownActiveEvents = (eventsQuery.data ?? []).filter(event => event.active && event.actor_id === session?.analyst_id)
  const lastActiveEvent = [...(eventsQuery.data ?? [])].filter(event => event.active).sort((left, right) => right.sequence - left.sequence)[0]
  const canDeleteLast = Boolean(lastActiveEvent && lastActiveEvent.actor_id === session?.analyst_id)
  const calibrateKickoff = useMutation({
    mutationFn: async (event: CanonicalEvent) => {
      const source = session?.source
      if (!source) throw new Error('No se encontró una fuente de video para la sesión de revisión.')
      const evidence = event.evidence ?? []
      const videoEvidence = evidence.find(item => item.kind === 'video' && item.video_source_id === source.id && item.video_anchor_seconds !== null && item.video_anchor_seconds !== undefined)
      if (!videoEvidence || videoEvidence.video_anchor_seconds === null || videoEvidence.video_anchor_seconds === undefined) throw new Error('El saque inicial no tiene un ancla de video válida.')
      const savedSession = await saveAnalysisSession(id, checkpoint(session, { clock_start_video_seconds: videoEvidence.video_anchor_seconds }))
      const revised = await reviseCanonicalEvent(event.id, {
        ...event.payload, regulation_seconds: 0, clock_unverified: false,
        evidence: evidence.map(({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty }) => ({ kind, reference, scheduled_match_id, official_snapshot_id, video_source_id, video_anchor_seconds, uncertainty })),
        reason: 'Calibración: saque inicial declarado como 00:00 oficial',
      })
      return { savedSession, revised }
    },
    onSuccess: async ({ savedSession, revised }) => {
      client.setQueryData(['analysis-session', id], savedSession)
      await Promise.all([client.invalidateQueries({ queryKey: ['analysis-session', id] }), client.invalidateQueries({ queryKey: ['canonical-events', id] })])
      setSelected(revised)
      setNotice('Saque inicial calibrado como 00:00. Ya podés registrar incidencias.')
    },
  })
  const currentVideoTime = player.currentTime
  const officialHomePlayers = useMemo(() => officialQuery.data?.home.players.map(p => ({
    key: `home-${p.jersey_number}-${p.name}`,
    jersey: p.jersey_number,
    name: p.name,
    side: 'home' as const,
    playerId: p.player_id,
  })) ?? [], [officialQuery.data])
  const officialAwayPlayers = useMemo(() => officialQuery.data?.away.players.map(p => ({
    key: `away-${p.jersey_number}-${p.name}`,
    jersey: p.jersey_number,
    name: p.name,
    side: 'away' as const,
    playerId: p.player_id,
  })) ?? [], [officialQuery.data])
  const anchoredMap = mapVideoTime(session?.time_segments ?? [], period, player.currentTime)
  const clockStart = session?.clock_start_video_seconds
  const baselineClock = hasValidClockStart && clockStart !== null && clockStart !== undefined
    ? Math.max(0, Math.round(player.currentTime - clockStart)) : null
  const map = !anchoredMap.clockUnverified
    ? anchoredMap
    : baselineClock !== null
      ? { regulationSeconds: baselineClock, uncertaintySeconds: 0, clockUnverified: false }
      : anchoredMap

  if (matchQuery.isLoading) return <div className="p-4">Cargando espacio de revisión…</div>
   if (matchQuery.isError || !matchQuery.data) return <div role="alert" className="p-4 text-red-700">No se pudo cargar el partido: {message(matchQuery.error)}</div>
   if (!canonicalEnabled) return <main className="min-h-screen bg-gray-50 p-3"><header className="mx-auto flex max-w-3xl items-center gap-2"><button className="btn" onClick={() => navigate('/matches')}>Volver</button><h1 className="text-lg font-semibold">Revisión: {matchQuery.data.home_team?.name ?? 'Local'} vs {matchQuery.data.away_team?.name ?? 'Visitante'}</h1></header><section className="card mx-auto mt-4 max-w-3xl space-y-3"><h2 className="font-semibold">Análisis canónico todavía no iniciado</h2>{officialQuery.isLoading ? <p className="text-sm">Verificando la planilla oficial…</p> : officialQuery.data ? <><p className="text-sm">La planilla oficial está confirmada. Podés iniciar el análisis para crear o retomar tu sesión de revisión.</p><button className="btn btn-primary" disabled={enable.isPending} onClick={() => enable.mutate()}>{enable.isPending ? 'Iniciando análisis…' : 'Iniciar análisis'}</button></> : officialQuery.isError && !isNotFound(officialQuery.error) ? <section role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-700"><h3 className="font-semibold">No se pudo verificar la planilla oficial</h3><p className="mt-1 text-sm">{message(officialQuery.error)}</p><button className="btn mt-3" onClick={() => officialQuery.refetch()}>Reintentar verificar planilla</button></section> : <p className="text-sm text-amber-900">Esta revisión es de solo lectura hasta que se confirme la planilla oficial del partido. No se puede iniciar ni registrar incidencias todavía.</p>}{notice && <p role="status" className="text-sm">{notice}</p>}</section></main>
  
  return (
    <main className="min-h-screen bg-gray-50 p-3">
      <header className="mx-auto flex max-w-7xl flex-wrap items-center gap-2">
        <button className="btn" onClick={() => navigate('/matches')}>Volver</button>
        <h1 className="flex-1 text-lg font-semibold">Revisión: {matchQuery.data?.home_team?.name ?? 'Local'} vs {matchQuery.data?.away_team?.name ?? 'Visitante'}</h1>
        <span className="rounded bg-indigo-100 px-2 py-1 text-sm text-indigo-950">Perfil: {profileLabel}</span>
        <label>Período <select className="review-target" value={period} onChange={e => { const next = Number(e.target.value); setPeriod(next); const anchor = session?.anchors?.find((item: any) => item.period === next); if (anchor) player.seekTo(anchor.video_seconds) }}><option value={1}>1</option><option value={2}>2</option><option value={3}>Prórroga 1</option><option value={4}>Prórroga 2</option></select></label>
      </header>
      <p className="mx-auto mt-2 max-w-7xl text-sm" aria-live="polite">{notice}</p>
      {helpOpen && <div className="fixed inset-0 z-30 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Ayuda de atajos"><section className="w-full max-w-md space-y-3 rounded bg-white p-4 shadow-xl"><div className="flex items-center justify-between"><h2 className="font-semibold">Atajos de revisión</h2><button className="review-target" onClick={() => setHelpOpen(false)} aria-label="Cerrar ayuda">×</button></div><p className="text-sm">Espacio: reproducir; ,/. y j/l/[ ]: buscar; n/p: eventos; a: calibración; t: revisar; Shift+n: motivo; s: guardar.</p></section></div>}
      {(sessionQuery.isError && !needsSetup) && <section role="alert" className="card mx-auto mt-3 max-w-7xl text-red-700"><h2 className="font-semibold">No se pudo cargar la sesión de revisión</h2><p className="mt-1 text-sm">{message(sessionQuery.error)}</p><button className="btn mt-3" onClick={() => sessionQuery.refetch()}>Reintentar cargar sesión</button></section>}
      {needsSetup && <section className="card mx-auto mt-3 max-w-7xl"><h2 className="font-semibold">Preparar revisión</h2><p className="text-sm">Guardá una URL de YouTube para revisar video, o continuá sin reproducción. Se aceptan enlaces de youtube.com, youtu.be y youtube-nocookie.com.</p><label className="mt-2 block text-sm">URL de YouTube<input className="review-target mt-1 w-full rounded border p-2" value={sourceUrl} onChange={event => { setSourceUrl(event.target.value); setSourceError('') }} placeholder="https://youtu.be/..." /></label>{sourceError && <p role="alert" className="mt-2 text-sm text-red-700">{sourceError}</p>}{saveSession.isError && <p role="alert" className="mt-2 text-sm text-red-700">No se pudo guardar la fuente: {message(saveSession.error)}</p>}<div className="mt-2 flex flex-wrap gap-2"><button className="btn btn-primary" disabled={saveSession.isPending} onClick={() => { const url = sourceUrl.trim(); if (!url) { setSourceError('Ingresá una URL de YouTube o continuá sin video.'); return } if (!supportedYouTubeUrl(url)) { setSourceError('Usá una URL válida de YouTube con un identificador de video.'); return } saveSession.mutate(checkpoint(undefined, { source: { url, availability_state: 'unknown' } })) }}>Guardar video y crear sesión</button><button className="btn" disabled={saveSession.isPending} onClick={() => saveSession.mutate(checkpoint(undefined, { source: null }))}>Continuar sin video</button></div></section>}
      {session && (
        <div className="mx-auto mt-3 grid max-w-7xl gap-3 lg:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-3">
            <section className="card">
              <h2 className="font-semibold">Video</h2>
              <VideoSection 
                session={session} 
                player={player} 
                playerUnavailable={playerUnavailable} 
                saveSession={saveSession} 
                sessionQuery={sessionQuery} 
                sourceUrl={sourceUrl} 
                setSourceUrl={setSourceUrl} 
                setSourceError={setSourceError} 
                sourceError={sourceError} 
                supportedYouTubeUrl={supportedYouTubeUrl} 
                saveSessionPending={saveSession.isPending} 
                setNotice={setNotice} 
              />
              {session.source && <MatchClock 
                session={session} 
                baselineClock={baselineClock} 
                map={map} 
                anchoredMap={anchoredMap} 
                currentVideoTime={currentVideoTime} 
                saveSessionPending={saveSession.isPending} 
              />}
              <IncidentCapture 
                matchQuery={matchQuery} 
                teamId={teamId} 
                setTeamId={setTeamId} 
                 hasValidClockStart={hasValidClockStart} 
                 pendingKickoff={pendingKickoff}
                 pendingKickoffs={pendingKickoffs}
                 selectPendingKickoff={setSelectedPendingKickoffId}
                videoReady={Boolean(session.source) && player.availability === 'ready'}
                mark={mark} 
                recordKickoff={() => kickoff.mutate()}
                recordingKickoff={kickoff.isPending}
                calibrateKickoff={() => pendingKickoff && calibrateKickoff.mutate(pendingKickoff)}
                calibratingKickoff={calibrateKickoff.isPending}
                wizardOpen={wizardOpen} 
                setWizardOpen={setWizardOpen} 
                profileLabel={profileLabel} 
                 canMark={hasCalibratedKickoff} 
              />
               {eventsQuery.isError ? <section role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-700"><h2 className="font-semibold">No se pudieron cargar los eventos canónicos</h2><p className="mt-1 text-sm">{message(eventsQuery.error)}</p><button className="btn mt-3" onClick={() => eventsQuery.refetch()}>Reintentar cargar eventos</button></section> : <EventTimeline 
                 events={eventsQuery.data ?? []} 
                selectedId={selected?.id ?? null} 
                highlightedId={highlightedId} 
                 onSelect={selectEvent} 
                 onViewVideo={selectEvent}
                onRevise={event => { setSelected(event); setModal(true) }} 
                onDelete={event => deleteEvent.mutate(event.id)} 
                  teamLabels={{ [matchQuery.data.home_team?.id ?? -1]: matchQuery.data.home_team?.name ?? 'Local', [matchQuery.data.away_team?.id ?? -2]: matchQuery.data.away_team?.name ?? 'Visitante' }}
                  playerLabels={Object.fromEntries([...officialHomePlayers, ...officialAwayPlayers].filter(player => player.playerId !== null).map(player => [player.playerId!, player.name]))}
                 activeOnly={false} 
               />}
               <section className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm"><h2 className="font-semibold">Recuperar mi análisis</h2><p className="mt-1">Estas acciones no eliminan el partido, la planilla ni las fuentes de video. Las incidencias quedan desactivadas con un motivo auditable y no se pueden restaurar desde esta pantalla.</p>{lastActiveEvent && !canDeleteLast && <p className="mt-2 text-amber-900">La última incidencia activa fue registrada por otra persona. Solo su analista puede eliminarla.</p>}<div className="mt-2 flex flex-wrap gap-2"><button className="btn" disabled={!canDeleteLast || deleteLast.isPending} onClick={() => setRecoveryAction('last')}>Eliminar última incidencia</button><button className="btn text-red-700" disabled={resetReview.isPending} onClick={() => setRecoveryAction('reset')}>Reiniciar mi análisis</button></div></section>
            </section>
            <Sidebar 
              officialQuery={officialQuery} 
              session={session} 
              draft={session.draft} 
              queue={session.queue} 
              anchorsOpen={anchorsOpen} 
              setAnchorsOpen={setAnchorsOpen} 
              anchorSave={anchorSave} 
              sessionId={id} 
            />
          </div>
        </div>
      )}
      {modal && selected && <EvidenceModal event={selected} source={session?.source ?? null} currentTime={player.currentTime} playable={!playerUnavailable} clockUnverified={(() => { const time = videoAnchorSeconds(selected); return time === null ? selected.payload.clock_unverified : mapVideoTime(session?.time_segments ?? [], selected.payload.period, time).clockUnverified })()} teams={matchQuery.data.home_team && matchQuery.data.away_team ? { home: matchQuery.data.home_team, away: matchQuery.data.away_team } : null} players={[...officialHomePlayers, ...officialAwayPlayers]} focusNotes={focusNotes} saving={revise.isPending} error={revise.isError ? message(revise.error) : undefined} onSave={data => revise.mutate(data)} onClose={() => { setFocusNotes(false); setModal(false) }} />}
      {wizardOpen && <IncidentWizard
        isOpen={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onSubmit={handleWizardSubmit}
        submitting={mark.isPending}
        period={period}
        regulationSeconds={map.regulationSeconds}
        clockUnverified={map.clockUnverified}
        teamId={teamId}
        homeTeam={{ id: matchQuery.data?.home_team?.id ?? 0, name: matchQuery.data?.home_team?.name ?? 'Local' }}
        awayTeam={{ id: matchQuery.data?.away_team?.id ?? 0, name: matchQuery.data?.away_team?.name ?? 'Visitante' }}
        officialHomePlayers={officialHomePlayers}
        officialAwayPlayers={officialAwayPlayers}
        hasVideo={!playerUnavailable}
        currentVideoTime={currentVideoTime}
        videoSourceId={session?.source?.id ?? null}
        videoUrl={session?.source?.original_url ?? null}
      />}
      {recoveryAction && <div className="fixed inset-0 z-30 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Confirmar recuperación"><section className="w-full max-w-md space-y-3 rounded bg-white p-4 shadow-xl"><h2 className="font-semibold">{recoveryAction === 'last' ? 'Eliminar última incidencia' : 'Reiniciar mi análisis'}</h2>{recoveryAction === 'last' ? <p className="text-sm">Se desactivará la incidencia activa #{lastActiveEvent?.sequence ?? 'sin dato'}. Solo se permite si es tuya y no deja eventos dependientes sin saque inicial calibrado. Esta acción no tiene restauración.</p> : <p className="text-sm">Se desactivarán {ownActiveEvents.length} incidencias activas de tu análisis. Se reiniciarán video, posición, reloj, ángulo, filtros, borrador, cola, anclajes y segmentos. Las fuentes históricas de video se conservan. Esta acción no tiene restauración.</p>}<div className="flex gap-2"><button className="btn" onClick={() => setRecoveryAction(null)}>Cancelar</button><button className="btn btn-primary" disabled={deleteLast.isPending || resetReview.isPending} onClick={() => recoveryAction === 'last' ? deleteLast.mutate() : resetReview.mutate()}>Confirmar</button></div></section></div>}
    </main>
  )
}
