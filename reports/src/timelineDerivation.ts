import type { Incident, PublicReport } from './projection'

export type MomentumKind = 'goal' | 'recovery' | 'turnover' | 'passive' | 'sanction' | 'other'

export type MomentumEvent = {
  reference: string
  period: number | null
  position: number
  displayTime: string
  videoSeconds: number | null
  clockUnverified: boolean
  teamSide: 'home' | 'away' | 'unknown'
  playerName: string | null
  outcome: string
  kind: MomentumKind
  homeGoals: number
  awayGoals: number
  scoreDiff: number
}

const isGoal = (outcome: string) => ['goal', 'gol'].includes(outcome.trim().toLowerCase())

const formatTime = (seconds: number, videoTime: boolean) => {
  const prefix = videoTime ? 'Video ' : ''
  return `${prefix}${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`
}

function momentumKind(incident: Incident): MomentumKind {
  if (isGoal(incident.outcome)) return 'goal'
  if (incident.event_kind === 'recovery') return 'recovery'
  if (incident.event_kind === 'turnover') return incident.outcome.trim().toLowerCase() === 'passive' ? 'passive' : 'turnover'
  if (incident.event_kind === 'foul_sanction') return 'sanction'
  return 'other'
}

/** Builds a chronological, public-safe score-flow dataset. */
export function deriveMomentum(incidents: Incident[]): MomentumEvent[] {
  const chronological = incidents
    .map((incident, index) => {
      const verified = !incident.clock_unverified && incident.regulation_seconds !== null
      const seconds = verified ? incident.regulation_seconds : incident.video_seconds
      return seconds === null ? null : { incident, index, seconds, verified }
    })
    .filter((entry): entry is { incident: Incident; index: number; seconds: number; verified: boolean } => entry !== null)
    .sort((a, b) => (a.incident.period ?? 0) - (b.incident.period ?? 0) || a.seconds - b.seconds || a.index - b.index)

  let homeGoals = 0
  let awayGoals = 0
  return chronological.map(({ incident, seconds }, index) => {
    if (isGoal(incident.outcome)) {
      if (incident.team_side === 'home') homeGoals += 1
      if (incident.team_side === 'away') awayGoals += 1
    }
    return {
      reference: incident.reference,
      period: incident.period,
      position: index,
      displayTime: formatTime(seconds, incident.clock_unverified || incident.regulation_seconds === null),
      videoSeconds: incident.video_seconds,
      clockUnverified: incident.clock_unverified,
      teamSide: incident.team_side,
      playerName: incident.player_name,
      outcome: incident.outcome,
      kind: momentumKind(incident),
      homeGoals,
      awayGoals,
      scoreDiff: homeGoals - awayGoals,
    }
  })
}

export function scoreMatchesSummary(events: MomentumEvent[], summary: PublicReport['team_summary']): boolean {
  if (!summary?.home || !summary.away) return true
  const last = events.at(-1)
  return !last || (last.homeGoals === summary.home.goals && last.awayGoals === summary.away.goals)
}
