# Proposal: Official 3ªM Competition Bootstrap

## Intent

Safely create the missing 2026 3ª División Masculino competition foundation so the approved official-planilla loader can load all 136 FEMEBAL sheets without cross-stage identity reuse or inferred team matches.

## Scope

### In Scope
- Provision distinct 2026 `Apertura Zona A` and `Torneo Permanencia` 3ªM stages, their stage-local CompetitionTeams and registrations; never reuse a CompetitionTeam from the existing 4ª Permanencia stage.
- Create reviewable, exact-label mapping records for the eight missing targets: Argentinos Juniors D; Defensores de Moreno; Deportivo Laferrere; Defensores de Banfield; Municipalidad de Avellaneda; Municipalidad de San Martín (Ce.M.E.F); Municipalidad de Tres de Febrero B; Municipalidad de Vicente López C.
- Preserve `B`/`C`/`D` variants, retain `Ce.M.E.F` as the club label, and expose browseable aliases only in `resources/planillas/_indexed/index.json`; canonical sources and SHA-256 values remain immutable.
- Require read-only database evidence plus explicit human approval of stage/team IDs and mapping hashes before derivation or the 136-PDF load.

### Out of Scope
- Fuzzy matching, prefix stripping, inferred aliases, or resolution from roster/opponent similarity alone.
- Parser changes, PDF replacement/upload, loader execution before approval, and changes to 4ª data.

## Capabilities

### New Capabilities
- `official-3m-competition-bootstrap`: Approved, stage-scoped provisioning and alias evidence required before the official 3ªM batch load.

### Modified Capabilities
- `competition-team-identity`: Resolve only exact approved labels against an approved target-stage CompetitionTeam; preserve qualifiers and variants.
- `fixture-seeding`: Seed the two 3ªM stages idempotently without sharing registrations or CompetitionTeams across stages.

## Approach

Use `resources/planillas/_discovery/manifest.json`, `identities/identity-summary.json`, `reconciliation-report.md`, `team-mapping.json`, and `_indexed/index.json` as direct evidence. The corpus has 136 canonical PDFs: 112 Apertura and 24 Permanencia; all parse with labelled home/away and scores, no missing team labels or parse errors. First produce a read-only stage/team-ID report, then a hash-bound mapping/approval artifact. Only approved exact mappings create target-stage records; unmatched labels block loading.

## Review and Delivery Gate

Human approval MUST confirm both target stages, every target-stage CompetitionTeam ID, all eight mappings, and manifest/mapping hashes. PR slice 1: stage bootstrap, mapping/approval validation, and tests; target the feature branch, stay within 400 changed lines, and be independently rollbackable. Later loader slices target the preceding branch (`feature-branch-chain`; execution `auto`).

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/services/fixture_seeder.py`, tests | Modified | Stage-local idempotent bootstrap |
| `resources/planillas/_discovery/` | Modified | Mapping, approval, and direct evidence |
| `resources/planillas/_indexed/index.json` | Modified | Browse aliases only |
| Database | Modified | 3ªM stage/team/registration records |
| Frontend / deployment | None | No client or deployment change |

## Risks and Rollback

| Risk | Mitigation |
|---|---|
| Wrong identity merge | Exact approved IDs only; no fuzzy matching |
| Variant/qualifier loss | Preserve suffixes and full `Ce.M.E.F` label |

Rollback deletes only bootstrap-created 3ªM registrations, CompetitionTeams, and stages in a transaction; it never alters PDFs, aliases, hashes, or 4ª records.

## Success Criteria

- [ ] Both 3ªM stages and all required stage-local teams are approved and idempotently provisioned.
- [ ] Every one of 136 canonical PDFs is eligible for the existing loader only after hash-bound approval.
- [ ] Alias browsing does not mutate canonical files or SHA-256 provenance.
