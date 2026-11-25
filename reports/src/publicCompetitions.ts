// Privacy boundary for the public 2026 competition hub. The catalog, every
// tournament artifact, and the forecast are static JSON; this module checks
// their exact allowlists before the UI can render them.

export type PointsRule = {
  win: number
  draw: number
  loss: number
  suspended_win: number
  suspended_loss: number
}

export type CompetitionCoverage = {
  matches_total: number
  matches_counted: number
  planillas_confirmed: number
  reported_only: number
  suspended: number
  pending: number
  rounds_played: number
  rounds_total: number
  status: 'partial' | 'complete'
  label: string
}

export type StandingRow = {
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

export type ScorerRow = {
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

export type ClubRow = {
  club: string
  appearances: number
  goals: number
  yellow: number
  two_min: number
  red: number
  blue: number
  players: number
}

export type MatchCoverage = 'planilla' | 'reported' | 'suspended' | 'pending' | 'cancelled'

export type RoundMatch = {
  home: string
  away: string
  home_goals: number | null
  away_goals: number | null
  coverage: MatchCoverage
}

export type CompetitionRound = {
  round: number
  date: string | null
  matches: RoundMatch[]
}

export type Streak = { length: number; from_round: number | null; to_round: number | null }

export type Split = {
  played: number
  points: number
  max_points: number
  points_effectiveness: number
  goals_for_per_game: number
  goals_against_per_game: number
}

export type Tier = { played: number; points: number; max_points: number; points_effectiveness: number }

export type Biggest = {
  round: number
  opponent: string
  location: 'home' | 'away'
  goals_for: number
  goals_against: number
  margin: number
}

export type CompetitionInsightClub = {
  club: string
  played: number
  won: number
  drawn: number
  lost: number
  points: number
  max_points: number
  points_effectiveness: number
  win_rate: number
  goals_for: number
  goals_against: number
  goal_difference: number
  goals_for_per_game: number
  goals_against_per_game: number
  home: Split
  away: Split
  streaks: {
    longest_win: Streak
    longest_unbeaten: Streak
    longest_loss: Streak
    current_unbeaten: Streak
  }
  form_last_5: { sequence: string[]; points: number; max_points: number }
  opponent_tiers: { top_five: Tier; middle: Tier; bottom_five: Tier }
  biggest_win: Biggest | null
  biggest_loss: Biggest | null
}

export type CompetitionRecord = {
  key: string
  label: string
  club?: string
  clubs?: string[]
  value: number
  unit: string
  detail: string
}

export type CompetitionInsights = {
  matches_counted: number
  suspended_matches: number
  clubs: CompetitionInsightClub[]
  records: CompetitionRecord[]
}

export type PublicCompetition = {
  schema_version: 'tournament-v3'
  public_key: string
  tournament: string
  competition: string
  zone: string | null
  season: number
  updated_at: string
  coverage: CompetitionCoverage
  points_rule: PointsRule
  standings: StandingRow[]
  scorers: ScorerRow[]
  clubs: ClubRow[]
  rounds: CompetitionRound[]
  insights: CompetitionInsights
}

export type CatalogEntry = {
  key: string
  label: string
  competition: string
  zone: string | null
  season: number
  status: 'in_progress' | 'finished'
  coverage: CompetitionCoverage
  updated_at: string
  file: string
  forecast_file: string | null
  summary: { sapa: { position: number; points: number; played: number } | null }
  next_match: { round: number; date: string | null; opponent: string; location: 'home' | 'away' } | null
}

export type PublicTournamentCatalog = {
  schema_version: 'tournaments-v1'
  generated_at: string
  tournaments: CatalogEntry[]
}

export type ForecastCampaignMatch = {
  round: number
  date: string | null
  opponent: string
  location: 'home' | 'away'
  goals_for: number
  goals_against: number
  result: 'win' | 'draw' | 'loss'
}

export type ForecastTeam = {
  club: string
  champion_probability: number
  finish_probabilities: { first: number; second: number; third: number }
  podium_probability: number
  expected_position: number
  campaign: ForecastCampaignMatch[]
}

export type ForecastFixture = {
  round: number
  date: string | null
  home: string
  away: string
  home_win_probability: number
  draw_probability: number
  away_win_probability: number
}

export type PlayerMatchForecast = {
  team: string
  opponent: string
  location: 'home' | 'away'
  expected_team_goals: number
  players: Array<{
    name: string
    appearances: number
    expected_goals: number
    one_or_more_goals_probability: number
    three_or_more_goals_probability: number
    two_minute_probability: number
    ejection_probability: number
    confidence: 'strong' | 'moderate' | 'exploratory'
  }>
}

export type ForecastArchive = {
  key: string
  title: string
  captured_at: string
  fixture: { round: number; date: string | null; home: string; away: string }
  result: { home_goals: number; away_goals: number }
  forecast: PublicForecast
}

export type PublicForecast = {
  schema_version: 'forecast-v1'
  public_key: string
  competition: string
  tournament: string
  season: number
  updated_at: string
  coverage: CompetitionCoverage
  points_rule: PointsRule
  teams: ForecastTeam[]
  fixtures: ForecastFixture[]
  player_forecast?: PlayerMatchForecast
  archives: ForecastArchive[]
  rival_profile: { club: string | null; competitions: Array<{ key: string; label: string }> }
}

const forbidden = /^(?:private|raw|note|database|credential|api|token|url|id|event|analysis|operational)$/i

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function assertNumber(value: unknown, label: string): number {
  if (typeof value !== 'number' || Number.isNaN(value)) throw new Error(`The public competition has an invalid ${label}.`)
  return value
}

function assertString(value: unknown, label: string): string {
  if (typeof value !== 'string') throw new Error(`The public competition has an invalid ${label}.`)
  return value
}

function assertNullableNumber(value: unknown, label: string): number | null {
  if (value === null) return null
  return assertNumber(value, label)
}

function assertNullableString(value: unknown, label: string): string | null {
  if (value === null) return null
  return assertString(value, label)
}

function assertFields(record: Record<string, unknown>, allowed: string[], label: string) {
  for (const key of Object.keys(record)) {
    if (!allowed.includes(key) || forbidden.test(key)) throw new Error(`The public competition contains a restricted field in ${label}.`)
  }
}

function decodeCoverage(value: unknown): CompetitionCoverage {
  if (!isRecord(value)) throw new Error('The public competition has invalid coverage.')
  assertFields(value, ['matches_total', 'matches_counted', 'planillas_confirmed', 'reported_only', 'suspended', 'pending', 'rounds_played', 'rounds_total', 'status', 'label'], 'coverage')
  return {
    matches_total: assertNumber(value.matches_total, 'matches_total'),
    matches_counted: assertNumber(value.matches_counted, 'matches_counted'),
    planillas_confirmed: assertNumber(value.planillas_confirmed, 'planillas_confirmed'),
    reported_only: assertNumber(value.reported_only, 'reported_only'),
    suspended: assertNumber(value.suspended, 'suspended'),
    pending: assertNumber(value.pending, 'pending'),
    rounds_played: assertNumber(value.rounds_played, 'rounds_played'),
    rounds_total: assertNumber(value.rounds_total, 'rounds_total'),
    status: value.status === 'complete' ? 'complete' : 'partial',
    label: assertString(value.label, 'coverage label'),
  }
}

function decodePointsRule(value: unknown): PointsRule {
  if (!isRecord(value)) throw new Error('The public competition has an invalid points rule.')
  assertFields(value, ['win', 'draw', 'loss', 'suspended_win', 'suspended_loss'], 'points rule')
  return {
    win: assertNumber(value.win, 'win points'),
    draw: assertNumber(value.draw, 'draw points'),
    loss: assertNumber(value.loss, 'loss points'),
    suspended_win: assertNumber(value.suspended_win, 'suspended win points'),
    suspended_loss: assertNumber(value.suspended_loss, 'suspended loss points'),
  }
}

function decodeStanding(value: unknown): StandingRow {
  if (!isRecord(value)) throw new Error('The public competition has an invalid standing.')
  assertFields(value, ['pos', 'club', 'played', 'won', 'drawn', 'lost', 'penalized', 'goals_for', 'goals_against', 'goal_difference', 'points'], 'standing')
  return {
    pos: assertNumber(value.pos, 'position'),
    club: assertString(value.club, 'club'),
    played: assertNumber(value.played, 'played'),
    won: assertNumber(value.won, 'won'),
    drawn: assertNumber(value.drawn, 'drawn'),
    lost: assertNumber(value.lost, 'lost'),
    penalized: assertNumber(value.penalized, 'penalized'),
    goals_for: assertNumber(value.goals_for, 'goals_for'),
    goals_against: assertNumber(value.goals_against, 'goals_against'),
    goal_difference: assertNumber(value.goal_difference, 'goal_difference'),
    points: assertNumber(value.points, 'points'),
  }
}

function decodeScorer(value: unknown): ScorerRow {
  if (!isRecord(value)) throw new Error('The public competition has an invalid scorer.')
  assertFields(value, ['name', 'club', 'appearances', 'goals', 'yellow', 'two_min', 'red', 'blue', 'goals_per_game'], 'scorer')
  return {
    name: assertString(value.name, 'scorer name'),
    club: assertString(value.club, 'scorer club'),
    appearances: assertNumber(value.appearances, 'appearances'),
    goals: assertNumber(value.goals, 'goals'),
    yellow: assertNumber(value.yellow, 'yellow'),
    two_min: assertNumber(value.two_min, 'two_min'),
    red: assertNumber(value.red, 'red'),
    blue: assertNumber(value.blue, 'blue'),
    goals_per_game: assertNumber(value.goals_per_game, 'goals_per_game'),
  }
}

function decodeClub(value: unknown): ClubRow {
  if (!isRecord(value)) throw new Error('The public competition has an invalid club row.')
  assertFields(value, ['club', 'appearances', 'goals', 'yellow', 'two_min', 'red', 'blue', 'players'], 'club row')
  return {
    club: assertString(value.club, 'club'),
    appearances: assertNumber(value.appearances, 'appearances'),
    goals: assertNumber(value.goals, 'goals'),
    yellow: assertNumber(value.yellow, 'yellow'),
    two_min: assertNumber(value.two_min, 'two_min'),
    red: assertNumber(value.red, 'red'),
    blue: assertNumber(value.blue, 'blue'),
    players: assertNumber(value.players, 'players'),
  }
}

function decodeRoundMatch(value: unknown): RoundMatch {
  if (!isRecord(value)) throw new Error('The public competition has an invalid round match.')
  assertFields(value, ['home', 'away', 'home_goals', 'away_goals', 'coverage'], 'round match')
  const coverage = value.coverage
  if (coverage !== 'planilla' && coverage !== 'reported' && coverage !== 'suspended' && coverage !== 'pending' && coverage !== 'cancelled') {
    throw new Error('The public competition has an invalid match coverage.')
  }
  return {
    home: assertString(value.home, 'home club'),
    away: assertString(value.away, 'away club'),
    home_goals: assertNullableNumber(value.home_goals, 'home goals'),
    away_goals: assertNullableNumber(value.away_goals, 'away goals'),
    coverage,
  }
}

function decodeRound(value: unknown): CompetitionRound {
  if (!isRecord(value)) throw new Error('The public competition has an invalid round.')
  assertFields(value, ['round', 'date', 'matches'], 'round')
  if (!Array.isArray(value.matches)) throw new Error('The public competition has an invalid round list.')
  return {
    round: assertNumber(value.round, 'round'),
    date: assertNullableString(value.date, 'round date'),
    matches: value.matches.map(decodeRoundMatch),
  }
}

function decodeStreak(value: unknown): Streak {
  if (!isRecord(value)) throw new Error('The public competition has an invalid streak.')
  assertFields(value, ['length', 'from_round', 'to_round'], 'streak')
  return {
    length: assertNumber(value.length, 'streak length'),
    from_round: assertNullableNumber(value.from_round, 'streak start'),
    to_round: assertNullableNumber(value.to_round, 'streak end'),
  }
}

function decodeSplit(value: unknown): Split {
  if (!isRecord(value)) throw new Error('The public competition has an invalid home/away split.')
  assertFields(value, ['played', 'points', 'max_points', 'points_effectiveness', 'goals_for_per_game', 'goals_against_per_game'], 'home/away split')
  return {
    played: assertNumber(value.played, 'split played'),
    points: assertNumber(value.points, 'split points'),
    max_points: assertNumber(value.max_points, 'split max points'),
    points_effectiveness: assertNumber(value.points_effectiveness, 'split effectiveness'),
    goals_for_per_game: assertNumber(value.goals_for_per_game, 'split goals for'),
    goals_against_per_game: assertNumber(value.goals_against_per_game, 'split goals against'),
  }
}

function decodeTier(value: unknown): Tier {
  if (!isRecord(value)) throw new Error('The public competition has an invalid opponent tier.')
  assertFields(value, ['played', 'points', 'max_points', 'points_effectiveness'], 'opponent tier')
  return {
    played: assertNumber(value.played, 'tier played'),
    points: assertNumber(value.points, 'tier points'),
    max_points: assertNumber(value.max_points, 'tier max points'),
    points_effectiveness: assertNumber(value.points_effectiveness, 'tier effectiveness'),
  }
}

function decodeBiggest(value: unknown): Biggest | null {
  if (value === null) return null
  if (!isRecord(value)) throw new Error('The public competition has an invalid biggest result.')
  assertFields(value, ['round', 'opponent', 'location', 'goals_for', 'goals_against', 'margin'], 'biggest result')
  if (value.location !== 'home' && value.location !== 'away') throw new Error('The public competition has an invalid biggest-result location.')
  return {
    round: assertNumber(value.round, 'biggest round'),
    opponent: assertString(value.opponent, 'biggest opponent'),
    location: value.location,
    goals_for: assertNumber(value.goals_for, 'biggest goals for'),
    goals_against: assertNumber(value.goals_against, 'biggest goals against'),
    margin: assertNumber(value.margin, 'biggest margin'),
  }
}

function decodeInsightClub(value: unknown): CompetitionInsightClub {
  if (!isRecord(value)) throw new Error('The public competition has an invalid club insight.')
  assertFields(value, ['club', 'played', 'won', 'drawn', 'lost', 'points', 'max_points', 'points_effectiveness', 'win_rate', 'goals_for', 'goals_against', 'goal_difference', 'goals_for_per_game', 'goals_against_per_game', 'home', 'away', 'streaks', 'form_last_5', 'opponent_tiers', 'biggest_win', 'biggest_loss'], 'club insight')
  if (!isRecord(value.streaks)) throw new Error('The public competition has invalid streaks.')
  assertFields(value.streaks, ['longest_win', 'longest_unbeaten', 'longest_loss', 'current_unbeaten'], 'streaks')
  if (!isRecord(value.form_last_5)) throw new Error('The public competition has invalid recent form.')
  assertFields(value.form_last_5, ['sequence', 'points', 'max_points'], 'recent form')
  if (!Array.isArray(value.form_last_5.sequence) || value.form_last_5.sequence.some((item) => item !== 'G' && item !== 'E' && item !== 'P')) {
    throw new Error('The public competition has an invalid recent-form sequence.')
  }
  if (!isRecord(value.opponent_tiers)) throw new Error('The public competition has invalid opponent tiers.')
  assertFields(value.opponent_tiers, ['top_five', 'middle', 'bottom_five'], 'opponent tiers')
  return {
    club: assertString(value.club, 'insight club'),
    played: assertNumber(value.played, 'insight played'),
    won: assertNumber(value.won, 'insight won'),
    drawn: assertNumber(value.drawn, 'insight drawn'),
    lost: assertNumber(value.lost, 'insight lost'),
    points: assertNumber(value.points, 'insight points'),
    max_points: assertNumber(value.max_points, 'insight max points'),
    points_effectiveness: assertNumber(value.points_effectiveness, 'insight effectiveness'),
    win_rate: assertNumber(value.win_rate, 'insight win rate'),
    goals_for: assertNumber(value.goals_for, 'insight goals for'),
    goals_against: assertNumber(value.goals_against, 'insight goals against'),
    goal_difference: assertNumber(value.goal_difference, 'insight goal difference'),
    goals_for_per_game: assertNumber(value.goals_for_per_game, 'insight goals for per game'),
    goals_against_per_game: assertNumber(value.goals_against_per_game, 'insight goals against per game'),
    home: decodeSplit(value.home),
    away: decodeSplit(value.away),
    streaks: {
      longest_win: decodeStreak(value.streaks.longest_win),
      longest_unbeaten: decodeStreak(value.streaks.longest_unbeaten),
      longest_loss: decodeStreak(value.streaks.longest_loss),
      current_unbeaten: decodeStreak(value.streaks.current_unbeaten),
    },
    form_last_5: {
      sequence: value.form_last_5.sequence,
      points: assertNumber(value.form_last_5.points, 'recent form points'),
      max_points: assertNumber(value.form_last_5.max_points, 'recent form max points'),
    },
    opponent_tiers: {
      top_five: decodeTier(value.opponent_tiers.top_five),
      middle: decodeTier(value.opponent_tiers.middle),
      bottom_five: decodeTier(value.opponent_tiers.bottom_five),
    },
    biggest_win: decodeBiggest(value.biggest_win),
    biggest_loss: decodeBiggest(value.biggest_loss),
  }
}

function decodeRecord(value: unknown): CompetitionRecord {
  if (!isRecord(value)) throw new Error('The public competition has an invalid record.')
  assertFields(value, ['key', 'label', 'club', 'clubs', 'value', 'unit', 'detail'], 'record')
  if (value.clubs !== undefined && (!Array.isArray(value.clubs) || value.clubs.some((item) => typeof item !== 'string'))) {
    throw new Error('The public competition has an invalid record club list.')
  }
  return {
    key: assertString(value.key, 'record key'),
    label: assertString(value.label, 'record label'),
    ...(value.club !== undefined ? { club: assertString(value.club, 'record club') } : {}),
    ...(value.clubs !== undefined ? { clubs: value.clubs as string[] } : {}),
    value: assertNumber(value.value, 'record value'),
    unit: assertString(value.unit, 'record unit'),
    detail: assertString(value.detail, 'record detail'),
  }
}

function decodeInsights(value: unknown): CompetitionInsights {
  if (!isRecord(value)) throw new Error('The public competition has invalid insights.')
  assertFields(value, ['matches_counted', 'suspended_matches', 'clubs', 'records'], 'insights')
  if (!Array.isArray(value.clubs) || !Array.isArray(value.records)) throw new Error('The public competition has invalid insight lists.')
  return {
    matches_counted: assertNumber(value.matches_counted, 'insight matches counted'),
    suspended_matches: assertNumber(value.suspended_matches, 'insight suspended matches'),
    clubs: value.clubs.map(decodeInsightClub),
    records: value.records.map(decodeRecord),
  }
}

export function decodePublicTournamentCatalog(value: unknown): PublicTournamentCatalog {
  if (!isRecord(value)) throw new Error('The public catalog is not a JSON object.')
  assertFields(value, ['schema_version', 'generated_at', 'tournaments'], 'catalog')
  if (value.schema_version !== 'tournaments-v1') throw new Error('Unsupported public catalog version.')
  if (!Array.isArray(value.tournaments)) throw new Error('The public catalog has an invalid tournament list.')
  return {
    schema_version: 'tournaments-v1',
    generated_at: assertString(value.generated_at, 'catalog date'),
    tournaments: value.tournaments.map((item) => {
      if (!isRecord(item)) throw new Error('The public catalog has an invalid tournament entry.')
      assertFields(item, ['key', 'label', 'competition', 'zone', 'season', 'status', 'coverage', 'updated_at', 'file', 'forecast_file', 'summary', 'next_match'], 'catalog entry')
      if (!isRecord(item.summary) || !('sapa' in item.summary)) throw new Error('The public catalog has an invalid summary.')
      const sapaValue = item.summary.sapa
      let sapa = null
      if (sapaValue !== null) {
        if (!isRecord(sapaValue)) throw new Error('The public catalog has an invalid SAPA summary.')
        assertFields(sapaValue, ['position', 'points', 'played'], 'SAPA summary')
        sapa = {
          position: assertNumber(sapaValue.position, 'SAPA position'),
          points: assertNumber(sapaValue.points, 'SAPA points'),
          played: assertNumber(sapaValue.played, 'SAPA played'),
        }
      }
      let nextMatch: CatalogEntry['next_match'] = null
      if (item.next_match !== null) {
        const next = item.next_match
        if (!isRecord(next)) throw new Error('The public catalog has an invalid next match.')
        assertFields(next, ['round', 'date', 'opponent', 'location'], 'next match')
        if (next.location !== 'home' && next.location !== 'away') throw new Error('The public catalog has an invalid next match location.')
        nextMatch = {
          round: assertNumber(next.round, 'next match round'),
          date: assertNullableString(next.date, 'next match date'),
          opponent: assertString(next.opponent, 'next match opponent'),
          location: next.location,
        }
      }
      return {
        key: assertString(item.key, 'tournament key'),
        label: assertString(item.label, 'tournament label'),
        competition: assertString(item.competition, 'competition'),
        zone: assertNullableString(item.zone, 'zone'),
        season: assertNumber(item.season, 'season'),
        status: item.status === 'finished' ? 'finished' : 'in_progress',
        coverage: decodeCoverage(item.coverage),
        updated_at: assertString(item.updated_at, 'updated_at'),
        file: assertString(item.file, 'tournament file'),
        forecast_file: assertNullableString(item.forecast_file, 'forecast file'),
        summary: { sapa },
        next_match: nextMatch,
      }
    }),
  }
}

export function decodePublicCompetition(value: unknown): PublicCompetition {
  if (!isRecord(value)) throw new Error('The public competition is not a JSON object.')
  assertFields(value, ['schema_version', 'public_key', 'tournament', 'competition', 'zone', 'season', 'updated_at', 'coverage', 'points_rule', 'standings', 'scorers', 'clubs', 'rounds', 'insights'], 'competition')
  if (value.schema_version !== 'tournament-v3') throw new Error('Unsupported public competition version.')
  if (!Array.isArray(value.standings) || !Array.isArray(value.scorers) || !Array.isArray(value.clubs) || !Array.isArray(value.rounds)) {
    throw new Error('The public competition has invalid lists.')
  }
  return {
    schema_version: 'tournament-v3',
    public_key: assertString(value.public_key, 'public key'),
    tournament: assertString(value.tournament, 'tournament name'),
    competition: assertString(value.competition, 'competition name'),
    zone: assertNullableString(value.zone, 'zone'),
    season: assertNumber(value.season, 'season'),
    updated_at: assertString(value.updated_at, 'updated_at'),
    coverage: decodeCoverage(value.coverage),
    points_rule: decodePointsRule(value.points_rule),
    standings: value.standings.map(decodeStanding),
    scorers: value.scorers.map(decodeScorer),
    clubs: value.clubs.map(decodeClub),
    rounds: value.rounds.map(decodeRound),
    insights: decodeInsights(value.insights),
  }
}

export function decodePublicForecast(value: unknown): PublicForecast {
  if (!isRecord(value)) throw new Error('The public forecast is not a JSON object.')
  assertFields(value, ['schema_version', 'public_key', 'competition', 'tournament', 'season', 'updated_at', 'coverage', 'points_rule', 'teams', 'fixtures', 'player_forecast', 'archives', 'rival_profile'], 'forecast')
  if (value.schema_version !== 'forecast-v1') throw new Error('Unsupported public forecast version.')
  if (!Array.isArray(value.teams) || !Array.isArray(value.fixtures)) throw new Error('The public forecast has invalid lists.')
  if (!isRecord(value.rival_profile)) throw new Error('The public forecast has an invalid rival profile.')
  assertFields(value.rival_profile, ['club', 'competitions'], 'rival profile')
  if (!Array.isArray(value.rival_profile.competitions)) throw new Error('The public forecast has an invalid rival competition list.')
  let playerForecast: PlayerMatchForecast | undefined
  if (value.player_forecast !== undefined) {
    if (!isRecord(value.player_forecast)) throw new Error('The public forecast has an invalid player forecast.')
    assertFields(value.player_forecast, ['team', 'opponent', 'location', 'expected_team_goals', 'players'], 'player forecast')
    if (value.player_forecast.location !== 'home' && value.player_forecast.location !== 'away') throw new Error('The public forecast has an invalid player forecast location.')
    if (!Array.isArray(value.player_forecast.players)) throw new Error('The public forecast has an invalid player forecast list.')
    playerForecast = {
      team: assertString(value.player_forecast.team, 'player forecast team'),
      opponent: assertString(value.player_forecast.opponent, 'player forecast opponent'),
      location: value.player_forecast.location,
      expected_team_goals: assertNumber(value.player_forecast.expected_team_goals, 'player forecast expected team goals'),
      players: value.player_forecast.players.map((player) => {
        if (!isRecord(player)) throw new Error('The public forecast has an invalid player projection.')
        assertFields(player, ['name', 'appearances', 'expected_goals', 'one_or_more_goals_probability', 'three_or_more_goals_probability', 'two_minute_probability', 'ejection_probability', 'confidence'], 'player projection')
        if (player.confidence !== 'strong' && player.confidence !== 'moderate' && player.confidence !== 'exploratory') throw new Error('The public forecast has an invalid player forecast confidence.')
        return {
          name: assertString(player.name, 'player forecast name'),
          appearances: assertNumber(player.appearances, 'player forecast appearances'),
          expected_goals: assertNumber(player.expected_goals, 'player forecast expected goals'),
          one_or_more_goals_probability: assertNumber(player.one_or_more_goals_probability, 'player forecast 1+ goals'),
          three_or_more_goals_probability: assertNumber(player.three_or_more_goals_probability, 'player forecast 3+ goals'),
          two_minute_probability: assertNumber(player.two_minute_probability, 'player forecast two-minute'),
          ejection_probability: assertNumber(player.ejection_probability, 'player forecast ejection'),
          confidence: player.confidence,
        }
      }),
    }
  }
  const archives: ForecastArchive[] = value.archives === undefined ? [] : (() => {
    if (!Array.isArray(value.archives)) throw new Error('The public forecast has an invalid archive list.')
    return value.archives.map((archive) => {
      if (!isRecord(archive)) throw new Error('The public forecast has an invalid archive.')
      assertFields(archive, ['key', 'title', 'captured_at', 'fixture', 'result', 'forecast'], 'forecast archive')
      if (!isRecord(archive.fixture) || !isRecord(archive.result)) throw new Error('The public forecast has an invalid archive match.')
      assertFields(archive.fixture, ['round', 'date', 'home', 'away'], 'forecast archive fixture')
      assertFields(archive.result, ['home_goals', 'away_goals'], 'forecast archive result')
      return {
        key: assertString(archive.key, 'forecast archive key'),
        title: assertString(archive.title, 'forecast archive title'),
        captured_at: assertString(archive.captured_at, 'forecast archive capture date'),
        fixture: {
          round: assertNumber(archive.fixture.round, 'forecast archive fixture round'),
          date: assertNullableString(archive.fixture.date, 'forecast archive fixture date'),
          home: assertString(archive.fixture.home, 'forecast archive fixture home'),
          away: assertString(archive.fixture.away, 'forecast archive fixture away'),
        },
        result: {
          home_goals: assertNumber(archive.result.home_goals, 'forecast archive home result'),
          away_goals: assertNumber(archive.result.away_goals, 'forecast archive away result'),
        },
        forecast: decodePublicForecast(archive.forecast),
      }
    })
  })()
  return {
    schema_version: 'forecast-v1',
    public_key: assertString(value.public_key, 'public key'),
    competition: assertString(value.competition, 'competition'),
    tournament: assertString(value.tournament, 'tournament name'),
    season: assertNumber(value.season, 'season'),
    updated_at: assertString(value.updated_at, 'updated_at'),
    coverage: decodeCoverage(value.coverage),
    points_rule: decodePointsRule(value.points_rule),
    teams: value.teams.map((item) => {
      if (!isRecord(item)) throw new Error('The public forecast has an invalid team.')
      assertFields(item, ['club', 'champion_probability', 'finish_probabilities', 'podium_probability', 'expected_position', 'campaign'], 'forecast team')
      if (!isRecord(item.finish_probabilities)) throw new Error('The public forecast has invalid finish probabilities.')
      assertFields(item.finish_probabilities, ['first', 'second', 'third'], 'finish probabilities')
      if (!Array.isArray(item.campaign)) throw new Error('The public forecast has an invalid campaign.')
      return {
        club: assertString(item.club, 'forecast club'),
        champion_probability: assertNumber(item.champion_probability, 'champion probability'),
        finish_probabilities: {
          first: assertNumber(item.finish_probabilities.first, 'first-place probability'),
          second: assertNumber(item.finish_probabilities.second, 'second-place probability'),
          third: assertNumber(item.finish_probabilities.third, 'third-place probability'),
        },
        podium_probability: assertNumber(item.podium_probability, 'podium probability'),
        expected_position: assertNumber(item.expected_position, 'expected position'),
        campaign: item.campaign.map((match) => {
          if (!isRecord(match)) throw new Error('The public forecast has an invalid campaign match.')
          assertFields(match, ['round', 'date', 'opponent', 'location', 'goals_for', 'goals_against', 'result'], 'campaign match')
          if (match.location !== 'home' && match.location !== 'away') throw new Error('The public forecast has an invalid campaign location.')
          if (match.result !== 'win' && match.result !== 'draw' && match.result !== 'loss') throw new Error('The public forecast has an invalid campaign result.')
          return {
            round: assertNumber(match.round, 'campaign round'),
            date: assertNullableString(match.date, 'campaign date'),
            opponent: assertString(match.opponent, 'campaign opponent'),
            location: match.location,
            goals_for: assertNumber(match.goals_for, 'campaign goals for'),
            goals_against: assertNumber(match.goals_against, 'campaign goals against'),
            result: match.result,
          }
        }),
      }
    }),
    fixtures: value.fixtures.map((item) => {
      if (!isRecord(item)) throw new Error('The public forecast has an invalid fixture.')
      assertFields(item, ['round', 'date', 'home', 'away', 'home_win_probability', 'draw_probability', 'away_win_probability'], 'forecast fixture')
      return {
        round: assertNumber(item.round, 'fixture round'),
        date: assertNullableString(item.date, 'fixture date'),
        home: assertString(item.home, 'fixture home'),
        away: assertString(item.away, 'fixture away'),
        home_win_probability: assertNumber(item.home_win_probability, 'home probability'),
        draw_probability: assertNumber(item.draw_probability, 'draw probability'),
        away_win_probability: assertNumber(item.away_win_probability, 'away probability'),
      }
    }),
    ...(playerForecast ? { player_forecast: playerForecast } : {}),
    archives,
    rival_profile: {
      club: assertNullableString(value.rival_profile.club, 'rival club'),
      competitions: value.rival_profile.competitions.map((item) => {
        if (!isRecord(item)) throw new Error('The public forecast has an invalid rival competition.')
        assertFields(item, ['key', 'label'], 'rival competition')
        return { key: assertString(item.key, 'rival competition key'), label: assertString(item.label, 'rival competition label') }
      }),
    },
  }
}
