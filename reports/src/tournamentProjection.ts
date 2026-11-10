// Privacy boundary for the public tournament projection. Keep the allowlists
// narrow: the public document carries only names and numbers, never database
// IDs, raw payloads, notes, URLs, or operational paths.

export type TournamentStanding = {
  pos: number
  club: string
  played: number
  won: number
  drawn: number
  lost: number
  penalized: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
}

export type TournamentScorer = {
  name: string
  club: string
  appearances: number
  goals: number
  yellow: number
  two_min: number
  red: number
  blue: number
  goals_per_game: number
}

export type TournamentClub = {
  club: string
  appearances: number
  goals: number
  yellow: number
  two_min: number
  red: number
  blue: number
  players: number
}

export type PublicTournament = {
  schema_version: 'tournament-v1'
  tournament: string
  season: number
  updated_at: string
  coverage: {
    rounds_played: number
    rounds_total: number
    status: 'partial' | 'complete'
    label: string
  }
  standings: TournamentStanding[]
  scorers: TournamentScorer[]
  clubs: TournamentClub[]
}

const forbidden = /^(?:private|raw|note|database|credential|api|token|url|id|event|analysis|operational)$/i

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) throw new Error(`The public tournament has an invalid ${label}.`)
  return value
}

function assertString(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new Error(`The public tournament has an invalid ${label}.`)
  return value
}

function assertFields(record: Record<string, unknown>, allowed: string[], label: string) {
  for (const key of Object.keys(record)) {
    if (!allowed.includes(key) || forbidden.test(key)) throw new Error(`The public tournament contains a restricted field in ${label}.`)
  }
}

export function decodePublicTournament(value: unknown): PublicTournament {
  if (!isRecord(value)) throw new Error('The public tournament is not a JSON object.')
  assertFields(value, ['schema_version', 'tournament', 'season', 'updated_at', 'coverage', 'standings', 'scorers', 'clubs'], 'root')
  if (value.schema_version !== 'tournament-v1') throw new Error('Unsupported public tournament version.')
  const tournament = assertString(value.tournament, 'tournament name')
  const season = assertNumber(value.season, 'season')
  const updated_at = assertString(value.updated_at, 'updated_at')
  if (!isRecord(value.coverage)) throw new Error('The public tournament has invalid coverage.')
  assertFields(value.coverage, ['rounds_played', 'rounds_total', 'status', 'label'], 'coverage')
  const coverage: PublicTournament['coverage'] = {
    rounds_played: assertNumber(value.coverage.rounds_played, 'rounds_played'),
    rounds_total: assertNumber(value.coverage.rounds_total, 'rounds_total'),
    status: value.coverage.status === 'complete' ? 'complete' : 'partial',
    label: assertString(value.coverage.label, 'coverage label'),
  }

  if (!Array.isArray(value.standings) || !Array.isArray(value.scorers) || !Array.isArray(value.clubs)) {
    throw new Error('The public tournament has invalid data.')
  }

  const standings = value.standings.map((item): TournamentStanding => {
    if (!isRecord(item)) throw new Error('The public tournament has an invalid standing.')
    assertFields(item, ['pos', 'club', 'played', 'won', 'drawn', 'lost', 'penalized', 'goals_for', 'goals_against', 'goal_difference', 'points'], 'standing')
    return {
      pos: assertNumber(item.pos, 'position'),
      club: assertString(item.club, 'club'),
      played: assertNumber(item.played, 'played'),
      won: assertNumber(item.won, 'won'),
      drawn: assertNumber(item.drawn, 'drawn'),
      lost: assertNumber(item.lost, 'lost'),
      penalized: assertNumber(item.penalized, 'penalized'),
      goals_for: assertNumber(item.goals_for, 'goals_for'),
      goals_against: assertNumber(item.goals_against, 'goals_against'),
      goal_difference: assertNumber(item.goal_difference, 'goal_difference'),
      points: assertNumber(item.points, 'points'),
    }
  })

  const scorers = value.scorers.map((item): TournamentScorer => {
    if (!isRecord(item)) throw new Error('The public tournament has an invalid scorer.')
    assertFields(item, ['name', 'club', 'appearances', 'goals', 'yellow', 'two_min', 'red', 'blue', 'goals_per_game'], 'scorer')
    return {
      name: assertString(item.name, 'scorer name'),
      club: assertString(item.club, 'scorer club'),
      appearances: assertNumber(item.appearances, 'appearances'),
      goals: assertNumber(item.goals, 'goals'),
      yellow: assertNumber(item.yellow, 'yellow'),
      two_min: assertNumber(item.two_min, 'two_min'),
      red: assertNumber(item.red, 'red'),
      blue: assertNumber(item.blue, 'blue'),
      goals_per_game: assertNumber(item.goals_per_game, 'goals_per_game'),
    }
  })

  const clubs = value.clubs.map((item): TournamentClub => {
    if (!isRecord(item)) throw new Error('The public tournament has an invalid club.')
    assertFields(item, ['club', 'appearances', 'goals', 'yellow', 'two_min', 'red', 'blue', 'players'], 'club')
    return {
      club: assertString(item.club, 'club'),
      appearances: assertNumber(item.appearances, 'appearances'),
      goals: assertNumber(item.goals, 'goals'),
      yellow: assertNumber(item.yellow, 'yellow'),
      two_min: assertNumber(item.two_min, 'two_min'),
      red: assertNumber(item.red, 'red'),
      blue: assertNumber(item.blue, 'blue'),
      players: assertNumber(item.players, 'players'),
    }
  })

  return { schema_version: 'tournament-v1', tournament, season, updated_at, coverage, standings, scorers, clubs }
}
