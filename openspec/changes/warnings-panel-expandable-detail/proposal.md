# Proposal: Expand Warning Comparison Details

## Intent

Let analysts inspect canonical evidence behind each Warnings Panel discrepancy without leaving the comparison or seeing unrelated events. The official planilla remains an immutable total-only reference.

## Scope

### In Scope
- Add an expandable, inline detail for every comparison with linked canonical events.
- Use a native button with `aria-expanded` and `aria-controls`; preserve table semantics with a full-width detail row.
- Lazily load existing canonical events, filter by `canonical_event_ids`, and show the official total plus each event's player, kind, period, regulation time, video time, and evidence type.
- Let video-anchored events seek through `seekTargetForEvent` and `useYouTubeSync`; retain readable non-video/unavailable evidence states.
- Add component coverage for disclosure, keyboard activation, ARIA linkage, displayed fields, and seeking boundaries.

### Out of Scope
- Backend APIs, schemas, persistence, or calculation changes.
- Official event timestamps or inferred official-event detail.
- Revisions, discrepancy resolution, official-data mutation, or any write action.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `review-statistics`: Reconciliation views expose a focused, read-only canonical-event disclosure for a selected official-versus-canonical comparison while retaining immutable official values.

## Approach

Replace the broad timeline drill-down with inline comparison disclosure in `WarningsPanel`. Fetch `canonical-events` and the analysis session only on first expansion, retain a selected comparison/event, and filter fetched events by that comparison's canonical IDs. Render official totals only; use the existing readiness-aware YouTube seek path for video anchors. Native buttons supply Enter/Space behavior without a key handler.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/components/WarningsPanel.tsx` | Modified | Inline filtered detail and event seeking. |
| `frontend/src/components/WarningsPanel.test.tsx` | Modified | Disclosure, accessibility, content, and seek tests. |
| Backend/database/deployment | None | Existing read endpoints and artifacts are reused. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Missing IDs or unavailable media | Medium | Show explicit empty/evidence state; do not seek. |
| Dense table/ARIA regressions | Medium | Full-width detail rows and stable unique control IDs. |
| Review size exceeds 400 lines | Medium | Approved `size:exception`; keep focused UI/tests. |

## Rollback Plan

Revert the frontend component and focused tests to restore the current read-only timeline drill-down. No data, API, or schema rollback is needed.

## Dependencies

- Existing `warnings-summary`, `canonical-events`, analysis-session, `seekTargetForEvent`, and `useYouTubeSync` contracts.

## Success Criteria

- [ ] Each linked comparison expands accessibly to its official total and only its linked canonical events.
- [ ] Events show all requested fields; official timestamps are never shown or inferred.
- [ ] Video seeks only for ready, video-anchored evidence; unavailable/PDF evidence remains readable.
- [ ] The UI remains strictly read-only and focused frontend tests pass.
