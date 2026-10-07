# 3ªM Bootstrap Specification

## Purpose

Provision an auditable 2026 3ªM foundation before official-planilla loading.

## Requirements

### Requirement: Create isolated target stages
The system MUST provision distinct 2026 `Apertura Zona A` and `Torneo Permanencia` 3ªM stages with stage-local CompetitionTeams and registrations. It MUST NOT reuse or alter another stage's records, including 4ª Permanencia.

#### Scenario: Create isolated records
- GIVEN a matching club exists in 4ª Permanencia
- WHEN bootstrap provisions a 3ªM mapping
- THEN both 3ªM stages have local records without changing 4ª records

### Requirement: Gate loading on approved hash-bound evidence
The system MUST report target stage and CompetitionTeam IDs from read-only evidence. Before derivation or canonical-PDF loading, human approval MUST cover both stages, every target ID, eight exact mappings, and manifest/mapping SHA-256 values. It MUST block unapproved, unmatched, or hash-mismatched input.

| Official label | Required preservation |
|---|---|
| Argentinos Juniors D | `D` |
| Defensores de Moreno | exact label |
| Deportivo Laferrere | exact label |
| Defensores de Banfield | exact label |
| Municipalidad de Avellaneda | exact label |
| Municipalidad de San Martín (Ce.M.E.F) | `Ce.M.E.F` club label |
| Municipalidad de Tres de Febrero B | `B` |
| Municipalidad de Vicente López C | `C` |

#### Scenario: Permit an approved corpus
- GIVEN approved IDs, all eight mappings, and matching evidence hashes
- WHEN the 136-PDF corpus is evaluated
- THEN it is eligible for the existing loader

#### Scenario: Reject changed evidence
- GIVEN an approval references a different manifest or mapping hash
- WHEN loading is requested
- THEN no PDF is loaded

### Requirement: Preserve provenance and support safe rehearsal and rollback
Dry run MUST use local evidence only and perform no mutation or loading. Browse aliases MAY appear only in `resources/planillas/_indexed/index.json`; canonical files and SHA-256 values MUST remain immutable. Rollback MUST transactionally remove only bootstrap-created 3ªM records, never aliases, evidence, PDFs, or 4ª data.

#### Scenario: Rehearse locally
- GIVEN local evidence and dry-run mode
- WHEN bootstrap is requested
- THEN it reports planned actions without mutations or loading

#### Scenario: Roll back bootstrap
- GIVEN a completed bootstrap
- WHEN rollback is approved
- THEN only its 3ªM stages, teams, and registrations are removed atomically
