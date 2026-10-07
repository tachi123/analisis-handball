# Match Review Workspace Specification

## Purpose

Unified video review page providing bidirectional playback↔timeline synchronization, incident tagging from current video position, explicit anchor/match-start mapping with `clock_unverified` visibility, player-unavailability handling, supported canonical revisions, and accessible keyboard/mouse controls — all aligned to existing per-match API contracts.

## Requirements

### Requirement: Bidirectional playback and timeline synchronization

The system MUST synchronize the YouTube player and event timeline bidirectionally: timeline click seeks player to `video_time - 2s`; player `timeupdate` highlights the current event in the timeline; period change auto-seeks to the corresponding anchor.

#### Scenario: Timeline click seeks player
- GIVEN a loaded match review session with events and anchors
- WHEN the analyst clicks an event in the timeline
- THEN the player seeks to `event.video_time - 2` seconds
- AND the timeline highlights the clicked event

#### Scenario: Player timeupdate highlights timeline event
- GIVEN the player is playing
- WHEN the player emits `timeupdate` at a video time
- THEN the timeline highlights the event whose `video_time` is closest to the current video time
- AND auto-scroll keeps the highlighted event visible

#### Scenario: Period change seeks to anchor
- GIVEN the analyst selects a different period
- WHEN the period selection changes
- THEN the player seeks to the anchor's `video_time` for that period

### Requirement: Incident tagging from current video position

The system MUST allow the analyst to tag an incident at the current video position, creating a `CanonicalEvidence` linked to the event with `video_source_id` and `video_anchor_seconds` derived from the player's current time.

#### Scenario: Create incident at current position
- GIVEN the analyst pauses at a video position showing an incident
- WHEN the analyst chooses "Mark incident at current position"
- THEN the workspace creates a new canonical event through `POST /matches/{match_id}/canonical-events`
- AND the new event includes `CanonicalEvidence` with `video_source_id` from the session and `video_anchor_seconds` equal to the player's current time
- AND the supported evidence state, note, and provenance are persisted

The evidence modal is deliberately an existing-event revision flow: it creates a replacement revision through `PATCH /canonical-events/{event_id}` and is not presented as the creation path for a new incident.

#### Scenario: Create incident without playable video
- GIVEN the video source is unavailable (`no_visible` or `ambiguous`)
- WHEN the analyst tags an incident
- THEN the evidence is saved with `no_visible` or `ambiguous` state
- AND `video_anchor_seconds` is null
- AND the event remains analyzable

### Requirement: Anchor and match-start mapping with clock_unverified visibility

The system MUST provide an anchors editor to create, edit, delete, and calibrate time anchors mapping video time to regulation match time, and MUST surface `clock_unverified` on events lacking playable segment coverage.

#### Scenario: Create anchor from current position
- GIVEN the analyst is viewing a specific period
- WHEN the analyst adds an anchor and clicks "Set from current position"
- THEN the anchor's `video_time` is set to the player's current time
- AND the analyst explicitly enters the anchor's regulation match time
- AND events in that period with persisted video provenance are recalibrated through their supported per-event `PATCH` contract

#### Scenario: Edit anchor recalculates mappings
- GIVEN existing anchors for a period
- WHEN the analyst modifies an anchor's `video_time` or `match_time`
- THEN events in that period with persisted `video_anchor_seconds` recalculate their canonical `regulation_seconds` via linear interpolation between anchors
- AND those events without anchor coverage are revised with `clock_unverified: true`
- AND each replacement revision includes the complete latest supported evidence collection, excluding response-only evidence IDs, because the current PATCH contract treats omitted evidence as an empty collection
- AND events without video provenance are not assigned a fabricated mapped time

#### Scenario: clock_unverified badge visibility
- GIVEN an event whose `mapped_match_time` falls outside any anchor pair
- WHEN the timeline renders
- THEN the event displays a `clock_unverified` badge
- AND the badge is visible in both timeline and evidence modal

### Requirement: Player unavailability behavior

The system MUST support full evidence tagging and review workflows when the YouTube player is unavailable, using the same evidence-state policy (`no_visible`/`ambiguous`) as the unified analysis record.

#### Scenario: No-playback evidence entry
- GIVEN the video source state is `unavailable`, `embedding-disabled`, `restricted`, or `player_error`
- WHEN the analyst opens the review workspace
- THEN the player displays an unavailable-state UI with retry/replace actions
- AND the timeline, anchors editor, evidence modal, and revision history remain fully functional
- AND new evidence uses `no_visible` or `ambiguous` state

#### Scenario: Runtime player failure
- GIVEN the player was ready and fails during review
- WHEN the failure is reported
- THEN the player state updates to reflect the error
- AND the supported session `source.availability_state` checkpoint reflects the failure
- AND all review functionality remains available
- AND no session data is lost

### Requirement: Canonical evidence revision with four states

The system MUST support revising events through an evidence modal offering four states (`confirmed`, `no_visible`, `ambiguous`, `replay`), a reason/note, and supported video provenance.

#### Scenario: Revise event evidence
- GIVEN an event in the timeline
- WHEN the analyst opens the evidence modal, selects a state, adds a reason, and saves
- THEN a new canonical event revision is created through its per-event `PATCH` contract
- AND the timeline updates to show the revised event as the current version

### Requirement: State unsupported history limits

The system MUST show the latest supported revision reason and evidence and MUST explain that chronological history, visual diffs, evidence confidence/visibility, corrected payloads, and `revision_of` are deferred until backend support exists.

#### Scenario: View revision limits
- GIVEN an event in the review workspace
- WHEN the analyst opens revision details
- THEN the latest supported reason and provenance are shown
- AND the deferred server-history limitation is visible

### Requirement: Accessible keyboard and mouse controls

The system MUST provide guarded keyboard shortcuts for playback, seek (±1/5/10s), event navigation, anchor, tag, save, notes, undo/redo, and help; shortcuts MUST NOT capture typing or browser/assistive-technology commands. Workspace buttons, text/select controls, and radio-label activation areas MUST meet ≥44×44px.

#### Scenario: Shortcut guard during text entry
- GIVEN focus is in a note textarea or editable field
- WHEN a shortcut key (e.g., Space, `,`, `.`, `j`, `l`, `[`, `]`, `a`, `t`, `s`, `n`, `u`, `r`, `?`) is pressed
- THEN the character is entered as text
- AND no workspace command executes

#### Scenario: Playback shortcuts
- GIVEN focus is not in an editable field
- WHEN Space is pressed
- THEN playback toggles play/pause

#### Scenario: Seek shortcuts
- GIVEN focus is not in an editable field
- WHEN `,` is pressed
- THEN player seeks -1 second
- WHEN `.` is pressed
- THEN player seeks +1 second
- WHEN `j` is pressed
- THEN player seeks -5 seconds
- WHEN `l` is pressed
- THEN player seeks +5 seconds
- WHEN `[` is pressed
- THEN player seeks -10 seconds
- WHEN `]` is pressed
- THEN player seeks +10 seconds

#### Scenario: Event navigation shortcuts
- GIVEN focus is not in an editable field
- WHEN `n` is pressed
- THEN timeline highlights next event
- WHEN `p` is pressed
- THEN timeline highlights previous event

#### Scenario: Action shortcuts
- GIVEN focus is not in an editable field
- WHEN `a` is pressed
- THEN anchors editor opens/closes through its visible calibration disclosure
- WHEN `t` is pressed
- THEN evidence modal opens for highlighted event
- WHEN `s` is pressed
- THEN current draft/revision saves
- WHEN `u` or `r` is pressed
- THEN the workspace explains that canonical undo/redo is unavailable until the backend exposes a restore contract
- WHEN `?` is pressed
- THEN shortcut help overlay opens

#### Scenario: Mouse target sizes
- GIVEN any interactive element in the workspace
- WHEN rendered
- THEN buttons, text/select controls, and radio-label activation areas expose a ≥44×44px touch target; the native radio glyph MAY remain visually smaller inside its labelled target
