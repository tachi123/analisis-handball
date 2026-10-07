# Delta for Canonical Live Handball Analysis

## MODIFIED Requirements

### Requirement: Record revisioned observed facts

The system MUST create versioned canonical events with match, period, observed time or `clock_unverified`, type, responsibility or `unknown`, outcome, uncertainty, analyst, provenance, and fixture/PDF or video evidence links. A canonical `shot` MAY include nullable numeric `shot_zone` values 1 through 9; omitted or `null` is valid. The system MUST reject `shot_zone` on every non-`shot` event and values outside integer 1–9. Revisions MUST retain prior payload, actor, time, reason, and their evidence links, including an existing `shot_zone` unless the revision explicitly changes it. Historic unzoned events MUST remain valid; the system MUST NOT backfill or mutate them. The system MUST distinguish observed fact from inference and MUST NOT fabricate either certainty or evidence.

(Previously: Canonical facts and revisions had no optional shot-zone contract.)

#### Scenario: Missing source detail

- GIVEN an observation has no supporting source detail
- WHEN it is saved
- THEN its evidence context is explicitly unknown

#### Scenario: Valid optional shot zone

- GIVEN a canonical `shot` command includes numeric zone 7
- WHEN it is created or revised
- THEN the revision payload preserves zone 7

#### Scenario: Invalid or historic zone payload

- GIVEN a non-shot includes `shot_zone`, a shot uses 0 or 10, or a historic shot omits it
- WHEN the payload is validated
- THEN invalid use is rejected and the historic unzoned shot remains readable
