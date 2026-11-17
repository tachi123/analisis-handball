import type { PublicTournamentCatalog } from './publicCompetitions'
import { formatDate } from './competitionFormat'

export function Competitions({ catalog, onOpen, onForecast, onHome }: {
  catalog: PublicTournamentCatalog
  onOpen: (key: string) => void
  onForecast: () => void
  onHome: () => void
}) {
  const forecastEntry = catalog.tournaments.find((entry) => entry.forecast_file)
  return <main className="report-shell tournament-shell" aria-labelledby="competitions-title">
    <header className="hero">
      <p className="eyebrow">FEMEBAL · Temporada 2026</p>
      <h1 id="competitions-title">Torneos <span>2026</span></h1>
      <p>Resultados y estadísticas derivados de las planillas cargadas.</p>
      <div className="hero-actions">
        <button className="home-link" onClick={onHome}>← Inicio</button>
        {forecastEntry && <button className="home-link" onClick={onForecast}>Pronóstico de cierre →</button>}
      </div>
    </header>

    <section className="competition-cards" aria-label="Torneos de 2026">
      {catalog.tournaments.map((entry) => <article className="competition-card" key={entry.key}>
        <div className="competition-card-head">
          <p className="eyebrow">{entry.competition}{entry.zone ? ` · Zona ${entry.zone}` : ''}</p>
          <h2>{entry.label}</h2>
          <span className={`status-pill ${entry.status}`}>{entry.status === 'in_progress' ? 'En curso' : 'Finalizado'}</span>
        </div>
        {entry.summary.sapa && <div className="competition-card-sapa">
          <div><strong>#{entry.summary.sapa.position}</strong><span>SAPA en la tabla</span></div>
          <div><strong>{entry.summary.sapa.points}</strong><span>puntos</span></div>
          <div><strong>{entry.summary.sapa.played}</strong><span>jugados</span></div>
        </div>}
        {entry.next_match ? <p className="competition-card-next">
          Próximo: {entry.next_match.location === 'home' ? 'SAPA vs' : 'vs'} <strong>{entry.next_match.opponent}</strong>
          <span>Fecha {entry.next_match.round} · {formatDate(entry.next_match.date)}</span>
        </p> : <p className="competition-card-next muted">Sin partidos pendientes en el fixture cargado.</p>}
        <p className="competition-card-coverage">{entry.coverage.label}</p>
        <div className="competition-card-actions">
          <button onClick={() => onOpen(entry.key)}>Ver torneo</button>
          {entry.forecast_file && <button className="secondary" onClick={onForecast}>Pronóstico</button>}
        </div>
      </article>)}
    </section>

    <section className="catalog-note" aria-label="Regla de puntos">
      <div>
        <p className="eyebrow">Cómo se puntúa</p>
        <h3>Victoria 3 · Empate 2 · Derrota 1</h3>
        <p>Un partido suspendido otorga 3 puntos al ganador y 0 al perdedor, y se marca como CP. Por eso una campaña de 11 victorias puede sumar 37 puntos.</p>
      </div>
      <div>
        <p className="eyebrow">Cobertura</p>
        <h3>{catalog.tournaments.reduce((total, entry) => total + entry.coverage.matches_counted, 0)} partidos con resultado</h3>
        <p>La cobertura indica qué partidos tienen planilla o resultado informado.</p>
      </div>
    </section>

    <footer className="tournament-footnote">Actualizado el {formatDate(catalog.generated_at)} · Datos derivados de planillas FEMEBAL confirmadas y resultados informados. No es la tabla oficial de FEMEBAL.</footer>
  </main>
}
