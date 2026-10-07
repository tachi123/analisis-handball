import type { CanonicalEvent, CanonicalEventKind, EvidenceState } from './types'
import { videoAnchorSeconds } from './timelineInteractions'

export type ReportFilters = {
  playerId: number | 'all'
  kind: CanonicalEventKind | 'all'
  period: number | 'all'
  evidenceState: EvidenceState | 'all'
}

export type ClockSource = 'verified' | 'video' | 'sequence'
export type TimelineRow = { event: CanonicalEvent; clockSource: ClockSource }

export const emptyReportFilters: ReportFilters = { playerId: 'all', kind: 'all', period: 'all', evidenceState: 'all' }

export function clockSource(event: CanonicalEvent): ClockSource {
  if (event.payload.regulation_seconds !== null && !event.payload.clock_unverified) return 'verified'
  return videoAnchorSeconds(event) !== null ? 'video' : 'sequence'
}

export function filterEvents(events: CanonicalEvent[], filters: ReportFilters) {
  return events.filter(event =>
    (filters.playerId === 'all' || event.payload.player_id === filters.playerId)
    && (filters.kind === 'all' || event.payload.kind === filters.kind)
    && (filters.period === 'all' || event.payload.period === filters.period)
    && (filters.evidenceState === 'all' || event.payload.evidence_state === filters.evidenceState),
  )
}

export function sortTimelineEvents(events: CanonicalEvent[]): TimelineRow[] {
  return events.map(event => ({ event, clockSource: clockSource(event) })).sort((left, right) => {
    const group = { verified: 0, video: 1, sequence: 2 }
    const groupOrder = group[left.clockSource] - group[right.clockSource]
    if (groupOrder) return groupOrder
    if (left.clockSource === 'verified') return left.event.payload.period - right.event.payload.period || (left.event.payload.regulation_seconds ?? 0) - (right.event.payload.regulation_seconds ?? 0) || left.event.sequence - right.event.sequence
    if (left.clockSource === 'video') return videoAnchorSeconds(left.event)! - videoAnchorSeconds(right.event)! || left.event.sequence - right.event.sequence
    return left.event.sequence - right.event.sequence
  })
}

export function timelineRows(events: CanonicalEvent[], filters: ReportFilters) {
  return sortTimelineEvents(filterEvents(events, filters))
}

export function fallbackLabel(source: ClockSource) {
  return source === 'verified' ? null : source === 'video' ? 'Reloj sin verificar; ordenado por ancla de video.' : 'Reloj sin verificar; ordenado por secuencia canónica.'
}
