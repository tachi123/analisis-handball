# Design: Match Review Workspace

Build a protected, per-match React workspace on the existing canonical-analysis contracts. It adds no backend endpoint, schema, or mobile-specific API; documentation is corrected before UI work so implementation cannot target the obsolete session-scoped URLs.

## Quick path

1. Load the match, its analyst-owned analysis session, and canonical events in parallel.
2. Keep player state local; checkpoint the complete session through its existing per-match `PUT` contract.
3. Derive review display data from the latest event revision and its video evidence; refresh canonical queries after a save.

## Technical Approach

`MatchReview` is a new route/page that composes the player hook, timeline, anchor editor, evidence editor, and local UI state. TanStack Query owns server data; the page owns selection, dialogs, and player time. The existing `MatchAnalysis` remains the canonical capture UI rather than being duplicated.

| Decision | Choice and rationale |
|---|---|
| Backend boundary | Use only `GET/PUT /api/v1/matches/{matchId}/analysis-session`, `GET/POST /matches/{matchId}/canonical-events`, and `PATCH /canonical-events/{eventId}`. These are intentional per-match contracts. |
| Player boundary | `useYouTubeSync` wraps the iframe postMessage lifecycle and exposes time/playback/seek commands; components never address the iframe directly. Seeking emits only `seekTo`, while playback state and displayed time remain provider-observed. This isolates provider failures. |
| Mapping boundary | Persist `anchors` and `time_segments` together in the session. Derive a playable segment only between consecutive, same-period anchors, then use existing `mapVideoTime`; never extrapolate. |
| Event truth | A timeline row is derived from the latest canonical event payload plus its latest revision's video evidence. The server sequence remains ordering authority. |

## Data Flow

```text
MatchReview
  ├─ queries: Match + AnalysisSession + CanonicalEvents
  ├─ useYouTubeSync(source) ── time/state ──> selected timeline row
  ├─ EventTimeline ── seek(videoEvidence.anchor - 2) ──> player
  ├─ AnchorsEditor ── anchors + derived segments ──> PUT analysis-session
  └─ EvidenceModal ── full CanonicalEventRevisionInput ──> PATCH event
                                                   └─ invalidate events/state/session
```

On a player time update, choose the closest event with video evidence for highlighting and keep it visible without moving focus. A period change seeks the selected period's earliest anchor. At desktop width, render playback beside a persisted-state panel that exposes `draft` and `queue` with explicit empty states, so resumable work is inspectable rather than merely retained in a checkpoint. On checkpoint, retain session fields not edited by the control (`source`, position, angle, filters, draft, queue, anchors, segments), because session `PUT` replaces supplied anchor/segment collections. Debounce position persistence; save anchors, filters, drafts, and queue explicitly after user actions.

Player sync must use `youtubeEmbedUrl`, `playerMessage`, and `playerAvailability`. Initial load restores `video_position_seconds`; player errors update the persisted availability state when a session is saved. `unavailable`, `embedding_disabled`, `restricted`, and `player_error` show an announced unavailable panel with retry and source-replacement affordances, while review controls remain usable.

## Canonical UI Flows

- **Create/tag:** the friendly "Mark incident at current position" action converts current player time with `mapVideoTime(session.time_segments, period, time)` and creates a new `CanonicalEventCommand` through the canonical per-match `POST`. It includes its normal `evidence_state`, `clock_unverified`, and a `video` evidence item containing the session source ID and current seconds. With no playable video, it uses `no_visible` or `ambiguous` and omits anchor seconds. The evidence modal is reserved for revising an existing selected event through PATCH.
- **Revise:** submit the complete latest command plus required `reason` to `PATCH /canonical-events/{id}`. A corrected tag is the revised command payload; invalidate events and derived state on success. Surface 403/409/422 inline and retain the draft.
- **Anchor:** add/edit/remove local anchors; persist a complete ordered anchor collection and generated valid `TimeSegment` collection. A single anchor is a seek landmark, not verified mapping coverage. Timeline and modal badges use `mapVideoTime(...).clockUnverified`.
- **Player sync:** selecting a row seeks to `max(0, video_anchor_seconds - 2)`. Rows lacking video evidence are selectable but do not seek; explain why.

## Unsupported or Incorrect Specification Claims

The corrected `video-review-workspace` delta uses the single per-analyst, per-match endpoint above. Session lists, active-session facades, and `/api/v1/canonical-analysis/matches/{id}/sessions*` remain intentionally unsupported.

The current backend does **not** persist evidence `confidence`, `visibility`, `corrected_payload`, or `revision_of`; `CanonicalEvidence` has provenance fields only. It also returns only the latest revision from `GET canonical-events`, so a persisted chronological history and server-backed visual diff cannot be built. The UI may show the latest revision reason/evidence, but those requirements are blocked until contracts change; do not fake them with client-only history. Automatic regulation-start defaults are likewise not a backend contract; require an explicit UI value until product policy defines it.

## UX, Accessibility, and Failure Behavior

Use loading skeletons, `role="alert"` for save/load failures, retry actions, and an empty-state explanation. All controls have visible labels, keyboard focus, and at least 44px targets. Register `dispatchReviewShortcut` only while the workspace is active; its editable/modifier/composition guards are mandatory. Escape closes dialogs, timeline rows support keyboard selection/Enter seek, badges have text alternatives, and status updates use a polite live region.

## File Changes

| File | Action | Description |
|---|---|---|
| `docs/architecture/match-review-spec.md` | Modify | Replace obsolete contracts and mark blocked claims. |
| `openspec/specs/video-review-workspace/spec.md` | Modify | Correct per-match endpoint scenarios. |
| `frontend/src/hooks/useYouTubeSync.ts` | Create | Isolated iframe synchronization and failure state. |
| `frontend/src/components/{EventTimeline,AnchorsEditor,EvidenceModal,RevisionHistory}.tsx` | Create | Review controls; history is limited to supported latest-revision data. |
| `frontend/src/pages/MatchReview.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/types.ts` | Modify/Create | Page composition, route, supported PATCH client/type alignment. |

## Testing and Chained Delivery

Unit-test mapping, shortcut guards, derived segment generation, seek clamping, paused-seek state preservation, and revision payload construction. Component-test loading, unavailable-player review, keyboard behavior, anchor persistence, and mutation errors with Vitest/Testing Library. The targeted backend route suite proves a roster-listed player is accepted without lineup, substitution, or active-goalkeeper context. Run frontend lint, build, and tests; no migration or rollout flag is required.

| Slice | Deliverable and verification | Budget |
|---|---|---|
| 1 → feature branch | Correct docs/spec claims; player hook and unit tests | ≤300 lines |
| 2 → 1 | Timeline evidence time, seek/highlight tests | ≤350 lines |
| 3 → 2 | Anchor editor, segment derivation, session persistence tests | ≤350 lines |
| 4 → 3 | Supported evidence revision modal and explicit unsupported-history presentation | ≤350 lines |
| 5 → 4 | Page/route assembly, shortcuts, unavailable-state integration tests | ≤400 lines |

Each slice is independently testable and revertible; commit its behavior, tests, and relevant docs together. Chained PRs are required before apply because the configured 400-line guard is at risk.

## Open Questions

- [ ] Product decision: what regulation seconds should a newly created period anchor default to?
- [ ] Backend follow-up required for persisted confidence/visibility and revision-history/diff requirements.
