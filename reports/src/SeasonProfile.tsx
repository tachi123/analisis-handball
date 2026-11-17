import type { PublicCompetition, PublicForecast } from './publicCompetitions'
import { ResultLegend, ResultStrip, type StripMatch } from './resultStrip'
import { decimal, formatDate, formatShortDate, normalizedClub, percent, signed } from './competitionFormat'
import { annualTotals, attackComposition, rosterContinuity, seasonMatches, seasonScorers } from './seasonData'

const shortCompetition = (competition: PublicCompetition) => competition.competition.startsWith('Apertura') ? `Apertura ${competition.zone ?? ''}`.trim() : competition.competition
const competitionDisplay = (competition: PublicCompetition) => competition.competition + (competition.zone ? ` · Zona ${competition.zone}` : '')

const stripFor = (matches: ReturnType<typeof seasonMatches>): StripMatch[] => matches.map((match) => ({
  key: match.key,
  label: `F${match.round}`,
  result: match.result,
  detail: `Fecha ${match.round} · ${match.location === 'home' ? 'Local' : 'Visitante'} vs ${match.opponent} · ${match.goalsFor ?? '—'}–${match.goalsAgainst ?? '—'}`,
}))

const streakSpan = (streak: { length: number; from_round: number | null; to_round: number | null }) =>
  streak.length === 0 ? 'Sin racha' : streak.from_round === streak.to_round ? `Fecha ${streak.from_round}` : `Fechas ${streak.from_round}–${streak.to_round}`

export function SeasonProfile({ club, competitions, forecast, onBack, onHome, onForecast, onTournament }: {
  club: string
  competitions: PublicCompetition[]
  forecast: PublicForecast | null
  onBack: () => void
  onHome: () => void
  onForecast: () => void
  onTournament: () => void
}) {
  const blocks = competitions.map((competition) => ({
    competition,
    standing: competition.standings.find((row) => normalizedClub(row.club) === normalizedClub(club)),
    insight: competition.insights.clubs.find((row) => normalizedClub(row.club) === normalizedClub(club)),
    matches: seasonMatches(competition, club),
  })).filter((block) => block.standing)
  const primary = blocks[blocks.length - 1]
  const annual = annualTotals(competitions, club)
  const scorers = seasonScorers(competitions, club)
  const previousScorers = competitions.length > 1 ? seasonScorers([competitions[0]], club) : []
  const currentScorers = seasonScorers([competitions[competitions.length - 1]], club)
  const continuity = rosterContinuity(previousScorers, currentScorers)
  const previousBlock = blocks[0]
  const currentBlock = blocks[blocks.length - 1]
  const composition = blocks.length > 1
    ? attackComposition(previousScorers, currentScorers, previousBlock.standing?.goals_for ?? 0, currentBlock.standing?.goals_for ?? 0)
    : null
  const pending = blocks.flatMap((block) => block.matches.filter((match) => match.result === 'pending'))
  const pendingFixture = forecast?.fixtures.find((fixture) => normalizedClub(fixture.home) === normalizedClub(club) || normalizedClub(fixture.away) === normalizedClub(club))
  const rivalHome = pendingFixture ? normalizedClub(pendingFixture.home) === normalizedClub(club) : false
  const rivalWin = pendingFixture ? (rivalHome ? pendingFixture.home_win_probability : pendingFixture.away_win_probability) : 0
  const rivalLoss = pendingFixture ? (rivalHome ? pendingFixture.away_win_probability : pendingFixture.home_win_probability) : 0

  return <main className="report-shell tournament-shell season-shell" aria-labelledby="season-title">
    <header className="hero">
      <p className="eyebrow">Temporada 2026 · {club}</p>
      <h1 id="season-title">{club} <span>2026</span></h1>
      <p>{annual.played} partidos jugados entre {competitions.map(shortCompetition).join(' y ')}{pending.length ? ` · ${pending.length} pendiente` : ''} · {formatDate(primary?.competition.updated_at ?? null)}.</p>
      <div className="hero-actions">
        <button className="home-link" onClick={onBack}>{forecast ? '← Pronóstico' : '← Torneos'}</button>
        <button className="home-link" onClick={onTournament}>Ver Permanencia</button>
        <button className="home-link" onClick={onForecast}>Pronóstico de cierre</button>
        <button className="home-link" onClick={onHome}>Inicio</button>
      </div>
    </header>

    <section className="annual-summary" aria-label="Resumen anual">
      <article><strong>{annual.played}</strong><span>jugados</span></article>
      <article><strong>{annual.points}</strong><span>puntos</span></article>
      <article><strong>{percent(annual.maxPoints ? annual.points / annual.maxPoints : 0, 1)}</strong><span>efectividad</span></article>
      <article><strong>{annual.won}–{annual.drawn}–{annual.lost}</strong><span>G · E · P</span></article>
      <article><strong>{decimal(annual.played ? annual.goalsFor / annual.played : 0)}</strong><span>GF por partido</span></article>
      <article><strong>{decimal(annual.played ? annual.goalsAgainst / annual.played : 0)}</strong><span>GC por partido</span></article>
    </section>

    <section className="season-blocks" aria-label="Competencias del año">
      {blocks.map((block) => <article className="season-block" key={block.competition.public_key}>
        <div className="season-block-head">
          <p className="eyebrow">{shortCompetition(block.competition)}</p>
          <h2>{competitionDisplay(block.competition)}</h2>
          <span className="position-pill">{block.standing?.pos}º</span>
        </div>
        <div className="season-block-stats">
          <div><strong>{block.standing?.points}</strong><span>puntos</span></div>
          <div><strong>{block.standing?.won}–{block.standing?.drawn}–{block.standing?.lost}</strong><span>G · E · P</span></div>
          <div><strong>{decimal(block.insight?.goals_for_per_game ?? 0)}</strong><span>GF / partido</span></div>
          <div><strong>{decimal(block.insight?.goals_against_per_game ?? 0)}</strong><span>GC / partido</span></div>
          <div><strong>{percent(block.insight?.points_effectiveness ?? 0, 1)}</strong><span>efectividad</span></div>
        </div>
        <ResultStrip matches={stripFor(block.matches)} label={`Resultados de ${club} en ${shortCompetition(block.competition)}`} />
      </article>)}
    </section>

    <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Todos los partidos</p><h2>El año completo, fecha por fecha</h2></div><small>Verde G · amarillo E · rojo P. El color refuerza el resultado; siempre está el texto.</small></div>
      {blocks.map((block) => <div className="season-match-block" key={block.competition.public_key}>
        <div className="season-match-head"><h3>{competitionDisplay(block.competition)}</h3><span>{block.matches.length} partidos</span></div>
        <ResultStrip matches={stripFor(block.matches)} label={`Partidos de ${club} en ${shortCompetition(block.competition)}`} />
        <div className="season-match-list">{block.matches.map((match) => {
          const isPending = match.result === 'pending'
          const matchFixture = isPending && forecast?.fixtures.find((fixture) => (normalizedClub(fixture.home) === normalizedClub(club) && normalizedClub(fixture.away) === normalizedClub(match.opponent)) || (normalizedClub(fixture.away) === normalizedClub(club) && normalizedClub(fixture.home) === normalizedClub(match.opponent)))
          const home = matchFixture ? normalizedClub(matchFixture.home) === normalizedClub(club) : false
          return <article className={`season-match-row ${match.result}`} key={match.key}>
            <span className="season-match-round">F{match.round}</span>
            <span className="season-match-date">{formatShortDate(match.date)}</span>
            <span className="season-match-venue">{match.location === 'home' ? 'Local' : 'Visitante'}</span>
            <strong className="season-match-opponent">vs {match.opponent}</strong>
            <span className="season-match-score">{isPending ? '—' : `${match.goalsFor}–${match.goalsAgainst}`}</span>
            <span className={`result-pill inline ${match.result}`}><b>{match.result === 'win' ? 'G' : match.result === 'draw' ? 'E' : match.result === 'loss' ? 'P' : '·'}</b><em>{isPending ? 'Pendiente' : match.result === 'win' ? 'Ganó' : match.result === 'draw' ? 'Empató' : 'Perdió'}</em></span>
            {matchFixture && <span className="season-match-probabilities">G {percent(home ? matchFixture.home_win_probability : matchFixture.away_win_probability)} · E {percent(matchFixture.draw_probability)} · P {percent(home ? matchFixture.away_win_probability : matchFixture.home_win_probability)}</span>}
          </article>
        })}</div>
      </div>)}
      <ResultLegend />
    </section>

    {composition && <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Composición del ataque</p><h2>¿Cambió el patrón de goleadores?</h2></div><small>Goles por grupo y concentración. La planilla describe; no atribuye causas.</small></div>
      <div className="attack-composition-grid">
        <div className="table-wrap"><table className="player-table attack-table">
          <thead><tr><th>Grupo</th><th>{previousBlock ? shortCompetition(previousBlock.competition) : 'Apertura'}</th><th>{currentBlock ? shortCompetition(currentBlock.competition) : 'Permanencia'}</th></tr></thead>
          <tbody>
            <tr><td>Retenidos ({composition.retained.players})</td><td>{composition.retained.previousGoals} ({percent(composition.previousTotal ? composition.retained.previousGoals / composition.previousTotal : 0, 1)})</td><td>{composition.retained.currentGoals} ({percent(composition.currentTotal ? composition.retained.currentGoals / composition.currentTotal : 0, 1)})</td></tr>
            <tr><td>Se fueron ({composition.departed.players})</td><td>{composition.departed.goals} ({percent(composition.previousTotal ? composition.departed.goals / composition.previousTotal : 0, 1)})</td><td>—</td></tr>
            <tr><td>Llegaron ({composition.arrived.players})</td><td>—</td><td>{composition.arrived.goals} ({percent(composition.currentTotal ? composition.arrived.goals / composition.currentTotal : 0, 1)})</td></tr>
            <tr><td><strong>Total</strong></td><td><strong>{composition.previousTotal}</strong></td><td><strong>{composition.currentTotal}</strong></td></tr>
          </tbody>
        </table></div>
        <div className="concentration-cards">
          <article><p>Top 1</p><strong>{percent(composition.concentration.previous.top1, 1)} → {percent(composition.concentration.current.top1, 1)}</strong><span>goles del máximo goleador sobre el total</span></article>
          <article><p>Top 3</p><strong>{percent(composition.concentration.previous.top3, 1)} → {percent(composition.concentration.current.top3, 1)}</strong><span>concentración del podio de goleadores</span></article>
          <article><p>Top 5</p><strong>{percent(composition.concentration.previous.top5, 1)} → {percent(composition.concentration.current.top5, 1)}</strong><span>concentración de los cinco máximos</span></article>
          <article><p>Con 10+ goles</p><strong>{composition.concentration.previous.scorers10} → {composition.concentration.current.scorers10}</strong><span>jugadores</span></article>
          <article><p>Con 20+ goles</p><strong>{composition.concentration.previous.scorers20} → {composition.concentration.current.scorers20}</strong><span>jugadores</span></article>
        </div>
      </div>
      <div className="attack-notes">
        <p><strong>Llegaron:</strong> {composition.arrived.details.map((row) => `${row.name} ${row.goals}/${row.appearances}`).join(' · ') || '—'}</p>
        <p><strong>Se fueron:</strong> {composition.departed.details.slice(0, 5).map((row) => `${row.name} ${row.goals}/${row.appearances}`).join(' · ') || '—'}{composition.departed.details.length > 5 ? ` · y ${composition.departed.details.length - 5} más` : ''}</p>
      </div>
      <p className="result-legend-note">La planilla no registra minutos, puestos, tiros ni asistencias. Por eso podemos mostrar cuánto aportaron los ingresos y si la concentración cambió, pero no afirmar que causaron la mejora.</p>
    </section>}

    <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Goleadores del año</p><h2>Quiénes sostuvieron el ataque</h2></div><small>Goles / partidos. La muestra importa: no es lo mismo 29 goles en 5 partidos que 116 en 27.</small></div>
      <div className="table-wrap"><table className="player-table season-scorers-table">
        <thead><tr><th>Jugador</th><th>Total</th><th>G/P</th>{competitions.map((competition) => <th key={competition.public_key}>{shortCompetition(competition)}</th>)}</tr></thead>
        <tbody>{scorers.slice(0, 12).map((row) => <tr key={row.name}>
          <td><strong>{row.name}</strong></td>
          <td className="scorers-goals">{row.goals} / {row.appearances}</td>
          <td>{decimal(row.appearances ? row.goals / row.appearances : 0, 2)}</td>
          {row.byCompetition.map((block) => <td key={block.key}>{block.goals} / {block.appearances}</td>)}
        </tr>)}</tbody>
      </table></div>
      {scorers.length > 12 && <details className="season-more-scorers"><summary>Ver los {scorers.length - 12} jugadores restantes</summary><div className="table-wrap"><table className="player-table"><thead><tr><th>Jugador</th><th>Total</th><th>G/P</th>{competitions.map((competition) => <th key={competition.public_key}>{shortCompetition(competition)}</th>)}</tr></thead><tbody>{scorers.slice(12).map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.goals} / {row.appearances}</td><td>{decimal(row.appearances ? row.goals / row.appearances : 0, 2)}</td>{row.byCompetition.map((block) => <td key={block.key}>{block.goals} / {block.appearances}</td>)}</tr>)}</tbody></table></div></details>}
    </section>

    {competitions.length > 1 && <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Continuidad</p><h2>¿Siguen los mismos jugadores?</h2></div><small>Coincidencia de nombres normalizados dentro del mismo club. No es un registro de pases.</small></div>
      <div className="continuity-card">
        <strong>{continuity.shared} de {continuity.current}</strong>
        <span>jugadores de {primary ? shortCompetition(primary.competition) : 'la competencia actual'} ya figuraban en {shortCompetition(competitions[0])}.</span>
        <b>{percent(continuity.retained, 1)}</b>
        <small>Aproximación: un cambio de grafía cuenta como jugador nuevo y dos personas con el mismo nombre normalizado se cuentan una sola vez.</small>
      </div>
    </section>}

    {primary?.insight && <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Marcas</p><h2>Rachas y rendimiento en {shortCompetition(primary.competition)}</h2></div><small>Hechos observados, no causas tácticas.</small></div>
      <div className="record-grid">
        <article className="record-card"><p>Mayor racha sin perder</p><strong>{primary.insight.streaks.longest_unbeaten.length} partidos</strong><span>{streakSpan(primary.insight.streaks.longest_unbeaten)}</span></article>
        <article className="record-card"><p>Mayor racha de victorias</p><strong>{primary.insight.streaks.longest_win.length} partidos</strong><span>{streakSpan(primary.insight.streaks.longest_win)}</span></article>
        <article className="record-card"><p>Forma reciente</p><strong>{primary.insight.form_last_5.points} / {primary.insight.form_last_5.max_points}</strong><span>{primary.insight.form_last_5.sequence.join(' · ')}</span></article>
        <article className="record-card"><p>Como local</p><strong>{percent(primary.insight.home.points_effectiveness, 1)}</strong><span>{primary.insight.home.points} de {primary.insight.home.max_points} puntos</span></article>
        <article className="record-card"><p>Como visitante</p><strong>{percent(primary.insight.away.points_effectiveness, 1)}</strong><span>{primary.insight.away.points} de {primary.insight.away.max_points} puntos</span></article>
        <article className="record-card"><p>Contra el top 5</p><strong>{primary.insight.opponent_tiers.top_five.points} / {primary.insight.opponent_tiers.top_five.max_points}</strong><span>{percent(primary.insight.opponent_tiers.top_five.points_effectiveness, 1)} de efectividad</span></article>
        <article className="record-card"><p>Contra los últimos 5</p><strong>{primary.insight.opponent_tiers.bottom_five.points} / {primary.insight.opponent_tiers.bottom_five.max_points}</strong><span>{percent(primary.insight.opponent_tiers.bottom_five.points_effectiveness, 1)} de efectividad</span></article>
        {primary.insight.biggest_win && <article className="record-card"><p>Mayor victoria</p><strong>{primary.insight.biggest_win.goals_for}–{primary.insight.biggest_win.goals_against}</strong><span>vs {primary.insight.biggest_win.opponent} · F{primary.insight.biggest_win.round}</span></article>}
        {primary.insight.biggest_loss && <article className="record-card"><p>Mayor derrota</p><strong>{primary.insight.biggest_loss.goals_for}–{primary.insight.biggest_loss.goals_against}</strong><span>vs {primary.insight.biggest_loss.opponent} · F{primary.insight.biggest_loss.round}</span></article>}
      </div>
      <p className="table-empty">Diferencia de gol anual: {signed(annual.goalsFor - annual.goalsAgainst)} · {annual.goalsFor} goles a favor y {annual.goalsAgainst} en contra en {annual.played} partidos.</p>
    </section>}

    {pending.length > 0 && <section className="dashboard-section pending-section">
      <div className="section-heading"><div><p className="eyebrow">Pendiente</p><h2>El próximo partido</h2></div><small>Probabilidades estimadas, no una cuota.</small></div>
      {pending.map((match) => <article className="pending-card" key={match.key}>
        <strong>{match.location === 'home' ? `${club} vs ${match.opponent}` : `${match.opponent} vs ${club}`}</strong>
        <span>Fecha {match.round} · {formatDate(match.date)} · {match.location === 'home' ? 'Local' : 'Visitante'}</span>
        {pendingFixture ? <div className="outcome-probabilities"><span><b>{percent(rivalWin)}</b> gana {club}</span><span><b>{percent(pendingFixture.draw_probability)}</b> empata</span><span><b>{percent(rivalLoss)}</b> pierde {club}</span></div> : <small>Sin proyección publicada para este partido.</small>}
      </article>)}
    </section>}

    <footer className="tournament-footnote">Datos derivados de planillas FEMEBAL confirmadas y resultados informados. La ficha anual compara competencias distintas; los totales no son una tabla de posiciones.</footer>
  </main>
}
