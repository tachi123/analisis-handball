# Design: Planilla Player Identity

## Technical Approach

Add a pure Python service and local CLI beside Phase 1. The CLI reads one manifest and an optional override JSON, flattens roster rows, computes deterministic identity links only within a source scope, and atomically emits review artifacts. It neither imports application modules nor writes the manifest, database, or models.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Scope | `(source_stage, normalized_tournament)`; `source_stage` is the first `source_path` segment because manifest v1 has no stage field | tournament alone; infer a club/team | Prevents cross-stage links using only source evidence. |
| Name comparison | NFD Unicode decomposition, remove combining marks, `casefold`, replace punctuation/whitespace with spaces, lexically sort tokens; multiset Sørensen–Dice `2*intersection/(left+right)`, threshold `>= 0.90` | fuzzy library; edit distance | Meets the spec exactly, handles accents/order, has no new dependency, and is explainable. |
| Evidence | Team is normalized with the same text routine; jersey is the integer `number` | team/jersey as matching keys | Names determine candidacy; team and jersey conservatively classify it. |
| Group construction | Union only safe `auto_group` links plus effective `accept`/`merge` overrides; review/conflict links remain evidence | automatically union every candidate | Keeps ambiguous homonyms and incomplete sheets out of preconfirmed groups. |
| IDs/order | Row ID: `sha256:side:page:roster_index`; identity ID: `identity-v1-` + first member row ID hash; sort by normalized scope/name/row ID | random IDs; input order | Stable IDs and byte-identical reruns. |

## Data Flow

```text
manifest.json + overrides.json
          │
          v
flatten rows -> normalize/scope -> scored links -> classify -> apply overrides
                                                              │
                                                              v
                                  identities.json / .csv / conflicts.md / summary.json
```

Rows with missing/empty names produce no link and remain singleton review identities. Candidate pairs are generated only inside each scope and sorted by `(left_row_id, right_row_id)`. A `>=0.90` same-team link is `auto_group` regardless of jersey; different-team or missing-team candidates are `review`. A below-threshold `conflict` is emitted only for same-team pairs with Dice `>=2/3` and `<0.90` that share at least two normalized-name tokens; all other below-threshold pairs are unlinked noise. Reasons retain raw and normalized evidence. Conflicts never union by default.

Overrides are `{ "schema_version": 1, "links": [{"action":"accept|merge|split|reject","left_row_id":"...","right_row_id":"..."}] }`. Validate the whole document and all row IDs before writing anything. Process the ordered array into final direct-link states (the later action wins), then rebuild components: default auto links except final prohibitions, followed by accepted/merged links. If a prohibited pair ends in one transitive component, fail without replacement; this makes incompatible human edits explicit. Overrides retain their action and sequence in output provenance.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/services/planilla_player_identity_service.py` | Create | Pure flattening, normalization, scoring, tiering, overrides, aggregates, and writers. |
| `backend/scripts/group_planilla_players.py` | Create | Model-free CLI: manifest path, output directory, optional overrides path. |
| `backend/tests/test_planilla_player_identity_service.py` | Create | Unit, artifact, CLI, and import-isolation coverage. |
| `resources/planillas/_discovery/{identities.json,identities.csv,conflicts.md,identity-summary.json}` | Generate | Review-only artifacts; not committed as application data. |

## Interfaces / Contracts

`build_identities(manifest, overrides=None) -> IdentityResult` returns only serializable data:

```json
{
  "schema_version": 1,
  "identities": [{"id":"identity-v1-...","scope":{"source_stage":"...","tournament":"..."},"tier":"auto_group|review","member_row_ids":["..."],"names":["..."],"teams":["..."],"preview":{"appearances":2,"goals":3,"yellow":0,"two_min":1,"red":0,"blue":0},"provenance":[]}],
  "links": [{"left_row_id":"...","right_row_id":"...","score":1.0,"tier":"auto_group|review|conflict","reasons":["..."]}]
}
```

`identities.csv` is one stable member row per identity with identity ID, tier, scope, raw/normalized name, team, jersey, and aggregate fields. `conflicts.md` lists only conflict links and evidence. `identity-summary.json` contains schema version, input paths/counts, identity/link/tier counts, and aggregate totals. Writers serialize UTF-8 JSON (`ensure_ascii=False`, indent 2, trailing LF), CSV LF, and sorted Markdown; write temporary siblings then replace all outputs only after success.

Later batch confirmation consumes `identities[].member_row_ids` and preview/provenance: it may offer `auto_group` and override-resolved review groups for analyst confirmation, while conflict links and unresolved review singletons remain non-importable. It must revalidate IDs against the unchanged manifest; this phase creates no Player mapping.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Unicode/order normalization, Dice boundary, scope, tiers, aggregates, override contradictions | Small synthetic manifest rows. |
| Integration | Four artifacts and byte stability; invalid override preserves old outputs | Run writer twice in temp directories. |
| CLI/isolation | Arguments, exit codes, and no database/model/SQLAlchemy imports | Subprocess/import guard matching Phase 1. |

## Migration / Rollout

No migration required. Run locally against the existing manifest; deletion of service, CLI, and generated review files fully rolls back.

## Open Questions

None.
