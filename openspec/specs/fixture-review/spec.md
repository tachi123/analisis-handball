# Fixture Review Specification (Delta)

## Purpose
Dedicated route for analyst to review a pending PDF against its fixture registration, confirm compatibility, and trigger identity resolution. Replaces conflated `/matches` review actions.

## ADDED Requirements

### Requirement: Preview PDF against fixture registration
The system MUST allow the analyst to preview a PDF planilla for a specific `fixtureKey` by comparing parsed sheet data against the `ScheduledMatch` registration sides. It MUST return parsed evidence, team compatibility (`compatible` | `incompatible` | `unresolved`), and score reconciliation (`match` | `mismatch` | `unknown`).

#### Scenario: Successful preview with compatible sides
- GIVEN a `fixtureKey` with pending `ScheduledMatch` (result_status != 'confirmed') and a valid FEMEBAL PDF uploaded
- WHEN the analyst requests preview via GET `/fixtures/:fixtureKey/review`
- THEN the system returns parsed preview with home/away compatibility and score reconciliation
- AND no `Match`, `OfficialSnapshot`, or `MatchSquad` is created

#### Scenario: Preview rejects already-confirmed fixture
- GIVEN a `fixtureKey` where `ScheduledMatch.result_status = 'confirmed'`
- WHEN the analyst requests preview
- THEN the system returns 409 error with code `fixture_already_confirmed`

#### Scenario: Preview rejects bye fixture
- GIVEN a `fixtureKey` that maps to a bye entry (`FixtureImportEntry.kind = 'bye'`)
- WHEN the analyst requests preview
- THEN the system returns 404 error

### Requirement: Confirm PDF with explicit team identity
The system MUST allow the analyst to confirm a previewed PDF by selecting existing `Team` records for home and away, acknowledging score mismatch if present, and creating the analysis `Match`, `OfficialSnapshot`, and `OfficialSnapshotPlayer[]` rows (with `player_id = null` pending resolution).

#### Scenario: Confirm creates full entity chain
- GIVEN a successful preview, analyst selects valid existing home/away `Team` IDs, acknowledges any score mismatch
- WHEN the analyst submits confirmation via POST `/fixtures/:fixtureKey/review`
- THEN the system creates exactly one `Match` linked to `ScheduledMatch.analysis_match`, one `OfficialSnapshot` with PDF file, and `OfficialSnapshotPlayer[]` rows with `player_id = null`
- AND `ScheduledMatch.result_status` is updated to reflect confirmation
- AND response includes `match_id` and redirects to `/fixtures/:fixtureKey/roster`

#### Scenario: Confirm is idempotent on re-run
- GIVEN a fixture already has a linked `Match` and confirmed `OfficialSnapshot`
- WHEN the analyst re-submits confirmation for the same PDF hash
- THEN the system returns the existing `match_id` and `snapshot_id` with `reused = true`
- AND no duplicate `Match`, `OfficialSnapshot`, or `OfficialSnapshotPlayer` rows are created

#### Scenario: Confirm rejects mismatched team selection
- GIVEN analyst selects home and away `Team` IDs that are identical
- WHEN confirmation is submitted
- THEN the system rejects with error "Los equipos confirmados deben ser distintos"

### Requirement: Exclude confirmed fixtures from review list
The system MUST filter the fixture list at `/pdf/fixtures` to only include `ScheduledMatch` where `result_status != 'confirmed'` AND has a pending PDF import (`FixtureImportEntry.kind = 'match'`). Already-confirmed fixtures MUST NOT appear.

#### Scenario: List excludes confirmed fixtures
- GIVEN multiple fixtures, some with `result_status = 'confirmed'`
- WHEN the analyst loads `/fixtures/:fixtureKey/review` or the fixture list
- THEN only fixtures with `result_status != 'confirmed'` are returned
- AND fixtures with `result_status = 'confirmed'` are absent from the list

## REMOVED Requirements

### Requirement: Review actions embedded in matches list
(Reason: Moved to dedicated `/fixtures/:fixtureKey/review` route for separation of concerns)

## Notes
- Uses existing services: `PDFService.fixture_preview()`, `PDFService.confirm_fixture()`
- Identity resolution is deferred to `/fixtures/:fixtureKey/roster` (see fixture-roster delta)
- Audit trail: PDF → FixtureImportEntry → ScheduledMatch → Match → OfficialSnapshot → OfficialSnapshotPlayer must remain intact