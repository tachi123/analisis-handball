# Competition Team Identity Specification

## Purpose
Preserve the source identity of FEMEBAL clubs and competition teams without manufacturing a team variant.

## Requirements

### Requirement: Preserve supplied competition-team variants
The system MUST create a canonical Club and a stage-scoped CompetitionTeam. A supplied variant MUST be preserved, while an absent variant MUST be represented explicitly as absent. The persistence identity MUST distinguish absent variant from every supplied variant. The system MUST NOT infer, invent, strip, or require a variant.

#### Scenario: Import a team with a supplied variant
- GIVEN the fixture names a team "Banfield B"
- WHEN the fixture is imported
- THEN its CompetitionTeam retains variant "B" and remains distinguishable from "Banfield A"

#### Scenario: Import a team without a variant
- GIVEN the fixture names a team "Banfield" with no variant
- WHEN the fixture is imported
- THEN the CompetitionTeam is created without a variant and is not assigned one

### Requirement: Match identities conservatively
The system MUST use the source club name, supplied variant state, and stage when resolving a CompetitionTeam. It MUST NOT merge candidates that remain ambiguous after those facts are considered.

#### Scenario: Similar source names remain distinct
- GIVEN a stage contains "Banfield" and "Banfield B"
- WHEN a source match names "Banfield B"
- THEN only the variant-bearing team is eligible for that side of the match
