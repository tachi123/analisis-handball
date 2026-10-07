# Delta for Review Statistics

## ADDED Requirements

### Requirement: Disclose canonical evidence for a warning comparison

The reconciliation view MUST provide an inline, read-only disclosure for each warning comparison with linked canonical events. The disclosure control MUST be a native button with a unique `aria-controls` target and accurate `aria-expanded` state. On first expansion, the system MUST load canonical events only as needed and MUST display only events whose identifiers occur in that comparison's `canonical_event_ids`. The detail MUST show the immutable official total only and MUST NOT show or infer official timestamps. A comparison without linked event identifiers MUST clearly state that no canonical events are linked and MUST NOT expose a non-functional disclosure control.

#### Scenario: Expand and collapse a linked comparison
- GIVEN a warning comparison has linked canonical event identifiers
- WHEN the analyst activates its disclosure button
- THEN an inline detail for that comparison is shown with the official total and only its linked events
- AND activating the button again hides the detail

#### Scenario: Comparison without linked events
- GIVEN a warning comparison has no canonical event identifiers
- WHEN the reconciliation view is displayed
- THEN it states that no canonical events are linked
- AND it does not offer a disclosure control that cannot reveal detail

#### Scenario: Use the disclosure from a keyboard
- GIVEN a linked comparison disclosure button has keyboard focus
- WHEN the analyst presses Enter or Space
- THEN the native button expands or collapses the same detail as pointer activation

#### Scenario: Associate the control and detail accessibly
- GIVEN a linked comparison is rendered
- WHEN its disclosure button is inspected before and after expansion
- THEN `aria-controls` references the unique inline detail target
- AND `aria-expanded` reflects whether that target is visible

### Requirement: Present and seek linked canonical-event evidence

Every disclosed canonical event MUST show its player, kind, period, regulation time, `clock_unverified` state, video time, and evidence type. A video-anchored event MAY offer a read-only seek action through the established `seekTargetForEvent` and `useYouTubeSync` path; it MUST seek only when a usable video anchor and ready player are available. PDF, unavailable, and non-video evidence MUST remain readable and MUST NOT trigger a seek. The disclosure MUST NOT offer revision, resolution, or official-data mutation actions.

#### Scenario: Seek a video-anchored event
- GIVEN a disclosed event has video evidence and the video player is ready
- WHEN the analyst activates its seek action
- THEN the established video synchronization flow seeks to that event's video time
- AND the displayed event fields remain read-only

#### Scenario: Display PDF or unavailable evidence
- GIVEN a disclosed event has PDF, unavailable, or non-video evidence
- WHEN the analyst views the event
- THEN its evidence type and all required event fields remain readable
- AND no video seek action is performed for unavailable video evidence
