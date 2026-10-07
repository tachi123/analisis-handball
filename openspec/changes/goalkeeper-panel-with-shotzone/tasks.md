# Tasks: Goalkeeper Panel with Shot Zone

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 800–1,150 total; 220–390/slice |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Slice 1 → Slice 2 → Slice 3 |
| Delivery strategy | ask-always |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| Slice 1 | Canonical goalkeeper projection | 1 | No branch/PR creation; backend rollback. |
| Slice 2 | `shot_zone` capture/API contract | 2 | Depends on Slice 1; preserve historic payloads. |
| Slice 3 | Goalkeeper panel and heatmap | 3 | Depends on prior contracts; UI rollback. |

## Phase 1: Slice 1 — Backend Projection + Tests

- [x] 1.1 Update `backend/app/schemas.py` with projection schemas, eligible `player_id`, filters, evidence/coverage, and unfiltered context.
- [x] 1.2 Implement revision replay in `backend/app/services/canonical_analysis_service.py`: unique active-keeper attribution, lineup-only participation, verified ranges, and separate coverage.
- [x] 1.3 Add authenticated, cutover-protected `GET /matches/{match_id}/canonical-player-projection` in `backend/app/api/routes/canonical_analysis.py`; reject invalid players/teams without legacy reads.
- [x] 1.4 Test `backend/tests/test_canonical_analysis_service.py`: attributed/unknown outcomes, rates, participation limits, clock buckets, evidence, and reconciliation.
- [x] 1.5 Test route auth, required player, filter validation, cutover, and response evidence in `backend/tests/test_canonical_analysis_routes.py`; run `python -m pytest`.

**Boundary:** starts with existing canonical revisions; finishes with a consumable authoritative projection. **Rollback:** revert route/service/schema changes; revisions remain untouched.

## Phase 2: Slice 2 — Capture/API `shot_zone` + Tests

- [x] 2.1 Add nullable integer `ShotZone` validation to `backend/app/schemas.py`; allow 1–9 only for `shot`, reject invalid values, and retain historic omissions.
- [x] 2.2 Preserve `shot_zone` through create/revise, remapping, evidence updates, and anchor recalibration in `backend/app/services/canonical_analysis_service.py`; test both backend modules.
- [x] 2.3 Extend `frontend/src/types.ts` and `frontend/src/api/client.ts` with `ShotZone` and projection query/response contracts; test query serialization in `frontend/src/api/client.test.ts`.
- [x] 2.4 Replace `frontend/src/components/GkCourtPicker.tsx` labels with accessible IHF targets 1–9; preserve shot-only drafts in `MatchAnalysis.tsx`, `MatchReview.tsx`, and `EvidenceModal.tsx`.
- [x] 2.5 Add Vitest coverage in `frontend/src/pages/{MatchAnalysis,MatchReview}.test.tsx` and `components/EvidenceModal.test.tsx` for zoned revision retention, unzoned shots, and no non-shot control; run backend pytest and `npm --prefix frontend test -- --run`.

**Boundary:** starts after projection contract; finishes with backwards-compatible canonical zone capture. **Rollback:** stop sending/removing the optional field; JSON revisions stay readable.

## Phase 3: Slice 3 — Panel, Heatmap, Timeline UI + Tests

- [x] 3.1 Create `frontend/src/pages/GoalkeeperPanel.tsx`: protected match-scoped eligible-player selection, projection loading, server metric/participation/coverage disclosures, and distinct unfiltered context.
- [x] 3.2 Create `frontend/src/components/ShotZoneHeatmap.tsx` with accessible server-only 3×3 IHF buckets and explicit missing/unknown/excluded/keeper-unknown/clock-unverified counts.
- [x] 3.3 Register the panel in `frontend/src/App.tsx`; reuse timeline/video seek utilities for evidence IDs and anchors without client recomputation.
- [x] 3.4 Add `GoalkeeperPanel.test.tsx` and `ShotZoneHeatmap.test.tsx` for selection, participation, coverage, labels, and anchored seek; run Vitest, lint, and `npm --prefix frontend run build`.

**Boundary:** starts after projection and zone contracts; finishes with the complete canonical UI. **Rollback:** remove route/page registration and new components; backend and historic data remain intact.

## Verifier Remediation

- [x] Align projection evidence with the panel's `id`/`revision` contract and use collision-proof evidence keys.
- [x] Account for every relevant projection event as recorded, missing-zone, excluded, unknown-keeper, or clock-unverified; misses never enter attribution buckets.
- [x] Add runtime coverage for unknown keepers, invalid filters, missing zones, save rate, video-anchored seek, revision zone persistence, unverified anchors, and the IHF-only picker.

**Verification:** targeted backend pytest (excluding the pre-existing migration failure), frontend Vitest, lint, and production build pass. No Alembic changes.
