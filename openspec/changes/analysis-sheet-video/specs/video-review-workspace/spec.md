# Delta for Video Review Workspace

## MODIFIED Requirements

### Requirement: Provide a dedicated video review workspace

The system MUST provide one protected browser workspace in the existing SPA for one analyst using the existing authentication prerequisite. `MatchAnalysis` remains the canonical capture UI and MUST provide an entry to `/match/:matchId/review`; the review route is its dedicated video-review complement and does not provide a route-level live/video mode switch. The review route MUST use the same analytical record and codebook. For a match with no saved source, it MUST clearly offer source setup before playback and retain review actions if playback is unavailable. At >=1024px it MUST present playback, event entry, timeline/review, and the persisted draft and queue together; smaller widths MAY stack them without losing core actions. The MVP MUST NOT require multi-user management or collaboration.

(Previously: Analysis did not require a review entry point or explicit first-time source setup.)

#### Scenario: Open dedicated review workspace

- GIVEN a prepared match and an authenticated analyst
- WHEN the analyst opens `/match/:matchId/review`
- THEN the protected route presents the dedicated review workspace
- AND it uses the same event types, evidence states, and official match context as canonical capture

#### Scenario: Enter review from analysis

- GIVEN an authenticated analyst is viewing a match in canonical analysis
- WHEN the analyst selects the video-review action
- THEN the app opens that match's dedicated review workspace
- AND canonical capture does not embed a second player or URL workflow

#### Scenario: Set up a first source

- GIVEN an authenticated analyst opens review for a match with no saved video source
- WHEN the workspace loads
- THEN it clearly offers source setup before playback
- AND review actions remain available if playback cannot start

#### Scenario: Desktop review

- GIVEN an authorized video review session at 1024px or wider
- WHEN the workspace loads
- THEN the analyst can view playback, the persisted draft, and the persisted review queue together
- AND empty draft and queue values have useful empty-state explanations
