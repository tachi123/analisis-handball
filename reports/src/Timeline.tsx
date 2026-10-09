import { useState, type KeyboardEvent } from 'react'
import type { PublicReport } from './projection'
import { deriveMomentum, scoreMatchesSummary, type MomentumEvent } from './timelineDerivation'

const WIDTH = 980
const HEIGHT = 260
const PAD = { top: 28, right: 30, bottom: 42, left: 42 }
const COLORS = { home: '#62c5ff', away: '#ffd166', recovery: '#44d49a', turnover: '#ff7a7a', passive: '#fb923c', sanction: '#c084fc', line: '#f4f8ff', muted: '#8eacc2' }

const markerColor = (event: MomentumEvent) => {
  if (event.kind === 'goal') return event.teamSide === 'home' ? COLORS.home : COLORS.away
  if (event.kind === 'recovery') return COLORS.recovery
  if (event.kind === 'turnover') return COLORS.turnover
  if (event.kind === 'passive') return COLORS.passive
  if (event.kind === 'sanction') return COLORS.sanction
  return COLORS.muted
}
const markerLabel = (event: MomentumEvent) => ({ goal: 'Gol', recovery: 'Recuperación', turnover: 'Pérdida', passive: 'Pasivo', sanction: 'Sanción', other: 'Incidencia' }[event.kind])
type MarkerFilter = 'summary' | 'goal' | 'turnover' | 'recovery' | 'sanction' | 'passive'
const filters: Array<{ value: MarkerFilter; label: string }> = [
  { value: 'summary', label: 'Resumen' }, { value: 'goal', label: 'Goles' }, { value: 'turnover', label: 'Pérdidas' },
  { value: 'recovery', label: 'Recuperaciones' }, { value: 'sanction', label: 'Sanciones' }, { value: 'passive', label: 'Pasivo' },
]

export function Timeline({ report, onSeek }: { report: PublicReport; onSeek: (reference: string, videoSeconds: number) => void }) {
  const [filter, setFilter] = useState<MarkerFilter>('summary')
  const events = deriveMomentum(report.incidents)
  if (!events.length) return null
  const relevant = events.filter((event) => event.kind !== 'other')
  const minDiff = Math.min(0, ...events.map((event) => event.scoreDiff))
  const maxDiff = Math.max(0, ...events.map((event) => event.scoreDiff))
  const range = Math.max(1, maxDiff - minDiff)
  const plotWidth = WIDTH - PAD.left - PAD.right
  const plotHeight = HEIGHT - PAD.top - PAD.bottom
  const x = (position: number) => PAD.left + (events.length === 1 ? plotWidth / 2 : position / (events.length - 1) * plotWidth)
  const y = (diff: number) => PAD.top + (maxDiff - diff) / range * plotHeight
  const scorePath = events.reduce((path, event, index) => index === 0 ? `M ${x(event.position)} ${y(event.scoreDiff)}` : `${path} H ${x(event.position)} V ${y(event.scoreDiff)}`, '')
  const seek = (event: MomentumEvent) => { if (event.videoSeconds !== null) onSeek(event.reference, event.videoSeconds) }
  const onKey = (event: KeyboardEvent<SVGCircleElement>, marker: MomentumEvent) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); seek(marker) } }
  const usesVideoClock = events.some((event) => event.clockUnverified)
  const scoreIsComplete = scoreMatchesSummary(events, report.team_summary)
  const lastGoal = relevant.filter((event) => event.kind === 'goal').at(-1)
  const markers = relevant.filter((event, index) => {
    if (filter !== 'summary') return event.kind === filter
    if (event.kind !== 'goal') return false
    const previousGoal = relevant.slice(0, index).reverse().find((item) => item.kind === 'goal')
    const changesLeader = previousGoal !== undefined && Math.sign(previousGoal.scoreDiff) !== Math.sign(event.scoreDiff)
    return event.reference === lastGoal?.reference || event.scoreDiff === 0 || changesLeader
  })

  return <section className="dashboard-section momentum-section" aria-labelledby="momentum-title">
    <div className="section-heading"><div><p className="eyebrow">Desarrollo</p><h2 id="momentum-title">Historia del partido</h2></div><small>La línea sube con {report.match.home_team} y baja con {report.match.away_team}</small></div>
    <div className="momentum-legend" aria-label="Referencias"><span className="home-key">● {report.match.home_team}</span><span className="away-key">● {report.match.away_team}</span><span>● Recuperación</span><span>● Pérdida</span><span>◆ Pasivo</span><span>● Sanción</span></div>
    <div className="momentum-filters" aria-label="Filtrar marcadores de la historia del partido">{filters.map((item) => <button key={item.value} className={filter === item.value ? 'active' : ''} aria-pressed={filter === item.value} onClick={() => setFilter(item.value)}>{item.label}</button>)}</div>
    <div className="momentum-scroll"><svg className="momentum-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Evolución de la diferencia de goles durante el partido">
      <rect x={PAD.left} y={PAD.top} width={plotWidth} height={y(0) - PAD.top} fill="#62c5ff" opacity=".08" />
      <rect x={PAD.left} y={y(0)} width={plotWidth} height={PAD.top + plotHeight - y(0)} fill="#ffd166" opacity=".08" />
      <line x1={PAD.left} x2={WIDTH - PAD.right} y1={y(0)} y2={y(0)} className="momentum-zero" />
      <text x={PAD.left} y={y(0) - 7} className="momentum-axis-label">{report.match.home_team} arriba</text>
      <text x={PAD.left} y={y(0) + 16} className="momentum-axis-label">Empate / {report.match.away_team} arriba</text>
      <path d={scorePath} className="momentum-score-line" />
      {markers.map((event) => <g key={event.reference}>
        <circle className="momentum-marker" cx={x(event.position)} cy={y(event.scoreDiff)} r={event.kind === 'goal' ? 7 : 5} fill={markerColor(event)} tabIndex={event.videoSeconds === null ? -1 : 0} role={event.videoSeconds === null ? undefined : 'button'} aria-label={`${markerLabel(event)}: ${event.playerName ?? report.match[event.teamSide === 'home' ? 'home_team' : 'away_team'] ?? 'equipo'}, ${event.displayTime}`} onClick={() => seek(event)} onKeyDown={(keyboardEvent) => onKey(keyboardEvent, event)} />
        {event.kind === 'passive' && <text x={x(event.position)} y={y(event.scoreDiff) + 3} textAnchor="middle" className="momentum-passive-mark">P</text>}
        {event.kind === 'goal' && <text x={x(event.position)} y={y(event.scoreDiff) - 12} textAnchor="middle" className="momentum-score-label">{event.homeGoals}–{event.awayGoals}</text>}
      </g>)}
      {events.filter((_event, index) => index === 0 || index === events.length - 1 || index % Math.ceil(events.length / 5) === 0).map((event) => <text key={`${event.reference}-time`} x={x(event.position)} y={HEIGHT - 14} textAnchor="middle" className="momentum-time-label">{event.displayTime}</text>)}
    </svg></div>
    {(usesVideoClock || report.coverage?.status === 'partial' || !scoreIsComplete) && <p className="momentum-disclosure">{usesVideoClock && '⚠ Algunos puntos se ubican con tiempo de video; el reloj de juego no fue verificado. '}{report.coverage?.status === 'partial' && 'El análisis es parcial. '}{!scoreIsComplete && 'El marcador de la línea refleja sólo los goles con tiempo disponible.'}</p>}
  </section>
}
