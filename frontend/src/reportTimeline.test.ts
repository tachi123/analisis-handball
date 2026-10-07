import { describe, expect, it } from 'vitest'
import { emptyReportFilters, filterEvents, sortTimelineEvents } from './reportTimeline'
import type { CanonicalEvent } from './types'

const event = (id: number, overrides: Partial<CanonicalEvent['payload']> = {}, anchor: number | null = null): CanonicalEvent => ({ id, sequence: id, active: true, payload: { kind: 'shot', period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null, ...overrides }, evidence: anchor === null ? [] : [{ id, kind: 'video', video_anchor_seconds: anchor, uncertainty: [] }] })

describe('report timeline model', () => {
  const events = [event(1, { player_id: 10, regulation_seconds: 40, clock_unverified: false }), event(2, { player_id: 11, kind: 'turnover', evidence_state: 'ambiguous' }, 15), event(3, { player_id: 10, period: 2 })]

  it('filters all dimensions together and clears back to all canonical events', () => {
    expect(filterEvents(events, { playerId: 10, kind: 'shot', period: 1, evidenceState: 'confirmed' })).toEqual([events[0]])
    expect(filterEvents(events, emptyReportFilters)).toEqual(events)
  })

  it('orders verified clocks before video fallback and sequence fallback with explicit sources', () => {
    expect(sortTimelineEvents([events[2], events[1], events[0]]).map(row => [row.event.id, row.clockSource])).toEqual([[1, 'verified'], [2, 'video'], [3, 'sequence']])
  })
})
