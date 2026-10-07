import { useEffect, useState } from 'react'
import { decodePublicReport, type PublicReport, type PlayerPublic } from './projection'

// Local report path — works without any env var, bundles with dist/root
const localReportPath = 'report.json'

function formatValue(label: string, value: string | number | null | undefined): string {
  if (value == null || value === undefined) return '-'
  return `${label}: ${value}`
}

// Build a safe display label from a player slug
function playerLabel(slug: string, name: string, jersey: string | null): string {
  // Use slug if available, otherwise fall back to name with jersey
  if (slug) return `${name} #${jersey || ''}`.trim()
  if (jersey) return `${name} #${jersey}`
  return name
}

export default function App() {
  const [report, setReport] = useState<PublicReport | null>(null)
  const [message, setMessage] = useState('Loading public report...')
  // State for selected player
  const [selectedPlayer, setSelectedPlayer] = useState<PlayerPublic | null>(null)

  useEffect(() => {
    // 1) Try local bundled report.json first (works without any env var)
    fetch(localReportPath).then((response) =>
      response.ok ? response.json() : Promise.reject(new Error('Local report unavailable.'))
    )
      .then((payload) => {
        setReport(decodePublicReport(payload))
        setMessage('')
      })
      .catch(() => setMessage('This public report is unavailable. Please try again later.'))
  }, [])

  if (!report) return <main><p role="status">{message}</p></main>

  const coverage = report.coverage
  const isPartial = coverage?.status === 'partial'

  // --- Player selector logic ---
  const allPlayers = report.players ?? []
  const hasPlayerData = allPlayers.length > 0

  // When a player is selected, show their panel
  const playerPanel = selectedPlayer ? (
    <section
      className="player-panel" role="region" aria-label="Selected player panel"
    >
      <h3>Player: {playerLabel(selectedPlayer.name, selectedPlayer.name, selectedPlayer.jersey_number)}</h3>
      <dl className="player-metrics" aria-label="Player metrics">
        {Object.entries(selectedPlayer.metrics).map(([name, value]) => (
          <div key={name} className="player-metric-row">
            <dt>{name}</dt>
            <dd>{formatValue(name, value)}</dd>
          </div>
        ))}
      </dl>
      {selectedPlayer.evidence.length > 0 && (
        <div className="player-evidence" aria-label="Player evidence">
          <h4>Related evidence</h4>
          <ul>
            {selectedPlayer.evidence.map((ev) => {
                const { reference, period, regulation_seconds, clock_unverified } = ev as {
                  reference: string
                  period: number | null
                  regulation_seconds: number | null
                  clock_unverified: boolean
                  observation?: string
                  media_available?: boolean
                  media_url?: string
                }
                return (
                  <li key={reference}>
                    <strong>{reference}</strong> — Period {period ?? '?'}
                    {regulation_seconds !== null && !clock_unverified && (
                      <span>{formatValue('reg', regulation_seconds)}</span>
                    )}
                  </li>
                )
              })}
          </ul>
        </div>
      )}
    </section>
  ) : null

  return <main aria-labelledby="report-header">
    <header>
      <h1 id="report-header">{report.match.home_team} vs {report.match.away_team}</h1>
      <p>{report.match.date} | Version {report.report_version}</p>
      {isPartial && (
        <div role="alert" aria-label="Partial analysis disclosure: this report covers only selected periods.">
          {coverage?.label ? `Partial analysis: only ${coverage.label} is covered` : 'Partial analysis: this report covers only selected periods.'}
        </div>
      )}
    </header>

    <section>
      <h2>Coaching focus</h2>
      <p>{report.coaching.question}</p>
      <p>{report.coaching.pattern_statement}</p>
      <strong>{report.coaching.action.kind}: {report.coaching.action.text}</strong>
    </section>

    <section>
      <h2>Metrics</h2>
      {Object.entries(report.metrics).map(([name, values]) => (
        <div key={name} className="metric-card" role="listitem">
          <span className="metric-name">{name}</span>
          <div className="metric-values">
            {Object.entries(values).map(([label, value]) => (
              <span key={label} className="metric-value">{formatValue(label, value)}</span>
            ))}
          </div>
        </div>
      ))}
    </section>

    {/* Player selector/chips area */}
    {hasPlayerData && (
      <section>
        <h2>Players</h2>
        <div className="player-chips" role="region" aria-label="Player selector chips">
          {allPlayers.map((player) => (
            <div
              key={player.slug}
              className="player-chip"
              role="button"
              tabIndex={0}
              onClick={() => setSelectedPlayer(player)}
              onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') (e.currentTarget as HTMLDivElement).click(); }}
              aria-pressed={selectedPlayer?.slug === player.slug}
              aria-selected={selectedPlayer?.slug === player.slug}
            >
              {playerLabel(player.name, player.name, player.jersey_number)}
            </div>
          ))}
        </div>
        {playerPanel}
      </section>
    )}

    <section>
      <h2>Evidence timeline</h2>
      {report.evidence.map((item) => (
        <article key={item.reference} className="evidence-item" role="article">
          <header>
            <strong>{item.reference}</strong>
            <span className="evidence-period">Period {item.period ?? '?'}</span>
          </header>
          <p>{item.observation}</p>
          <small>
            {item.clock_unverified && <span className="clock-status">Clock unverified</span>}
            {item.regulation_seconds !== null && !item.clock_unverified ? (
              <span className="regulation-clock">({formatValue('reg', item.regulation_seconds)})</span>
            ) : item.clock_unverified && (
              <span className="clock-status">Clock unavailable</span>
            )}
          </small>
          {item.media_available && item.media_url && (
            <p><a href={item.media_url} target="_blank" rel="noopener noreferrer">Approved evidence</a></p>
          )}
        </article>
      ))}
    </section>

    {report.reconciliation && report.reconciliation.length > 0 && (
      <section>
        <h2>Reconciliation</h2>
        <dl className="reconciliation-list" aria-label="Reconciliation entries">
          {report.reconciliation.map((item, idx) => (
            <div key={idx} className="reconciliation-item">
              <dt>{item.side || 'unknown'}:</dt>
              <dd>{item.official !== null ? `official: ${item.official}` : 'official: N/A'}</dd>
              <dd>{item.analytical !== null ? `analytical: ${item.analytical}` : 'analytical: N/A'}</dd>
              {item.discrepancy !== null && (
                <>
                  <dt>discrepancy:</dt>
                  <dd>{item.discrepancy}</dd>
                </>
              )}
            </div>
          ))}
        </dl>
      </section>
    )}

    <footer>
      Source: {report.source.label} ({report.source.status}).
      {report.uncertainty_disclosure && (
        <span>{report.uncertainty_disclosure}</span>
      )}
    </footer>
  </main>
}