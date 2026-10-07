import { describe, expect, it } from 'vitest'
import { derivePlayableSegments, mapVideoTime, playerAvailability } from './videoReview'

const segments = [
  { id: 1, period: 1, video_start_seconds: 10, video_end_seconds: 70, regulation_start_seconds: 5, regulation_end_seconds: 65, uncertainty_seconds: 2, coverage: 'playable' as const, clock_unverified: false },
  { id: 2, period: 1, video_start_seconds: 70, video_end_seconds: 95, regulation_start_seconds: null, regulation_end_seconds: null, uncertainty_seconds: 0, coverage: 'cut' as const, clock_unverified: true },
  { id: 3, period: 1, video_start_seconds: 95, video_end_seconds: 105, regulation_start_seconds: null, regulation_end_seconds: null, uncertainty_seconds: 0, coverage: 'offset' as const, clock_unverified: true },
  { id: 4, period: 1, video_start_seconds: 105, video_end_seconds: 120, regulation_start_seconds: null, regulation_end_seconds: null, uncertainty_seconds: 0, coverage: 'replay' as const, clock_unverified: true },
  { id: 5, period: 1, video_start_seconds: 120, video_end_seconds: 140, regulation_start_seconds: null, regulation_end_seconds: null, uncertainty_seconds: 0, coverage: 'pause' as const, clock_unverified: true },
  { id: 6, period: 1, video_start_seconds: 140, video_end_seconds: 200, regulation_start_seconds: 65, regulation_end_seconds: 125, uncertainty_seconds: 3, coverage: 'playable' as const, clock_unverified: false },
  { id: 7, period: 2, video_start_seconds: 1900, video_end_seconds: 1930, regulation_start_seconds: null, regulation_end_seconds: null, uncertainty_seconds: 0, coverage: 'halftime' as const, clock_unverified: true },
  { id: 8, period: 3, video_start_seconds: 1930, video_end_seconds: 1990, regulation_start_seconds: 0, regulation_end_seconds: 60, uncertainty_seconds: 1, coverage: 'playable' as const, clock_unverified: false },
]

describe('video review mapping', () => {
  it('maps only inside the selected playable segment', () => {
    expect(mapVideoTime(segments, 1, 40)).toEqual({ regulationSeconds: 35, uncertaintySeconds: 2, clockUnverified: false })
    expect(mapVideoTime(segments, 1, 170)).toEqual({ regulationSeconds: 95, uncertaintySeconds: 3, clockUnverified: false })
  })

  it('keeps cuts, delays, replays, non-play, and halftime clock-unverified', () => {
    expect(mapVideoTime(segments, 1, 80)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
    expect(mapVideoTime(segments, 1, 100)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
    expect(mapVideoTime(segments, 1, 110)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
    expect(mapVideoTime(segments, 1, 130)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
    expect(mapVideoTime(segments, 2, 1910)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
  })

  it('maps overtime independently and never extrapolates across a delay', () => {
    expect(mapVideoTime(segments, 3, 1960)).toEqual({ regulationSeconds: 30, uncertaintySeconds: 1, clockUnverified: false })
    expect(mapVideoTime(segments, 1, 1920)).toEqual({ regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true })
  })

  it('keeps provider outages distinct', () => {
    expect(playerAvailability(101)).toBe('embedding_disabled')
    expect(playerAvailability(100)).toBe('unavailable')
    expect(playerAvailability(2)).toBe('player_error')
    expect(playerAvailability()).toBe('unknown')
  })

  it('derives coverage only between increasing anchors in the same period', () => {
    const anchors = [
      { id: 1, period: 1, video_seconds: 10, regulation_seconds: 0, uncertainty_seconds: 1 },
      { id: 2, period: 1, video_seconds: 70, regulation_seconds: 60, uncertainty_seconds: 2 },
      { id: 3, period: 2, video_seconds: 100, regulation_seconds: 0, uncertainty_seconds: 1 },
    ]
    expect(derivePlayableSegments(anchors)).toEqual([{ period: 1, video_start_seconds: 10, video_end_seconds: 70, regulation_start_seconds: 0, regulation_end_seconds: 60, uncertainty_seconds: 2, coverage: 'playable', clock_unverified: false }])
  })
})
