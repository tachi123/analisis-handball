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

  it('decode the forecast and the legacy fallback', () => {
    const forecast = decodePublicForecast(read('forecast_permanencia-2026.json'))
    expect(forecast.teams.length).toBe(16)
    expect(forecast.rival_profile.club).toBe('Lanús C')
    const legacy = decodePublicTournament(read('tournament.json'))
    expect(legacy.forecast?.points_rule?.win).toBe(3)
  })
})
