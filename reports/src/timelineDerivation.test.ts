import { describe, expect, it } from 'vitest'
import type { Incident } from './projection'
import { deriveMomentum, scoreMatchesSummary } from './timelineDerivation'

const incident = (overrides: Partial<Incident>): Incident => ({
  reference: 'event', period: 1, regulation_seconds: null, clock_unverified: true, clock_label: null,
  incident_type: 'Incidencia', outcome: '', team_side: 'home', player_name: null, player_slug: null,
  event_kind: 'other', video_seconds: null, ...overrides,
})

describe('deriveMomentum', () => {
  it('orders events by period and usable time, preferring verified clock time', () => {
    const events = deriveMomentum([
      incident({ reference: 'video', regulation_seconds: null, video_seconds: 25 }),
      incident({ reference: 'clock', regulation_seconds: 10, clock_unverified: false, video_seconds: 200 }),
      incident({ reference: 'second-half', period: 2, regulation_seconds: 0, clock_unverified: false }),
    ])
    expect(events.map((event) => event.reference)).toEqual(['clock', 'video', 'second-half'])
  })

  it('omits events without a usable time anchor', () => {
    expect(deriveMomentum([incident({ reference: 'missing' })])).toEqual([])
  })

  it('derives the running score from goals instead of starting from final totals', () => {
    const events = deriveMomentum([
      incident({ reference: 'home-goal', outcome: 'Gol', event_kind: 'shot', regulation_seconds: 1, clock_unverified: false }),
      incident({ reference: 'away-goal', outcome: 'goal', event_kind: 'shot', team_side: 'away', regulation_seconds: 2, clock_unverified: false }),
    ])
    expect(events.map((event) => event.scoreDiff)).toEqual([1, 0])
    expect(scoreMatchesSummary(events, { home: { goals: 1 }, away: { goals: 1 } } as never)).toBe(true)
  })

  it('classifies passive as a distinct turnover cause', () => {
    const [event] = deriveMomentum([incident({ event_kind: 'turnover', outcome: 'passive', video_seconds: 10 })])
    expect(event.kind).toBe('passive')
  })
})
