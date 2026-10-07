# Design: Expand Warning Comparison Details

`WarningsPanel` will turn each linked warning comparison into a focused, read-only inline disclosure. It reuses the existing canonical-event/session reads and video synchronization; no backend, schema, or mobile-client work is required.

## Technical Approach

Keep `warnings-summary` as the authoritative source for official totals and `canonical_event_ids`. A native disclosure button in each linked comparison cell inserts a full-width table detail row immediately after its owning player/total row. The row loads canonical events and the analysis session lazily, filters events by the owning comparison IDs, and renders only those canonical records.

Each event row exposes the player label, kind, period, regulation time, explicit `clock_unverified` state, video-anchor time, and evidence kinds. Its read-only evidence action selects that event in the filtered `ReportEventTimeline` state and queues its existing `seekTargetForEvent` flow. The player seeks only once `useYouTubeSync` reports a ready iframe.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Inline full-width `<tr>` detail after the comparison row | Modal; section nested in a table cell | Preserves valid table structure, keeps the official total in context, and avoids unrelated events. |
| Native per-comparison button with stable detail ID | Custom keyboard handler; clickable `div` | Native buttons supply Enter/Space and focus behavior. `aria-expanded` and `aria-controls` make each disclosure state inspectable. |
| Query-enabled-on-expansion cache | Eager fetch; new endpoint | `getCanonicalEvents` and `getAnalysisSession` already exist and React Query caches them after the first expansion. |
| Filter with `canonical_event_ids` client-side | Display all events; backend filter | The summary already carries the authorization/scope IDs; filtering prevents unrelated evidence without API changes. |
| Reuse timeline selection and seek lifecycle | Duplicate video controls; direct iframe messaging | Retains the tested readiness guard in `useYouTubeSync` and `seekTargetForEvent`. |

## Data Flow

```text
warnings-summary comparison
  -> disclosure button (expandedComparisonKey)
  -> React Query: canonical-events + analysis-session (first expansion)
  -> canonical_event_ids filter
  -> inline event rows + filtered ReportEventTimeline selection
  -> evidence action -> selectedEvent + pendingSeekId
  -> seekTargetForEvent -> ready useYouTubeSync iframe -> seekTo
```

Expansion sets a polite live notice (for example, which comparison opened); collapse announces closure and returns focus to the same native disclosure button. Switching comparisons closes the prior detail, keeps focus on the newly activated button, and clears a pending seek. A comparison without IDs renders the explicit no-linked-events text and no disclosure button. Loading and fetch failures remain inside the detail row; no official timestamp is rendered or inferred.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/components/WarningsPanel.tsx` | Modify | Replace global drill-down state with keyed inline disclosure, scoped event presentation, live notices, filtered timeline selection, and readiness-aware evidence seeking. |
| `frontend/src/components/WarningsPanel.test.tsx` | Modify | Cover disclosure, unique ARIA linkage/state, native keyboard activation/focus, filtering, required fields, evidence states, and ready-only seek. |
| `frontend/src/components/ReportEventTimeline.tsx` | Modify | Accept the warning panel's already filtered event list and preserve selected-event indication without exposing unrelated events or write controls. |

## Interfaces / Contracts

No API or schema contract changes. Component state remains local:

```ts
type ExpandedComparison = string | null
type PendingSeek = number | null
// linkedEvents = events.filter(event => comparison.canonical_event_ids.includes(event.id))
```

`getCanonicalEvents(matchId)`, `getAnalysisSession(matchId)`, `WarningComparison.canonical_event_ids`, `seekTargetForEvent`, and `useYouTubeSync` are reused unchanged. An evidence action is rendered only when `seekTargetForEvent(event)` returns a target; PDF, unavailable, and other non-video evidence display their kind but do not queue a seek.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Component | Expand/collapse, ARIA IDs/state, no-ID comparison, focused filtered detail | Vitest + Testing Library assertions on buttons, rows, live region, and focus. |
| Component | Native Enter/Space and accessible focus management | Focus the actual button and use keyboard activation; assert no custom duplicate activation. |
| Component integration | Required fields, PDF/unavailable visibility, video action and ready-player seek | Mock existing reads and `useYouTubeSync`; verify `seekTo` only after readiness. |
| E2E | Not available | No configured runner; record component coverage instead. |

## Migration / Rollout

No migration, flag, deployment, API, schema, or mobile-client rollout is required. Roll back by reverting the two focused component changes and their tests.

## Review Scope

Deliver one frontend work unit: inline warning evidence and its focused tests. It is intentionally one slice under the 400-line review budget; the approved `size:exception` remains available only if the measured UI-plus-test diff exceeds the budget.

## Open Questions

None.
