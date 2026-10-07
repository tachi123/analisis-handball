# Warnings Summary Specification

## Purpose

Expose a read-only, match-scoped comparison of eligible canonical analysis against immutable official player and match totals, with traceable evidence and explicit limits.

## Requirements

### Requirement: Derive authoritative warnings totals

The system MUST provide an authenticated, canonical-cutover-gated warnings summary for a match. It MUST derive per-player and match totals for goals, yellow cards, two-minute exclusions, red cards, and blue cards solely from active, observed, confirmed canonical events and the immutable official snapshot. Clients MUST NOT calculate authoritative totals.

#### Scenario: Eligible player total

- GIVEN an eligible canonical player has recorded goals or sanctions and an official player record
- WHEN the warnings summary is requested
- THEN it returns that player's canonical and official totals for every supported metric
- AND it returns the match totals from the same sources

#### Scenario: Ineligible canonical event

- GIVEN a canonical event is inactive, unobserved, or unconfirmed
- WHEN the warnings summary is derived
- THEN that event does not affect any canonical total

### Requirement: Classify comparison limits and discrepancies

For each supported total, the system MUST return exactly one status: `exact`, `within_tolerance`, `missing_in_canonical`, `missing_in_official`, or `not_comparable`. `exact` SHALL represent equal comparable values; `within_tolerance` SHALL represent a non-identical value accepted by the declared metric policy. The summary MUST report goal/card timestamps and goalkeeper substitutions as `not_comparable` when immutable official data lacks the required detail, rather than infer a mismatch or tolerance result.

#### Scenario: Equal totals

- GIVEN canonical and official values for a player metric are equal
- WHEN the summary is requested
- THEN that comparison has status `exact`

#### Scenario: Unavailable temporal or substitution detail

- GIVEN the official snapshot has no timestamp or goalkeeper-substitution record
- WHEN those checks are included in the summary
- THEN each check has status `not_comparable` and an availability explanation

#### Scenario: Absent player counterpart

- GIVEN a player exists on only one comparison source
- WHEN the summary is requested
- THEN the relevant comparison is `missing_in_canonical` or `missing_in_official` without identity guessing

### Requirement: Preserve evidence and official immutability

Every canonical-backed player or match comparison MUST expose its contributing canonical event IDs and evidence IDs. The system MUST preserve official values as read-only reference data and MUST NOT offer resolution, synchronization, audit, or revision actions through this capability.

#### Scenario: Trace a discrepancy

- GIVEN a returned total is not `exact`
- WHEN a consumer reads its evidence references
- THEN it can identify the contributing canonical events and evidence without modifying either source

### Requirement: Present accessible read-only warnings

The StatisticsPage MUST render the match-context warnings summary as aggregated player rows and match totals. Each status MUST have semantic text, an icon, a non-color visual distinction, and an accessible name or description. Evidence-bearing rows MUST be keyboard operable with Enter and Space and MUST expose a read-only drill-down.

#### Scenario: Keyboard evidence drill-down

- GIVEN a focused row with canonical evidence
- WHEN the user presses Enter or Space
- THEN the drill-down opens or selects the linked event without a mutation action
- AND focus and status context remain available to assistive technology

#### Scenario: Navigate linked evidence

- GIVEN a user activates a warning row
- WHEN linked canonical evidence is available
- THEN the UI MUST reuse `ReportEventTimeline`, `timelineInteractions`, and `mapVideoTime` to select the event and navigate to its video or PDF evidence
- AND unavailable media is communicated without offering resolution, sync, or audit controls
