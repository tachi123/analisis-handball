import type { TimeAnchor, TimeSegment, VideoAvailabilityState } from './types'

export type VideoTimeMapping = {
  regulationSeconds: number | null
  uncertaintySeconds: number | null
  clockUnverified: boolean
}

export function mapVideoTime(segments: TimeSegment[], period: number, videoSeconds: number): VideoTimeMapping {
  const segment = segments.find(candidate =>
    candidate.period === period
    && candidate.coverage === 'playable'
    && !candidate.clock_unverified
    && candidate.regulation_start_seconds !== null
    && candidate.regulation_end_seconds !== null
    && candidate.video_start_seconds <= videoSeconds
    && videoSeconds <= candidate.video_end_seconds,
  )
  const regulationStart = segment?.regulation_start_seconds
  const regulationEnd = segment?.regulation_end_seconds
  if (!segment || regulationStart === null || regulationStart === undefined || regulationEnd === null || regulationEnd === undefined) {
    return { regulationSeconds: null, uncertaintySeconds: null, clockUnverified: true }
  }
  const progress = (videoSeconds - segment.video_start_seconds) / (segment.video_end_seconds - segment.video_start_seconds)
  return {
    regulationSeconds: Math.round(regulationStart + progress * (regulationEnd - regulationStart)),
    uncertaintySeconds: segment.uncertainty_seconds,
    clockUnverified: false,
  }
}

export function playerAvailability(errorCode?: number): VideoAvailabilityState {
  if (errorCode === 101 || errorCode === 150) return 'embedding_disabled'
  if (errorCode === 100) return 'unavailable'
  if (errorCode === 2 || errorCode === 5) return 'player_error'
  return 'unknown'
}

/** Creates verified coverage only from an explicit pair of anchors in one period. */
export function derivePlayableSegments(anchors: TimeAnchor[]): Array<Omit<TimeSegment, 'id'>> {
  const ordered = [...anchors].sort((left, right) => left.period - right.period || left.video_seconds - right.video_seconds)
  return ordered.flatMap((anchor, index) => {
    const next = ordered[index + 1]
    if (!next || next.period !== anchor.period || next.video_seconds <= anchor.video_seconds || next.regulation_seconds <= anchor.regulation_seconds) return []
    return [{ period: anchor.period, video_start_seconds: anchor.video_seconds, video_end_seconds: next.video_seconds,
      regulation_start_seconds: anchor.regulation_seconds, regulation_end_seconds: next.regulation_seconds,
      uncertainty_seconds: Math.max(anchor.uncertainty_seconds, next.uncertainty_seconds), coverage: 'playable' as const, clock_unverified: false }]
  })
}
