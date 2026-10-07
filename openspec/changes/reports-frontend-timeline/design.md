# Design: Match Reports Timeline

## Technical Approach

Add `/match/:matchId/reports` as a protected, read-only SPA page. It loads the existing per-match canonical reads in parallel, keeps filters and selection local, and never writes data or derives authoritative filtered metrics. The page reuses the established YouTube/session boundary; a missing session or unavailable player leaves the timeline and details usable.

## Architecture Decisions

| Decision | Choice | Alternative / rationale |
|---|---|---|
| Reporting boundary | New `MatchReportsTimeline` page, not an extension of `MatchReview` | Mixing capture/revision controls into reports violates the read-only requirement and enlarges an already dense page. |
| Timeline reuse | Extract pure video-anchor/seek/closest-event helpers from `EventTimeline` into `timelineInteractions.ts`; keep `mapVideoTime` in `videoReview.ts` and `useYouTubeSync` unchanged | Duplicating MatchReview's anchor lookup and `max(0, anchor - 2)` seek would drift. The new page imports only these narrow, tested seams. |
| Chronology | Pure report model sorts by `(confidence group, period, time, sequence)`: verified regulation time, usable video anchor, then sequence | `sequence` is capture order, so it is only a stable last fallback. Fallback rows visibly state `clock_unverified`. |
| Context authority | Render canonical state, metrics, and reconciliation responses verbatim in a dedicated summary component | Client-filtered counts are useful navigation only; presenting them as metrics would contradict the canonical contract. |

## Component Boundaries and Data Flow

`MatchReportsTimeline` owns route validation, React Query reads, selected event, filters, player-name lookup from `match.squad`, and the read-only video session.

```
getMatch + getCanonicalEvents + getCanonicalState + getCanonicalMetrics + getCanonicalReconciliation + getAnalysisSession
                                      │
                                      ▼
                         MatchReportsTimeline
                         ├─ reportTimeline model → TimelineFilters + ReportEventTimeline
                         ├─ selected event → EventDetailPanel + mapVideoTime display hint
                         ├─ source/session → useYouTubeSync → read-only player / seek
                         └─ untouched responses → CanonicalContext
```

`reportTimeline.ts` exposes `TimelineFilters`, `filterEvents`, `sortTimelineEvents`, and player/kind/period/evidence option builders. `ReportEventTimeline` renders filters, result status, roving event buttons, and calls `onSelect`; `EventDetailPanel` displays only the latest canonical payload, evidence, revision/reason, active state, roster-source labels, and uncertainty. `CanonicalContext` adapts the existing StatisticsPage metric/reconciliation presentation without package, publish, or mutation controls.

Selection records the event first. If `timelineInteractions` finds a video anchor and `useYouTubeSync` is ready, it seeks to the established two-second-preroll target. Otherwise it announces the specific no-seek condition. `mapVideoTime(session.time_segments, period, anchor)` may label mapping coverage, but never overwrites canonical clock values or changes ordering.

## Interfaces / Contracts

```ts
type ReportFilters = {
  playerId: number | 'all'; kind: CanonicalEventKind | 'all'
  period: number | 'all'; evidenceState: EvidenceState | 'all'
}

type TimelineRow = { event: CanonicalEvent; clockSource: 'verified' | 'video' | 'sequence' }
```

No API, type-contract, database, backend, or Capacitor changes are required. Existing query keys remain `['match', id]`, `['canonical-events', id]`, `['canonical-state', id]`, `['canonical-metrics', id]`, `['canonical-reconciliation', id]`, and `['analysis-session', id]`.

## Accessibility and Routing

Wrap the new route in the existing `ProtectedRoute`; page-level match query errors use the established unavailable/error state. Add an explicit “Reports timeline” entry in match context. Filters use labeled native selects and a clear-filters button; an `aria-live` status announces visible count and selection/no-seek results. Event rows are semantic buttons with visible `focus-visible` styling and roving focus. Up/Down (plus Home/End) operate only while a timeline row has focus; inputs/selects receive normal typing and no window-level shortcut handler is installed. Help text describes these keys.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/pages/MatchReportsTimeline.tsx` | Create | Protected read-only composition, queries, player, selection. |
| `frontend/src/components/ReportEventTimeline.tsx` | Create | Filters, ordered list, keyboard selection, details panel. |
| `frontend/src/components/CanonicalContext.tsx` | Create | Unfiltered state/metrics/reconciliation display. |
| `frontend/src/reportTimeline.ts` | Create | Pure filtering, ordering, labels, and tests. |
| `frontend/src/timelineInteractions.ts` | Create | Shared video-anchor, seek-target, closest-event helpers. |
| `frontend/src/components/EventTimeline.tsx` | Modify | Consume extracted helpers; preserve review behavior. |
| `frontend/src/pages/MatchReview.tsx` | Modify | Consume shared seek helper; preserve mutation behavior. |
| `frontend/src/App.tsx`, `frontend/src/pages/MatchesPage.tsx` | Modify | Protected route and explicit entry. |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | Filter combinations, confidence/fallback sorting, seek target, unknown labels | Vitest for pure model/interaction modules. |
| Component | Count/live announcements, details, no-seek, keyboard and text-entry safety | Testing Library with mocked player/API. |
| Route | Authenticated route, unauthenticated redirect, match-unavailable state, unfiltered context | Extend App/page tests with React Query and MemoryRouter. |

## Delivery Slices

Each slice is a reviewable work unit with tests in the same commit and stays below 400 changed lines.

1. **Route and shared seams** (~260 lines): extract timeline interactions, add protected reports shell and Matches entry, route/helper tests. Rollback removes route/entry.
2. **Readable canonical timeline** (~380 lines): add pure report model and timeline/detail components with filters, sort, uncertainty, and keyboard tests. Rollback removes report-only components.
3. **Context and optional playback** (~360 lines): compose canonical context and read-only player/session seek, add unavailable/authority tests. Rollback removes these sections without data impact.

## Migration / Rollout

No migration required. Ship the slices as a chained feature branch; slice 1 targets the feature branch, and each later slice targets its immediate predecessor. No backend deployment change is needed.

## Open Questions

None.
