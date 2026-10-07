# Canonical Live Handball Analysis Specification

## Purpose
Define the evidence-backed match record for analytical state, metrics, and reports.

## Requirements

### Requirement: Record revisioned observed facts
The system MUST create versioned canonical events with match, period, observed time or `clock_unverified`, type, responsibility or `unknown`, outcome, uncertainty, analyst, provenance, and fixture/PDF or video evidence links. Revisions MUST retain prior payload, actor, time, reason, and their evidence links. The system MUST distinguish observed fact from inference and MUST NOT fabricate either certainty or evidence.

#### Scenario: Missing source detail
- GIVEN an observation has no supporting source detail
- WHEN it is saved
- THEN its evidence context is explicitly unknown

### Requirement: Derive only observed state
The system MUST derive analytical score, discipline, and possession from ordered canonical transitions. Possessions MUST identify owner, start, and terminal basis or remain unresolved. The system MUST NOT invent possession, recovery, substitution, goalkeeper, lineup, or rule consequences.

#### Scenario: Lost sequence
- GIVEN play is no longer visible before the next owner
- WHEN the sequence is recorded
- THEN possession remains unresolved without a claimed recovery

### Requirement: Accept roster-eligible responsibility
The system MUST accept a visible live event for any player documented on that match's official roster/planilla. It MUST NOT require an inferred/exhaustive on-court lineup, substitutions, or active goalkeeper as a gate. Those facts MAY be recorded when observed and MUST remain optional context. Unknown goalkeeper attribution MUST remain team-level unknown.

#### Scenario: Roster player without lineup context
- GIVEN a player is on the official planilla and lineup context is unknown
- WHEN the analyst records that player as responsible
- THEN the event is accepted with explicit unknown context

### Requirement: Reconcile and cut over safely
The system MUST show observed goals, cards, and exclusions beside immutable fixture/PDF official values, with discrepancy evidence linked to canonical revisions. Legacy rows MUST remain readable and excluded until reviewed. Canonical mode MUST reject legacy writes; rollback MAY provide read-only legacy fallback without deleting canonical or official records.

#### Scenario: Canonical cutover
- GIVEN canonical mode is active for a match
- WHEN a legacy writer submits analysis data
- THEN it is rejected while history remains readable

### Requirement: Verify canonical invariants
The system MUST have automated tests for roster eligibility, optional context, explicit unknowns, revision evidence, server metrics, reports, reconciliation, and cutover fallback.

#### Scenario: Invariant regression
- GIVEN relevant behavior changes
- WHEN automated verification runs
- THEN a violation of those invariants fails verification
