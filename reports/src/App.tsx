import { useEffect, useMemo, useState } from 'react'
import { decodePublicReport, type PlayerPublic, type PublicReport } from './projection'

const BATCH = 6
const n = (value: unknown) => typeof value === 'number' ? value : 0
const pct = (numerator: number, denominator: number) => denominator ? `${Math.round((numerator / denominator) * 100)}%` : '—'
const playerLabel = (player: PlayerPublic) => `${player.name}${player.jersey_number ? ` · #${player.jersey_number}` : ''}`
const clock = (seconds: number | null, unverified: boolean, label: string | null) => unverified ? 'Reloj sin verificar' : seconds === null ? (label ?? 'Tiempo sin verificar') : `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`

function Comparison({ label, home, away, homeName, awayName, suffix = '' }: { label: string; home: number; away: number; homeName: string; awayName: string; suffix?: string }) {
  const max = Math.max(home, away, 1)
  return <article className="compare-card"><p>{label}</p><div><strong>{home}{suffix}</strong><span>{homeName}</span><i style={{ width: `${home / max * 100}%` }} /></div><div><strong>{away}{suffix}</strong><span>{awayName}</span><i className="away" style={{ width: `${away / max * 100}%` }} /></div></article>
}

function TeamDashboard({ report }: { report: PublicReport }) {
  const summary = report.team_summary
  if (!summary?.home || !summary.away) return null
  const { home, away } = summary
  return <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Panorama</p><h2>Comparativa de equipos</h2></div><small>Período analizado</small></div><div className="comparison-grid">
    <Comparison label="Goles" home={home.goals} away={away.goals} homeName={home.name} awayName={away.name} />
    <Comparison label="Tiros" home={home.shots} away={away.shots} homeName={home.name} awayName={away.name} />
    <Comparison label="Eficacia" home={home.shots ? Math.round(home.goals / home.shots * 100) : 0} away={away.shots ? Math.round(away.goals / away.shots * 100) : 0} homeName={home.name} awayName={away.name} suffix="%" />
    <Comparison label="Pérdidas" home={home.turnovers} away={away.turnovers} homeName={home.name} awayName={away.name} />
    <Comparison label="Recuperaciones" home={home.recoveries} away={away.recoveries} homeName={home.name} awayName={away.name} />
    <Comparison label="Sanciones" home={home.sanctions} away={away.sanctions} homeName={home.name} awayName={away.name} />
  </div></section>
}

export default function App() {
  const [report, setReport] = useState<PublicReport | null>(null)
  const [message, setMessage] = useState('Cargando informe público…')
  const [team, setTeam] = useState<'all' | 'home' | 'away'>('all')
  const [playerSlug, setPlayerSlug] = useState('all')
  const [kind, setKind] = useState('all')
  const [visible, setVisible] = useState(BATCH)

  useEffect(() => { fetch('report.json').then((response) => response.ok ? response.json() : Promise.reject()).then((data) => { setReport(decodePublicReport(data)); setMessage('') }).catch(() => setMessage('No se pudo abrir el informe. Actualizá la página o volvé a intentar.')) }, [])
  if (!report) return <main className="report-status"><p role="status">{message}</p></main>

  const players = report.players ?? []
  const fields = players.filter((player) => player.role === 'field_player' && (team === 'all' || player.team_side === team))
  const keepers = players.filter((player) => player.role === 'goalkeeper' && (team === 'all' || player.team_side === team))
  const types = useMemo(() => [...new Set(report.incidents.map((incident) => incident.incident_type))], [report.incidents])
  const incidents = useMemo(() => report.incidents.filter((incident) => (team === 'all' || incident.team_side === team) && (playerSlug === 'all' || incident.player_slug === playerSlug) && (kind === 'all' || incident.incident_type === kind)), [report.incidents, team, playerSlug, kind])
  const reset = (callback: () => void) => { callback(); setVisible(BATCH) }
  const selected = players.find((player) => player.slug === playerSlug) ?? null

  return <main className="report-shell" aria-labelledby="report-header">
    <header className="hero"><p className="eyebrow">Informe de partido</p><div className="match-line"><h1 id="report-header">{report.match.home_team} <span>vs</span> {report.match.away_team}</h1><select aria-label="Seleccionar partido" defaultValue="current"><option value="current">{report.match.date ?? 'Partido actual'} · Partido 1</option></select></div><p>{report.coverage?.label ?? 'Cobertura del análisis no especificada'}</p>{report.coverage?.status === 'partial' && <strong className="coverage-badge">Análisis parcial · sólo períodos cargados</strong>}</header>
    <TeamDashboard report={report} />
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Plantel</p><h2>Jugadores de campo</h2></div><div className="filter-row"><button className={team === 'all' ? 'active' : ''} onClick={() => reset(() => setTeam('all'))}>Todos</button><button className={team === 'home' ? 'active' : ''} onClick={() => reset(() => setTeam('home'))}>{report.match.home_team}</button><button className={team === 'away' ? 'active' : ''} onClick={() => reset(() => setTeam('away'))}>{report.match.away_team}</button></div></div><div className="player-grid">{fields.map((player) => <button className={`player-card ${playerSlug === player.slug ? 'selected' : ''}`} key={player.slug} onClick={() => reset(() => setPlayerSlug(player.slug))}><span>#{player.jersey_number ?? '—'}</span><h3>{player.name}</h3><strong>{n(player.metrics.goals)} goles <em>{pct(n(player.metrics.goals), n(player.metrics.shots))}</em></strong><small>{n(player.metrics.shots)} tiros · {n(player.metrics.turnovers)} pérdidas · {n(player.metrics.recoveries)} recuperaciones</small></button>)}</div>{selected?.role === 'field_player' && <div className="selected-panel"><strong>{playerLabel(selected)}</strong><span>{n(selected.metrics.goals)} goles / {n(selected.metrics.shots)} tiros · {pct(n(selected.metrics.goals), n(selected.metrics.shots))} eficacia</span></div>}</section>
    <section className="dashboard-section keeper-section"><div className="section-heading"><div><p className="eyebrow">Defensa</p><h2>Arqueros</h2></div><small>Atajadas sobre tiros al arco</small></div><div className="keeper-grid">{keepers.map((player) => <article className="keeper-card" key={player.slug}><span>ARQ · #{player.jersey_number ?? '—'}</span><h3>{player.name}</h3><strong>{n(player.metrics.saves)} atajadas <em>{pct(n(player.metrics.saves), n(player.metrics.shots_faced))}</em></strong><p>{n(player.metrics.shots_faced)} tiros al arco · {n(player.metrics.goals_conceded)} goles recibidos</p></article>)}</div></section>
    <section className="dashboard-section"><div className="section-heading"><div><p className="eyebrow">Video y análisis</p><h2>Incidencias del partido</h2></div><small>{incidents.length} incidencias</small></div><div className="timeline-filters"><select aria-label="Filtrar jugador" value={playerSlug} onChange={(event) => reset(() => setPlayerSlug(event.target.value))}><option value="all">Todos los jugadores</option>{players.map((player) => <option key={player.slug} value={player.slug}>{playerLabel(player)}</option>)}</select><select aria-label="Filtrar tipo" value={kind} onChange={(event) => reset(() => setKind(event.target.value))}><option value="all">Todos los tipos</option>{types.map((type) => <option key={type} value={type}>{type}</option>)}</select></div><div className="timeline">{incidents.slice(0, visible).map((incident) => <article className="timeline-item" key={incident.reference}><time>{clock(incident.regulation_seconds, incident.clock_unverified, incident.clock_label)}</time><div><span className={`team-dot ${incident.team_side}`} /><strong>{incident.player_name ?? incident.incident_type}</strong><p>{incident.player_name ? `${incident.incident_type} · ${incident.outcome || 'Sin resultado'}` : incident.outcome || incident.incident_type}</p><small>Período {incident.period ?? 'sin verificar'} · Video no disponible para esta publicación</small></div></article>)}</div>{visible < incidents.length && <button className="load-more" onClick={() => setVisible((count) => count + BATCH)}>Mostrar 6 incidencias más</button>}</section>
    <footer>Fuente: {report.source.label}. {report.uncertainty_disclosure}</footer>
  </main>
}
