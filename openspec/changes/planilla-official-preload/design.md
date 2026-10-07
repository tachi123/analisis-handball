# Design: Official Planilla Preload

## Technical Approach

Three independently testable slices convert the reviewed corpus into fixture-linked, local-path official evidence, then query only confirmed evidence. Slice A is pure and produces the JSON already accepted by `fixture_seeder`; Slice B is the sole database writer; Slice C adds read-only stage endpoints and extends the existing fixture list. No PDF is uploaded or copied.

## Architecture Decisions

| Decision | Alternatives / tradeoff | Choice and rationale |
|---|---|---|
| Stable fixture identity | Current DB-ID key is stable only after import | Add optional `entry.fixture_key` to the seeder contract; derivation emits `planilla:<record-sha8>:<seq>`. Existing payloads retain `_fixture_key`; curated reruns and batch links remain deterministic. |
| Evidence verification | Rehashing 137 PDFs is safest but needlessly expensive | The manifest supplies SHA; derivation records local size/mtime. Loader trusts it when both match, otherwise stream-hashes with `sha256_file`; it always uses `PDFService` limits and verifies pages. |
| Batch provenance and rollback | Delete by broad stage can destroy unrelated work | Add `OfficialBatchRun` (input hashes, status, rejection/report, timestamps) and nullable `OfficialSnapshot.batch_run_id`; rollback deletes snapshots/players/matches created by that run in a transaction, records `rolled_back_at`, and never deletes shared fixture entities. |
| Confirmed read boundary | Aggregating all snapshot rows risks draft data | Add `is_confirmed` (existing confirmed imports backfilled true); Slice B writes true and all read queries filter it. Snapshot player rows stay immutable facts, not `Player` identities. |

## Data Flow

```
manifest.json + identity-summary.json + team-mapping.json
        -> derive_planilla_fixture.py -> derived-fixtures.json + derivation report
approval.json (manifest_sha256, mapping_sha256)
        -> load_official_planillas.py -> FixtureSeeder -> ScheduledMatch
                                               -> local PDF validation -> Match -> OfficialSnapshot
stage API <- confirmed snapshots/player facts + ScheduledMatch <- /pdf/fixtures
```

### Slice A — derivation

Create `planilla_derivation_service.py` and `scripts/derive_planilla_fixtures.py`. It accepts explicit manifest, identity summary, mapping, output and date-to-round rule paths; normalizes neither persisted labels nor mapping values. It sorts by manifest SHA then source path, assigns sequence within each SHA, groups records into distinct 2026 Apertura Zona A and Permanencia stages, and emits canonical UTF-8 JSON (`sort_keys`, newline) plus unresolved report. The mapping is reviewed data, shaped as:

```json
{"schema_version":1,"manifest_sha256":"…","labels":{"72 unresolved labels":{"club":"Banfield","variant":"B"}}}
```

Actual `labels` keys are exact source labels; each maps to `{club, variant|null}`. An absent/invalid label is reported and omitted, never guessed. Derived entries include SHA/path/size/mtime/page count, extracted teams/scores/rosters, round, and explicit fixture key.

### Slice B — approved loader

Create `official_planilla_loader_service.py` and `scripts/load_official_planillas.py --manifest --mapping --derived --approval [--dry-run]`. Validate all JSON hashes and approval binding before opening a transaction. Call `fixture_seeder.import_fixture`, resolve each explicit key, and validate source path containment, size, page count, and the parsed teams/scores using the existing `PDFService` parser/limits without `save_pdf`. Create the linked `Match`, `OfficialSnapshot` (original local `source_path`), and `OfficialSnapshotPlayer` facts. Team/score/page/hash mismatches are skipped with fixture key and reason; malformed approval rejects the whole batch before writes. Re-running the approved input reuses its `OfficialBatchRun`, fixture, match, and snapshot. Persist a structured report for created/reused/skipped/rejected records.

## Interfaces / Contracts

```json
{"schema_version":1,"manifest_sha256":"…","mapping_sha256":"…","derived_sha256":"…","approved_by":"…","approved_at":"2026-08-26T00:00:00Z"}
```

`GET /api/v1/stages/{stage_id}/standings`, `/scorers`, and `/player-averages` return 409 `no_confirmed_official_data` when empty. `GET /api/v1/pdf/fixtures` adds `official_snapshot_id`, `is_preloaded`, and `youtube_link` (the linked `Match.youtube_link` or `""`); it returns only non-bye fixtures, and selection rejects non-confirmed evidence. Standings use injected/configured points and tie-break rules; aggregates group `OfficialSnapshotPlayer.name` per stage and side, with appearances counted once per snapshot/player.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/services/planilla_derivation_service.py` | Create | Pure manifest/mapping derivation. |
| `backend/scripts/derive_planilla_fixtures.py` | Create | Deterministic derivation CLI. |
| `backend/app/services/official_planilla_loader_service.py` | Create | Approval-gated local loader and rollback. |
| `backend/scripts/load_official_planillas.py` | Create | Batch CLI/report exit codes. |
| `backend/app/services/stage_performance_service.py` | Create | Confirmed-snapshot read models. |
| `backend/app/api/routes/stage_performance.py` | Create | Stage read endpoints. |
| `backend/app/models.py`, `backend/alembic/versions/*` | Modify | Batch audit, snapshot provenance/confirmation indexes. |
| `backend/app/services/fixture_seeder.py`, `pdf_service.py`, `schemas.py`, `api/routes/pdf.py`, `main.py` | Modify | Explicit keys, local validation, fixture contract, routes. |
| `frontend/src/types.ts`, `api/client.ts`, `pages/MatchesPage.tsx` | Modify | Consume/display fixture `youtube_link` only. |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | Byte-stable derivation, 72-label mapping failures, key/round rules, mtime-size hash reuse | Fixtures and mocked hash/parser calls. |
| Integration | Approval atomic rejection, idempotent load, mismatch skips, rollback ownership, aggregates/409 | SQLite migrated DB and local temporary PDFs. |
| API/UI | Confirmed-only routes and fixture `youtube_link` rendering | FastAPI route tests; Vitest existing MatchesPage patterns. |

## Migration / Rollout

Migrate audit/provenance fields and indexes first, backfill existing snapshots as confirmed, deploy code, run derivation/review, then execute the explicitly approved dry-run and load. Roll back by batch-run audit deletion only; source and curated artifacts remain unchanged.

## Open Questions

None.
