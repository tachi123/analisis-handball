import { describe, expect, it } from 'vitest'
import { decodePublicTournament } from './tournamentProjection'

const valid = {
  schema_version: 'tournament-v1',
  tournament: 'Torneo Permanencia 2026 3ªM',
  season: 2026,
  updated_at: '2026-11-10',
  coverage: { rounds_played: 13, rounds_total: 15, status: 'partial', label: 'Cubre fechas jugadas.' },
  standings: [
    { pos: 1, club: 'Lanús C', played: 13, won: 10, drawn: 1, lost: 2, penalized: 0, goals_for: 394, goals_against: 332, goal_difference: 62, points: 34 },
    { pos: 4, club: 'S.A.P.A.', played: 13, won: 9, drawn: 1, lost: 3, penalized: 0, goals_for: 347, goals_against: 328, goal_difference: 19, points: 32 },
  ],
  scorers: [
    { name: 'Losso, Emiliano', club: 'C.S. y D. Defensores de Banfield', appearances: 11, goals: 105, yellow: 2, two_min: 3, red: 0, blue: 0, goals_per_game: 9.55 },
  ],
  clubs: [
    { club: 'S.A.P.A.', appearances: 167, goals: 327, yellow: 6, two_min: 30, red: 4, blue: 0, players: 22 },
  ],
}

describe('decodePublicTournament', () => {
  it('decodes a valid tournament document', () => {
    const decoded = decodePublicTournament(valid)
    expect(decoded.schema_version).toBe('tournament-v1')
    expect(decoded.standings).toHaveLength(2)
    expect(decoded.standings[1].club).toBe('S.A.P.A.')
    expect(decoded.standings[1].points).toBe(32)
    expect(decoded.scorers[0].goals).toBe(105)
    expect(decoded.coverage.status).toBe('partial')
  })

  it('rejects a restricted field', () => {
    const poisoned = { ...valid, standings: [{ ...valid.standings[0], internal_id: 123 }] }
    expect(() => decodePublicTournament(poisoned)).toThrow(/restricted field/)
  })

  it('rejects a document with a database-id field', () => {
    const poisoned = { ...valid, database: 'postgres' }
    expect(() => decodePublicTournament(poisoned)).toThrow(/restricted field/)
  })

  it('decodes the allowlisted forecast in tournament-v2', () => {
    const projected = {
      ...valid,
      schema_version: 'tournament-v2',
      forecast: {
        simulations: 20000,
        methodology: 'Estimate only.',
        teams: [{ club: 'S.A.P.A.', champion_probability: 0.18 }],
        fixtures: [{ round: 14, date: '2026-11-14', home: 'S.A.P.A.', away: 'Lanús C', home_win_probability: 0.4, draw_probability: 0.1, away_win_probability: 0.5 }],
      },
    }
    expect(decodePublicTournament(projected).forecast?.fixtures[0].home).toBe('S.A.P.A.')
  })
})
