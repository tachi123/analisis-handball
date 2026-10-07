# Temporal Evidence Audit Specification

### Requirement: Separate clocks
The system MUST persist video time separately from regulation time, map only through configured period-aware anchors and segments, never wall time, and state mapping uncertainty. Regulation time MUST default to two 30-minute periods. The system MUST support pauses, broadcast delays, cuts, replays, small second-level offsets, halftime, overtime, and non-play ranges. It MUST display both clocks where a mapping exists and mark unmapped evidence `clock_unverified`; it MUST NOT reject or alter an otherwise valid observation solely because it differs from a rigid continuous clock.

#### Scenario: Anchored event
- GIVEN an active segment with reliable anchors
- WHEN an event is tagged at a video time
- THEN a calculated match clock is shown and persisted for that segment

#### Scenario: Unmapped event
- GIVEN no reliable mapping covers the selected video time
- WHEN evidence is saved
- THEN match time is unverified rather than guessed

#### Scenario: Broadcast offset
- GIVEN a valid observation falls after a broadcast delay or cut within a period
- WHEN its video time differs by seconds from a continuous regulation clock
- THEN the observation is retained with its period-aware mapping or stated uncertainty rather than rejected or rewritten

### Requirement: Apply the observable MVP codebook
Each analytical observation MUST retain the versioned codebook entry and only represent: shot/outcome or 7m; confirmed assist; turnover or possession change with a visible cause; recovery; clearly visible defensive action; foul/sanction; transition outcome; or goalkeeper outcome. A turnover/possession-change cause MUST be one of `bad_control`, `bad_pass`, `interception`, `steal`, `offensive_foul`, `technical_violation`, `out_of_play`, `other_visible`, or `ambiguous`. The codebook MUST NOT define passing accuracy, passing opportunities, or a pass-rate denominator.

#### Scenario: Visible turnover cause
- GIVEN possession changes after a visible interception
- WHEN the analyst records the turnover
- THEN the observation stores `interception` as its cause without inferring pass attempts

#### Scenario: Unsupported passing claim
- GIVEN the analyst is reviewing a sequence of passes
- WHEN no complete attempt, receiver, and outcome protocol exists
- THEN the observation cannot be used to claim passing accuracy or opportunities

### Requirement: Capture evidence state and uncertainty
Each event MUST retain source/angle, video timestamp when available, analyst, note, review state, and one evidence state: `confirmed`, `no_visible`, `ambiguous`, or `replay`. `confirmed` requires the coded fact to be visible enough for the codebook definition. `no_visible` means the relevant action is outside or obscured by the view; `ambiguous` means competing interpretations remain; `replay` identifies repeated footage of an already observed sequence. The last three states MUST remain valid and auditable.

#### Scenario: Occluded action
- GIVEN the action cannot be fully seen
- WHEN the analyst saves a tag
- THEN the event remains valid with evidence state `no_visible` and its uncertainty is reviewable

#### Scenario: Repeated footage
- GIVEN a broadcast replay shows an already recorded action
- WHEN the analyst marks the footage
- THEN the observation is retained as `replay` and is not a second analytical occurrence

### Requirement: Preserve revisions
The system MUST support event edit, soft-delete, restore, and revision. Audit records MUST include actor, timestamp, before/after payload, and reason. Undo MUST target the selected event/revision, never insertion order. Official records MUST remain separate.

#### Scenario: Correction
- GIVEN an active event is selected
- WHEN an authorized analyst corrects it with a reason
- THEN the prior revision remains immutable and the new revision becomes active

### Requirement: Keep MVP identity scope explicit
The MVP MUST attribute evidence, revisions, anchors, and audit records to the single analyst using the existing authentication prerequisite. It MUST NOT claim multi-user isolation or introduce new authorization behavior; user management and collaboration are deferred.

#### Scenario: Single-analyst attribution
- GIVEN the analyst is authenticated by the existing app
- WHEN evidence or a correction is saved
- THEN the record is attributed to that analyst and no new permission workflow is required

### Requirement: Link evidence to canonical revisions
Evidence MUST identify its exact canonical event revision, fact/inference classification, and uncertainty. Fixture/PDF and video references, when available, MUST remain linked; absence MUST be explicit. Evidence MUST NOT overwrite official snapshots or resolve unknowns without reviewed observation.

#### Scenario: Revision-specific correction
- GIVEN a revision replaces an observation
- WHEN evidence is reviewed
- THEN each revision exposes its own evidence and provenance
