# Backfill Execution Specification

## Purpose
One-off script to execute confirmation for the blocked PDF `7164158c7b0e9b17.pdf`, resolve player identities via explicit analyst decisions, and create the full entity chain (Match + OfficialSnapshot + MatchSquad + StageRoster) to unlock analysis.

## Requirements

### Requirement: Locate PDF by SHA256 and find matching ScheduledMatch
The system MUST locate the PDF file by its SHA256 hash `7164158c7b0e9b17` in `manifest.json` / `derived-fixtures.json`, find the corresponding `FixtureImportEntry`, and retrieve the linked `ScheduledMatch`.

#### Scenario: PDF hash resolves to fixture
- GIVEN PDF `7164158c7b0e9b17.pdf` exists in `resources/planillas/` and is indexed in `manifest.json` with `FixtureImportEntry` linking to a `ScheduledMatch`
- WHEN the backfill script runs with the PDF hash as input
- THEN the script identifies the correct `ScheduledMatch.fixture_key`
- AND the fixture has `result_status != 'confirmed'` (not yet processed)

#### Scenario: PDF hash not found
- GIVEN the PDF hash does not exist in `manifest.json` or `derived-fixtures.json`
- WHEN the backfill script runs
- THEN the script exits with error "PDF hash not found in import index"

### Requirement: Execute confirmation flow using existing services
The system MUST invoke `PDFService.fixture_preview()` and `PDFService.confirm_fixture()` with the stored PDF bytes and confirmation data (team IDs, player roster from PDF parse) to create `Match`, `OfficialSnapshot`, and `OfficialSnapshotPlayer[]` (with `player_id = null`).

#### Scenario: Confirmation creates entity chain
- GIVEN a valid `fixtureKey` and PDF bytes
- WHEN `PDFService.confirm_fixture()` is called with `FixtureConfirmation` (home_team_id, away_team_id, home_players, away_players from parsed PDF)
- THEN exactly one `Match` is created linked to `ScheduledMatch.analysis_match`
- AND exactly one `OfficialSnapshot` is created with PDF file reference
- AND `OfficialSnapshotPlayer[]` rows are created for all parsed players with `player_id = null`
- AND `ScheduledMatch.result_status` is updated

#### Scenario: Confirmation is idempotent
- GIVEN the backfill script runs twice for the same PDF hash
- WHEN the second run executes
- THEN `PDFService.confirm_fixture()` returns `reused = true` with existing `match_id` and `snapshot_id`
- AND no duplicate `Match`, `OfficialSnapshot`, or `OfficialSnapshotPlayer` rows are created

### Requirement: Resolve player identities via explicit analyst decisions
For each `OfficialSnapshotPlayer` row with `player_id = null`, the system MUST present the analyst with a choice: link an existing `Player` (suggested by team + normalized name match) OR create a new `Player` (name, jersey_number, team_id, position). NO automatic matching.

#### Scenario: Analyst links existing player
- GIVEN an unresolved `OfficialSnapshotPlayer` with name "García", jersey 10, side "home"
- WHEN the analyst selects existing `Player` ID 42 (team matches fixture home team, normalized name matches)
- THEN `OfficialSnapshotPlayer.player_id` is set to 42
- AND `MatchSquad` is created/updated with official stats (goals, cards)
- AND `StageRoster` is upserted for the home registration with jersey 10

#### Scenario: Analyst creates new player
- GIVEN an unresolved `OfficialSnapshotPlayer` with name "López", jersey 7, side "away"
- WHEN the analyst chooses "Crear identidad nueva" and confirms
- THEN a new `Player` is created with name="López", team_id=away_team_id, default_jersey_number=7
- AND `OfficialSnapshotPlayer.player_id` is set to the new player ID
- AND `MatchSquad` and `StageRoster` are created as above

#### Scenario: Resolution rejects duplicate player assignment
- GIVEN two unresolved rows resolve to the same existing `Player` ID
- WHEN resolution is submitted
- THEN the system rejects with "one player cannot resolve multiple official roster rows"

#### Scenario: Resolution rejects cross-team assignment
- GIVEN an unresolved home-side row resolves to a player belonging to the away team
- WHEN resolution is submitted
- THEN the system rejects with "selected player does not belong to the fixture side"

### Requirement: Complete entity chain verification
After all identities are resolved, the system MUST verify the full audit trail: PDF → `FixtureImportEntry` → `ScheduledMatch` → `Match` → `OfficialSnapshot` → `OfficialSnapshotPlayer[]` → `MatchSquad[]` + `StageRoster[]`.

#### Scenario: Full chain verified
- GIVEN backfill completes for PDF `7164158c7b0e9b17.pdf`
- WHEN verification runs
- THEN `ScheduledMatch.analysis_match` points to created `Match`
- AND `Match.official_snapshots` contains the created `OfficialSnapshot`
- AND `OfficialSnapshot.players` all have `player_id != null`
- AND `Match.squad` has one entry per `OfficialSnapshotPlayer` with matching jersey and official stats
- AND `StageRoster` has one entry per registration per resolved player with matching jersey
- AND `/match/{matchId}/analysis` loads with complete squad dropdowns

### Requirement: Uses existing services only
The backfill MUST use only existing services: `PDFService.fixture_preview()`, `PDFService.confirm_fixture()`, `PDFService.resolve_fixture_roster()`. NO new service methods.

#### Scenario: Backfill uses only existing public methods
- GIVEN the backfill script executes
- WHEN it calls PDF service methods
- THEN only `fixture_preview`, `confirm_fixture`, `resolve_fixture_roster` are invoked
- AND no direct database manipulation bypasses service validation

## Notes
- Input: PDF SHA256 hash `7164158c7b0e9b17`
- Output: Populated `Match`, `OfficialSnapshot`, `MatchSquad[]`, `StageRoster[]`
- Idempotent: re-running updates existing records, doesn't duplicate
- Analyst interaction required for identity resolution (no automation)
- PDF file must be present in `resources/planillas/` and indexed