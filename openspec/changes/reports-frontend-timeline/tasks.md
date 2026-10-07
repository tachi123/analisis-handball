# Tasks: Match Reports Timeline

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 1,140–1,360 total; each slice 240–380 |
| 400-line budget risk | High (feature total) |
| Chained PRs recommended | Yes |
| Delivery strategy | ask-always |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Slice / boundary | Est. lines | Likely files | Verification / rollback |
|---|---:|---|---|
| 1. Foundation, route, canonical fetch | 240–320 | `timelineInteractions.ts`, `EventTimeline.tsx`, `MatchReview.tsx`, page, route, entry, tests | Route/auth/helper tests; revert this slice together. |
| 2. Filterable timeline and ordering | 300–380 | `reportTimeline.ts`, `ReportEventTimeline.tsx`, unit/component tests | Filter/sort/count tests; remove report model/list only. |
| 3. Detail, seek, canonical context | 280–360 | page, `CanonicalContext.tsx`, component/page tests | Seek/no-seek/context tests; remove detail/context only. |
| 4. Accessibility, keyboard, integration | 220–300 | report files, `App.test.tsx`, page tests | Keyboard, route, unavailable, full frontend suite; revert polish/tests or completed chain. |

## Phase 1: Foundation, Route, and Canonical Fetch (Slice 1)

- [x] 1.1 Create `frontend/src/timelineInteractions.ts`; extract anchor lookup, closest-event, and two-second-preroll seek target from `EventTimeline.tsx`/`MatchReview.tsx` without changing review mutations.
- [x] 1.2 Create `frontend/src/pages/MatchReportsTimeline.tsx` shell: validate `matchId`; parallel-read match, canonical events/state/metrics/reconciliation, and analysis session with existing query keys; render established loading/unavailable states.
- [x] 1.3 Add protected `/match/:matchId/reports` in `frontend/src/App.tsx` and a “Reports timeline” match entry in `frontend/src/pages/MatchesPage.tsx`; add helper and authenticated/redirect route tests.

## Phase 2: Filterable Timeline and Ordering (Slice 2)

- [x] 2.1 Create `frontend/src/reportTimeline.ts` with typed filter options, combined local filtering, confidence ordering (verified clock → video anchor → sequence), and explicit fallback labels; unit-test mixed evidence and clear filters.
- [x] 2.2 Create `frontend/src/components/ReportEventTimeline.tsx` with labeled native player/kind/period/evidence selects, clear filters, ordered read-only event buttons, and visible-count live status; test combined filters and uncertainty.
- [x] 2.3 Wire the pure model into `MatchReportsTimeline.tsx`; confirm filters never alter fetched canonical state, metrics, or reconciliation.

## Phase 3: Event Detail, Video Seek, and Canonical Context (Slice 3)

- [x] 3.1 Add selected-event detail to `ReportEventTimeline.tsx`: latest payload/evidence, revision/reason, active state, roster labels, and uncertainty; omit all mutation and history-drill-down controls.
- [x] 3.2 Use `useYouTubeSync` and `timelineInteractions.ts` in `MatchReportsTimeline.tsx`; select first, seek only when player and anchor are usable, map coverage as a hint, and announce each no-seek reason.
- [x] 3.3 Create `frontend/src/components/CanonicalContext.tsx` from the read-only canonical sections of `StatisticsPage.tsx`; render untouched state, metrics, and reconciliation responses. Test seek/no-seek and unfiltered authority.

## Phase 4: Accessibility, Keyboard, and Integration (Slice 4)

- [x] 4.1 Implement roving row focus and scoped Up/Down/Home/End handling in `ReportEventTimeline.tsx`; retain native input/select behavior, focus-visible styles, help text, and selection live announcements.
- [x] 4.2 Add `MatchReportsTimeline.test.tsx` and extend `App.test.tsx`: keyboard navigation/text safety, detail announcement, unavailable match, protected routing, no edit controls, and unchanged canonical context under filters.
- [x] 4.3 Run `npm --prefix frontend test -- --run`, `npm --prefix frontend run lint`, and `npm --prefix frontend run build`; record actual diff size per slice before opening its chained PR.

### Verifier remediation — 2026-08-27

- [x] 4.4 Add runtime coverage that opens the timeline through its match-context entry and that verifies the protected `/match/:matchId/reports` compatibility redirect reaches the timeline.
- [x] 4.5 Extend selected-event detail coverage to assert the current payload, evidence, revision/reason, active state, and clock uncertainty.

### Apply verification — 2026-08-27

| Work unit | Actual size / boundary | Verification |
|---|---|---|
| Maintainer-approved `size:exception` | 311 physical lines across the newly added report modules and tests; route/entry integration is limited to `App.tsx` and `MatchesPage.tsx`. The verifier-remediation tests additionally adjust `App.tsx` to make the existing `/reports` redirect path-relative. No Git workflow was performed. | 80 frontend tests passed; lint passed; production build passed; `backend/tests/test_canonical_analysis_routes.py` passed (10 tests, 28 pre-existing Pydantic deprecation warnings). |
