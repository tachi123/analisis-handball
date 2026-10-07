# Tasks: Expand Warning Comparison Details

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 350–430 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | One frontend work unit; use the approved size exception only if measured diff exceeds 400 lines. |
| Delivery strategy | ask-always |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Inline warning evidence with focused tests | Single PR | Component, timeline scoping, and tests land together; approved exception if needed. |

## Phase 1: Scoped Disclosure Foundation

- [x] 1.1 Modify `frontend/src/components/WarningsPanel.tsx` to replace global drill-down state with a keyed expanded comparison, stable detail IDs, and a native disclosure button using accurate `aria-expanded`/`aria-controls`.
- [x] 1.2 Enable `getCanonicalEvents(matchId)` and `getAnalysisSession(matchId)` only after first expansion; filter fetched events by the active comparison's `canonical_event_ids` and render explicit no-linked-events text without a button.
- [x] 1.3 Modify `frontend/src/components/ReportEventTimeline.tsx` to accept the already filtered warning-event list and retain selected-event indication without exposing unrelated events or write controls.

## Phase 2: Detail, Evidence, and Accessibility

- [x] 2.1 Render the expanded comparison as a full-width table detail row with immutable official total and per-event player, kind, period, regulation time, `clock_unverified`, video time, and evidence type; never render or infer official timestamps.
- [x] 2.2 Wire video-only evidence actions through filtered selection, `seekTargetForEvent`, and the ready `useYouTubeSync` player; keep PDF, unavailable, and non-video evidence readable with no seek action.
- [x] 2.3 Add a polite ARIA live announcement for expand, collapse, selection, and unavailable evidence; collapse returns focus to its disclosure, while switching comparisons clears pending seeks and keeps focus on the activated control.
- [x] 2.4 Remove the custom Enter/Space key handler from `WarningsPanel.tsx`; rely on native button activation and preserve visible focus styling.

## Phase 3: Focused Component Verification

- [x] 3.1 Extend `frontend/src/components/WarningsPanel.test.tsx` for pointer and native Enter/Space expand-collapse, unique ARIA linkage/state, live notices, focus return, and no-ID comparisons.
- [x] 3.2 Test lazy canonical/session reads, comparison-ID filtering, required canonical fields, immutable official total, and absence of official timestamps or mutation controls.
- [x] 3.3 Test ready-player video seek plus PDF/unavailable/non-video evidence visibility and the absence of seek actions/calls for those states.
- [x] 3.4 Run `npm --prefix frontend test -- --run`, `npm --prefix frontend run lint`, and `npm --prefix frontend run build`; record measured changed lines before opening the single PR. Measured work-unit footprint: 314 lines across the component, scoped timeline presentation, focused tests, and task checklist; within the 400-line budget.

## Phase 4: Verifier Remediation

- [x] 4.1 Add a Chromium-backed Vitest Browser Mode test that focuses the native disclosure button, sends Enter to expand and Space to collapse, and verifies the inline detail and `aria-expanded` state without dispatching a manual click.
- [x] 4.2 Add `npm --prefix frontend run test:browser` and keep browser test files excluded from the jsdom-only suite; run browser, frontend, lint, and production-build verification.
