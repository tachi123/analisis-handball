# Verification Report — Goalkeeper Panel with Shot Zone

**Change:** `goalkeeper-panel-with-shotzone`  
**Mode:** Standard (`strict_tdd: false`)  
**Date:** 2026-08-27  
**Verdict:** **PASS WITH WARNINGS** — all change-specific critical gaps are closed and their runtime coverage passes. The only failing targeted tests are the pre-existing, unrelated Alembic duplicate-column migrations.

## Completeness

| Metric | Value |
|---|---:|
| Tasks total | 16 |
| Tasks complete | 16 |
| Tasks incomplete | 0 |

## Build & Tests Execution

| Command | Result |
|---|---|
| `npm --prefix frontend test -- --run` | ✅ 21 files, 86 tests passed |
| `npm --prefix frontend run lint` | ✅ passed with zero warnings |
| `npm --prefix frontend run build` | ✅ passed (`tsc -b && vite build`) |
| `python -m pytest tests/test_canonical_analysis_service.py tests/test_canonical_analysis_routes.py` | ⚠️ 25 passed, 2 failed |
| Same backend command with `-k "not migration"` | ✅ 25 passed, 2 deselected |

Coverage tooling and a threshold are not configured.

The two full-run failures are unrelated migration reversibility tests. Both fail while `73b208e83d81` tries to add `competition_teams.external_code` after `600464b8cb43` already added it (`sqlite3.OperationalError: duplicate column name: external_code`). No Alembic change belongs to this feature.

## Spec Compliance Matrix

| Requirement / scenario | Passing runtime evidence | Result |
|---|---|---|
| Optional numeric IHF zone; invalid/non-shot rejection; historic omission | `test_shot_zone_is_optional_for_shots_and_rejected_elsewhere` | ✅ COMPLIANT |
| Create/revise preserves zone and revision evidence | `test_repeated_video_anchor_revisions_retain_latest_video_provenance` | ✅ COMPLIANT |
| Zoned workspace revision retains zone; non-shot exposes no control | `EvidenceModal scenarios > retains a selected IHF zone when revising a shot`; conditional control in `EvidenceModal` | ✅ COMPLIANT |
| Roster eligibility and invalid player/team/range filters | `test_player_projection_rejects_invalid_filters` | ✅ COMPLIANT |
| Active keeper attribution and observed-only participation | `test_player_projection_replays_keeper_context_and_discloses_unknowns` | ✅ COMPLIANT |
| Unknown keeper, missing zone, defined save rate, and coverage accounting | `test_player_projection_accounts_for_unknown_missing_zone_excluded_and_unverified_shots` | ✅ COMPLIANT |
| Unverified-clock result and video anchor stay outside a precise range | Same coverage test; asserts separate bucket, eligible outcome boundary, and anchor | ✅ COMPLIANT |
| Unfiltered canonical/reconciliation context accompanies projection | `test_player_projection_replays_keeper_context_and_discloses_unknowns`; panel renders explicit unfiltered label | ✅ COMPLIANT |
| Select server projection and disclose observed participation only | `GoalkeeperPanel > renders server metrics and separates unknown keeper coverage` | ✅ COMPLIANT |
| Evidence IDs/revision contract and anchored seek | `GoalkeeperPanel > renders projection evidence IDs and seeks an anchored evidence item` | ✅ COMPLIANT |
| IHF-only 1–9 picker, no legacy-origin values | `GkCourtPicker > exposes only numeric IHF 1–9 target zones and never legacy origins` | ✅ COMPLIANT |
| Server-only heatmap and explicit coverage labels | `ShotZoneHeatmap > renders server buckets and explicit unknown coverage` | ✅ COMPLIANT |

**Compliance summary:** 12/12 listed scenario groups have passing covering tests.

## Correctness (Static Evidence)

| Check | Status | Evidence |
|---|---|---|
| Evidence field alignment | ✅ | Projection emits `id`/`revision`; TypeScript projection evidence extends `CanonicalEvent`; panel renders both and uses collision-proof keys. |
| Coverage buckets | ✅ | `read_player_projection` accounts for recorded, missing-zone, excluded, unknown/unknown-keeper, and clock-unverified outcomes; runtime coverage test exercises each required bucket. |
| Unknown/unverified eligibility boundary | ✅ | Only confirmed observed opponent `shot` events with `save` or `goal` reach `goalkeeper_unknown` or range-filtered `clock_unverified`; test asserts those bucketed evidence outcomes. |
| Clock separation | ✅ | `clock_unverified` events with an active range are bucketed separately, never counted in range metrics or zones. |
| No inferred keeper claims | ✅ | Participation is only lineup counts/evidence; neither service nor panel derives minutes, starts, or exhaustive appearances. |
| No fabricated filtered metrics | ✅ | Metrics and heatmap use server projection; match canonical/reconciliation context is explicitly unfiltered. |
| No legacy mixing | ✅ | Projection reads `CanonicalEvent` revisions only. Legacy models occur only in isolated `legacy_dry_run`, not the projection path. |

## Coherence (Design)

| Decision | Followed? | Notes |
|---|---|---|
| Canonical server-authoritative projection | ✅ Yes | Authenticated route delegates to canonical revision replay. |
| Conservative active-keeper replay | ✅ Yes | Exactly one opposing active keeper is required for attribution. |
| Nullable JSON `shot_zone`; no migration/backfill | ✅ Yes | Payload serialization preserves it; no feature migration was added. |
| IHF target picker replaces legacy-origin vocabulary | ✅ Yes | Picker sends only numeric target cells 1–9. |
| Existing video seek utilities | ✅ Yes | Panel uses `seekTargetForEvent`, `videoAnchorSeconds`, and `mapVideoTime`; seek test passes. |

## Issues Found

### CRITICAL

None.

### WARNING

1. **Unrelated Alembic migration failure:** `600464b8cb43` and `73b208e83d81` both add `competition_teams.external_code`, so SQLite migration-to-head tests fail with a duplicate-column error. This is outside this change.

### SUGGESTION

1. Add a shared API response schema/DTO generation step to prevent future backend/TypeScript field-name drift.
