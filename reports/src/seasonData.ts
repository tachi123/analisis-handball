import type { PublicCompetition } from './publicCompetitions'
import type { ResultKind } from './resultStrip'
import { normalizedClub, resultFromScore } from './competitionFormat'

export type SeasonMatch = {
  key: string
  competitionKey: string
  competitionLabel: string
  round: number
  date: string | null
  opponent: string
  location: 'home' | 'away'
  goalsFor: number | null
  goalsAgainst: number | null
  result: ResultKind
}

export type SeasonScorer = {
  name: string
  club: string
  goals: number
  appearances: number
  byCompetition: Array<{ key: string; label: string; goals: number; appearances: number }>
}

export type AttackGroup = {
  players: number
  goals: number
  details: Array<{ name: string; goals: number; appearances: number }>
}

export type Concentration = {
  top1: number
  top3: number
  top5: number
  scorers10: number
  scorers20: number
}

export type AttackComposition = {
  previousTotal: number
  currentTotal: number
  retained: { players: number; previousGoals: number; currentGoals: number }
  departed: AttackGroup
  arrived: AttackGroup
  concentration: { previous: Concentration; current: Concentration }
}

const normalizePlayer = (name: string) => name
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase()
  .replace(/[^a-z0-9]+/g, ' ')
  .trim()
  .split(/\s+/)
  .sort()
  .join(' ')

export function seasonMatches(competition: PublicCompetition, club: string): SeasonMatch[] {
  const rows: SeasonMatch[] = []
  for (const round of competition.rounds) {
    for (const match of round.matches) {
      const home = normalizedClub(match.home) === normalizedClub(club)
      const away = normalizedClub(match.away) === normalizedClub(club)
      if (!home && !away) continue
      const goalsFor = home ? match.home_goals : match.away_goals
      const goalsAgainst = home ? match.away_goals : match.home_goals
      rows.push({
        key: `${competition.public_key}-${round.round}-${match.home}-${match.away}`,
        competitionKey: competition.public_key,
        competitionLabel: competition.competition + (competition.zone ? ` · Zona ${competition.zone}` : ''),
        round: round.round,
        date: round.date,
        opponent: home ? match.away : match.home,
        location: home ? 'home' : 'away',
        goalsFor,
        goalsAgainst,
        result: goalsFor === null || goalsAgainst === null ? 'pending' : resultFromScore(goalsFor, goalsAgainst),
      })
    }
  }
  return rows
}

export function seasonScorers(competitions: PublicCompetition[], club: string): SeasonScorer[] {
  const grouped = new Map<string, SeasonScorer>()
  for (const competition of competitions) {
    for (const row of competition.scorers) {
      if (normalizedClub(row.club) !== normalizedClub(club)) continue
      const key = normalizePlayer(row.name)
      const current = grouped.get(key) ?? {
        name: row.name,
        club,
        goals: 0,
        appearances: 0,
        byCompetition: competitions.map((item) => ({
          key: item.public_key,
          label: item.competition + (item.zone ? ` · Zona ${item.zone}` : ''),
          goals: 0,
          appearances: 0,
        })),
      }
      current.goals += row.goals
      current.appearances += row.appearances
      const block = current.byCompetition.find((item) => item.key === competition.public_key)
      if (block) {
        block.goals += row.goals
        block.appearances += row.appearances
      }
      grouped.set(key, current)
    }
  }
  return [...grouped.values()].sort((left, right) => right.goals - left.goals || right.appearances - left.appearances || left.name.localeCompare(right.name, 'es'))
}

export function rosterContinuity(previous: SeasonScorer[], current: SeasonScorer[]) {
  const previousNames = new Set(previous.map((row) => normalizePlayer(row.name)))
  const currentNames = new Set(current.map((row) => normalizePlayer(row.name)))
  const shared = [...currentNames].filter((name) => previousNames.has(name)).length
  return {
    previous: previousNames.size,
    current: currentNames.size,
    shared,
    retained: currentNames.size ? shared / currentNames.size : 0,
  }
}

export function annualTotals(competitions: PublicCompetition[], club: string) {
  const totals = { played: 0, won: 0, drawn: 0, lost: 0, points: 0, maxPoints: 0, goalsFor: 0, goalsAgainst: 0 }
  for (const competition of competitions) {
    const row = competition.standings.find((item) => normalizedClub(item.club) === normalizedClub(club))
    if (!row) continue
    totals.played += row.played
    totals.won += row.won
    totals.drawn += row.drawn
    totals.lost += row.lost
    totals.points += row.points
    totals.maxPoints += row.played * competition.points_rule.win
    totals.goalsFor += row.goals_for
    totals.goalsAgainst += row.goals_against
  }
  return totals
}

const concentration = (rows: SeasonScorer[], total: number): Concentration => {
  const ordered = [...rows].sort((left, right) => right.goals - left.goals)
  const share = (count: number) => total
    ? ordered.slice(0, count).reduce((sum, row) => sum + row.goals, 0) / total
    : 0
  return {
    top1: share(1),
    top3: share(3),
    top5: share(5),
    scorers10: rows.filter((row) => row.goals >= 10).length,
    scorers20: rows.filter((row) => row.goals >= 20).length,
  }
}

/**
 * Describe how the scoring load is split between retained, departed, and new
 * players. This is a descriptive decomposition, not a causal claim: planillas
 * do not record minutes, positions, shots, or assists.
 */
export function attackComposition(
  previous: SeasonScorer[],
  current: SeasonScorer[],
  previousTotal: number,
  currentTotal: number,
): AttackComposition {
  const previousKeys = new Set(previous.map((row) => normalizePlayer(row.name)))
  const currentKeys = new Set(current.map((row) => normalizePlayer(row.name)))
  const retainedKeys = new Set([...previousKeys].filter((key) => currentKeys.has(key)))
  const details = (rows: SeasonScorer[]) => rows
    .map((row) => ({ name: row.name, goals: row.goals, appearances: row.appearances }))
    .sort((left, right) => right.goals - left.goals || left.name.localeCompare(right.name, 'es'))
  const departed = previous.filter((row) => !currentKeys.has(normalizePlayer(row.name)))
  const arrived = current.filter((row) => !previousKeys.has(normalizePlayer(row.name)))

  return {
    previousTotal,
    currentTotal,
    retained: {
      players: retainedKeys.size,
      previousGoals: previous.filter((row) => retainedKeys.has(normalizePlayer(row.name))).reduce((sum, row) => sum + row.goals, 0),
      currentGoals: current.filter((row) => retainedKeys.has(normalizePlayer(row.name))).reduce((sum, row) => sum + row.goals, 0),
    },
    departed: { players: departed.length, goals: departed.reduce((sum, row) => sum + row.goals, 0), details: details(departed) },
    arrived: { players: arrived.length, goals: arrived.reduce((sum, row) => sum + row.goals, 0), details: details(arrived) },
    concentration: {
      previous: concentration(previous, previousTotal),
      current: concentration(current, currentTotal),
    },
  }
}
