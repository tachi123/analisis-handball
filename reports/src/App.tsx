import { useEffect, useMemo, useState } from 'react'
import { decodePublicReport, type PlayerPublic, type PublicReport } from './projection'

const BATCH = 6
const n = (value: unknown) => typeof value === 'number' ? value : 0
const pct = (numerator: number, denominator: number) => denominator ? `${Math.round((numerator / denominator) * 100)}%` : '—'
const playerLabel = (player: PlayerPublic) => `${player.name}${player.jersey_number ? ` · #${player.jersey_number}` : ''}`
const clock = (seconds: number | null, unverified: boolean, label: string | null) => unverified ? 'Reloj sin verificar' : seconds === null ? (label ?? 'Tiempo sin verificar') : `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`

function Comparison({ label, home, away, suffix = '' }: { label: string; home: number; away: number; suffix?: string }) {
  const max = Math.max(home, away, 1)
  return <article className="pyramid-row"><strong className="pyramid-value home-value">{home}{suffix}</strong><i className="pyramid-bar home-bar" style={{ width: `${home / max * 100}%` }} /><span>{label}</span><i className="pyramid-bar away-bar" style={{ width: `${away / max * 100}%` }} /><strong className="pyramid-value away-value">{away}{suffix}</strong></article>
}

function TeamDashboard({ report }: { report: PublicReport }) {
  const summary = report.team_summary
  if (!summary?.home || !summary.away) return null
  const { home, away } = summary
  return <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Panorama</p><h2>Comparativa de equipos</h2></div><small>{home.name} ← comparación → {away.name}</small></div><div className="pyramid-chart">
    <Comparison label="Goles" home={home.goals} away={away.goals} />
    <Comparison label="Tiros" home={home.shots} away={away.shots} />
    <Comparison label="Eficacia" home={home.shots ? Math.round(home.goals / home.shots * 100) : 0} away={away.shots ? Math.round(away.goals / away.shots * 100) : 0} suffix="%" />
    <Comparison label="Al arco" home={home.shots_on_target} away={away.shots_on_target} />
    <Comparison label="Atajadas rivales" home={home.saves_against} away={away.saves_against} />
    <Comparison label="Afuera / palo" home={home.outside_or_woodwork} away={away.outside_or_woodwork} />
    <Comparison label="Pérdidas" home={home.turnovers} away={away.turnovers} />
    <Comparison label="Recuperaciones" home={home.recoveries} away={away.recoveries} />
    <Comparison label="Sanciones" home={home.sanctions} away={away.sanctions} />
  </div></section>
}

export default function App() {
  const [report, setReport] = useState<PublicReport | null>(null)
  const [message, setMessage] = useState('Cargando informe público…')
  const [team, setTeam] = useState<'all' | 'home' | 'away'>('all')
  const [playerSlug, setPlayerSlug] = useState('all')
  const [kind, setKind] = useState('all')
  const [visible, setVisible] = useState(BATCH)
  const [videoSeconds, setVideoSeconds] = useState<number | null>(null)

  useEffect(() => { fetch('report.json').then((response) => response.ok ? response.json() : Promise.reject()).then((data) => { setReport(decodePublicReport(data)); setMessage('') }).catch(() => setMessage('No se pudo abrir el informe. Actualizá la página o volvé a intentar.')) }, [])
  const reportIncidents = report?.incidents ?? []
  const types = useMemo(() => [...new Set(reportIncidents.map((incident) => incident.incident_type))], [reportIncidents])
  const incidents = useMemo(() => reportIncidents.filter((incident) => (team === 'all' || incident.team_side === team) && (playerSlug === 'all' || incident.player_slug === playerSlug) && (kind === 'all' || incident.incident_type === kind)), [reportIncidents, team, playerSlug, kind])
  const defaultVideoSeconds = reportIncidents.find((incident) => incident.video_seconds !== null)?.video_seconds ?? 0
  if (!report) return <main className="report-status"><p role="status">{message}</p></main>

  const players = report.players ?? []
  const fields = players.filter((player) => player.role === 'field_player' && (team === 'all' || player.team_side === team))
  const keepers = players.filter((player) => player.role === 'goalkeeper' && (team === 'all' || player.team_side === team))
  const keeperAttribution = report.team_summary ? (['home', 'away'] as const).map((side) => {
    const assigned = players.filter((player) => player.role === 'goalkeeper' && player.team_side === side).reduce((total, player) => total + n(player.metrics.shots_faced), 0)
    const opponent = side === 'home' ? report.team_summary?.away : report.team_summary?.home
    return { team: side === 'home' ? report.match.home_team : report.match.away_team, assigned, unassigned: Math.max(0, n(opponent?.shots_on_target) - assigned) }
  }).filter((item) => item.assigned > 0 && item.unassigned > 0) : []
  const reset = (callback: () => void) => { callback(); setVisible(BATCH) }
  const selected = players.find((player) => player.slug === playerSlug) ?? null

  return <main className="report-shell" aria-labelledby="report-header">
    <header className="hero"><p className="eyebrow">Informe de partido</p><div className="match-line"><h1 id="report-header">{report.match.home_team} <span>vs</span> {report.match.away_team}</h1><select aria-label="Seleccionar partido" defaultValue="current"><option value="current">{report.match.date ?? 'Partido actual'} · Partido 1</option></select></div><p>{report.coverage?.label ?? 'Cobertura del análisis no especificada'}</p>{report.coverage?.status === 'partial' && <strong className="coverage-badge">Análisis parcial · sólo períodos cargados</strong>}{report.video && <a className="video-link" href={`https://www.youtube.com/watch?v=${report.video.video_id}`} target="_blank" rel="noreferrer">▶ Abrir video del partido</a>}</header>
    <TeamDashboard report={report} />
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Plantel</p><h2>Jugadores de campo</h2></div><div className="filter-row"><button className={team === 'all' ? 'active' : ''} onClick={() => reset(() => setTeam('all'))}>Todos</button><button className={team === 'home' ? 'active' : ''} onClick={() => reset(() => setTeam('home'))}>{report.match.home_team}</button><button className={team === 'away' ? 'active' : ''} onClick={() => reset(() => setTeam('away'))}>{report.match.away_team}</button></div></div><div className="table-wrap"><table className="player-table"><thead><tr><th>Jugador</th><th>Tot.</th><th>Al arco</th><th>Goles</th><th>Efic.</th><th>Atajadas rival</th><th>Afuera / palo</th><th>Pérdidas</th><th>Recup.</th></tr></thead><tbody>{fields.map((player) => <tr className={playerSlug === player.slug ? 'selected' : ''} key={player.slug} onClick={() => reset(() => setPlayerSlug(player.slug))}><td>#{player.jersey_number ?? '—'} · <strong>{player.name}</strong></td><td>{n(player.metrics.shots)}</td><td>{n(player.metrics.shots_on_target)}</td><td>{n(player.metrics.goals)}</td><td>{pct(n(player.metrics.goals), n(player.metrics.shots))}</td><td>{n(player.metrics.saves_against)}</td><td>{n(player.metrics.outside_or_woodwork)}</td><td>{n(player.metrics.turnovers)}</td><td>{n(player.metrics.recoveries)}</td></tr>)}</tbody></table></div>{selected?.role === 'field_player' && <div className="selected-panel"><strong>{playerLabel(selected)}</strong><span>{n(selected.metrics.goals)} goles / {n(selected.metrics.shots)} tiros · {pct(n(selected.metrics.goals), n(selected.metrics.shots))} eficacia</span></div>}</section>
    <section className="dashboard-section keeper-section"><div className="section-heading"><div><p className="eyebrow">Defensa</p><h2>Arqueros</h2></div><small>Atajadas sobre tiros al arco asignados</small></div><div className="keeper-grid">{keepers.map((player) => <article className="keeper-card" key={player.slug}><span>ARQ · #{player.jersey_number ?? '—'}</span><h3>{player.name}</h3><strong>{n(player.metrics.saves)} atajadas <em>{pct(n(player.metrics.saves), n(player.metrics.shots_faced))}</em></strong><p>{n(player.metrics.shots_faced)} tiros al arco asignados · {n(player.metrics.goals_conceded)} goles recibidos</p></article>)}</div>{keeperAttribution.map((item) => <p className="keeper-note" key={item.team}>{item.team}: {item.unassigned} tiros al arco sin arquero asignado; no se atribuyen a un jugador.</p>)}</section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Video y análisis</p><h2>Incidencias del partido</h2></div><small>{incidents.length} incidencias</small></div>{report.video ? <div className="video-player"><iframe key={videoSeconds ?? defaultVideoSeconds} title="Video del partido" src={`https://www.youtube-nocookie.com/embed/${report.video.video_id}?start=${Math.floor(videoSeconds ?? defaultVideoSeconds)}&autoplay=0&rel=0`} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen /><p>Elegí una incidencia para llevar el video al momento exacto.</p></div> : <p className="video-note">El video no está disponible para esta publicación.</p>}<div className="timeline-filters"><select aria-label="Filtrar jugador" value={playerSlug} onChange={(event) => reset(() => setPlayerSlug(event.target.value))}><option value="all">Todos los jugadores</option>{players.map((player) => <option key={player.slug} value={player.slug}>{playerLabel(player)}</option>)}</select><select aria-label="Filtrar tipo" value={kind} onChange={(event) => reset(() => setKind(event.target.value))}><option value="all">Todos los tipos</option>{types.map((type) => <option key={type} value={type}>{type}</option>)}</select></div><div className="timeline">{incidents.slice(0, visible).map((incident) => <article className="timeline-item" key={incident.reference}><time>{clock(incident.regulation_seconds, incident.clock_unverified, incident.clock_label)}</time><div><span className={`team-dot ${incident.team_side}`} /><strong>{incident.player_name ?? incident.incident_type}</strong><p>{incident.player_name ? `${incident.incident_type} · ${incident.outcome || 'Sin resultado'}` : incident.outcome || incident.incident_type}</p><small>Período {incident.period ?? 'sin verificar'} · {report.video && incident.video_seconds !== null ? <button className="jump-link" onClick={() => setVideoSeconds(incident.video_seconds)}>▶ Ver momento</button> : report.video ? 'Sin posición de video' : 'Video no disponible para esta publicación'}</small></div></article>)}</div>{visible < incidents.length && <button className="load-more" onClick={() => setVisible((count) => count + BATCH)}>Mostrar 6 incidencias más</button>}</section>
    <footer>Fuente: {report.source.label}. {report.uncertainty_disclosure}</footer>
  </main>
}
