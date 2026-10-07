# Verification Report: warnings-panel

**Change**: `warnings-panel`  
**Version**: N/A (delta specification)  
**Mode**: Standard (`strict_tdd: false`)  
**Preflight**: auto; OpenSpec; `size:exception`  
**Verification context**: final fresh-context, read-only review (2026-08-28)

## Verdict: PASS WITH WARNINGS

All 24 planned tasks are complete and every specification scenario has passed runtime coverage. The prior video first-activation, true Enter/Space activation, and all unavailable-media fallback gaps are closed. The only warning is an unrelated Alembic migration collision on `competition_teams.external_code` in the broader targeted backend suite; the warnings-summary route test passes independently.

## Completeness

| Metric | Value |
| --- | ---: |
| Tasks total | 24 |
| Tasks complete | 24 |
| Tasks incomplete | 0 |

## Build & Tests Execution

| Command | Result |
| --- | --- |
| `npm test -- --run` (`frontend`) | ✅ 22 files, 97 tests passed |
| `npm run lint` (`frontend`) | ✅ passed |
| `npm run build` (`frontend`) | ✅ passed (`tsc -b && vite build`) |
| `python -m pytest tests/test_canonical_analysis_routes.py::test_warnings_summary_is_authenticated_cutover_gated_and_traceable` (`backend`) | ✅ 1 passed |
| `python -m pytest tests/test_canonical_analysis_service.py tests/test_canonical_analysis_routes.py` (`backend`) | ⚠️ 26 passed, 2 failed only in unrelated Alembic migration checks |

Coverage is not configured (`openspec/config.yaml`). The focused backend command emitted 28 pre-existing Pydantic deprecation warnings; they are not a warnings-panel failure.

## Spec Compliance Matrix

| Requirement | Scenario | Runtime evidence | Result |
| --- | --- | --- | --- |
| Authoritative totals | Eligible player and match totals | `test_warnings_summary_is_authenticated_cutover_gated_and_traceable` creates eligible player and playerless goals and verifies player/match totals across supported metrics. | ✅ COMPLIANT |
| Authoritative totals | Ineligible canonical event | The same route test posts inferred, ambiguous, and deactivated events; returned canonical totals exclude them. | ✅ COMPLIANT |
| Statuses and limitations | Equal totals | Focused route test asserts yellow `exact`; the tested response includes all five metrics. | ✅ COMPLIANT |
| Statuses and limitations | Unavailable temporal or substitution detail | Focused route test asserts all three reasoned `not_comparable` limitations. | ✅ COMPLIANT |
| Statuses and limitations | Absent player counterpart | Focused route test asserts a distinct official-only null-ID player row without identity guessing. | ✅ COMPLIANT |
| Evidence and immutability | Trace a discrepancy | Focused route test asserts canonical event/evidence IDs and verifies unchanged official snapshot scores. | ✅ COMPLIANT |
| Accessible read-only warnings | Keyboard evidence drill-down | `WarningsPanel.test.tsx` dispatches Enter and Space independently, without a manual click, then verifies evidence opening, retained focus, live status, and no mutation control. | ✅ COMPLIANT |
| Accessible read-only warnings | Navigate linked evidence | First activation waits for iframe `onReady` before seeking. PDF-only and unavailable, embedding-disabled, restricted, removed, and `player_error` fallback cases retain timeline evidence and do not seek. | ✅ COMPLIANT |

**Compliance summary**: 8/8 scenarios compliant.

## Correctness (Static Evidence)

| Requirement | Status | Evidence |
| --- | --- | --- |
| Authenticated, cutover-gated endpoint | ✅ Implemented | `backend/app/api/routes/canonical_analysis.py:73-76`; focused route test covers unauthenticated 403 and cutover 409. |
| Five metrics, statuses, evidence, immutable official values | ✅ Implemented | `canonical_analysis_service.py:419-594`; service derives only from `read_metrics` and the latest `OfficialSnapshot`. |
| Explicit identities and playerless match totals | ✅ Implemented | `read_warnings_summary` unions explicit player IDs, retains official-only null-ID rows, and aggregates playerless eligible events into match totals. |
| Accessible, read-only panel | ✅ Implemented | Native evidence buttons, accessible status descriptions, live region, and `ReportEventTimeline`; no `EvidenceModal` or mutation action is used. |
| First video drill-down activation | ✅ Implemented and tested | Pending selected event waits for mounted iframe readiness before calling `seekTo`; the component integration test observes the seek only after `onReady`. |
| Enter/Space keyboard operation | ✅ Implemented and tested | Explicit keydown activation forwards Enter and Space to the native button click path while focus remains on the activated row. |
| Unavailable/restricted/removed/error video fallbacks | ✅ Implemented and tested | `unavailable`, `embedding_disabled`, `restricted`, `player_error`, and removed-video (`unavailable`) cases render readable timeline detail without iframe or seek. |

## Design Coherence

| Decision | Followed? | Notes |
| --- | --- | --- |
| Server-derived canonical versus immutable official comparison | ✅ Yes | Service owns eligibility, aggregation, comparison, and provenance. |
| Zero-tolerance discrete counts | ✅ Yes | Unequal comparable values receive directional missing statuses. |
| Explicit player IDs; no legacy mixing | ✅ Yes | The warnings derivation reads canonical metrics and official snapshots only. |
| Compose `ReportEventTimeline`; avoid `EvidenceModal` | ✅ Yes | Drill-down is timeline-based and exposes no mutation controls. |
| Seek only after mounted ready player | ✅ Yes | Effect requires `availability === 'ready'` plus an iframe content window. |

## Issues Found

### CRITICAL

None.

### WARNING

- **Unrelated Alembic `external_code` migration collision.** The broader backend command has two failing migration-reversibility tests because both `600464b8cb43_add_external_code_to_competition_team.py` and `73b208e83d81_add_external_code_column_to_competition_.py` add `competition_teams.external_code`; SQLite reports `duplicate column name: external_code`. The independently run warnings-summary route test passes, and this change adds no migration.

### SUGGESTION

None.

## Scope Boundary

No warnings-specific migration, feature flag, deployment change, legacy-source read, revision save, resolution, synchronization, or audit action was found. Rollback remains route-plus-panel removal only; canonical and official records remain unchanged.
