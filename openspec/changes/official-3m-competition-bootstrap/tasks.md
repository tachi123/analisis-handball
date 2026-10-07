# Tasks: Official 3ªM Competition Bootstrap

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 850–1,050 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Bootstrap → derivation gate → loader gate |
| Delivery strategy | auto-chain |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Bootstrap and evidence | PR #1 | Base: feature/tracker branch; tests included. |
| 2 | Exact derivation gate | PR #2 | Base: PR #1 branch; tests included. |
| 3 | Completed-approval loader gate | PR #3 | Base: PR #2 branch; tests and alias audit included. |

## Phase 1: Bootstrap Foundation (PR #1, ~350 lines)

- [x] 1.1 Create `backend/app/services/official_competition_bootstrap_service.py` to validate schema-v1 manifest, transactionally find/create 2026 stages, exact clubs, stage-local `CompetitionTeam`s and registrations, and reject conflicts. (Critical lifecycle remediation validates raw canonical manifest, mapping, reconciliation, and report evidence against approval before a session add/flush/write.)
- [x] 1.2 Add report, dry-run, and guarded rollback helpers: no PDF access/mutation in dry-run; rollback removes only empty bootstrap-owned 3ªM records atomically and leaves 4ª data intact. (Adversarial stale-evidence regressions assert zero flushes/writes; migrated SQLite coverage added.)
- [x] 1.3 Create `backend/scripts/bootstrap_official_3m_competition.py` with explicit DB URL, manifest/report paths, `--dry-run`, and approved `--rollback` commands. (Dry-run prints its report and never writes `--report`; real execution alone may write it.)
- [x] 1.4 Add `bootstrap-manifest.json` and `bootstrap-approval.json`; preserve exact variants and `Ce.M.E.F`; write only browse aliases to `_indexed/index.json` without changing canonical paths/hashes. (Slice 1 implements the read-only evidence manifest and pending approval boundary, including schema-v1 cryptographic binding of the canonical manifest, mapping, reconciliation, report, distinct stage IDs, and globally unique exact source-label-to-CompetitionTeam IDs; no index mutation.)
- [x] 1.5 Add `backend/tests/test_official_competition_bootstrap_service.py`: isolated stages, rerun IDs/no duplicates, 4ª preservation, dry-run, conflicts, and rollback guards. Test: `python -m pytest backend/tests/test_official_competition_bootstrap_service.py`.

## Phase 2: Exact Mapping and Derivation Gate (PR #2, ~300 lines)

- [x] 2.1 Upgrade `resources/planillas/_discovery/team-mapping.json` to schema v2 with manifest hash, exact source labels, target club/variant, and stage keys for all eight required mappings.
- [x] 2.2 Update `backend/app/services/planilla_derivation_service.py` to validate manifest targets, bootstrap report IDs/hashes, exact stage-scoped mapping, and pre-derivation approval; embed `bootstrap_approval_sha256` in derived output.
- [x] 2.3 Update `backend/scripts/derive_planilla_fixtures.py` to require bootstrap report and approval inputs and reject missing, unmatched, or hash-mismatched evidence.
- [x] 2.4 Extend `backend/tests/test_planilla_derivation_service.py` for variant/near-match rejection, missing target ID, and approval/hash gates. Test: `python -m pytest backend/tests/test_planilla_derivation_service.py`.

**Approval gate:** only a maintainer/user may approve the report’s two stages, every target ID, eight exact mappings, and manifest/mapping/report hashes. Automation may validate or reject an approval; it cannot create mapping approval.

## Phase 3: Completed Approval Loader Gate (PR #3, ~250 lines)

- [x] 3.1 Update `backend/app/services/official_planilla_loader_service.py` to require completed approval bindings for bootstrap report, mapping, manifest, and derived SHA-256 before fixture writes.
- [x] 3.2 Extend `backend/tests/test_official_planilla_loader_service.py` to reject absent/preliminary/mismatched bindings without loading and accept matching completed evidence while retaining PDF provenance checks.
- [x] 3.3 Run targeted regression suites: `python -m pytest backend/tests/test_official_competition_bootstrap_service.py backend/tests/test_planilla_derivation_service.py backend/tests/test_official_planilla_loader_service.py`.

## Phase 4: Chain Verification

- [ ] 4.1 Before each PR, verify its diff is at or below 400 changed lines; retarget/rebase child branches if a child includes an ancestor’s diff. Test: `python -m pytest backend/tests/test_fixture_seeder.py backend/tests/test_competition_team_identity.py`.
