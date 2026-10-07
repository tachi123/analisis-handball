# Video Review Workspace Specification

### Requirement: Provide a dedicated video review workspace
The system MUST provide one protected browser workspace in the existing SPA for one analyst using the existing authentication prerequisite. `MatchAnalysis` remains the canonical capture UI; `/match/:matchId/review` is its dedicated video-review complement and does not provide a route-level live/video mode switch. The review route MUST use the same analytical record and codebook. At >=1024px it MUST present playback, event entry, timeline/review, and the persisted draft and queue together; smaller widths MAY stack them without losing core actions. The MVP MUST NOT require multi-user management or collaboration.

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

### Requirement: Limit manual capture to observable MVP events
The workspace MUST offer only the approved observable codebook: shots/outcomes and 7m; confirmed assists; turnover or possession change with visible cause; recovery; clearly visible defensive action; foul/sanction; transition outcome; goalkeeper outcome; and evidence state. It MUST NOT present passing accuracy or passing-opportunity capture.

#### Scenario: Ambiguous observation
- GIVEN the analyst cannot establish an event or responsible player from the available view
- WHEN the analyst records the observation
- THEN `ambiguous` or `no_visible` is available without requiring invented detail

### Requirement: Reflect supported player state
The player integration MUST expose supported playback, seek, observed time, availability, and errors through the provider boundary. The workspace MUST reflect asynchronous outcomes and MUST NOT assume commands succeeded. When the provider is unavailable, embedding-disabled, restricted, or reports a player error, playback MAY be absent while review, persisted-state inspection, and no-playback evidence entry remain available.

#### Scenario: Seek while paused
- GIVEN paused playback at a known video time
- WHEN the analyst seeks
- THEN the workspace sends only the provider `seekTo` command and does not issue a playback command
- AND playback remains paused until an observed provider state message says otherwise
- AND the displayed video time updates only from observed player state

### Requirement: Support accessible keyboard operation
The system MUST provide names, tooltips, focus order/visibility, and shortcut help. Guarded commands MUST cover playback, seek +/-1/5/10 seconds, event navigation, anchor, tag, save, notes, undo/redo, and help; shortcuts MUST NOT capture typing or browser/assistive-technology commands.

#### Scenario: Text entry
- GIVEN focus is in a note or editable field
- WHEN a shortcut key is pressed
- THEN the key is entered as text and no workspace command runs

### Requirement: Resume work
The system MUST checkpoint session/source/angle, video position, anchors, filters, drafts, and queue through the existing per-match session endpoint, and resume supported state after reload even when playback is unavailable.

#### Scenario: Reload during outage
- GIVEN saved review data and an unavailable provider
- WHEN the analyst reloads
- THEN the source, angle, video position, anchors, filters, draft, and queue are restored through the per-match session endpoint
- AND the persisted draft and queue remain visible for analyst inspection
- AND no-playback entry remains possible

### Requirement: Capture roster-eligible events in both modes
Live and video MUST use the same canonical events and accept visible events for official-roster players without lineup, substitution, or active-goalkeeper context. Observed context MAY be shown; unknowns MUST be explicit and MUST NOT block capture.

#### Scenario: Unknown lineup context
- GIVEN a roster-listed player has no reliable lineup timeline
- WHEN an event is saved
- THEN it is accepted through the same per-match canonical-event contract
- AND no lineup, substitution, or active-goalkeeper event is required as a capture gate
- AND the response identifies the accepted roster provenance while goalkeeper context remains unknown
