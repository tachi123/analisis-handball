import { useMemo, useState } from 'react'
import type { CompetitionRound, MatchCoverage, PublicCompetition, RoundMatch, StandingRow } from './publicCompetitions'
import { ResultStrip, type StripMatch } from './resultStrip'
import { decimal, formatDate, formatShortDate, isSapa, percent, resultFromScore, signed } from './competitionFormat'

const coverageLabel = (coverage: MatchCoverage) => coverage === 'planilla' ? 'Planilla confirmada' : coverage === 'reported' ? 'Resultado informado' : coverage === 'suspended' ? 'Partido suspendido' : coverage === 'cancelled' ? 'Cancelado' : 'Pendiente'

function matchStrip(competition: PublicCompetition, matchesClub: (name: string) => boolean): StripMatch[] {
  const rows: StripMatch[] = []
  for (const round of competition.rounds) {
    for (const match of round.matches) {
      const home = matchesClub(match.home)
      if (!home && !matchesClub(match.away)) continue
      if (match.home_goals === null || match.away_goals === null) {
        rows.push({ key: `${round.round}-${match.home}-${match.away}`, label: `F${round.round}`, result: 'pending', detail: `Fecha ${round.round} · ${home ? 'Local' : 'Visitante'} vs ${home ? match.away : match.home} · pendiente` })
        continue
      }
      const goalsFor = home ? match.home_goals : match.away_goals
      const goalsAgainst = home ? match.away_goals : match.home_goals
      rows.push({
        key: `${round.round}-${match.home}-${match.away}`,
        label: `F${round.round}`,
        result: resultFromScore(goalsFor, goalsAgainst),
        detail: `Fecha ${round.round} · ${home ? 'Local' : 'Visitante'} vs ${home ? match.away : match.home} · ${goalsFor}–${goalsAgainst}`,
      })
    }
  }
  return rows
}

function MatchRow({ round, match }: { round: CompetitionRound; match: RoundMatch }) {
  const sapa = isSapa(match.home) || isSapa(match.away)
  return <article className={`round-match ${sapa ? 'sapa-match' : ''}`}>
    <div className="round-match-teams">
      <strong>{match.home}</strong>
      <span>{match.home_goals === null ? '—' : match.home_goals}–{match.away_goals === null ? '—' : match.away_goals}</span>
      <strong>{match.away}</strong>
    </div>
    <div className="round-match-meta">
      <span className={`match-coverage ${match.coverage}`}>{coverageLabel(match.coverage)}</span>
      <small>{formatShortDate(round.date)}</small>
    </div>
  </article>
}

export function CompetitionDetail({ competition, onBack, onHome, onForecast, onSeason }: {
  competition: PublicCompetition
  onBack: () => void
  onHome: () => void
  onForecast?: () => void
  onSeason?: () => void
}) {
  const sapa = competition.standings.find((row) => isSapa(row.club))
  const sapaInsight = competition.insights.clubs.find((row) => isSapa(row.club))
  const sapaStrip = useMemo(() => matchStrip(competition, isSapa), [competition])
  const sapaForm = sapaStrip.filter((match) => match.result !== 'pending').slice(-5)
  const lastPlayed = [...competition.rounds].reverse().find((round) => round.matches.some((match) => match.home_goals !== null))?.round ?? competition.rounds[0]?.round ?? 1
  const [selectedRound, setSelectedRound] = useState(lastPlayed)
  const [scorerClub, setScorerClub] = useState(() => competition.scorers.find((row) => isSapa(row.club))?.club ?? 'all')
  const scorerClubs = [...new Set(competition.scorers.map((row) => row.club))].sort((left, right) => left.localeCompare(right, 'es'))
  const visibleScorers = scorerClub === 'all' ? competition.scorers.slice(0, 30) : competition.scorers.filter((row) => row.club === scorerClub)
  const round = competition.rounds.find((row) => row.round === selectedRound) ?? competition.rounds[0]
  const isFinished = competition.coverage.pending === 0
  const title = competition.competition + (competition.zone ? ` · Zona ${competition.zone}` : '')

  return <main className="report-shell tournament-shell" aria-labelledby="competition-title">
    <header className="hero">
      <p className="eyebrow">{competition.competition}{competition.zone ? ` · Zona ${competition.zone}` : ''} · {competition.season}</p>
      <h1 id="competition-title">{title}</h1>
      <p>{competition.tournament} · {competition.coverage.label} · Actualizado el {formatDate(competition.updated_at)}.</p>
      <div className="hero-actions">
        <button className="home-link" onClick={onBack}>← Torneos</button>
        <button className="home-link" onClick={onHome}>Inicio</button>
        {onForecast && <button className="home-link" onClick={onForecast}>Pronóstico de cierre →</button>}
        {onSeason && <button className="home-link" onClick={onSeason}>Temporada 2026 de Lanús →</button>}
      </div>
      <nav className="tournament-nav" aria-label="Secciones del torneo"><a href="#resumen">Resumen</a><a href="#marcas">Marcas</a><a href="#posiciones">Posiciones</a><a href="#fechas">Fechas</a><a href="#goleadores">Goleadores</a><a href="#disciplina">Disciplina</a></nav>
    </header>

    <section className="rule-note" aria-label="Regla de puntos">
      <strong>Cómo se puntúa:</strong> victoria {competition.points_rule.win} · empate {competition.points_rule.draw} · derrota {competition.points_rule.loss}. Suspendido: {competition.points_rule.suspended_win}/{competition.points_rule.suspended_loss} y CP. Desempate olímpico: primero los partidos entre los equipos igualados.
    </section>

    {sapa && <section id="resumen" className="sapa-spotlight" aria-label="Resumen de SAPA">
      <div className="sapa-spotlight-team">
        <p className="eyebrow">Nuestro equipo</p>
        <h2>S.A.P.A.</h2>
        <span className="sapa-spotlight-pos">#{sapa.pos} en la tabla</span>
      </div>
      <div className="sapa-spotlight-stats">
        <article><strong>{sapa.points}</strong><span>puntos</span></article>
        <article><strong>{sapa.played}</strong><span>jugados</span></article>
        <article><strong>{sapa.won}–{sapa.drawn}–{sapa.lost}</strong><span>G · E · P</span></article>
        <article><strong>{sapa.goals_for}</strong><span>goles a favor</span></article>
        <article><strong>{sapa.goals_against}</strong><span>goles en contra</span></article>
      </div>
      {sapaInsight && <div className="sapa-spotlight-extra">
        <div><strong>{percent(sapaInsight.points_effectiveness, 1)}</strong><span>efectividad de puntos</span></div>
        <div><strong>{decimal(sapaInsight.goals_for_per_game)}</strong><span>goles a favor por partido</span></div>
        <div><strong>{decimal(sapaInsight.goals_against_per_game)}</strong><span>goles en contra por partido</span></div>
        <div><strong>{sapaInsight.streaks.current_unbeaten.length}</strong><span>partidos sin perder</span></div>
        <div className="sapa-spotlight-form"><span>Últimos {sapaForm.length}</span><ResultStrip matches={sapaForm} compact label="Forma reciente de SAPA" /></div>
      </div>}
    </section>}

    <section id="marcas" className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Marcas</p><h2>Rachas y extremos del torneo</h2></div></div>
      <div className="record-grid">{competition.insights.records.map((record) => <article className="record-card" key={record.key}>
        <p>{record.label}</p>
        <strong>{record.club ?? record.clubs?.join(' · ')}</strong>
        <span>{record.unit === 'de los puntos' ? percent(record.value, 1) : decimal(record.value, record.value % 1 === 0 ? 0 : 1)} {record.unit}</span>
        <small>{record.detail}</small>
      </article>)}</div>
      <p className="result-legend-note">Verde = ganó · amarillo = empató · rojo = perdió.</p>
    </section>

    <section id="posiciones" className="dashboard-section">
      <div className="section-heading">
        <div><p className="eyebrow">Clasificación</p><h2>Tabla de posiciones</h2></div>
        <small>Ordenada con el desempate olímpico del torneo.</small>
      </div>
      <div className="table-wrap"><table className="player-table standings-table">
        <thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>CP</th><th>GF</th><th>GC</th><th>Dif</th><th>Pts</th></tr></thead>
        <tbody>{competition.standings.map((row: StandingRow) => <tr key={row.club} className={isSapa(row.club) ? 'sapa-row' : ''}>
          <td className="standings-pos">{row.pos}</td>
          <td className="standings-club"><strong>{row.club}</strong></td>
          <td>{row.played}</td><td>{row.won}</td><td>{row.drawn}</td><td>{row.lost}</td>
          <td>{row.penalized || '—'}</td><td>{row.goals_for}</td><td>{row.goals_against}</td>
          <td className={row.goal_difference > 0 ? 'diff-positive' : row.goal_difference < 0 ? 'diff-negative' : ''}>{signed(row.goal_difference)}</td>
          <td className="standings-points">{row.points}</td>
        </tr>)}</tbody>
      </table></div>
    </section>

    <section id="fechas" className="dashboard-section">
      <div className="section-heading">
        <div><p className="eyebrow">Fixture y resultados</p><h2>Fecha por fecha</h2></div>
        <small>{competition.coverage.matches_counted} partidos con resultado · {competition.coverage.pending} pendientes.</small>
      </div>
      <div className="round-picker" role="tablist" aria-label="Elegir fecha">{competition.rounds.map((row) => <button key={row.round} role="tab" aria-selected={row.round === selectedRound} className={row.round === selectedRound ? 'active' : ''} onClick={() => setSelectedRound(row.round)}>F{row.round}</button>)}</div>
      {round && <div className="round-panel">
        <div className="round-panel-head"><strong>Fecha {round.round}</strong><span>{formatDate(round.date)}</span></div>
        <div className="round-matches">{round.matches.map((match) => <MatchRow key={`${round.round}-${match.home}-${match.away}`} round={round} match={match} />)}</div>
      </div>}
    </section>

    <section id="goleadores" className="dashboard-section">
      <div className="section-heading">
        <div><p className="eyebrow">Goleadores</p><h2>Tabla de goleadores</h2></div>
        <label className="scorer-club-filter">Club <select aria-label="Filtrar goleadores por club" value={scorerClub} onChange={(event) => setScorerClub(event.target.value)}><option value="all">Top 30 del torneo</option>{scorerClubs.map((club) => <option key={club} value={club}>{club}</option>)}</select></label>
      </div>
      <div className="table-wrap"><table className="player-table scorers-table">
        <thead><tr><th>#</th><th>Jugador</th><th>Club</th><th>PJ</th><th>Goles</th><th>G/P</th><th>AM</th><th>2'</th><th>R</th><th>AZ</th></tr></thead>
        <tbody>{visibleScorers.map((row, index) => <tr key={`${row.name}-${row.club}`} className={isSapa(row.club) ? 'sapa-row' : ''}>
          <td>{index + 1}</td><td><strong>{row.name}</strong></td><td>{row.club}</td><td>{row.appearances}</td>
          <td className="scorers-goals">{row.goals}</td><td>{decimal(row.goals_per_game, 2)}</td>
          <td>{row.yellow}</td><td>{row.two_min}</td><td>{row.red}</td><td>{row.blue}</td>
        </tr>)}</tbody>
      </table></div>
      {scorerClub === 'all' && <p className="table-empty">Se muestran los 30 máximos goleadores. Elegí un club para ver su plantel completo.</p>}
    </section>

    <section id="disciplina" className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Disciplina</p><h2>Sanciones por club</h2></div><small>Amarillas · exclusiones 2' · rojas · azules por planilla oficial.</small></div>
      <div className="table-wrap"><table className="player-table clubs-table">
        <thead><tr><th>Club</th><th>Goles</th><th>Jugadores</th><th>AM</th><th>2'</th><th>R</th><th>AZ</th></tr></thead>
        <tbody>{competition.clubs.map((row) => <tr key={row.club} className={isSapa(row.club) ? 'sapa-row' : ''}>
          <td><strong>{row.club}</strong></td><td>{row.goals}</td><td>{row.players}</td><td>{row.yellow}</td><td>{row.two_min}</td><td>{row.red}</td><td>{row.blue}</td>
        </tr>)}</tbody>
      </table></div>
    </section>

    <footer className="tournament-footnote">{isFinished ? 'Torneo finalizado' : 'Torneo en curso'} · Datos derivados de planillas FEMEBAL confirmadas y resultados informados. No es la tabla oficial de FEMEBAL.</footer>
  </main>
}
