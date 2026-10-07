# Stage Performance Read Models Specification

## Purpose

Expose stage standings and official player performance from confirmed snapshots.

## Requirements

### Requirement: Calculate standings from confirmed official results
The system MUST calculate standings exclusively from confirmed `OfficialSnapshot` results, MUST exclude byes, and MUST apply configurable points and tiebreak rules.

#### Scenario: Rank a confirmed stage
- GIVEN confirmed non-bye results and configured rules
- WHEN standings are requested
- THEN points and ordering follow those rules only

#### Scenario: Reject a stage without confirmed data
- GIVEN a stage has no confirmed snapshots
- WHEN standings or player averages are requested
- THEN the API returns a defined no-confirmed-data error

### Requirement: Aggregate official player averages
The system MUST provide per-stage player goals, cards, appearances, and their per-match averages exclusively from confirmed snapshots. It MUST NOT create reusable player identities from snapshot facts.

#### Scenario: Calculate a player average
- GIVEN a player has six goals in three confirmed stage appearances
- WHEN player averages are requested
- THEN goals are six, appearances are three, and goals-per-match is two
