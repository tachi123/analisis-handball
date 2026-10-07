# Delta for Review Statistics

## ADDED Requirements

### Requirement: Derive goalkeeper and zone coverage server-side

The server MUST derive goalkeeper saves, goals conceded, observed-decision save rate when its denominator is supported, discipline, and IHF zone coverage solely from latest active, included, confirmed eligible canonical revisions. It MUST expose counts, numerator/denominator where defined, excluded, unknown, missing-zone, goalkeeper-unknown, and clock-unverified coverage with revision evidence links. Clients and reports MUST NOT calculate or submit these authoritative values.

#### Scenario: Defined goalkeeper rate

- GIVEN two attributed confirmed saves and one attributed confirmed goal
- WHEN the goalkeeper metric is returned
- THEN observed-decision save rate has numerator two and denominator three

#### Scenario: Unknown attribution

- GIVEN an eligible goal has no uniquely observed active goalkeeper
- WHEN statistics are derived
- THEN it is disclosed as `goalkeeper_unknown`, not as conceded by a player

### Requirement: Preserve canonical reconciliation context in projections

The system MUST provide immutable official and unfiltered match-level canonical metrics and reconciliation context alongside a filtered player projection. It MUST distinguish that context from filtered results and MUST NOT alter official values or derive it from legacy rows.

#### Scenario: Filtered player view

- GIVEN a goalkeeper projection is filtered to one period
- WHEN reconciliation context is returned
- THEN the response labels match-level canonical and official context as unfiltered
