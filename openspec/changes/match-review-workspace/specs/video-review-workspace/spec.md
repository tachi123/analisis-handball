# Delta for Video Review Workspace

## ADDED Requirements

### Requirement: Align to per-match API contracts and CanonicalEvidence linkage

The system MUST use existing per-match canonical analysis endpoints and MUST link `CanonicalEvidence` to `video_source_id` and `video_anchor_seconds` for video↔regulation time mapping.
(Previously: spec referenced session-scoped endpoints and did not specify evidence linkage)

#### Scenario: Load session via per-match endpoint
- GIVEN a match ID and authenticated analyst
- WHEN the workspace loads
- THEN it calls `GET /api/v1/matches/{match_id}/analysis-session`
- AND checkpoints the complete analyst-owned session through `PUT /api/v1/matches/{match_id}/analysis-session`

#### Scenario: Evidence links to video source
- GIVEN the analyst marks a new incident at the current player time
- WHEN the workspace creates the event through `POST /matches/{match_id}/canonical-events`
- THEN the command includes `video_source_id` from the session's video source
- AND includes `video_anchor_seconds` from the player's current time only when video is playable

The evidence modal revises an existing event through `PATCH /canonical-events/{event_id}`; it is not a disguised event-creation flow.

#### Scenario: Map video time to regulation time
- GIVEN an event with `video_anchor_seconds` and session anchors
- WHEN the system calculates `mapped_match_time`
- THEN it uses the existing `mapVideoTime` utility with the session's anchors
- AND returns `clock_unverified: true` when the video time falls outside anchor coverage

#### Scenario: Seek while paused
- GIVEN the provider has reported paused playback
- WHEN the analyst seeks from the workspace
- THEN the provider boundary sends only `seekTo` and does not send a playback command
- AND the workspace remains paused until a later provider state message changes it
- AND displayed time changes only after observed provider delivery

## MODIFIED Requirements

### Requirement: Provide one unified Match Analysis workspace

The system MUST provide one browser workspace in the existing SPA for one analyst using the existing authentication prerequisite. Video mode MUST add playback, timeline, and review using per-match API contracts and `CanonicalEvidence` linkage without changing the analytical record or codebook. At >=1024px video mode MUST present playback, event entry, and timeline/review panels; smaller widths MAY stack them without losing core actions. The MVP MUST NOT require multi-user management or collaboration.
(Previously: referenced session-scoped endpoints and did not mention per-match contracts or evidence linkage)

#### Scenario: Open the dedicated review workspace
- GIVEN a prepared match and an authenticated analyst
- WHEN the analyst opens the protected review route
- THEN the workspace uses the same canonical event types, evidence states, and official match context
- AND it uses per-match endpoints for session management

The workspace does not own a live/video mode switch: `MatchAnalysis` remains the canonical capture UI and the review route is its dedicated video-review complement. A switch scenario here would claim a route-level behavior this feature does not provide.

#### Scenario: Desktop review
- GIVEN an authorized video review session at 1024px or wider
- WHEN the workspace loads
- THEN the analyst can view playback, the persisted session draft, and the persisted review queue together
- AND an empty draft or queue presents an explanation rather than an empty panel
- AND evidence revisions link to `video_source_id` and `video_anchor_seconds`

### Requirement: Resume work

The system MUST checkpoint session/source/angle, video position, anchors, filters, drafts, and queue through the per-match session endpoint, and resume supported state after reload even when playback is unavailable.
(Previously: did not specify per-match endpoint persistence)

#### Scenario: Reload during outage
- GIVEN saved review data and an unavailable provider
- WHEN the analyst reloads
- THEN the source, angle, video position, anchors, filters, draft, and queue are restored via `GET /api/v1/matches/{match_id}/analysis-session`
- AND the persisted draft and queue are exposed for analyst inspection
- AND no-playback entry remains possible using `no_visible`/`ambiguous` evidence states

## REMOVED Requirements

### Requirement: Session-scoped facade endpoints
(Reason: Backend intentionally uses per-match contracts; session-scoped endpoints `/api/v1/canonical-analysis/sessions/{id}/*` are not implemented and will not be added)
