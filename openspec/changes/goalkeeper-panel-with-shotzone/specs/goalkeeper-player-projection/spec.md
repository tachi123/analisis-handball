# Goalkeeper Player Projection Specification

## Purpose

Provide one authenticated, server-authoritative canonical projection for a selected match player or goalkeeper.

## Requirements

### Requirement: Provide a filtered canonical player projection

The system MUST provide `GET /matches/{match_id}/canonical-player-projection` for a roster-eligible `player_id`, with optional match-team, period, and regulation-time filters. It MUST validate that supplied teams belong to the match and MUST derive the response only from latest active, eligible canonical revisions; it MUST NOT read legacy analysis data or accept client-calculated claims.

#### Scenario: Eligible filtered request

- GIVEN an authenticated analyst selects a roster-eligible player and valid period filter
- WHEN the projection is requested
- THEN the server returns only matching canonical projection claims

#### Scenario: Invalid player or team

- GIVEN the player is not roster-eligible or the supplied team is outside the match
- WHEN the projection is requested
- THEN the server rejects the request without a projection

### Requirement: Attribute goalkeeper outcomes and participation conservatively

The system MUST replay canonical sequence to attribute an opponent `save` or `goal` to a selected goalkeeper only when exactly one observed opposing `goalkeeper_change(active)` applies at that instant. It MUST report unattributable outcomes in `goalkeeper_unknown`. Participation MUST contain only observed `lineup_change` evidence and counts; it MUST NOT claim minutes, starts, exhaustive appearances, or infer an active keeper from lineup changes.

#### Scenario: Observed active goalkeeper

- GIVEN an eligible opponent goal follows one observed active opposing goalkeeper
- WHEN the projection is derived
- THEN the goal is counted as that goalkeeper's conceded goal with its evidence

#### Scenario: Missing active-keeper evidence

- GIVEN no unique observed active opposing goalkeeper applies
- WHEN an opponent save or goal is derived
- THEN it is counted in `goalkeeper_unknown` and not attributed

### Requirement: Disclose coverage, evidence, and unfiltered context

The projection MUST return saves, goals conceded, discipline, observed participation, evidence event/revision IDs, and video anchors. It MUST return IHF zone heatmap buckets for attributed opponent shots: zones 1–9, `missing_zone`, excluded, unknown, `goalkeeper_unknown`, and `clock_unverified`. A regulation-time range MUST apply only to verified-clock events; matching unverified-clock events MUST remain separately disclosed. It MUST also return unfiltered match-level canonical metrics and reconciliation context, clearly distinct from filtered projection results.

#### Scenario: Time-filtered evidence

- GIVEN a time range and an eligible event with `clock_unverified`
- WHEN the projection is requested
- THEN the event and its anchors appear only in the `clock_unverified` bucket

#### Scenario: Missing shot zone

- GIVEN an attributed eligible opponent shot has no `shot_zone`
- WHEN the heatmap is derived
- THEN it increments `missing_zone` without assigning a zone
