import { useEffect, useRef, useState, useMemo, startTransition } from 'react'
import { decodePublicReportCatalog, reportFileName, reportLabel, type PublicReportCatalog } from './catalog'
import { decodePublicReport, type PlayerPublic, type PublicReport } from './projection'
import { Timeline } from './Timeline'

const n = (value: unknown) => typeof value === 'number' ? value : 0
const pct = (numerator: number, denominator: number) => denominator ? `${Math.round((numerator / denominator) * 100)}%` : '—'
const VIDEO_PREROLL_SECONDS = 3
const playerLabel = (player: PlayerPublic) => `${player.name}${player.jersey_number ? ` · #${player.jersey_number}` : ''}`
const goalkeeperSplit = (player: PlayerPublic, suffix: '7m' | 'counterattack', label: string) => {
  const faced = n(player.metrics[`shots_faced_${suffix}`])
  if (!faced) return null
  const saves = n(player.metrics[`saves_${suffix}`])
  return <span>{label}: {saves}/{faced} · {pct(saves, faced)}</span>
}

function Comparison({ label, home, away, suffix = '' }: { label: string; home: number; away: number; suffix?: string }) {
  const max = Math.max(home, away, 1)
  return <article className="pyramid-row"><strong className="pyramid-value home-value">{home}{suffix}</strong><i className="pyramid-bar home-bar" style={{ width: `${home / max * 100}%` }} /><span>{label}</span><i className="pyramid-bar away-bar" style={{ width: `${away / max * 100}%` }} /><strong className="pyramid-value away-value">{away}{suffix}</strong></article>
}

function TeamDashboard({ report }: { report: PublicReport }) {
  const summary = report.team_summary
  if (!summary?.home || !summary.away) return null
  const { home, away } = summary
  return <section className="dashboard-section">
  <div className="section-heading">
    <div>
      <p className="eyebrow">Panorama</p>
      <h2>Comparativa de equipos</h2>
      <small>{home.name} ← comparación → {away.name}</small>
    </div>
  </div>
  <div className="pyramid-chart">
    <Comparison label="Goles" home={home.goals} away={away.goals} />
    <Comparison label="Tiros" home={home.shots} away={away.shots} />
    <Comparison label="Eficacia" home={home.shots ? Math.round(home.goals / home.shots * 100) : 0} away={away.shots ? Math.round(away.goals / away.shots * 100) : 0} suffix="%" />
    <Comparison label="Al arco" home={home.shots_on_target} away={away.shots_on_target} />
    <Comparison label="Atajadas rivales" home={home.saves_against} away={away.saves_against} />
    <Comparison label="Afuera / palo" home={home.outside_or_woodwork} away={away.outside_or_woodwork} />
    <Comparison label="Pérdidas" home={home.turnovers} away={away.turnovers} />
    <Comparison label="Recuperaciones" home={home.recoveries} away={away.recoveries} />
    <Comparison label="Sanciones" home={home.sanctions} away={away.sanctions} />
  </div>
</section>
}

const blockKey = (period: number, startSeconds: number) => `${period}-${startSeconds}`
const blockLabel = (period: number, startSeconds: number, endSeconds: number) => `P${period} · ${Math.floor(startSeconds / 60)}–${Math.floor(endSeconds / 60)}’`

function PhaseDashboard({ report, selectedBlock, onSelectBlock, playerSlug }: { report: PublicReport; selectedBlock: string | null; onSelectBlock: (key: string | null) => void; playerSlug: string }) {
  const analysis = report.phase_analysis
  if (!analysis) return null
  const selected = analysis.blocks.find((block) => blockKey(block.period, block.start_seconds) === selectedBlock) ?? null
  const playerEvents = selected && playerSlug !== 'all' ? report.incidents.filter((incident) => incident.player_slug === playerSlug && incident.period === selected.period && incident.regulation_seconds !== null && !incident.clock_unverified && (incident.regulation_seconds % 1800) >= selected.start_seconds && (incident.regulation_seconds % 1800) < selected.end_seconds) : []
  const homeName = report.match.home_team ?? 'Local'
  const awayName = report.match.away_team ?? 'Visitante'
  const clock = (period: number, seconds: number) => `P${period} · ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
  let homeTotal = 0
  let awayTotal = 0
  return <>
    <section className="dashboard-section" aria-labelledby="phase-analysis-title">
      <div className="section-heading"><div><p className="eyebrow">Fase 1</p><h2 id="phase-analysis-title">Mini-partidos de 10 minutos</h2></div><small>El parcial explica quién ganó el tramo; el acumulado explica el partido.</small></div>
      <div className="table-wrap"><table className="player-table phase-table"><thead><tr><th>Tramo</th><th>Parcial</th><th>Marcador acumulado</th><th>Lectura</th></tr></thead><tbody>{analysis.blocks.map((block) => {
        const key = blockKey(block.period, block.start_seconds); const winner = block.winner === 'draw' ? 'Empate' : block.winner === 'home' ? homeName : awayName
        homeTotal += block.home.goals; awayTotal += block.away.goals
        return <tr key={key} className={selectedBlock === key ? 'selected' : ''} onClick={() => onSelectBlock(selectedBlock === key ? null : key)}><td><strong>{blockLabel(block.period, block.start_seconds, block.end_seconds)}</strong></td><td><strong>{block.home.goals}–{block.away.goals}</strong><small>{homeName}: {block.home.shots} tiros · {pct(block.home.goals, block.home.shots)} · {block.home.turnovers} pérdidas</small><small>{awayName}: {block.away.shots} tiros · {pct(block.away.goals, block.away.shots)} · {block.away.turnovers} pérdidas</small></td><td><strong>{homeTotal}–{awayTotal}</strong></td><td>{winner === 'Empate' ? 'Tramo empatado' : `${winner} ganó el tramo`}</td></tr>
      })}</tbody></table></div>
      {selected && <div className="selected-panel"><strong>{blockLabel(selected.period, selected.start_seconds, selected.end_seconds)}</strong><span>{homeName}: {selected.home.recoveries} recuperaciones · {awayName}: {selected.away.recoveries} recuperaciones</span>{playerSlug !== 'all' && <span>Jugador seleccionado: {playerEvents.filter((event) => event.outcome === 'Gol').length} goles, {playerEvents.filter((event) => event.event_kind === 'shot').length} tiros y {playerEvents.filter((event) => event.event_kind === 'turnover').length} pérdidas en este tramo.</span>}</div>}
    </section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Arqueros</p><h2>Presión rival y respuesta</h2></div><small>Separado por tiempo, total y 7 metros</small></div><div className="table-wrap"><table className="player-table"><thead><tr><th>Defensa</th><th>Período</th><th>Intentos</th><th>Al arco</th><th>Atajadas</th><th>Goles</th><th>7 m</th></tr></thead><tbody>{(['home', 'away'] as const).flatMap((side) => { const team = side === 'home' ? homeName : awayName; const context = analysis.goalkeeper_context[side]; return ([['Primer tiempo', context.first_half], ['Segundo tiempo', context.second_half], ['Total', context.total]] as const).map(([label, row]) => <tr key={`${side}-${label}`}><td><strong>{team}</strong></td><td>{label}</td><td>{row.opponent_attempts}</td><td>{row.opponent_on_target}</td><td>{row.saves} · {pct(row.saves, row.opponent_on_target)}</td><td>{row.goals_conceded} · {pct(row.goals_conceded, row.opponent_attempts)}</td><td>{row.seven_meters.goals}/{row.seven_meters.attempts} goles · {row.seven_meters.saves} atajadas</td></tr>)})}</tbody></table></div></section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Momentos</p><h2>Rachas y concesiones rápidas</h2></div><small>Secuencias observadas, no causas tácticas inferidas</small></div><div className="phase-insights"><article><h3>Rachas de gol</h3>{analysis.scoring_runs.length ? <ul>{analysis.scoring_runs.map((run) => <li key={`${run.start.period}-${run.start.seconds}-${run.end.seconds}`}>{run.team_side === 'home' ? homeName : awayName}: {run.goals} goles seguidos · {clock(run.start.period, run.start.seconds)} a {clock(run.end.period, run.end.seconds)}</li>)}</ul> : <p>Sin rachas de dos o más goles.</p>}</article><article><h3>Gol rival dentro de 10 segundos</h3>{analysis.quick_concessions.length ? <ul>{analysis.quick_concessions.map((item) => <li key={`${item.at.period}-${item.at.seconds}-${item.conceding_side}`}>{clock(item.at.period, item.at.seconds)} · {item.conceding_side === 'home' ? homeName : awayName} recibió gol {item.seconds_after_terminal}s después de {item.terminal_kind === 'turnover' ? 'una pérdida' : 'una finalización'}.</li>)}</ul> : <p>Sin secuencias inmediatas verificadas.</p>}<small>No equivale a “error de repliegue”; esa causa requiere observación explícita.</small></article></div></section>
  </>
}

type IncidentCardProps = {
  incident: PublicReport['incidents'][number]
  videoSeconds: number | null
  onSeek: (seconds: number) => void
  onSelect: (reference: string) => void
  isSelected: boolean
  report: PublicReport
}

function clockDisplay(regulationSeconds: number | null, clockUnverified: boolean, videoSeconds: number | null): React.ReactNode {
  // If clock is verified and regulation seconds exist → show time
  if (!clockUnverified && regulationSeconds !== null) {
    const mins = Math.floor(regulationSeconds / 60)
    const secs = Math.round(regulationSeconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }
  // If clock is unverified and video seconds exist → show video time with subtle unverified indicator
  if (clockUnverified && videoSeconds !== null) {
    const mins = Math.floor(videoSeconds / 60)
    const secs = Math.round(videoSeconds % 60)
    return (
      <span>
        Video {mins}:{secs.toString().padStart(2, '0')} 
        <span className="unverified-clock-badge" title="Reloj no verificado">⚠</span>
      </span>
    )
  }
  // If clock is unverified but no video → show generic unverified label
  if (clockUnverified) {
    return 'Reloj sin verificar'
  }
  // Fallback: generic time display
  return regulationSeconds === null ? 'Tiempo sin verificar' : `${Math.floor(regulationSeconds / 60)}:${String(Math.round(regulationSeconds % 60)).padStart(2, '0')}`
}

function IncidentCard({ incident, videoSeconds, onSeek, onSelect, isSelected, report }: IncidentCardProps) {
  const displayTime = clockDisplay(incident.regulation_seconds, incident.clock_unverified, videoSeconds ?? incident.video_seconds)
  const isVideoAvailable = report.video && incident.video_seconds !== null

  return <article className={`timeline-item ${isSelected ? 'selected' : ''}`} key={incident.reference}>

    <time>{displayTime}</time>

    <div>
      <span className={`team-dot ${incident.team_side}`} />
      <strong>{incident.player_name ?? incident.incident_type}</strong>

      <p>{incident.player_name ? `${incident.incident_type} · ${incident.outcome || 'Sin resultado'}` : incident.outcome || incident.incident_type}</p>

      <small>Período {incident.period ?? 'sin verificar'} · {isVideoAvailable ? (
        <button
          className="jump-link"
          onClick={() => { onSeek(incident.video_seconds ?? 0); onSelect(incident.reference) }}
          aria-label={`Llevar video a ${incident.video_seconds} segundos`}
        >
          Ir al video
        </button>
      ) : ''}</small>
    </div>
  </article>
}

// Reproductor de video YouTube persistente - iframe único con enablejsapi=1
// Race-free: onLoad handler marca listo inmediatamente, luego buscSeconds change
// postea seekTo y playVideo a iframe.contentWindow
type VideoPlayerProps = {
  videoId: string | null
  videoSeconds: number | null
}

function VideoPlayer({ videoId, videoSeconds }: VideoPlayerProps) {
  const playerRef = useRef<HTMLIFrameElement>(null)
  const [isReady, setIsReady] = useState(false)

  // Al cambiar videoSeconds y player listo, hacer seek y play
  useEffect(() => {
    if (!isReady || !playerRef.current || videoSeconds === null) return
    const targetOrigin = 'https://www.youtube-nocookie.com'
    // Seek al segundo especificado y reproducir inmediatamente
    playerRef.current.contentWindow?.postMessage(
      JSON.stringify({ event: 'command', func: 'seekTo', args: [videoSeconds, true] }),
      targetOrigin
    )
    // Reproducir video después de hacer seek
    playerRef.current.contentWindow?.postMessage(
      JSON.stringify({ event: 'command', func: 'playVideo' }),
      targetOrigin
    )
  }, [isReady, videoSeconds])

  // Always render the persistent iframe visible;
  // expose a valid external timestamped YouTube link as fallback
  return (
    <div className="persistent-player" title="Video del Partido">
      <iframe
        title="Video del Partido"
        src={`https://www.youtube-nocookie.com/embed/${videoId}?enablejsapi=1&origin=${window.location.origin}&autoplay=0&rel=0`}
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        ref={playerRef}
        onLoad={() => setIsReady(true)}
      />
      <div className="fallback-video">
        <a
          className="video-link"
          href={videoId
            ? `https://www.youtube.com/watch?v=${videoId}&t=${videoSeconds ?? 0}`
            : `https://www.youtube.com/watch?v=${videoId}`}
          target="_blank"
          rel="noreferrer"
        >
          ▶ Ver video en YouTube (fallback)
        </a>
      </div>
    </div>
  )
}

export default function App() {
  const [report, setReport] = useState<PublicReport | null>(null)
  const [message, setMessage] = useState('Cargando informe público…')
  const [catalog, setCatalog] = useState<PublicReportCatalog | null>(null)
  const [catalogLoaded, setCatalogLoaded] = useState(false)
  const [selectedReportKey, setSelectedReportKey] = useState<string | null>(null)
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null)
  const [playerSlug, setPlayerSlug] = useState('all')
const [kind, setKind] = useState('all')
const [team, setTeam] = useState<'all' | 'home' | 'away'>('all')
const [videoSeconds, setVideoSeconds] = useState<number | null>(null)
const [selectedIncidentRef, setSelectedIncidentRef] = useState<{ reference: string | null; videoSeconds: number } | null>(null)
  

  useEffect(() => {
    let active = true
    fetch('reports.json')
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data) => {
        const decoded = decodePublicReportCatalog(data)
        if (!active) return
        setCatalog(decoded)
        setSelectedReportKey(decoded.reports[0]?.key ?? null)
      })
      .catch(() => { if (active) setCatalog(null) })
      .finally(() => { if (active) setCatalogLoaded(true) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!catalogLoaded || (catalog && catalog.reports.length > 0 && !selectedReportKey)) return
    let active = true
    const file = selectedReportKey ? reportFileName(selectedReportKey) : 'report.json'
    setReport(null)
    setMessage('Cargando informe público…')
    fetch(file)
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((data) => {
        if (!active) return
        setReport(decodePublicReport(data))
        setMessage('')
      })
      .catch(() => { if (active) setMessage('No se pudo abrir el informe. Actualizá la página o volvé a intentar.') })
    return () => { active = false }
  }, [catalog, catalogLoaded, selectedReportKey])

  function selectReport(key: string) {
    startTransition(() => {
      setSelectedReportKey(key)
      setPlayerSlug('all')
      setKind('all')
      setTeam('all')
      setVideoSeconds(null)
      setSelectedIncidentRef(null)
      setSelectedBlock(null)
    })
  }

  const reportIncidents = report?.incidents ?? []
  const types = useMemo(() => [...new Set(reportIncidents.map((incident) => incident.incident_type))], [reportIncidents])
  const filteredIncidents = useMemo(() => reportIncidents.filter((incident) => (playerSlug === 'all' || incident.player_slug === playerSlug) && (kind === 'all' || incident.incident_type === kind)), [reportIncidents, playerSlug, kind])
  const defaultVideoSeconds = reportIncidents.find((incident) => incident.video_seconds !== null)?.video_seconds ?? 0
  if (!report) return <main className="report-status"><p role="status">{message}</p></main>

  const players = report.players ?? []
  const keepers = players.filter((player) => player.role === 'goalkeeper')
  const fields = players.filter((player) => player.role === 'field_player' && (team === 'all' || player.team_side === team))
  const selected = players.find((player) => player.slug === playerSlug) ?? null
  const keeperAttribution = report.team_summary ? (['home', 'away'] as const).map((side) => {
    const assigned = players.filter((player) => player.role === 'goalkeeper' && player.team_side === side).reduce((total, player) => total + n(player.metrics.shots_faced), 0)
    const opponent = side === 'home' ? report.team_summary?.away : report.team_summary?.home
    return { team: side === 'home' ? report.match.home_team : report.match.away_team, assigned, unassigned: Math.max(0, n(opponent?.shots_on_target) - assigned) }
  }).filter((item) => item.assigned > 0 && item.unassigned > 0) : []
  

  // Determinar el video actual: si hay un incidente seleccionado, usar su segundos;
  // sino el default; sino null.
  const currentVideoSeconds = selectedIncidentRef?.videoSeconds ?? videoSeconds ?? defaultVideoSeconds
  const cueVideo = (seconds: number) => setVideoSeconds(Math.max(0, seconds - VIDEO_PREROLL_SECONDS))

  // Cuando se hace clic en un marcador del timeline, seek al video_seconds del evento
  function handleMarkerClick(reference: string, videoSeconds: number | null) {
    cueVideo(videoSeconds ?? 0)
    setSelectedIncidentRef({ reference, videoSeconds: videoSeconds ?? 0 })
  }

  return <main className="report-shell" aria-labelledby="report-header">
    <header className="hero"><p className="eyebrow">Informe de partido</p><div className="match-line"><h1 id="report-header">{report.match.home_team} <span>vs</span> {report.match.away_team}</h1>{catalog && catalog.reports.length > 1 && <select aria-label="Seleccionar partido" value={selectedReportKey ?? ''} onChange={(event) => selectReport(event.target.value)}>{catalog.reports.map((entry) => <option key={entry.key} value={entry.key}>{reportLabel(entry)}</option>)}</select>}</div><p>{report.coverage?.label ?? 'Cobertura del análisis no especificada'}</p>{report.coverage?.status === 'partial' && <strong className="coverage-badge">Análisis parcial · sólo períodos cargados</strong>}{report.video && <a className="video-link" href={`https://www.youtube.com/watch?v=${report.video.video_id}`} target="_blank" rel="noreferrer">▶ Abrir video del partido</a>}</header>
    <TeamDashboard report={report} />
    <PhaseDashboard report={report} selectedBlock={selectedBlock} onSelectBlock={setSelectedBlock} playerSlug={playerSlug} />
    <Timeline report={report} onSeek={handleMarkerClick} />
    <section className="dashboard-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Plantel</p>
          <h2>Jugadores de campo</h2>
        </div>
        <div className="filter-row">
          <button className={team === 'all' ? 'active' : ''} onClick={() => setTeam('all')}>Todos</button>
          <button className={team === 'home' ? 'active' : ''} onClick={() => setTeam('home')}>{report.match.home_team}</button>
          <button className={team === 'away' ? 'active' : ''} onClick={() => setTeam('away')}>{report.match.away_team}</button>
        </div>
      </div>
      <div className="table-wrap">
      <table className="player-table">
        <thead>
          <tr>
            <th>Jugador</th>
            <th>Tot.</th>
            <th>Al arco</th>
            <th>Goles</th>
            <th>Efic.</th>
            <th>Atajadas rival</th>
            <th>Afuera / palo</th>
            <th>Pérdidas</th>
            <th>Recup.</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((player) => (
            <tr className={playerSlug === player.slug ? 'selected' : ''} key={player.slug} onClick={() => setPlayerSlug(player.slug)}>
              <td>#{player.jersey_number ?? '—'} · <strong>{player.name}</strong></td>
              <td>{n(player.metrics.shots)}</td>
              <td>{n(player.metrics.shots_on_target)}</td>
              <td>{n(player.metrics.goals)}</td>
              <td>{pct(n(player.metrics.goals), n(player.metrics.shots))}</td>
              <td>{n(player.metrics.saves_against)}</td>
              <td>{n(player.metrics.outside_or_woodwork)}</td>
              <td>{n(player.metrics.turnovers)}</td>
              <td>{n(player.metrics.recoveries)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    {selected?.role === 'field_player' && (
      <div className="selected-panel">
        <strong>{playerLabel(selected)}</strong>
        <span>{n(selected.metrics.goals)} goles / {n(selected.metrics.shots)} tiros · {pct(n(selected.metrics.goals), n(selected.metrics.shots))} eficacia</span>
      </div>
    )}
    </section>
    <section className="dashboard-section keeper-section"><div className="section-heading"><div><p className="eyebrow">Defensa</p><h2>Arqueros</h2></div><small>Atajadas sobre tiros al arco asignados</small></div><div className="keeper-grid">{keepers.map((player) => <article className="keeper-card" key={player.slug}><span>ARQ · #{player.jersey_number ?? '—'}</span><h3>{player.name}</h3><strong>{n(player.metrics.saves)} atajadas <em>{pct(n(player.metrics.saves), n(player.metrics.shots_faced))}</em></strong><p>{n(player.metrics.shots_faced)} tiros al arco asignados · {n(player.metrics.goals_conceded)} goles recibidos</p><div className="keeper-splits">{goalkeeperSplit(player, '7m', '7 m')}{goalkeeperSplit(player, 'counterattack', 'Contra')}</div></article>)}</div>{keeperAttribution.map((item) => <p className="keeper-note" key={item.team}>{item.team}: {item.unassigned} tiros al arco sin arquero asignado; no se atribuyen a un jugador.</p>)}</section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Video y análisis</p><h2>Incidencias del partido</h2></div><small>{filteredIncidents.length} incidencias</small></div>

      {/* Persistent video player - single iframe, not remounted on key change */}
      {report.video ? (
        <div className="persistent-video-wrapper">
          <VideoPlayer videoId={report.video.video_id} videoSeconds={videoSeconds} />
          {/* Controles de tiempo visibles solo cuando hay video con incidentes */}
          {currentVideoSeconds !== null && <div className="video-time-indicator">
            <span>Tiempo actual: {Math.floor(currentVideoSeconds / 60)}:${String(Math.round(currentVideoSeconds % 60)).padStart(2, '0')}</span>
          </div>}
        </div>
      ) : (
        <p className="video-note">El video no está disponible para esta publicación.</p>
      )}

<div className="timeline-filters">
        <select aria-label="Filtrar jugador" value={playerSlug} onChange={(event) => setPlayerSlug(event.target.value)}>
          <option value="all">Todos los jugadores</option>
          {players.map((player) => <option key={player.slug} value={player.slug}>{playerLabel(player)}</option>)}
        </select>
        <select aria-label="Filtrar tipo" value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="all">Todos los tipos</option>
          {types.map((type) => <option key={type} value={type}>{type}</option>)}
        </select>
      </div>

      {/* Scrollable incident panel - all filtered events, fixed height */}
      <div className="incident-panel">
        <span className="panel-title">Incidencias</span>
        <div className="incidents-list" style={{ maxHeight: 400, overflowY: 'auto' }}>
          {filteredIncidents.map((incident) => (
            <IncidentCard
              key={incident.reference}
              incident={incident}
              videoSeconds={incident.video_seconds ?? 0}
              onSeek={cueVideo}
              onSelect={(ref) => setSelectedIncidentRef({ reference: ref, videoSeconds: incident.video_seconds ?? 0 })}
              isSelected={selectedIncidentRef?.reference === incident.reference}
              report={report}
            />
          ))}
        </div>
      </div>

      <footer>Fuente: {report.source.label}. {report.uncertainty_disclosure}</footer>
  </section>
</main>
}
