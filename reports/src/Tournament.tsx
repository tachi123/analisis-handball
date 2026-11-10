import type { PublicTournament } from './tournamentProjection'

const normalize = (name: string) => name.normalize('NFD').replace(/[\u0300-\u036f.\s]/g, '').toLowerCase()
const isSapa = (name: string) => normalize(name) === 'sapa'

export function Tournament({ tournament, onBack }: { tournament: PublicTournament; onBack: () => void }) {
  const sapa = tournament.standings.find((row) => isSapa(row.club))
  const sapaClub = tournament.clubs.find((row) => isSapa(row.club))
  const topScorers = tournament.scorers.slice(0, 20)
  const sapaScorers = tournament.scorers.filter((row) => isSapa(row.club)).slice(0, 8)

  return (
    <main className="report-shell tournament-shell" aria-labelledby="tournament-title">
      <header className="hero">
        <p className="eyebrow">FEMEBAL · Permanencia 2026 · Mayores 3ª Masculino</p>
        <h1 id="tournament-title">Torneo <span>en vivo</span></h1>
        <p>{tournament.coverage.label}</p>
        <button className="home-link" onClick={onBack}>← Partidos analizados</button>
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

      <section className="dashboard-section">
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

      <section className="dashboard-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Goleadores</p>
            <h2>Máximos artilleros</h2>
          </div>
          <small>Top {topScorers.length} del torneo · goles por planilla oficial.</small>
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
              {topScorers.map((row, index) => (
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
        <section className="dashboard-section">
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
