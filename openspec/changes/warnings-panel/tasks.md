# Tasks: Add Canonical Warnings Panel

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450-600 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Backend derivation + endpoint + tests → PR 2: Frontend panel + drill-down + tests |
| Delivery strategy | ask-on-risk (size:exception approved) |
| Chain strategy | size:exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size:exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend warnings derivation, endpoint, service/route tests | PR 1 | Independent read-only slice; no DB migration |
| 2 | Frontend types, client, panel, StatisticsPage integration, tests | PR 2 | Depends on PR 1; read-only panel with drill-down |

## Phase 1: Backend Service & Endpoint (Slice 1)

- [x] 1.1 Add `blue_card` sanction outcome support in `backend/app/services/canonical_analysis_service.py`
- [x] 1.2 Implement `read_warnings_summary` aggregation: bucket canonical events by player/match, union with official snapshot players
- [x] 1.3 Add comparison logic: zero-tolerance statuses (`exact`, `missing_in_canonical`, `missing_in_official`), `not_comparable` for temporal/GK checks
- [x] 1.4 Preserve canonical event IDs and evidence IDs in comparison results; include match totals from eligible playerless events
- [x] 1.5 Add `GET /matches/{id}/warnings-summary` route in `backend/app/api/routes/canonical_analysis.py` with auth and cutover guard
- [x] 1.6 Return `WarningsSummary` contract with `match_id`, `official_snapshot_id`, `players[]`, `match_totals`, `limitations[]`

## Phase 2: Backend Tests (Slice 1)

- [x] 2.1 Test eligibility filtering: active/observed/confirmed only; inactive/unobserved/unconfirmed excluded
- [x] 2.2 Test player identity matching: explicit `player_id` only; official-only rows with null `player_id` kept separate
- [x] 2.3 Test zero-tolerance statuses: equal → `exact`, unequal present → `missing_in_canonical`/`missing_in_official`, never `within_tolerance`
- [x] 2.4 Test evidence IDs: canonical event IDs and evidence IDs present on every canonical-backed comparison
- [x] 2.5 Test match totals: include eligible playerless canonical events; official totals from snapshot players
- [x] 2.6 Test limitations: goal_timestamps, card_timestamps, goalkeeper_substitutions always `not_comparable` with reason
- [x] 2.7 Test route: auth required, 409 when cutover not active, response shape, official snapshot immutability

## Phase 3: Frontend Types, Client & Panel (Slice 2)

- [x] 3.1 Add warnings contract types in `frontend/src/types.ts` (`WarningStatus`, `WarningMetric`, `WarningComparison`, `WarningsSummary`)
- [x] 3.2 Add typed `getWarningsSummary` in `frontend/src/api/client.ts`
- [x] 3.3 Create `frontend/src/components/WarningsPanel.tsx`: semantic table/list with match totals + player rows
- [x] 3.4 Each status: visible text, Lucide icon (`aria-hidden`), accessible label with status + canonical/official values, color supplementary
- [x] 3.5 Evidence rows: native `<button>` (Enter/Space), `aria-describedby` → status, no mutation controls
- [x] 3.6 Activation loads canonical events/session, selects first linked event, renders `ReportEventTimeline`, announces via `role=status` live region
- [x] 3.7 Drill-down calls `seekTargetForEvent`; usable anchor + ready player → `seekTo`; `mapVideoTime` adds clock context; PDF-only/unavailable → announce no seek

## Phase 4: Frontend Integration & Tests (Slice 2)

- [x] 4.1 Integrate panel in `frontend/src/pages/StatisticsPage.tsx`: fetch with `['warnings-summary', id]`, mount `WarningsPanel`
- [x] 4.2 Add `WarningsPanel.test.tsx`: semantic statuses, true keyboard activation (Enter/Space), selection, read-only seek, unavailable media
- [x] 4.3 Update `StatisticsPage.test.tsx`: mock `getWarningsSummary`, assert match-scoped panel renders and integrates
- [x] 4.4 Verify no legacy `Event`, `AnalysisEvent`, or `GoalkeeperShot` data is used anywhere
- [x] 4.5 Fix first-activation video drill-down: defer seek until the mounted player reports ready; cover the iframe lifecycle with an integration test
- [x] 4.6 Close final verifier gaps: assert keyboard-triggered drill-down retains focus/status context and cover unavailable, embedding-disabled, restricted, and removed-player fallbacks without a seek
- [x] 4.7 Cover the runtime `player_error` fallback: retain evidence drill-down while omitting the player iframe and never seek

## Phase 5: Cleanup

- [x] 5.1 Confirm no database migrations, feature flags, or deployment changes needed
- [x] 5.2 Verify rollback: remove route + panel only; canonical/official records unchanged
