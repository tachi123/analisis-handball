import { describe, expect, it } from 'vitest'
import { decodePublicCompetition, decodePublicForecast, decodePublicTournamentCatalog } from './publicCompetitions'

const coverage = {
  matches_total: 120,
  matches_counted: 111,
  planillas_confirmed: 110,
  reported_only: 0,
  suspended: 1,
  pending: 9,
  rounds_played: 14,
  rounds_total: 15,
  status: 'partial',
  label: 'Cobertura parcial.',
}

const pointsRule = { win: 3, draw: 2, loss: 1, suspended_win: 3, suspended_loss: 0 }

const insightClub = {
  club: 'S.A.P.A.',
  played: 2,
  won: 1,
  drawn: 1,
  lost: 0,
  points: 5,
  max_points: 6,
  points_effectiveness: 0.833,
  win_rate: 0.5,
  goals_for: 55,
  goals_against: 50,
  goal_difference: 5,
  goals_for_per_game: 27.5,
  goals_against_per_game: 25,
  home: { played: 1, points: 3, max_points: 3, points_effectiveness: 1, goals_for_per_game: 30, goals_against_per_game: 25 },
  away: { played: 1, points: 2, max_points: 3, points_effectiveness: 0.667, goals_for_per_game: 25, goals_against_per_game: 25 },
  streaks: {
    longest_win: { length: 1, from_round: 1, to_round: 1 },
    longest_unbeaten: { length: 2, from_round: 1, to_round: 2 },
    longest_loss: { length: 0, from_round: null, to_round: null },
    current_unbeaten: { length: 2, from_round: 1, to_round: 2 },
  },
  form_last_5: { sequence: ['G', 'E'], points: 5, max_points: 6 },
  opponent_tiers: {
    top_five: { played: 1, points: 3, max_points: 3, points_effectiveness: 1 },
    middle: { played: 0, points: 0, max_points: 0, points_effectiveness: 0 },
    bottom_five: { played: 1, points: 2, max_points: 3, points_effectiveness: 0.667 },
  },
  biggest_win: { round: 1, opponent: 'Lanús C', location: 'home', goals_for: 30, goals_against: 25, margin: 5 },
  biggest_loss: null,
}

const validCompetition = {
  schema_version: 'tournament-v3',
  public_key: 'permanencia-2026',
  tournament: 'Torneo Permanencia 2026 3ªM',
  competition: 'Permanencia 2026',
  zone: null,
  season: 2026,
  updated_at: '2026-11-17',
  coverage,
  points_rule: pointsRule,
  standings: [{ pos: 3, club: 'S.A.P.A.', played: 2, won: 1, drawn: 1, lost: 0, penalized: 0, goals_for: 55, goals_against: 50, goal_difference: 5, points: 5 }],
  scorers: [{ name: 'Delpieri, Mateo', club: 'S.A.P.A.', appearances: 2, goals: 12, yellow: 1, two_min: 0, red: 0, blue: 0, goals_per_game: 6 }],
  clubs: [{ club: 'S.A.P.A.', appearances: 30, goals: 55, yellow: 3, two_min: 1, red: 0, blue: 0, players: 15 }],
  rounds: [
    { round: 1, date: '2026-08-09', matches: [{ home: 'S.A.P.A.', away: 'Lanús C', home_goals: 30, away_goals: 25, coverage: 'planilla' }] },
    { round: 2, date: '2026-08-16', matches: [{ home: 'S.A.P.A.', away: 'Palermo Handball', home_goals: null, away_goals: null, coverage: 'pending' }] },
  ],
  insights: {
    matches_counted: 2,
    suspended_matches: 1,
    clubs: [insightClub],
    records: [{ key: 'best_attack', label: 'Mayor promedio de goles a favor', club: 'S.A.P.A.', value: 27.5, unit: 'goles por partido', detail: '55 goles en 2 partidos' }],
  },
}

const validCatalog = {
  schema_version: 'tournaments-v1',
  generated_at: '2026-11-17',
  tournaments: [{
    key: 'permanencia-2026',
    label: 'Permanencia 2026',
    competition: 'Permanencia 2026',
    zone: null,
    season: 2026,
    status: 'in_progress',
    coverage,
    updated_at: '2026-11-17',
    file: 'tournament_permanencia-2026.json',
    forecast_file: 'forecast_permanencia-2026.json',
    summary: { sapa: { position: 3, points: 35, played: 14 } },
    next_match: { round: 15, date: '2026-11-22', opponent: 'Lanús C', location: 'away' },
  }],
}

const validForecast = {
  schema_version: 'forecast-v1',
  public_key: 'permanencia-2026',
  competition: 'Permanencia 2026',
  tournament: 'Torneo Permanencia 2026 3ªM',
  season: 2026,
  updated_at: '2026-11-17',
  coverage,
  simulations: 20000,
  methodology: 'Estimación estadística.',
  points_rule: pointsRule,
  teams: [{
    club: 'S.A.P.A.',
    champion_probability: 0.04,
    finish_probabilities: { first: 0.04, second: 0.2, third: 0.4 },
    podium_probability: 0.64,
    expected_position: 3.08,
    campaign: [{ round: 1, date: '2026-08-09', opponent: 'Lanús C', location: 'home', goals_for: 30, goals_against: 25, result: 'win' }],
  }],
  fixtures: [{ round: 15, date: '2026-11-22', home: 'Lanús C', away: 'S.A.P.A.', home_win_probability: 0.7, draw_probability: 0.04, away_win_probability: 0.26 }],
  rival_profile: { club: 'Lanús C', competitions: [{ key: 'permanencia-2026', label: 'Permanencia 2026' }] },
}

describe('decodePublicTournamentCatalog', () => {
  it('decodes the catalog metadata and the SAPA summary', () => {
    const decoded = decodePublicTournamentCatalog(validCatalog)
    expect(decoded.tournaments[0].key).toBe('permanencia-2026')
    expect(decoded.tournaments[0].summary.sapa?.position).toBe(3)
    expect(decoded.tournaments[0].next_match?.location).toBe('away')
  })

  it('rejects a restricted catalog field', () => {
    const poisoned = { ...validCatalog, tournaments: [{ ...validCatalog.tournaments[0], internal_id: 9 }] }
    expect(() => decodePublicTournamentCatalog(poisoned)).toThrow(/restricted field/)
  })
})

describe('decodePublicCompetition', () => {
  it('decodes standings, rounds, scorers and marks', () => {
    const decoded = decodePublicCompetition(validCompetition)
    expect(decoded.standings[0].points).toBe(5)
    expect(decoded.rounds[1].matches[0].coverage).toBe('pending')
    expect(decoded.rounds[1].matches[0].home_goals).toBeNull()
    expect(decoded.insights.clubs[0].form_last_5.sequence).toEqual(['G', 'E'])
    expect(decoded.insights.records[0].value).toBe(27.5)
    expect(decoded.points_rule.loss).toBe(1)
  })

  it('rejects a restricted nested round field', () => {
    const poisoned = {
      ...validCompetition,
      rounds: [{ ...validCompetition.rounds[0], matches: [{ ...validCompetition.rounds[0].matches[0], raw_payload: 'x' }] }],
    }
    expect(() => decodePublicCompetition(poisoned)).toThrow(/restricted field/)
  })
})

describe('decodePublicForecast', () => {
  it('decodes podium probabilities and the rival profile', () => {
    const decoded = decodePublicForecast(validForecast)
    expect(decoded.teams[0].podium_probability).toBe(0.64)
    expect(decoded.teams[0].finish_probabilities.third).toBe(0.4)
    expect(decoded.rival_profile.club).toBe('Lanús C')
  })

  it('rejects a restricted nested team field', () => {
    const poisoned = { ...validForecast, teams: [{ ...validForecast.teams[0], raw_payload: 'x' }] }
    expect(() => decodePublicForecast(poisoned)).toThrow(/restricted field/)
  })
})
