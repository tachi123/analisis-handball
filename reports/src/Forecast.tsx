import { useState } from 'react'
import type { PublicCompetition, PublicForecast } from './publicCompetitions'
import { ResultLegend, ResultStrip, type StripMatch } from './resultStrip'
import { decimal, formatDate, isSapa, percent, tinyPercent } from './competitionFormat'

function campaignStrip(team: PublicForecast['teams'][number]): StripMatch[] {
  return team.campaign.map((match) => ({
    key: `F${match.round}-${match.opponent}`,
    label: `F${match.round}`,
    result: match.result,
    detail: `Fecha ${match.round} · ${match.location === 'home' ? 'Local' : 'Visitante'} vs ${match.opponent} · ${match.goals_for}–${match.goals_against} · ${match.result === 'win' ? 'Ganó' : match.result === 'draw' ? 'Empató' : 'Perdió'}`,
  }))
}

function CampaignList({ team }: { team: PublicForecast['teams'][number] }) {
  return <div className="campaign-list">
    <ResultStrip matches={campaignStrip(team)} compact label={`Campaña de ${team.club}`} />
    <div className="campaign-table-wrap"><table className="player-table campaign-table">
      <thead><tr><th>Fecha</th><th>Día</th><th>Cond.</th><th>Rival</th><th>Resultado</th><th>Marcador</th></tr></thead>
      <tbody>{team.campaign.map((match) => <tr key={`${match.round}-${match.opponent}`}>
        <td>F{match.round}</td>
        <td>{formatDate(match.date)}</td>
        <td>{match.location === 'home' ? 'Local' : 'Visitante'}</td>
        <td><strong>{match.opponent}</strong></td>
        <td><span className={`result-pill inline ${match.result}`}><b>{match.result === 'win' ? 'G' : match.result === 'draw' ? 'E' : 'P'}</b><em>{match.result === 'win' ? 'Ganó' : match.result === 'draw' ? 'Empató' : 'Perdió'}</em></span></td>
        <td>{match.goals_for}–{match.goals_against}</td>
      </tr>)}</tbody>
    </table></div>
  </div>
}

export function Forecast({ forecast, tournament, onBack, onHome, onTournament, onSeason }: {
  forecast: PublicForecast
  tournament: PublicCompetition | null
  onBack: () => void
  onHome: () => void
  onTournament: () => void
  onSeason: () => void
}) {
  const [showAll, setShowAll] = useState(false)
  const sapa = forecast.teams.find((team) => isSapa(team.club))
  const sapaFixture = forecast.fixtures.find((fixture) => isSapa(fixture.home) || isSapa(fixture.away))
  const contenders = forecast.teams.filter((team) => team.podium_probability > 0 || isSapa(team.club))
  const visible = showAll ? contenders : contenders.slice(0, 8)
  const sapaHome = sapaFixture ? isSapa(sapaFixture.home) : false
  const sapaWin = sapaFixture ? (sapaHome ? sapaFixture.home_win_probability : sapaFixture.away_win_probability) : 0
  const sapaLoss = sapaFixture ? (sapaHome ? sapaFixture.away_win_probability : sapaFixture.home_win_probability) : 0
  const sapaRival = sapaFixture ? (sapaHome ? sapaFixture.away : sapaFixture.home) : forecast.rival_profile.club
  const formSummary = (team: PublicForecast['teams'][number]) => {
    const last = team.campaign.slice(-5)
    const points = last.reduce((total, match) => total + (match.result === 'win' ? forecast.points_rule.win : match.result === 'draw' ? forecast.points_rule.draw : forecast.points_rule.loss), 0)
    return { points, max: last.length * forecast.points_rule.win }
  }

  return <main className="report-shell tournament-shell forecast-shell" aria-labelledby="forecast-page-title">
    <header className="hero">
      <p className="eyebrow">Pronóstico · {forecast.competition} · {forecast.season}</p>
      <h1 id="forecast-page-title">Cierre y <span>podio</span></h1>
      <p>Actualizado el {formatDate(forecast.updated_at)}.</p>
      <div className="hero-actions">
        <button className="home-link" onClick={onBack}>← Torneos</button>
        <button className="home-link" onClick={onHome}>Inicio</button>
        <button className="home-link" onClick={onTournament}>Ver torneo →</button>
        {forecast.rival_profile.club && <button className="home-link" onClick={onSeason}>Ver temporada 2026 de {forecast.rival_profile.club} →</button>}
      </div>
    </header>

    <section className="sapa-forecast-panel" aria-label="Pronóstico de SAPA">
      <div className="sapa-forecast-title">
        <p className="eyebrow">Nuestro equipo</p>
        <h2>S.A.P.A.</h2>
        <p>Estimación estadística.</p>
      </div>
      {sapa ? <div className="finish-cards">
        <article><strong>{tinyPercent(sapa.finish_probabilities.first)}</strong><span>1.º</span></article>
        <article><strong>{tinyPercent(sapa.finish_probabilities.second)}</strong><span>2.º</span></article>
        <article><strong>{tinyPercent(sapa.finish_probabilities.third)}</strong><span>3.º</span></article>
        <article className="podium"><strong>{tinyPercent(sapa.podium_probability)}</strong><span>Podio</span></article>
        <article><strong>{decimal(sapa.expected_position, 2)}</strong><span>Puesto esperado</span></article>
      </div> : <p className="table-empty">SAPA no aparece en la proyección de este torneo.</p>}
      {sapaFixture && <article className="sapa-next-fixture">
        <div><p className="eyebrow">Próximo partido</p><strong>{sapaHome ? 'SAPA vs' : 'vs'} {sapaRival}</strong><span>Fecha {sapaFixture.round} · {formatDate(sapaFixture.date)} · {sapaHome ? 'Local' : 'Visitante'}</span></div>
        <div className="outcome-probabilities"><span><b>{percent(sapaWin)}</b> gana</span><span><b>{percent(sapaFixture.draw_probability)}</b> empata</span><span><b>{percent(sapaLoss)}</b> pierde</span></div>
      </article>}
    </section>

    <section className="dashboard-section">
      <div className="section-heading">
        <div><p className="eyebrow">Panorama de podio</p><h2>Quién puede terminar 1.º, 2.º o 3.º</h2></div>
        <small>Podio = 1.º + 2.º + 3.º.</small>
      </div>
      <div className="table-wrap podium-wrap"><table className="player-table podium-table">
        <thead><tr><th>Equipo</th><th>1.º</th><th>2.º</th><th>3.º</th><th>Podio</th><th>Puesto esp.</th><th>Últimos 5</th></tr></thead>
        <tbody>{visible.map((team) => <tr key={team.club} className={isSapa(team.club) ? 'sapa-row' : ''}>
          <td><strong>{team.club}</strong></td>
          <td>{tinyPercent(team.finish_probabilities.first)}</td>
          <td>{tinyPercent(team.finish_probabilities.second)}</td>
          <td>{tinyPercent(team.finish_probabilities.third)}</td>
          <td className="podium-value">{tinyPercent(team.podium_probability)}</td>
          <td>{decimal(team.expected_position, 2)}</td>
          <td><div className="form-cell"><ResultStrip matches={campaignStrip(team).slice(-5)} compact label={`Últimos 5 de ${team.club}`} /><small>{formSummary(team).points} / {formSummary(team).max} pts</small></div></td>
        </tr>)}</tbody>
      </table></div>
      {contenders.length > 8 && <button className="show-all" onClick={() => setShowAll(!showAll)}>{showAll ? 'Ver menos' : `Ver todos los equipos (${contenders.length})`}</button>}
      <ResultLegend />
      <p className="result-legend-note">Cada pastilla es una fecha: verde G (ganó), amarillo E (empató), rojo P (perdió). En la tabla se ven las últimas 5; el camino completo, con rival y marcador, está en «Campañas».</p>
    </section>

    <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Campañas</p><h2>El camino jugado de cada aspirante</h2></div></div>
      <div className="campaign-details">{contenders.map((team) => <details key={team.club} open={isSapa(team.club)}>
        <summary><span><strong>{team.club}</strong><small>{team.campaign.length} partidos jugados · {tinyPercent(team.podium_probability)} de podio</small></span><span className="summary-strip"><ResultStrip matches={campaignStrip(team)} compact label={`Campaña de ${team.club}`} /></span></summary>
        <CampaignList team={team} />
      </details>)}</div>
    </section>

    <section className="dashboard-section">
      <div className="section-heading"><div><p className="eyebrow">Fecha final</p><h2>Todos los cruces pendientes</h2></div><small>{forecast.fixtures.length} partidos · probabilidades G/E/P.</small></div>
      <div className="forecast-fixtures fixture-grid">{forecast.fixtures.map((fixture) => {
        const home = isSapa(fixture.home)
        const away = isSapa(fixture.away)
        return <article key={`${fixture.round}-${fixture.home}-${fixture.away}`} className={home || away ? 'sapa-fixture' : ''}>
          <div><strong>{fixture.home} vs {fixture.away}</strong><span>Fecha {fixture.round} · {formatDate(fixture.date)}</span></div>
          <div className="outcome-probabilities"><span><b>{percent(fixture.home_win_probability)}</b> local</span><span><b>{percent(fixture.draw_probability)}</b> empate</span><span><b>{percent(fixture.away_win_probability)}</b> visitante</span></div>
        </article>
      })}</div>
    </section>

    {tournament && <p className="table-empty">Cobertura del torneo: {tournament.coverage.label}</p>}
    <footer className="tournament-footnote">Datos derivados de planillas FEMEBAL confirmadas y resultados informados.</footer>
  </main>
}
