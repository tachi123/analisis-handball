# Tasks: Official Planilla Preload

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 1,300–1,900 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → 7, one work unit each |
| Delivery strategy | force-chained |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No — maintainer selected feature-branch-chain.
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Deterministic derivation | PR 1 | Base main; tests included. |
| 2 | Reviewed mapping resolution | PR 2 | After PR 1. |
| 3 | Approved SQLite loader | PR 3 | After PR 2; migration included. |
| 4 | Safe CLI corpus-copy proof | PR 4 | After PR 3. |
| 5 | Confirmed-data read APIs | PR 5 | After PR 3. |
| 6 | Fixture video-link UI | PR 6 | After PR 5. |
| 7 | Operator runbook | PR 7 | After PRs 3–6. |

## Phase 1: Derivation and Mapping

- [x] 1.1 Create `backend/app/services/planilla_derivation_service.py` for canonical SHA/path-sorted JSON, stage/round rules, `planilla:<sha8>:<seq>` keys, and unresolved-label reporting; add byte-stability, real-artifact, and no-guess tests.
- [x] 1.2 Add `backend/scripts/derive_planilla_fixtures.py` with explicit manifest, identity, mapping, rule, and output arguments; test CLI outputs and exit failures in `backend/tests/test_planilla_derivation_service.py`.
- [x] 1.3 Add versioned `resources/planillas/_discovery/team-mapping.json` and a resolution report workflow; map exact labels only, test absent/invalid labels, then regenerate reviewed derived artifacts.

## Phase 2: Approved Batch Loader

- [x] 2.1 Extend `backend/app/models.py` and add an Alembic revision for `OfficialBatchRun`, snapshot `batch_run_id`/`is_confirmed`, indexes, and confirmed backfill; prove migration and rollback ownership with SQLite tests.
- [x] 2.2 Update `backend/app/services/fixture_seeder.py` to honor supplied deterministic fixture keys while retaining bye exclusion and idempotency; extend `backend/tests/test_fixture_seeder_unit.py`.
- [x] 2.3 Create `backend/app/services/official_planilla_loader_service.py` for approval-hash preflight, local PDF/path/parser validation, FixtureSeeder-based writes, snapshots/player facts, reports, reuse, skips, and transactional rollback; add `backend/tests/test_official_planilla_loader_service.py` for rejection, mismatch, idempotency, and rollback.
- [x] 2.4 Add `backend/scripts/load_planilla_official.py` for approved/dry-run batch reports and exit codes; test it only against SQLite and temporary PDFs.

## Phase 3: Safe End-to-End Proof

- [x] 3.1 Copy a selected real corpus PDF and reviewed JSON into an isolated temporary corpus; add `backend/tests/test_official_planilla_preload_cli.py` to derive then load the copy into SQLite, asserting no live DB/source mutation.

## Phase 4: Confirmed Performance APIs

- [x] 4.1 Create `backend/app/services/stage_performance_service.py` for confirmed-only standings, scorers, and player averages with configurable points/tiebreaks and bye exclusion; add focused SQLite service tests.
- [x] 4.2 Add `backend/app/api/routes/stage_performance.py`, register it in `backend/app/main.py`, and add `backend/tests/test_stage_performance_routes.py` for aggregates and `409 no_confirmed_official_data`.

## Phase 5: Fixture Selection Video Link

- [x] 5.1 Extend `backend/app/services/pdf_service.py`, `schemas.py`, and `api/routes/pdf.py` to return confirmed preload metadata and `youtube_link`, and reject unconfirmed selection; cover in `backend/tests/test_pdf_routes.py`.
- [x] 5.2 Update `frontend/src/types.ts`, `api/client.ts`, and `pages/MatchesPage.tsx` to surface the selected fixture’s video link without video ingestion; extend `frontend/src/pages/MatchesPage.test.tsx`.

## Phase 6: Operator Documentation

- [x] 6.1 Update `docs/local-recovery-runbook.md` with derive, mapping review, approval, dry-run, backup, and post-verification live-load steps; explicitly prohibit real-DB load in automated tests.
