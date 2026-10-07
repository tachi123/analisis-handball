import { describe, expect, it } from 'vitest'
import { closestEventId, seekTargetForEvent, videoAnchorSeconds } from './timelineInteractions'
import type { CanonicalEvent } from './types'

const anchored = (id: number, anchor: number): CanonicalEvent => ({ id, sequence: id, active: true, payload: { kind: 'shot', period: 1, regulation_seconds: null, clock_unverified: true, team_id: null, player_id: null, outcome: null, fact_kind: 'observed', evidence_state: 'confirmed', uncertainty: [], note: null }, evidence: [{ id, kind: 'video', video_anchor_seconds: anchor, uncertainty: [] }] })

describe('timeline interactions', () => {
  it('finds usable anchors, applies the review preroll, and selects the closest anchored event', () => {
    const first = anchored(1, 1); const second = anchored(2, 18)
    expect(videoAnchorSeconds(first)).toBe(1)
    expect(seekTargetForEvent(first)).toBe(0)
    expect(closestEventId([first, second], 16)).toBe(2)
  })

  it('does not invent a seek target when video provenance is absent', () => {
    const noVideo = { ...anchored(3, 10), evidence: [] }
    expect(videoAnchorSeconds(noVideo)).toBeNull()
    expect(seekTargetForEvent(noVideo)).toBeNull()
    expect(closestEventId([noVideo], 10)).toBeNull()
  })
})
