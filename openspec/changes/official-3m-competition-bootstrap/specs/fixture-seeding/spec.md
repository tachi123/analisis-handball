# Delta for Fixture Seeding

## ADDED Requirements

### Requirement: Bootstrap 3ªM stages idempotently
The system MUST idempotently seed approved 2026 3ªM `Apertura Zona A` and `Torneo Permanencia`. Re-running unchanged approved evidence MUST not duplicate stages, CompetitionTeams, or registrations, or share them between stages.

#### Scenario: Re-run approved bootstrap
- GIVEN bootstrap completed for matching approved evidence
- WHEN it runs again
- THEN the existing 3ªM records are retained without duplicates

#### Scenario: Keep stage registrations separate
- GIVEN an exact club label is mapped in both target stages
- WHEN both stages are provisioned
- THEN each stage has a distinct CompetitionTeam and registration
