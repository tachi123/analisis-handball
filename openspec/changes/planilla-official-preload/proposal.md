# Proposal: Official Planilla Preload

## Intent

Turn the reviewed discovery and identity corpus into auditable official match data, so an analyst can select a pre-loaded match, validate its sheet, and attach live video analysis without re-entering fixture facts.

## Scope

### In Scope
- Deterministically derive curated, seeder-compatible fixtures for new 2026 3ª Masculino stages from the manifest, identity team names, date-inferred rounds, scores, and reviewed missing-label mappings.
- Gate one idempotent batch official load behind an explicit corpus approval; seed fixture entities and attach each source PDF as SHA-256/local-path OfficialSnapshot evidence to its ScheduledMatch.
- Expose stage standings, top scorers, player goals/cards/appearance averages, and fixture-selection rows including an empty `youtube_link` for the existing video flow.

### Out of Scope
- Persisting a reusable player roster or creating legacy player identities beyond immutable snapshot player facts needed by the read models.
- Re-uploading PDFs, changing source files, video ingestion, or automatic resolution of unreviewed identity conflicts/missing labels.

## Capabilities

### New Capabilities
- `official-planilla-preload`: Approved batch conversion of reviewed sheets into fixture-linked official evidence.
- `stage-performance-read-models`: Official-snapshot standings and player aggregate read APIs.

### Modified Capabilities
- `fixture-seeding`: Accept deterministic manifest-derived curated payloads for additional stages while retaining idempotency and bye exclusion.
- `match-preparation`: List pre-loaded fixtures and allow fixture-key selection of an already-linked official snapshot for video analysis.
- `review-statistics`: Treat confirmed official snapshot values as immutable inputs for official player/team reconciliation.

## Approach

Build a pure derivation command that emits versioned JSON plus a reviewed missing-team mapping. A separate database-backed loader requires one approval file matching the manifest/mapping hashes, reuses `fixture_seeder`, deterministically derives `fixture_key`, and records path/SHA provenance rather than uploading bytes. Read services aggregate only confirmed snapshots; result status comes from official scores and `Libre` never participates.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/services/fixture_seeder.py` | Modified | Derived stage provisioning |
| `backend/app/services/*official*`, `backend/app/api/*` | New/Modified | Batch loader and read APIs |
| `backend/app/models/*`, `backend/alembic/` | Modified | Snapshot provenance/read-model support if absent |
| `resources/planillas/_discovery/` | New | Mapping, approval, deterministic payloads |
| `frontend/src/pages/MatchesPage.tsx`, `frontend/src/api/client.ts` | Modified | Pre-loaded selection/video handoff |
| Deployment | None | No new service or external storage |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Incorrect team mapping or stage merge | Medium | Hash-bound approval, explicit mapping, new stage keys, rerun tests |
| Duplicate/altered evidence | Low | Idempotent keys and SHA-256 provenance |
| Misleading aggregates | Medium | Confirmed snapshots only; configurable rules; exclude byes |

## Rollback Plan

Revert the release and delete only loader-created, approval-traceable records/snapshots in a transaction; retain source PDFs and derived artifacts. Existing fixtures, snapshots, canonical analysis, and videos remain untouched.

## Dependencies

- Reviewed `manifest.json`, identity artifacts, missing-label mapping, and explicit batch approval.

## Success Criteria

- [ ] Re-running approved derivation/load creates no duplicate fixture or evidence records.
- [ ] Both new 3ªM stages expose scored non-bye fixtures with local-path/SHA evidence.
- [ ] Selection, standings, scorers, and averages reflect confirmed snapshots only and surface `youtube_link`.
