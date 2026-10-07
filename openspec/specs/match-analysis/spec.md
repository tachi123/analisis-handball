# Match Analysis Specification (Delta)

## Purpose
Canonical event tagging page for a confirmed match. No behavioral change; verification that backfill produces fully populated squads for analysis.

## ADDED Requirements

### Requirement: Analysis page loads with complete squad dropdowns from backfill
The system MUST render `/match/:matchId/analysis` with both home and away squad dropdowns fully populated when the match was created via the backfill flow (PDF confirmation + identity resolution).

#### Scenario: Backfill match opens analysis with full squads
- GIVEN a `Match` created via backfill for PDF `7164158c7b0e9b17.pdf` with all `OfficialSnapshotPlayer` resolved, `MatchSquad[]` and `StageRoster[]` populated
- WHEN the analyst navigates to `/match/{matchId}/analysis`
- THEN the page loads without errors
- AND squad selectors show all players from both teams with correct jersey numbers
- AND canonical event tagging functions normally

## MODIFIED Requirements

### Requirement: Match analysis requires populated squads
The system MUST only enable canonical event tagging when the match has at least one `MatchSquad` entry per team. (Previously: Assumed squads existed; now verified for backfill-created matches)

#### Scenario: Analysis rejects match with empty squads
- GIVEN a `Match` exists but has no `MatchSquad` entries (should not occur after backfill)
- WHEN the analyst opens `/match/{matchId}/analysis`
- THEN the page shows a clear error: "Plantel no disponible. Resolvé la planilla primero."
- AND event tagging controls are disabled

## Notes
- No code changes to `MatchAnalysis.tsx` or canonical analysis services
- Verification only: backfill must produce `MatchSquad[]` for both sides
- Existing canonical analysis spec (`canonical-live-handball-analysis`) unchanged