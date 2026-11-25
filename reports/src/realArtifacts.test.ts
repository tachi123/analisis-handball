import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { decodePublicCompetition, decodePublicForecast, decodePublicTournamentCatalog } from './publicCompetitions'
import { decodePublicTournament } from './tournamentProjection'

const read = (name: string) => JSON.parse(readFileSync(new URL(`../public/${name}`, import.meta.url), 'utf-8'))

describe('shipped public artifacts', () => {
  it('decode the catalog and every tournament artifact', () => {
    const catalog = decodePublicTournamentCatalog(read('tournaments.json'))
    expect(catalog.tournaments).toHaveLength(3)
    for (const entry of catalog.tournaments) {
      const competition = decodePublicCompetition(read(entry.file))
      expect(competition.public_key).toBe(entry.key)
      expect(competition.rounds.length).toBeGreaterThan(0)
      expect(competition.insights.clubs.length).toBeGreaterThan(0)
    }
  })

  it('decodes the completed forecast and retains its pre-match archive', () => {
    const forecast = decodePublicForecast(read('forecast_permanencia-2026.json'))
    expect(forecast.teams).toHaveLength(0)
    expect(forecast.archives).toHaveLength(1)
    expect(forecast.archives[0].forecast.teams).toHaveLength(16)
    expect(forecast.archives[0].result).toEqual({ home_goals: 31, away_goals: 30 })
    const legacy = decodePublicTournament(read('tournament.json'))
    expect(legacy.forecast?.points_rule?.win).toBe(3)
  })
})
