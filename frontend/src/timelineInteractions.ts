import type { CanonicalEvent } from './types'

export function videoAnchorSeconds(event: CanonicalEvent): number | null {
  const anchor = event.evidence?.find(item => item.kind === 'video')?.video_anchor_seconds
  return typeof anchor === 'number' ? anchor : null
}

export function seekTargetForEvent(event: CanonicalEvent): number | null {
  const anchor = videoAnchorSeconds(event)
  return anchor === null ? null : Math.max(0, anchor - 2)
}

export function closestEventId(events: CanonicalEvent[], time: number) {
  return events.reduce<CanonicalEvent | null>((closest, event) => {
    const anchor = videoAnchorSeconds(event)
    if (anchor === null) return closest
    return !closest || Math.abs(anchor - time) < Math.abs(videoAnchorSeconds(closest)! - time) ? event : closest
  }, null)?.id ?? null
}
