# Exploration: match-review-workspace

> **Historical discovery snapshot (pre-implementation):** The “current” and “new file” statements below describe the state when this change was explored. The implemented scope, actual per-match contracts, and backend limitations are authoritative in `proposal.md`, `design.md`, `tasks.md`, `openspec/specs/video-review-workspace/spec.md`, and `docs/architecture/api-spec.md`.

## Current State

### Backend (FastAPI + SQLAlchemy) — Ready

**Canonical Analysis Service** (`backend/app/services/canonical_analysis_service.py:284-492`):
- `create_event`, `revise_event`, `deactivate_event` — canonical CRUD with revision history
- `read_events`, `read_state`, `read_metrics`, `read_reconciliation`, `legacy_dry_run` — derived reads with evidence linkage
- Evidence model (`CanonicalEvidence`) supports: `fixture`, `pdf`, `video`, `unavailable` kinds with `video_source_id` + `video_anchor_seconds`
- Server-side sequencing (`sequence`), **not** wall-clock time; `clock_unverified` flag marks unreliable mappings
- Cutover flag `Match.canonical_analysis_enabled` blocks legacy writes, preserves reads

**Analysis Session Service** (`backend/app/services/analysis_session_service.py:10-55`):
- YouTube URL validation/parsing → `VideoSource` (provider, provider_video_id)
- `TimeAnchor`: period, video_seconds, regulation_seconds, uncertainty_seconds
- `TimeSegment`: period, video range, optional regulation range, coverage (playable/pause/cut/replay/halftime/offset), clock_unverified
- Session state: mode (live/video), video_position_seconds, anchors[], time_segments[], filters, draft, queue

**API Routes** (`backend/app/api/routes/canonical_analysis.py:25-75`, `backend/app/api/routes/analysis.py:13-25`):
- `GET/PUT /matches/{match_id}/analysis-session` — session with video source, anchors, segments
- `GET/POST /matches/{match_id}/canonical-events` — canonical events
- `PATCH/DELETE /canonical-events/{event_id}` — revise/deactivate
- `GET /matches/{match_id}/canonical-state|metrics|reconciliation|legacy-dry-run` — derived reads
- `PUT /matches/{match_id}/canonical-cutover` — admin toggle

**Models** (`backend/app/models.py:320-386`):
- `VideoSource`, `AnalysisSession`, `TimeAnchor`, `TimeSegment`
- `CanonicalEvent` (sequence), `CanonicalEventRevision` (payload + evidence), `CanonicalEvidence` (video_source_id, video_anchor_seconds)

### Frontend (React 18 + TypeScript + Vite + TanStack Query) — Partial

**MatchAnalysis.tsx** (`frontend/src/pages/MatchAnalysis.tsx:27-61`):
- Live mode: timer (`useTimer`), canonical event creation, mode toggle (live/video)
- Video mode: same command schema, `clock_unverified` forced true, no playback UI

**Video Review Infrastructure** (exists, unused):
- `videoReview.ts:15-36` — `mapVideoTime(segments, period, videoSeconds)` → regulation mapping with uncertainty
- `reviewShortcuts.ts:26-51` — keyboard shortcuts: space=play/pause, ,/./j/l=seek, [/]=navigate events, a=add anchor, t=tag, s=save, n=notes, u/r=undo/redo, ?=help
- `types.ts:183-240` — full types: `VideoSource`, `TimeAnchor`, `TimeSegment`, `AnalysisSession`, `CanonicalEventCommand`

**API Client** (`frontend/src/api/client.ts:107-110`):
- `getAnalysisSession(matchId)`, `saveAnalysisSession(matchId, data)`
- `getCanonicalEvents`, `getCanonicalState`, `getCanonicalMetrics`, `getCanonicalReconciliation`
- `createCanonicalEvent(matchId, data)`

### Documentation — Out of Sync

| Document | Status |
|---|---|
| `openspec/specs/video-review-workspace/spec.md` | High-level requirements only; no API contract detail |
| `openspec/specs/canonical-live-handball-analysis/spec.md` | Canonical invariants; no video-review workspace detail |
| `openspec/specs/video-source-management/spec.md` | Source validation/availability; no workspace integration |
| `docs/architecture/match-review-spec.md` | **Detailed UI spec** but references **incorrect endpoints** (e.g., `/canonical-analysis/sessions/{id}` vs actual `/matches/{match_id}/analysis-session`) |
| `docs/README.md` | Flags "Canonical Analysis Foundation: Backend ready; UI MatchReview pending" |

## Affected Areas

| Path | Why Affected |
|---|---|
| `frontend/src/pages/MatchReview.tsx` | Implemented subsequent work — main video review workspace |
| `frontend/src/hooks/useYouTubeSync.ts` | **New file** — YouTube iframe API sync (play/pause/seek/timeupdate) |
| `frontend/src/components/EventTimeline.tsx` | **New file** — timeline with click→seek and evidence badges; filter controls are not part of the usable MVP |
| `frontend/src/components/AnchorsEditor.tsx` | **New file** — anchor CRUD + "set from current position" |
| `frontend/src/components/EvidenceModal.tsx` | **New file** — 4 evidence states + confidence + visibility + note + correct payload |
| `frontend/src/components/RevisionHistory.tsx` | **New file** — audit trail with visual diff |
| `frontend/src/api/client.ts` | Update endpoint references if any drift |
| `docs/architecture/match-review-spec.md` | **Must update** to reflect actual backend contracts (per-match, not per-session) |
| `openspec/specs/video-review-workspace/spec.md` | **May update** to align with implemented API contracts |

## Approaches

### Approach 1: Align Documentation to Actual APIs (Recommended)
**Description**: Update `match-review-spec.md` and OpenSpec specs to match the existing per-match backend contracts. Build frontend against current APIs without backend changes.

- **Pros**:
  - Backend is complete and tested (275 tests pass)
  - No backend risk; preserves canonical architecture
  - Faster delivery — frontend only
  - API contracts are clean: per-match session, canonical events with video evidence linkage
- **Cons**:
  - `match-review-spec.md` references session-scoped endpoints that don't exist; must be corrected
  - Frontend must adapt to per-match (not per-session) API structure
- **Effort**: Medium (frontend implementation + doc updates)

### Approach 2: Add Session-Scoped Backend Endpoints for Parity with Spec
**Description**: Add `/canonical-analysis/sessions/{id}/events|anchors|reconcile` routes wrapping existing per-match logic to match the documented spec.

- **Pros**:
  - Matches existing `match-review-spec.md` exactly
  - Cleaner separation if multi-session-per-match ever needed
- **Cons**:
  - Unnecessary backend change for MVP (single analyst, one session per match)
  - Adds maintenance surface; duplicates per-match logic
  - Violates "preserve canonical-analysis architecture" — current design is per-match intentional
- **Effort**: Medium-High (backend + frontend + migration risk)

### Approach 3: Hybrid — Per-Match APIs with Session Facade
**Description**: Keep per-match backend; add a thin frontend facade that presents a session-like interface (loading match session as "the session").

- **Pros**:
  - Backend unchanged
  - Frontend can follow spec's mental model
  - Minimal adaptation code
- **Cons**:
  - Adds abstraction layer that may confuse
  - Spec still documents non-existent endpoints
- **Effort**: Medium (frontend facade + doc updates)

## Recommendation

**Approach 1: Align Documentation to Actual APIs**

**Why**:
1. The backend architecture is **intentionally per-match** — `AnalysisSession` is owned by `Match` (one-to-many but MVP uses one). Session-scoped endpoints would be premature abstraction.
2. All required data flows exist: video source, anchors, segments, canonical events with `video_source_id` + `video_anchor_seconds` evidence.
3. The `mapVideoTime` utility already implements the core video↔regulation mapping using `TimeSegment` coverage logic.
4. Keyboard shortcuts (`reviewShortcuts.ts`) are implemented and tested.
5. Documentation drift is the only blocker — fixing it is cheaper than adding backend endpoints.

**Implementation Path**:
1. **Update `docs/architecture/match-review-spec.md`** to reference actual endpoints:
   - `GET/PUT /api/v1/matches/{match_id}/analysis-session`
   - `GET/POST /api/v1/matches/{match_id}/canonical-events`
   - `PATCH/DELETE /api/v1/canonical-events/{event_id}`
   - `GET /api/v1/matches/{match_id}/canonical-state|metrics|reconciliation`
2. **Update `openspec/specs/video-review-workspace/spec.md`** to reflect per-match contracts and evidence linkage to `CanonicalEvidence.video_source_id`.
3. **Build `MatchReview.tsx`** following the corrected spec using existing hooks/components:
   - `useYouTubeSync` wrapping YouTube iframe API
   - `EventTimeline` consuming `getCanonicalEvents` + `mapVideoTime`
   - `AnchorsEditor` bound to `AnalysisSession.anchors` + `saveAnalysisSession`
   - `EvidenceModal` → `PATCH /canonical-events/{event_id}` with revised `evidence_state`, `confidence`, `note`, optional `corrected_payload`
   - `RevisionHistory` from `GET /canonical-events` revision data (already in response)

## Risks

1. **Documentation drift**: If `match-review-spec.md` isn't updated first, frontend implementation will target non-existent endpoints. **Mitigation**: Update docs as first task.
2. **YouTube iframe API flakiness**: Embedding-disabled, restricted, unavailable, or player-error sources break playback. **Mitigation**: the existing `AnalysisSession.availability_state` contract and `videoReview.playerAvailability` handle these supported states; workspace must support no-playback entry (`no_visible`/`ambiguous` evidence states). `removed` is not a backend availability value.
3. **Clock drift/uncertainty**: `mapVideoTime` returns `clockUnverified: true` when no playable segment covers the video time. Analyst must see this badge and understand `regulation_seconds` is unreliable. **Mitigation**: UI must surface `clock_unverified` badge per event (already in `CanonicalEventCommand`).
4. **Single-session assumption**: MVP assumes one analyst, one session per match. If requirements change, per-match API still supports multiple sessions (filter by `analyst_id`).
5. **Review budget (400 lines)**: Full `MatchReview.tsx` with 5 components + hook may exceed. **Mitigation**: Split into stacked PRs (player → timeline → anchors → evidence → history) per chained-PR skill.

## Ready for Proposal

**Yes** — the exploration is complete. The orchestrator should:
1. Present the recommendation (Approach 1) to the user
2. Confirm the decision: **align docs to actual APIs, no backend changes**
3. Launch the proposal phase with scope: documentation updates + frontend `MatchReview.tsx` implementation per corrected spec
