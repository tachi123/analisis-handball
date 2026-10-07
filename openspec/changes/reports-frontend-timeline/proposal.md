# Proposal: Match Reports Timeline

## Intent

Give analysts a dedicated, read-only match timeline for reviewing canonical observations without mixing reporting with event capture or revision editing.

## Scope

### In Scope
- Add a protected, match-scoped timeline page and an explicit match-context entry point.
- Display canonical events in verified regulation-time order; fall back to video anchor, then canonical sequence, and label clock uncertainty.
- Filter events by player, kind, period, and evidence state; selection shows current payload, evidence, revision, active state, and uncertainty, and seeks video when available.
- Show unfiltered server-derived canonical state, metrics, and reconciliation context.

### Out of Scope
- Backend endpoints, database/schema changes, or new canonical contracts.
- Historical revision payload drill-down.
- Filtered client-calculated or authoritative metrics.
- Editing, capture, revision, or exclusion controls on the timeline page.

## Capabilities

### New Capabilities
- `match-report-timeline`: Read-only, match-scoped canonical-event timeline with filters, details, optional video seek, and unfiltered canonical context.

### Modified Capabilities
- `video-review-workspace`: Add a separate reporting route/entry boundary while preserving the review workspace as the editing surface.

## Approach

Build the page from current per-match canonical reads. Reuse narrow, tested video seek/time-mapping and event interaction utilities from `MatchReview`; keep filters local to the list and preserve server responses as the sole authority for metrics and reconciliation.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/pages/MatchReview.tsx` | Modified | Share stable playback/seek interaction boundary. |
| `frontend/src/components/EventTimeline.tsx` | Modified | Reusable chronological, filterable read-only list/details. |
| `frontend/src/pages/StatisticsPage.tsx` | Modified | Reuse canonical context presentation. |
| `frontend/src/pages/MatchesPage.tsx`, `frontend/src/App.tsx` | Modified | Route and match-context entry. |
| Backend / database / deployment | Unchanged | Existing canonical contracts and deployment model remain sufficient. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Sequence is not game-clock order | Medium | Apply explicit fallback order and uncertainty labels. |
| Missing video/playback | Medium | Keep filters and details fully usable; explain unavailable seek. |
| Reporting drifts into editing | Low | Separate route and omit mutation controls. |

## Rollback Plan

Remove the route and entry point; no data, API, schema, or deployment rollback is required.

## Dependencies

- Existing authenticated match context, canonical event/state/metrics/reconciliation reads, and optional video session.

## Success Criteria

- [ ] Analysts can open the protected read-only page from match context and inspect canonical events without edit controls.
- [ ] Ordering, filters, details, keyboard access, and video/no-video selection behavior are covered by frontend tests.
- [ ] Context remains unfiltered and server-derived; uncertain clocks and unavailable seeks are explicit.
