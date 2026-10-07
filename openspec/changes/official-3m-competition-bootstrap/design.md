# Design: Official 3ªM Competition Bootstrap

## Technical Approach

Add a local, idempotent bootstrap path before the existing derivation/official-loader path. A reviewed manifest declares only the two 2026 3ªM stages and their exact target club/variant pairs. The bootstrap service creates stage-local records, emits a read-only ID evidence report, and never reads PDFs. Derivation then accepts only an exact mapping plus approval bound to the discovery, bootstrap, and mapping hashes; the existing loader remains the final PDF-provenance gate.

## Architecture Decisions

| Decision | Alternatives / tradeoff | Decision and rationale |
|---|---|---|
| Separate bootstrap service | Reuse `_registration`, which creates identities while importing fixtures | Create `official_competition_bootstrap_service.py`. Bootstrap must be reviewable without fixture/PDF work and must not let loader input create unapproved teams. |
| Manifest is declarative and stage-scoped | Infer participants from rosters/opponents; share 4ª records | `bootstrap-manifest.json` names both stages and exact club/variant pairs. Reuse only exact `Club.name`; create a distinct `CompetitionTeam` and registration per stage. No heuristic or cross-stage merge. |
| Two-step approval | Approve only derived JSON after derivation | `bootstrap-approval.json` is approved before derivation and hash-binds database evidence; after deterministic derivation it is completed with `derived_sha256` before loading. This prevents unapproved derivation and preserves the existing load gate. |

## Data Flow

```
manifest + exact mapping ──> bootstrap CLI ──> DB transaction
                                  │                 │
                                  └──> bootstrap-report.json (stage/team IDs)
manifest/mapping/report + human approval ──> derive CLI ──> derived-fixtures.json
derived + completed approval + PDFs ──> existing load_planilla_official CLI
```

Creation order inside one transaction: find/create `Season(2026)`; find/create each `TournamentStage` by `(season_id, name)` and verify category/division/gender; for each manifest entry find/create exact `Club.name`; find/create `CompetitionTeam(club_id, stage_id, variant_key)`; then find/create `TeamRegistration(competition_team_id, stage_id)`. A conflicting existing row fails rather than being rewritten. Reruns return the same IDs and create nothing.

## Interfaces / Contracts

`resources/planillas/_discovery/bootstrap-manifest.json` (canonical JSON, schema v1):

```json
{"schema_version":1,"manifest_sha256":"…","stages":[{"key":"apertura-3m-2026","name":"Apertura Zona A 2026 3ªM","category":"Mayores","division":"3ª División","gender":"Masculino","teams":[{"club":"Argentinos Juniors","variant":"D"}]}]}
```

Both required stage keys are `apertura-3m-2026` and `permanencia-3m-2026`. Teams cover approved source-label targets for their observed stage; a team appearing in both receives two records. `variant` is `null` or a non-empty exact string; `B`/`C`/`D` and `Municipalidad de San Martín (Ce.M.E.F)` are preserved.

Extend `team-mapping.json` to schema v2: retain `manifest_sha256`; each exact source label maps to `{ "club", "variant", "stage_keys" }`. The eight unresolved labels use their full source labels (including institutional prefixes) as keys and the approved target values listed in the proposal. Every `stage_key` must contain that target in the bootstrap manifest; no normalization or fallback lookup is permitted.

`bootstrap-report.json` is canonical, read-only evidence: `{schema_version, manifest_sha256, bootstrap_manifest_sha256, stages:[{key,id,teams:[{club,variant,club_id,competition_team_id,registration_id}]}]}`. `bootstrap-approval.json` requires these three SHA-256 values plus the complete stage/team-ID list and explicit approver metadata. Derivation validates all fields and its output embeds `bootstrap_approval_sha256`; completing approval adds the exact `derived_sha256`. The loader rejects absent/mismatched bindings.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/services/official_competition_bootstrap_service.py` | Create | Validate manifest, idempotently provision, report/rollback helpers. |
| `backend/scripts/bootstrap_official_3m_competition.py` | Create | Explicit database URL, manifest/report paths, dry-run and rollback commands. |
| `backend/app/services/planilla_derivation_service.py` | Modify | Validate v2 mapping and pre-derivation approval; embed approval hash. |
| `backend/scripts/derive_planilla_fixtures.py` | Modify | Require bootstrap report and approval for official derivation. |
| `backend/app/services/official_planilla_loader_service.py` | Modify | Require completed bootstrap/derived approval bindings. |
| `resources/planillas/_discovery/{bootstrap-manifest.json,team-mapping.json,bootstrap-approval.json}` | Create/Modify | Reviewable source, mappings, and approval. |
| `resources/planillas/_indexed/index.json` | Modify | Add browse aliases only; retain canonical paths and hashes. |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | Manifest, mapping, and approval validation | Reject missing stages, label changes, variant loss, ID/hash mismatch, and conflicting pre-existing data. |
| Integration | Bootstrap ordering/idempotency and rollback | Migrated SQLite DB: verify stage-local teams/registrations, unchanged 4ª rows, same IDs on rerun; rollback deletes only manifest-created empty bootstrap records. |
| Integration | Gate/provenance chain | CLI tests prove derivation/load reject unapproved evidence; successful fixture loading preserves source bytes/SHA-256. |

## Migration / Rollout

No schema migration or client/API change. Slice 1 (feature branch, under 400 changed lines) contains bootstrap, validation, and tests; later loader work targets the prior branch. Rollback is a transaction and is allowed only when bootstrap-owned stages have no fixture imports, scheduled matches, or official batches; otherwise it fails without deletion. It never changes PDFs, aliases, hashes, clubs reused by other data, or 4ª records.

## Open Questions

None.
