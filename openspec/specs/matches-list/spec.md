# Matches List Specification (Delta)

## Purpose
Clean fixture list page showing only searchable, paginated fixtures with `roster_status` badges. No create form, no review actions, no history tabs.

## ADDED Requirements

### Requirement: List fixtures with roster status badge
The system MUST return a paginated list of `ScheduledFixtureRead` objects filtered to `result_status != 'confirmed'`. Each fixture MUST include `roster_status` (enum: `not_confirmed` | `needs_identity_resolution` | `ready`) and `unresolved_roster_players` count.

#### Scenario: List shows fixtures with correct status badges
- GIVEN fixtures in various states: no PDF, PDF confirmed but unresolved identities, fully resolved
- WHEN the analyst loads `/matches` (GET)
- THEN response includes all fixtures with `result_status != 'confirmed'`
- AND each fixture shows `roster_status` badge: `not_confirmed` (no snapshot), `needs_identity_resolution` (snapshot exists, some `player_id = null`), `ready` (all resolved)
- AND `unresolved_roster_players` count is accurate

#### Scenario: List supports search and stage filter
- GIVEN fixtures across multiple stages
- WHEN the analyst searches by team name, date, or filters by stage
- THEN results are filtered client-side (or server-side) matching the query
- AND pagination works for large result sets

### Requirement: No create match form on matches list
The system MUST NOT render the "Nuevo partido" create form on `/matches`. Manual match creation is a separate flow (out of scope).

#### Scenario: Create form absent from matches list
- GIVEN the analyst navigates to `/matches`
- WHEN the page renders
- THEN no create form, team selectors, date picker, or score inputs are present
- AND no "Crear y abrir análisis" button exists

### Requirement: No review or roster action buttons on matches list
The system MUST NOT render "Resolver planilla" or "Abrir análisis" buttons on `/matches`. Navigation to review/roster is via dedicated routes.

#### Scenario: Action buttons absent from matches list
- GIVEN a fixture with `roster_status = 'needs_identity_resolution'` or `ready`
- WHEN the analyst views the list row
- THEN no "Resolver planilla" link or "Abrir análisis" button is rendered
- AND the row is informational only (shows teams, date, score, stage, status badge)

## REMOVED Requirements

### Requirement: Create match form on matches page
(Reason: Separated to dedicated manual match creation flow; keeps `/matches` focused on fixture list)

### Requirement: Roster action buttons on fixture rows
(Reason: Moved to `/fixtures/:fixtureKey/review` and `/fixtures/:fixtureKey/roster` routes)

### Requirement: History tabs on matches page
(Reason: Not part of this change; matches list is strictly fixtures needing action)

## Notes
- Uses existing `GET /pdf/fixtures` endpoint with added `result_status != 'confirmed'` filter
- Response model: `ScheduledFixtureRead` (already includes `roster_status`, `unresolved_roster_players`)
- Frontend: `MatchesPage.tsx` stripped to list+search only