# Tasks: Planilla Player Identity

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 850–1,100 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Six behavior-complete work units |
| Delivery strategy | ask-on-risk (resolved for this work as `feature-branch-chain`) |
| Chain strategy | feature-branch-chain |

Decision needed before apply: No — resolved by orchestrator: feature-branch-chain
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Normalization and similarity core | PR 1 | Base: main; tests included. |
| 2 | Grouping tiers and conflicts | PR 2 | Base: PR 1; synthetic manifest fixtures. |
| 3 | Validated overrides | PR 3 | Base: PR 2; atomic failure coverage. |
| 4 | Stable review artifacts | PR 4 | Base: PR 3; writer tests included. |
| 5 | Model-free CLI | PR 5 | Base: PR 4; import guard included. |
| 6 | Real-corpus end-to-end proof | PR 6 | Base: PR 5; manifest-only and read-only. |

## Phase 1: Identity foundation

- [x] 1.1 Create `backend/app/services/planilla_player_identity_service.py` with manifest roster flattening, stable row IDs/scopes, Unicode token normalization, multiset Dice scoring, and serializable result types.
- [x] 1.2 Add `backend/tests/test_planilla_player_identity_service.py` unit cases for accent/case/order equivalence, `0.90` inclusion/`0.89` exclusion, and cross-stage isolation.

## Phase 2: Conservative grouping

- [x] 2.1 Implement sorted candidate linking, union-find auto groups, deterministic identity IDs, manifest-only appearance/goals/card previews, and evidence provenance in `planilla_player_identity_service.py`.
- [x] 2.2 Extend `test_planilla_player_identity_service.py` with synthetic fixtures shaped like discovery records: missing team label, missing jersey, team homonym, and same-team jersey swap; assert review/conflict tiers and no unsafe union.

## Phase 3: Analyst overrides

- [x] 3.1 Add whole-document override validation and ordered accept/merge/split/reject resolution to `planilla_player_identity_service.py`, rejecting incompatible transitive components before output.
- [x] 3.2 Test later-action precedence, accepted review merges, rejected links, unknown schema/action/row IDs, contradiction failure, deterministic provenance, and unchanged output target on invalid input.

## Phase 4: Deterministic review artifacts

- [x] 4.1 Add atomic UTF-8/LF writers in `planilla_player_identity_service.py` for `identities.json`, `identities.csv`, `conflicts.md`, and `identity-summary.json`, with sorted rows and explicit tier/aggregate counts.
- [x] 4.2 Test all four artifacts twice in temporary directories for byte identity, CSV member-row shape, conflict-only Markdown, summary totals, and no partial replacement after a writer failure.

## Phase 5: Local command boundary

- [x] 5.1 Create `backend/scripts/group_planilla_players.py` with manifest/output positional paths, optional overrides argument, clear validation exit codes, and only the four named artifacts.
- [x] 5.2 Add subprocess CLI and AST/import-guard tests proving the service and script load without `app.database`, `app.models`, or `sqlalchemy` imports.

## Phase 6: Corpus verification

- [x] 6.1 Add a `@pytest.mark.corpus` CLI test over `resources/planillas/_discovery/manifest.json`; rerun into two temporary outputs and assert all bytes match, the manifest bytes remain unchanged, and tier counts are sane/non-degenerate without PDF reparsing.

## Phase 7: Revised grouping contract

- [x] 7.1 Update same-team identity classification so matching names auto-group despite jersey changes or missing jerseys, record sorted distinct identity jerseys and a non-blocking variation note, and retain team-homonym isolation.
- [x] 7.2 Update focused unit coverage for jersey swaps, missing jerseys, and cross-team homonyms.

## Phase 8: Conflict evidence gate

- [x] 8.1 Restrict below-threshold same-team conflicts to Dice `>= 2/3` and `< 0.90` with at least two shared normalized name tokens; preserve `>= 0.90` same-team auto-groups regardless of jersey.
- [x] 8.2 Add focused coverage for the `2/3` boundary, below-gate unlinked noise, and the two-shared-token requirement.
