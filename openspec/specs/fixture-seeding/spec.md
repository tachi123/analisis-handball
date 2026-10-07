# Fixture Seeding Specification

## Purpose
Import the FEMEBAL `Torneo Metropolitano Clausura Permanencia | Mayores - 4º División - Masculino` fixture from analyst-supplied copied data or curated JSON.

## Requirements

### Requirement: Import supplied fixture data idempotently
The system MUST import analyst-supplied curated JSON into stage metadata, clubs, competition teams, registrations, rounds, and non-bye matches. It MUST retain the original payload, source label, capture time, and SHA-256 in an import audit. It MUST NOT scrape, require, or bulk-import fixture PDFs. Re-importing an unchanged source hash MUST be a no-op.

#### Scenario: Prove the first three supplied rounds
- GIVEN copied fixture data for rounds 1 through 3, including played and future scheduled entries
- WHEN the analyst imports it
- THEN all non-bye entries are available with their source dates, times, teams, source audit, and supplied results

#### Scenario: Import the remaining tournament
- GIVEN copied data for the remaining rounds is supplied later
- WHEN it is imported with the existing first three rounds
- THEN the complete tournament fixture is available without duplicate records or assumed match counts

### Requirement: Exclude fixture byes from competition entities
The system MUST treat FEMEBAL `Libre` as a fixture bye. It MUST retain it as a source-only import entry and MUST NOT create a Club, CompetitionTeam, TeamRegistration, player, ScheduledMatch, result, standings input, or statistics input for it.

#### Scenario: Import a Libre entry
- GIVEN a copied round contains a `Libre` entry
- WHEN the fixture is imported
- THEN no opponent, registration, match, standings input, or player-statistics input is created for it
- AND the import audit identifies the original bye entry

### Requirement: Preserve fixture result authority
The system MUST store a supplied fixture result with explicit `reported`, `approved`, or `disputed` status. A later import or match-sheet integration MAY flag disagreement, but MUST NOT silently replace an approved fixture result.

#### Scenario: Match sheet disagrees with fixture result
- GIVEN a played ScheduledMatch has an approved fixture result
- WHEN its uploaded match sheet reports a different score
- THEN the disagreement is visible for analyst review and the fixture result remains unchanged
