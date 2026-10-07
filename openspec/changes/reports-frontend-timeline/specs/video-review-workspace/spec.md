# Delta for Video Review Workspace

## MODIFIED Requirements

### Requirement: Provide a dedicated video review workspace
The system MUST provide one protected browser workspace in the existing SPA for one analyst using the existing authentication prerequisite. `MatchAnalysis` remains the canonical capture UI; `/match/:matchId/review` is its dedicated video-review complement and does not provide a route-level live/video mode switch. A separate protected, match-scoped reports timeline route MAY present canonical observations read-only; it MUST NOT replace or add mutation controls to the review workspace. The review route MUST use the same analytical record and codebook. At >=1024px it MUST present playback, event entry, timeline/review, and the persisted draft and queue together; smaller widths MAY stack them without losing core actions. The MVP MUST NOT require multi-user management or collaboration.

(Previously: The protected review route was the only dedicated complement to canonical capture.)

#### Scenario: Open dedicated review workspace
- GIVEN a prepared match and an authenticated analyst
- WHEN the analyst opens `/match/:matchId/review`
- THEN the protected route presents the dedicated review workspace
- AND it uses the same event types, evidence states, and official match context as canonical capture

#### Scenario: Desktop review
- GIVEN an authorized video review session at 1024px or wider
- WHEN the workspace loads
- THEN the analyst can view playback, the persisted draft, and the persisted review queue together
- AND empty draft and queue values have useful empty-state explanations

#### Scenario: Keep reporting separate from editing
- GIVEN an authenticated analyst opens the match reports timeline
- WHEN canonical observations are rendered
- THEN no capture or revision control is available
- AND the review workspace remains the editing surface
