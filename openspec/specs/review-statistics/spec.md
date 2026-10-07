# Review Statistics Specification

### Requirement: Calculate denominator-aware reviewed metrics
The system MUST calculate only from active, included, `confirmed` eligible events. Every reported metric MUST expose count, numerator, denominator, excluded, and unknown values; count-only metrics MUST label denominator `not_applicable`, rather than imply an opportunity rate. `no_visible` and `ambiguous` records are unknown; `replay`, inactive, out-of-scope, and explicitly excluded records are excluded. A missing reliable clock remains separately `clock_unverified`.

#### Scenario: Soft-deleted event
- GIVEN an event is inactive or excluded
- WHEN statistics are recalculated
- THEN it contributes to neither numerator nor denominator and remains auditable

#### Scenario: Unknown observation
- GIVEN an otherwise relevant event is `no_visible` or `ambiguous`
- WHEN statistics are recalculated
- THEN it increments unknown and contributes to neither numerator nor denominator

### Requirement: Use only defined MVP denominators
The system MUST calculate shot conversion as confirmed goals divided by confirmed shot outcomes (`goal`, `saved`, `missed`, `woodwork`, or `blocked`), and 7m conversion as confirmed 7m goals divided by confirmed 7m outcomes. Goalkeeper save rate, if displayed, MUST be labelled observed-decision save rate and use confirmed saves divided by confirmed saves plus goals conceded. Confirmed assists, turnovers/possession changes by cause, recoveries, visible defensive actions, fouls/sanctions, and goalkeeper outcomes MUST be count-only. Transition outcome distribution MAY use confirmed transition sequences as its denominator. The system MUST NOT calculate passing accuracy, passing opportunities, possession efficiency, or any denominator not fully supported by the codebook.

#### Scenario: Shot conversion
- GIVEN confirmed eligible shot outcomes include six goals and four non-goals
- WHEN shot conversion is displayed
- THEN numerator is six, denominator is ten, and excluded and unknown values are shown alongside it

#### Scenario: Defensive count
- GIVEN confirmed visible blocks are reported
- WHEN the defensive-action metric is displayed
- THEN its count and `not_applicable` denominator are shown without claiming defensive opportunities

### Requirement: Reconcile official data
The system MUST preserve the official FEMEBAL sheet and its official team/player score and discipline values as immutable reference data. It MUST show analytical confirmed goals and sanctions beside those values and visibly flag every discrepancy with an explanation and supporting evidence. Analytical observations, statistics, reconciliation, and their revisions MUST NOT overwrite or otherwise alter official values. Unknown, excluded, and clock-unverified analytical observations MUST explain analytical coverage without changing the official snapshot.

#### Scenario: Goal discrepancy
- GIVEN reviewed active goals differ from the official score
- WHEN reconciliation is opened
- THEN both values, the discrepancy explanation, and supporting analytical evidence are visible, with no official-data mutation

#### Scenario: Analytical revision remains separate
- GIVEN an analyst revises an event that changes an analytical goal or sanction total
- WHEN reconciliation is refreshed
- THEN the analytical total and discrepancy evidence update while the official FEMEBAL value remains unchanged

### Requirement: Recalculate after an analytical revision
Statistics and package calculations MUST update after event creation, revision, restore, evidence-state change, or exclusion while retaining audit history and the single-analyst MVP scope.

#### Scenario: Restore correction
- GIVEN a previously excluded reviewed event is restored as confirmed and included
- WHEN the analyst refreshes statistics
- THEN only that eligible event changes the applicable count or denominator

### Requirement: Publish the first coach-value package
The system MUST support a reviewed player, unit, or team package for one coaching question. The package MUST include 3-8 approved evidence references, match and source context, a pattern statement, every metric's count/numerator/denominator/excluded/unknown values, official reconciliation, uncertainty disclosure, and exactly one keep/do/change action. Its public form MUST be a curated projection and MUST NOT publish credentials, raw event logs, private notes, unapproved media links, or local database access.

#### Scenario: Package with incomplete visibility
- GIVEN a reviewed question has confirmed and no-visible observations
- WHEN the analyst prepares the package
- THEN the package shows its evidence, unknown count, and one action without presenting unknown observations as confirmed findings

### Requirement: Make the statistics policy testable
The MVP MUST expose whether an event is included, excluded, unknown, or clock-unverified under the defined policy; it MUST NOT infer an authoritative score or percentage from an unspecified rule.

#### Scenario: Policy-defined calculation
- GIVEN active reviewed events are recalculated
- WHEN a metric is displayed
- THEN its declared numerator and denominator follow the codebook while excluded, unknown, and clock-unverified records remain visible

### Requirement: Derive canonical metrics server-side
The server MUST derive authoritative metrics solely from eligible canonical revisions and expose revision evidence links. Clients and reports MUST NOT calculate or submit authoritative metrics. Roster-eligible responsibility MAY support a metric despite unknown lineup context; unknown responsibility, unresolved possession, unavailable goalkeeper, inference-only, and unreviewed legacy records MUST NOT support the affected claim.

#### Scenario: Client metric mismatch
- GIVEN a client total differs from canonical revisions
- WHEN a report metric is requested
- THEN the server-derived total is used

### Requirement: Reconcile official and observed discipline
The system MUST reconcile observed goals, cards, and exclusions with immutable fixture/PDF official score and discipline values, including discrepancy status, unknown coverage, and linked revisions.

#### Scenario: Discipline discrepancy
- GIVEN observed exclusions differ from the official planilla
- WHEN reconciliation is viewed
- THEN both values and linked evidence appear without official mutation
