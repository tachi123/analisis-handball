# Fixture Roster Specification (Delta)

## Purpose
Identity resolution page for confirmed fixture rosters. Extends existing flow to accept navigation from `/fixtures/:fixtureKey/review` and ensures resolution creates `MatchSquad[]` and `StageRoster[]` for each registration.

## MODIFIED Requirements

### Requirement: Create one confirmed fixture-linked analysis match

The system MUST re-read the fixture by `fixture_key`, reparse uploaded bytes, validate compatible registration sides and explicit existing identities, and create or link exactly one analysis `Match` with official snapshot and squad. It MUST reject duplicate links safely, preserve fixture scores and result status, require acknowledgement for a known score mismatch, and return the linked `match_id` for video analysis. **During subsequent identity resolution at `/fixtures/:fixtureKey/roster`, the system MUST create `MatchSquad[]` entries synced from `OfficialSnapshotPlayer` and `StageRoster[]` entries upserted per `TeamRegistration` for each resolved player.**
(Previously: Created Match + OfficialSnapshot + squad during confirmation; StageRoster creation was implicit but not explicitly specified)

#### Scenario: Retry confirmation after success
- GIVEN a fixture already has a linked analysis match
- WHEN the analyst retries the same confirmation
- THEN the system returns the existing `match_id` and creates no additional match, snapshot, or squad

#### Scenario: Block an unacknowledged discrepancy
- GIVEN both fixture and sheet scores are present and differ
- WHEN confirmation omits acknowledgement
- THEN the system rejects the request and leaves all fixture values unchanged

#### Scenario: Identity resolution creates full squad and stage roster
- GIVEN a confirmed fixture with `OfficialSnapshot` and `OfficialSnapshotPlayer[]` (some with `player_id = null`)
- WHEN the analyst resolves all unresolved players via POST `/pdf/fixtures/{fixtureKey}/roster-resolution` (choose existing Player OR create new)
- THEN for each resolved row: `OfficialSnapshotPlayer.player_id` is set, `MatchSquad` is created/updated with official stats, and `StageRoster` is upserted for the registration with jersey number
- AND `PDFService._roster_is_ready()` returns true only when all rows have `player_id`, `MatchSquad` count = 1 per player, `StageRoster` count = 1 per registration+jersey

#### Scenario: Identity resolution rejects duplicate player assignment
- GIVEN two `OfficialSnapshotPlayer` rows resolve to the same `Player` ID
- WHEN resolution is submitted
- THEN the system rejects with "one player cannot resolve multiple official roster rows"

#### Scenario: Identity resolution rejects cross-team player assignment
- GIVEN a resolved `Player` belongs to a different `Team` than the fixture side
- WHEN resolution is submitted
- THEN the system rejects with "selected player does not belong to the fixture side"

#### Scenario: Identity resolution rejects jersey conflict in stage roster
- GIVEN a `Player` already has a `StageRoster` entry for the registration with a different jersey number
- WHEN resolution assigns a new jersey number
- THEN the system rejects with "player is already assigned to jersey X in stage roster"

## ADDED Requirements

### Requirement: Accept fixtureKey from review flow navigation
The system MUST allow the `FixtureRosterPage` to be reached via redirect from `/fixtures/:fixtureKey/review` after successful confirmation. The page MUST load the roster for the given `fixtureKey` using existing `GET /pdf/fixtures/{fixtureKey}/roster`.

#### Scenario: Navigation from review to roster
- GIVEN analyst completes confirmation at `/fixtures/:fixtureKey/review` (POST)
- WHEN confirmation succeeds
- THEN frontend navigates to `/fixtures/:fixtureKey/roster`
- AND roster page loads with all `OfficialSnapshotPlayer` rows showing candidates for unresolved players

## REMOVED Requirements

### Requirement: Roster resolution only accessible from matches list
(Reason: Now accessible from dedicated review flow; matches list no longer has action buttons)

## Notes
- Uses existing `PDFService.resolve_fixture_roster()` which already creates `MatchSquad` and `StageRoster` via `_upsert_roster_entries()`
- Frontend: `FixtureRosterPage.tsx` unchanged except for accepting navigation from review flow
- Analyst decision per row: link existing `Player` (by team + name match suggestions) OR create new `Player` (name, jersey, team, position)
- NO auto-match: explicit analyst decision required per constraint