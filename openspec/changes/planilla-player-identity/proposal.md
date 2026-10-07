# Proposal: Planilla Player Identity

## Intent

Turn Phase 1's 136 canonical, read-only roster records into auditable player-identity candidates before any historical data is persisted. Analysts need deterministic grouping despite name variants and incomplete team labels.

## Scope

### In Scope
- Read the existing discovery `manifest.json` only; emit deterministic `identities.json`, `identities.csv`, conflicts report, and summary.
- Group roster rows within the same source tournament/stage using normalized name similarity, labelled team context, and jersey evidence; classify `auto_group`, `review`, or `conflict`.
- Preserve and explicitly report accent/case/order variants, jersey swaps, team homonyms, missing jerseys, and the 72 missing-team-label sheets; degrade to available context rather than infer a team.
- Define a versioned, human-editable override file that deterministically accepts, splits, merges, or rejects candidate links on re-run.
- Preview candidate appearances, goals, and card totals from manifest roster rows only.
- Extend the Phase 1 model/database import guard to this service and CLI.

### Out of Scope
- Batch confirmation into database entities.
- Standings API.
- YouTube hooking.

## Capabilities

### New Capabilities
- `planilla-player-identity-grouping`: Deterministic, reviewable, manifest-only roster identity grouping and aggregate previews.

### Modified Capabilities
- None.

## Approach

Build a pure grouping service and local CLI alongside the discovery pipeline. Canonicalize display-name tokens (Unicode accents, case, punctuation, and surname/given-name order), score only within tournament/stage, and use team and jersey as corroborating—not decisive—evidence. Stable candidate IDs, ordered inputs, explicit confidence reasons, and validated overrides make re-runs byte-stable. Ambiguous evidence stays reviewable; it never creates a Player or queries application models.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/services/planilla_player_identity_service.py` | New | Pure grouping, scoring, overrides, aggregates |
| `backend/scripts/group_planilla_players.py` | New | Model-free local CLI |
| `backend/tests/test_planilla_player_identity_service.py` | New | Edge cases, determinism, import guard |
| `resources/planillas/_discovery/` | Generated | Identity review artifacts only |
| Frontend / Database / Deployment | None | No UI, models, migrations, writes, or deployment |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Incorrect merge from incomplete context | High | Conservative tiers, conflict report, overrides |
| Parser-truncated names | Medium | Preserve raw evidence; require review |
| Output drift | Low | Stable ordering, schema version, byte-stability tests |

## Rollback Plan

Remove the pure CLI/service and generated identity artifacts. The manifest, PDFs, database, and application records remain untouched.

## Dependencies

- Phase 1 `resources/planillas/_discovery/manifest.json` schema v1 and its import-isolation pattern.

## Success Criteria

- [ ] The 136-record manifest produces deterministic identities JSON/CSV, conflict report, and summary without model imports or DB writes.
- [ ] All required ambiguity cases are tiered and evidenced; missing team labels do not block unrelated safe groups.
- [ ] Override edits rerun deterministically and aggregates equal manifest-only roster totals.
