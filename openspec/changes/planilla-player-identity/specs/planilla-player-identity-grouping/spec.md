# Planilla Player Identity Grouping Specification

## Purpose

Produce auditable, read-only player-identity candidates and roster-only previews from the discovery manifest.

## Requirements

### Requirement: Deterministic candidate matching

The system MUST read only discovery `manifest.json` roster rows. It MUST compare rows only within the same source tournament and stage. It MUST preserve each raw name and derive a comparison name by Unicode decomposition and accent removal, case folding, punctuation/whitespace normalization, and lexically sorted tokens. Its token similarity score MUST be the Sørensen–Dice score of the normalized token multisets; a candidate link MUST require a score of at least `0.90`. An `auto_group` link MUST have equal nonempty normalized team labels; jersey values MUST NOT block the group.

#### Scenario: Accent, case, and token-order variant
- GIVEN two rows have the same tournament, stage, team, jersey, and names `García, Ana María` and `ana maria garcia`
- WHEN identities are grouped
- THEN their normalized names and score are identical and they are `auto_group`ed

#### Scenario: Similarity threshold boundary
- GIVEN otherwise eligible rows with a calculated score of `0.90`, and another pair with `0.89`
- WHEN identities are grouped
- THEN only the `0.90` pair is a candidate link

#### Scenario: Cross-stage names
- GIVEN equal normalized names, teams, and jerseys in different tournament or stage values
- WHEN identities are grouped
- THEN the rows are not linked

#### Scenario: Same name with different jerseys
- GIVEN two qualifying rows have the same tournament, stage, and nonempty normalized team, names with a score of at least `0.90`, and jerseys `1` and `8`
- WHEN identities are grouped
- THEN the rows are `auto_group`ed into one identity
- AND the identity records jerseys `[1, 8]` and a non-blocking jersey-variation note

### Requirement: Conservative confidence classification

The system MUST classify candidate evidence as `auto_group`, `review`, or `conflict` with raw evidence and a reason. A qualifying pair lacking a team label MUST be `review` and MUST NOT be merged automatically. A qualifying pair with different nonempty normalized team labels MUST remain separate and MUST NEVER merge, regardless of jersey. A qualifying same-team pair with a score of at least `0.90` MUST merge despite missing, equal, or different jersey values; its identity MUST expose a deterministic list of known jerseys and a non-blocking note when more than one known jersey is present. `conflict` MUST be reserved for genuinely contradictory evidence: same tournament/stage/team scope, Dice similarity `>= 2/3` and `< 0.90`, and at least two shared normalized name tokens, or an analyst-flagged conflict. Lower-scoring or one-token matches MUST remain unlinked noise with no tier.

#### Scenario: Missing team label
- GIVEN a qualifying name and jersey pair where one row has no team label
- WHEN identities are grouped
- THEN it is emitted as `review` without an inferred team or automatic merge

#### Scenario: Missing jersey
- GIVEN a qualifying name and nonempty team pair where one row has no jersey
- WHEN identities are grouped
- THEN it is `auto_group`ed and retains the missing-jersey evidence

#### Scenario: Team homonym protection
- GIVEN equal normalized names in the same tournament and stage but different nonempty teams
- WHEN identities are grouped
- THEN they remain separate team-scoped identities and are never merged

#### Scenario: Below-threshold name collision
- GIVEN rows share a tournament, stage, and nonempty normalized team, have Dice similarity `>= 2/3` and `< 0.90`, and share at least two normalized name tokens
- WHEN identities are grouped
- THEN they remain separate and a `conflict` records the contradictory evidence

#### Scenario: Below-conflict-gate noise
- GIVEN same-team rows have Dice similarity below `2/3`, or share fewer than two normalized name tokens
- WHEN identities are grouped
- THEN they remain separate and emit no link tier

#### Scenario: Analyst-flagged conflict
- GIVEN an analyst has flagged a same-scope identity conflict
- WHEN identities are grouped
- THEN the affected evidence is emitted as `conflict` and is not automatically merged

### Requirement: Overrides and preview aggregates

The system MUST accept a human-editable JSON override document with `schema_version: 1` and an ordered `links` array of `{action, left_row_id, right_row_id}`. `action` MUST be one of `accept`, `merge`, `split`, or `reject`; unknown versions, actions, or row IDs MUST fail without output replacement. Overrides MUST be applied in array order: `accept`/`merge` join the named rows, while `split`/`reject` prohibit that link; the same input and overrides MUST yield the same result. Each candidate MUST preview appearances, goals, and every card total exclusively from its included manifest roster rows.

#### Scenario: Deterministic override rerun
- GIVEN a valid override file that merges two review rows and rejects another link
- WHEN grouping runs twice against unchanged inputs
- THEN both runs produce the same candidate memberships and aggregates

#### Scenario: Aggregate source boundary
- GIVEN a candidate containing three manifest roster rows with recorded goals and cards
- WHEN its preview is emitted
- THEN appearances, goals, and card totals equal those three rows only

### Requirement: Stable review artifacts and isolation

The system MUST emit `identities.json`, `identities.csv`, a conflicts report, and a summary with schema version, stable candidate IDs, deterministic ordering, and explicit tier counts. Unchanged inputs and overrides MUST produce byte-identical artifacts. The service and CLI MUST NOT import application models, open database connections, write database entities, or modify the discovery manifest.

#### Scenario: Byte-stable output
- GIVEN unchanged manifest and overrides
- WHEN the command runs twice
- THEN every emitted artifact has identical bytes

#### Scenario: Import isolation
- GIVEN model/database imports and connections are guarded to fail
- WHEN the grouping service and CLI are loaded and run
- THEN identity artifacts are produced without triggering the guard
