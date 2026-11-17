import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { decodePublicCompetition } from './publicCompetitions'
import { annualTotals, attackComposition, rosterContinuity, seasonMatches, seasonScorers } from './seasonData'

const read = (name: string) => JSON.parse(readFileSync(new URL(`../public/${name}`, import.meta.url), 'utf-8'))
const apertura = decodePublicCompetition(read('tournament_apertura-zona-b-2026.json'))
const permanencia = decodePublicCompetition(read('tournament_permanencia-2026.json'))

describe('Lanús 2026 season calculations', () => {
  it('collects every match, including the pending final round', () => {
    const aperturaMatches = seasonMatches(apertura, 'Lanús C')
    const permanenciaMatches = seasonMatches(permanencia, 'Lanús C')
    expect(aperturaMatches).toHaveLength(15)
    expect(permanenciaMatches).toHaveLength(15)
    const pending = permanenciaMatches.find((match) => match.result === 'pending')
    expect(pending?.round).toBe(15)
    expect(pending?.opponent).toBe('S.A.P.A.')
    expect(pending?.location).toBe('home')
  })

  it('adds the annual totals without merging tables', () => {
    const totals = annualTotals([apertura, permanencia], 'Lanús C')
    expect(totals.played).toBe(29)
    expect(totals.points).toBe(60)
    expect(totals.maxPoints).toBe(87)
    expect(totals.goalsFor).toBe(800)
    expect(totals.goalsAgainst).toBe(766)
  })

  it('groups the annual scorers by normalized name', () => {
    const scorers = seasonScorers([apertura, permanencia], 'Lanús C')
    const szymborski = scorers.find((row) => row.name.toLowerCase().includes('szymborski') && row.name.toLowerCase().includes('lautaro'))
    expect(szymborski?.goals).toBe(116)
    expect(szymborski?.appearances).toBe(27)
    expect(szymborski?.byCompetition).toHaveLength(2)
  })

  it('estimates squad continuity from the two competitions', () => {
    const previous = seasonScorers([apertura], 'Lanús C')
    const current = seasonScorers([permanencia], 'Lanús C')
    const continuity = rosterContinuity(previous, current)
    expect(continuity.previous).toBe(27)
    expect(continuity.current).toBe(22)
    expect(continuity.shared).toBe(19)
    expect(continuity.retained).toBeCloseTo(0.864, 3)
  })

  it('describes the attack composition without claiming causality', () => {
    const previous = seasonScorers([apertura], 'Lanús C')
    const current = seasonScorers([permanencia], 'Lanús C')
    const composition = attackComposition(previous, current, 380, 420)

    expect(composition.retained.players).toBe(19)
    expect(composition.retained.previousGoals).toBe(306)
    expect(composition.retained.currentGoals).toBe(330)
    expect(composition.departed.goals).toBe(74)
    expect(composition.arrived.goals).toBe(90)
    expect(composition.arrived.players).toBe(3)
    expect(composition.arrived.details[0].name).toContain('Barreto')
    expect(composition.concentration.previous.top3).toBeCloseTo(0.405, 3)
    expect(composition.concentration.current.top5).toBeCloseTo(0.590, 3)
  })
})
