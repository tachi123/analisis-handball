import { useState } from 'react'
import type { PublicTournament } from './tournamentProjection'

const normalize = (name: string) => name.normalize('NFD').replace(/[\u0300-\u036f.\s]/g, '').toLowerCase()
const isSapa = (name: string) => normalize(name) === 'sapa'
const percent = (value: number) => value > 0 && value < 0.001 ? '<0,1%' : `${Math.round(value * 100)}%`
const updatedLabel = (value: string) => {
  const [year, month, day] = value.split('-')
  return year && month && day ? `Actualizado el ${day}/${month}/${year}` : 'Actualización sin fecha'
}

export function Tournament({ tournament, onBack }: { tournament: PublicTournament; onBack: () => void }) {
  const sapa = tournament.standings.find((row) => isSapa(row.club))
  const sapaClub = tournament.clubs.find((row) => isSapa(row.club))
  const topScorers = tournament.scorers.slice(0, 20)
  const sapaScorers = tournament.scorers.filter((row) => isSapa(row.club)).slice(0, 8)
  const [scorerClub, setScorerClub] = useState('all')
  const scorerClubs = [...new Set(tournament.scorers.map((row) => row.club))].sort((left, right) => left.localeCompare(right, 'es'))
  const visibleScorers = scorerClub === 'all' ? topScorers : tournament.scorers.filter((row) => row.club === scorerClub)
  const forecast = tournament.forecast
  const contenders = forecast?.teams.filter((team) => team.champion_probability > 0) ?? []
  const forecastRounds = [...new Set(forecast?.fixtures.map((fixture) => fixture.round) ?? [])].sort((left, right) => left - right)
  const upcomingSapa = forecast?.fixtures.filter((fixture) => isSapa(fixture.home) || isSapa(fixture.away)) ?? []

  return (
    <main className="report-shell tournament-shell" aria-labelledby="tournament-title">
      <header className="hero">
        <p className="eyebrow">FEMEBAL · Permanencia 2026 · Mayores 3ª Masculino</p>
        <h1 id="tournament-title">Torneo <span>2026</span></h1>
        <p>{tournament.coverage.label} · {updatedLabel(tournament.updated_at)}.</p>
        <button className="home-link" onClick={onBack}>← Partidos analizados</button>
        <nav className="tournament-nav" aria-label="Secciones del torneo"><a href="#forecast">Proyección</a><a href="#standings">Posiciones</a><a href="#scorers">Goleadores</a><a href="#discipline">Disciplina</a></nav>
      </header>

      {sapa && (
        <section className="sapa-spotlight" aria-label="Resumen de SAPA">
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
        </section>
      )}

      {forecast && <section id="forecast" className="forecast-dashboard" aria-labelledby="forecast-title">
        <div className="section-heading"><div><p className="eyebrow">Proyección estadística</p><h2 id="forecast-title">Camino al campeonato</h2></div><small>{forecast.simulations.toLocaleString('es-AR')} simulaciones del fixture pendiente.</small></div>
        <div className="forecast-grid">
          <article className="championship-card">
            <p>Probabilidad de SAPA</p>
            <strong>{percent(forecast.teams.find((team) => isSapa(team.club))?.champion_probability ?? 0)}</strong>
            <span>de terminar campeón</span>
          </article>
          <article className="contenders-card"><p>Equipos con chances simuladas</p><strong>{contenders.length}</strong><span>aspirantes al campeonato</span></article>
        </div>
        <div className="forecast-table-wrap"><table className="forecast-table"><thead><tr><th>Equipo</th><th>Campeón</th>{forecastRounds.map((round) => <th key={round}>Fecha {round}</th>)}</tr></thead><tbody>{contenders.map((team) => <tr key={team.club} className={isSapa(team.club) ? 'sapa-forecast-row' : ''}><td><strong>{team.club}</strong></td><td className="forecast-champion"><strong>{percent(team.champion_probability)}</strong></td>{forecastRounds.map((round) => { const fixture = forecast.fixtures.find((item) => item.round === round && (item.home === team.club || item.away === team.club)); if (!fixture) return <td key={round}>—</td>; const home = fixture.home === team.club; const win = home ? fixture.home_win_probability : fixture.away_win_probability; const loss = home ? fixture.away_win_probability : fixture.home_win_probability; const rival = home ? fixture.away : fixture.home; return <td key={round} className="forecast-match"><strong>{home ? 'vs' : '@'} {rival}</strong><span><b>{percent(win)}</b> G · {percent(fixture.draw_probability)} E · {percent(loss)} P</span></td> })}</tr>)}</tbody></table></div>
        {upcomingSapa.length > 0 && <div className="forecast-fixtures"><p className="eyebrow">Próximos partidos de SAPA</p>{upcomingSapa.map((fixture) => { const sapaHome = isSapa(fixture.home); const win = sapaHome ? fixture.home_win_probability : fixture.away_win_probability; const loss = sapaHome ? fixture.away_win_probability : fixture.home_win_probability; const rival = sapaHome ? fixture.away : fixture.home; return <article key={`${fixture.round}-${fixture.home}-${fixture.away}`}><div><strong>Fecha {fixture.round} · {sapaHome ? 'SAPA vs' : 'vs'} {rival}</strong><span>{fixture.date ?? 'Fecha a confirmar'}</span></div><div className="outcome-probabilities"><span><b>{percent(win)}</b> gana</span><span><b>{percent(fixture.draw_probability)}</b> empata</span><span><b>{percent(loss)}</b> pierde</span></div></article> })}</div>}
        <details className="forecast-method"><summary>Cómo leer esta proyección</summary><p>{forecast.methodology} Usa la regla vigente de puntos y los desempates por diferencia de gol y goles a favor. Los resultados informados sin planilla pueden cambiar cuando se confirme la planilla oficial.</p></details>
      </section>}

      <section id="standings" className="dashboard-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Clasificación</p>
            <h2>Tabla de posiciones</h2>
          </div>
          <small>Resultados informados del torneo; no reemplazan la tabla oficial de FEMEBAL.</small>
        </div>
        <div className="table-wrap">
          <table className="player-table standings-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Equipo</th>
                <th>PJ</th>
                <th>G</th>
                <th>E</th>
                <th>P</th>
                <th>CP</th>
                <th>GF</th>
                <th>GC</th>
                <th>Dif</th>
                <th>Pts</th>
              </tr>
            </thead>
            <tbody>
              {tournament.standings.map((row) => (
                <tr key={row.club} className={isSapa(row.club) ? 'sapa-row' : ''}>
                  <td className="standings-pos">{row.pos}</td>
                  <td className="standings-club"><strong>{row.club}</strong></td>
                  <td>{row.played}</td>
                  <td>{row.won}</td>
                  <td>{row.drawn}</td>
                  <td>{row.lost}</td>
                  <td>{row.penalized || '—'}</td>
                  <td>{row.goals_for}</td>
                  <td>{row.goals_against}</td>
                  <td className={row.goal_difference > 0 ? 'diff-positive' : row.goal_difference < 0 ? 'diff-negative' : ''}>{row.goal_difference > 0 ? `+${row.goal_difference}` : row.goal_difference}</td>
                  <td className="standings-points">{row.points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="scorers" className="dashboard-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Goleadores</p>
            <h2>Máximos artilleros</h2>
          </div>
          <label className="scorer-club-filter">Club <select aria-label="Filtrar goleadores por club" value={scorerClub} onChange={(event) => setScorerClub(event.target.value)}><option value="all">Top del torneo</option>{scorerClubs.map((club) => <option key={club} value={club}>{club}</option>)}</select></label>
        </div>
        <div className="table-wrap">
          <table className="player-table scorers-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Jugador</th>
                <th>Club</th>
                <th>PJ</th>
                <th>Goles</th>
                <th>G/P</th>
              </tr>
            </thead>
            <tbody>
              {visibleScorers.map((row, index) => (
                <tr key={`${row.name}-${row.club}`} className={isSapa(row.club) ? 'sapa-row' : ''}>
                  <td>{index + 1}</td>
                  <td><strong>{row.name}</strong></td>
                  <td>{row.club}</td>
                  <td>{row.appearances}</td>
                  <td className="scorers-goals">{row.goals}</td>
                  <td>{row.goals_per_game.toFixed(2).replace('.', ',')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {visibleScorers.length === 0 && <p className="table-empty">No hay goleadores registrados para este club.</p>}
        {sapaScorers.length > 0 && (
          <div className="sapa-scorers">
            <p className="eyebrow">Goleadores de SAPA</p>
            <ul>
              {sapaScorers.map((row) => (
                <li key={row.name}><strong>{row.name}</strong><span>{row.goals} goles · {row.appearances} PJ</span></li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {sapaClub && (
        <section id="discipline" className="dashboard-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Disciplina</p>
              <h2>Sanciones por club</h2>
            </div>
            <small>Amarillas · exclusiones 2' · rojas · azules por planilla oficial.</small>
          </div>
          <div className="table-wrap">
            <table className="player-table clubs-table">
              <thead>
                <tr>
                  <th>Club</th>
                  <th>Goles</th>
                  <th>Jugadores</th>
                  <th>AM</th>
                  <th>2'</th>
                  <th>R</th>
                  <th>AZ</th>
                </tr>
              </thead>
              <tbody>
                {tournament.clubs.map((row) => (
                  <tr key={row.club} className={isSapa(row.club) ? 'sapa-row' : ''}>
                    <td><strong>{row.club}</strong></td>
                    <td>{row.goals}</td>
                    <td>{row.players}</td>
                    <td>{row.yellow}</td>
                    <td>{row.two_min}</td>
                    <td>{row.red}</td>
                    <td>{row.blue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <footer className="tournament-footnote">Datos derivados de las planillas oficiales FEMEBAL confirmadas. Cobertura parcial según fechas jugadas.</footer>
    </main>
  )
}
