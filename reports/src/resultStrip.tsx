export type ResultKind = 'win' | 'draw' | 'loss' | 'pending'

export type StripMatch = {
  key: string
  label: string
  result: ResultKind
  detail: string
}

export const resultLetter = (result: ResultKind) => result === 'win' ? 'G' : result === 'draw' ? 'E' : result === 'loss' ? 'P' : '·'

export function ResultStrip({ matches, compact = false, label }: { matches: StripMatch[]; compact?: boolean; label: string }) {
  return <div className={`result-strip ${compact ? 'compact' : ''}`} role="list" aria-label={label}>
    {matches.map((match) => <span
      key={match.key}
      role="listitem"
      className={`result-pill ${match.result}`}
      title={match.detail}
      aria-label={match.detail}
    >
      <b>{match.label}</b><em>{resultLetter(match.result)}</em>
    </span>)}
  </div>
}

export function ResultLegend() {
  return <p className="result-legend"><span className="result-pill win"><b>G</b><em>Ganó</em></span><span className="result-pill draw"><b>E</b><em>Empató</em></span><span className="result-pill loss"><b>P</b><em>Perdió</em></span><span className="result-pill pending"><b>·</b><em>Pendiente</em></span></p>
}
