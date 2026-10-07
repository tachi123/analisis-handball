# Match Review Workspace

**Status:** Implemented frontend workspace using the existing per-match canonical-analysis API. No backend contract is added by this feature.

## Quick path

1. Open `/match/:matchId/review` as an authenticated analyst.
2. Calibrate the video with explicit period and regulation-time anchors.
3. Use **Mark incident at current position** to create a new canonical event through the per-match POST. Select an existing event only when you need to revise it through PATCH.

## Supported contracts

| Need | Existing contract |
|---|---|
| Match | `GET /api/v1/matches/{matchId}` |
| Analyst session | `GET` / `PUT /api/v1/matches/{matchId}/analysis-session` |
| Canonical events | `GET` / `POST /api/v1/matches/{matchId}/canonical-events` |
| Revision | `PATCH /api/v1/canonical-events/{eventId}` |

The session is scoped to the authenticated analyst and match. The `PUT` request is a checkpoint: it sends the complete session state, including source, angle, position, filters, draft, queue, anchors, and time segments. At desktop width, the review page renders the persisted draft and queue beside playback, with explicit empty-state explanations. There are no session-list, active-session, session-scoped event, reconciliation, export, or offline-sync endpoints for this workspace.

## Video and clock behavior

- The player and timeline synchronize in both directions. Selecting evidence seeks to two seconds before its video anchor; player time highlights the closest anchored event.
- Seeking while paused sends only the provider seek command. The workspace stays paused unless the provider later reports a different observed playback state, and it renders time only from provider delivery.
- A period anchor always requires an explicit regulation match time. There is no automatic match-start default.
- A playable mapping exists only between consecutive anchors in the same period. One anchor is a seek landmark, not clock coverage.
- Events outside valid playable segments display `clock_unverified` and retain an unset regulation time.
- Saving anchors recalibrates only existing events that already have `video_anchor_seconds`, using audited per-event `PATCH` revisions. Each revision sends the complete latest evidence collection (without response IDs): the current backend defaults omitted PATCH evidence to `[]` and returns only latest-revision evidence. Events without video provenance are not assigned a guessed match time.
- When YouTube is unavailable, embedding-disabled, restricted, or reports a player error, analysts can still review and create/revise events using `no_visible` or `ambiguous` evidence without a video anchor. `removed` is not listed by the backend `AvailabilityState` contract and is not claimed as a provider state.
- A runtime provider failure is checkpointed as `source.availability_state` through the same complete per-match session `PUT`; it does not discard review state.
- The review route creates events with the same per-match canonical contract as live capture. A roster-listed player is eligible without a lineup, substitution, or active-goalkeeper record; unavailable context remains explicitly unknown rather than blocking capture.

## Evidence and revision limits

Each canonical event response exposes only its latest revision, its `reason`, and provenance evidence. Video provenance supports `video_source_id`, `video_anchor_seconds`, `reference`, and `uncertainty`.

Marking an incident is an explicit `POST /matches/{matchId}/canonical-events` action at the current player time. The evidence modal is intentionally a PATCH-only flow for an existing event; it never claims to create a new incident or silently turns a create action into a revision.

The backend does **not** persist evidence confidence, visibility, corrected payloads, `revision_of`, or a chronological server history. The workspace therefore does not imply that these fields are saved or render a fabricated diff/history. A future backend contract is required for those capabilities.

## Accessibility

Buttons, text/select controls, modal close actions, timeline revise actions, and radio-label activation areas have 44×44px targets; radio controls retain a conventional-size glyph inside the full-height label. Workspace shortcuts are active only outside editable controls; `n`/`p` navigate events, `a` toggles the visible calibration disclosure, Shift+`n` opens and focuses review notes, and `[`/`]` seek ±10 seconds. `?` opens shortcut help. Escape closes dialogs, and status/error feedback is announced. Canonical undo/redo remains unavailable because the backend has no restore endpoint.
