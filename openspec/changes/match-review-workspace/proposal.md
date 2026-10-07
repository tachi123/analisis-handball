# Proposal: match-review-workspace

## Intent

Build a friendly video review workspace where playback and timeline synchronize bidirectionally, incident tagging uses current video position, and analysts set match-start/time anchors to map video to regulation time while clearly surfacing unverified clocks. Align documentation to existing per-match backend contracts — no backend changes.

## Scope

### In Scope
- Update `docs/architecture/match-review-spec.md` to reference actual per-match API endpoints
- Update `openspec/specs/video-review-workspace/spec.md` to reflect implemented API contracts and evidence linkage
- Maintain `frontend/src/pages/MatchReview.tsx` as the implemented workspace page
- Create `useYouTubeSync` hook for YouTube iframe API synchronization
- Create `EventTimeline` component with click→seek, evidence badges, and `clock_unverified`
- Create `AnchorsEditor` component for anchor CRUD + "set from current position"
- Create `EvidenceModal` for 4 evidence states + confidence + visibility + note + corrected payload
- Create `RevisionHistory` component for audit trail with visual diff
- Update `frontend/src/api/client.ts` if any endpoint references drifted

### Out of Scope
- Backend API changes (per-match contracts are intentional and complete)
- Session-scoped facade endpoints (`/canonical-analysis/sessions/{id}/*`)
- Multi-analyst collaboration or multi-session-per-match UI
- SAPA report export (separate future work)
- Offline IndexedDB sync (deferred)

## Capabilities

### New Capabilities
- `match-review-workspace`: Unified video review page with YouTube sync, timeline, anchors, evidence tagging, and revision history

### Modified Capabilities
- `video-review-workspace`: Update spec to align with per-match API contracts and `CanonicalEvidence.video_source_id` linkage
- `video-source-management`: No spec change; workspace uses existing `VideoSource` and `availability_state`

## Approach

Follow **Approach 1** from exploration: align docs to actual APIs, build frontend only. Backend is complete (275 tests pass). Use existing `AnalysisSession` (per-match), `TimeAnchor`, `TimeSegment`, `CanonicalEvent` with `CanonicalEvidence` linking to `video_source_id` + `video_anchor_seconds`. Leverage existing `mapVideoTime` utility for video↔regulation mapping with `clock_unverified` flag. Use existing `reviewShortcuts.ts` keyboard bindings.

Implementation order (enables stacked PRs):
1. Docs update (`match-review-spec.md`, OpenSpec specs)
2. `useYouTubeSync` hook + YouTube player integration
3. `EventTimeline` with evidence badges, click→seek
4. `AnchorsEditor` with set-from-current-position
5. `EvidenceModal` + `RevisionHistory`
6. `MatchReview.tsx` assembly + integration tests

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docs/architecture/match-review-spec.md` | Modified | Fix endpoint references to per-match contracts |
| `openspec/specs/video-review-workspace/spec.md` | Modified | Align with implemented API and evidence model |
| `frontend/src/pages/MatchReview.tsx` | Implemented | Main workspace page |
| `frontend/src/hooks/useYouTubeSync.ts` | Implemented | YouTube iframe API wrapper |
| `frontend/src/components/EventTimeline.tsx` | New | Timeline with seek and evidence badges |
| `frontend/src/components/AnchorsEditor.tsx` | New | Anchor CRUD + calibration UI |
| `frontend/src/components/EvidenceModal.tsx` | New | Evidence state + revision capture |
| `frontend/src/components/RevisionHistory.tsx` | New | Audit trail with visual diff |
| `frontend/src/api/client.ts` | Modified | Verify endpoint references |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Documentation drift causes frontend to target non-existent endpoints | High | Update docs as first task before any component work |
| YouTube iframe API flakiness (embedding disabled, restricted, unavailable, player error) | Medium | Handle the backend-supported `availability_state` values; support no-playback entry (`no_visible`/`ambiguous`) |
| Clock drift/uncertainty not surfaced clearly | Medium | Mandatory `clock_unverified` badge per event; `mapVideoTime` already returns flag |
| Full workspace exceeds 400-line review budget | High | Split into chained PRs: player → timeline → anchors → evidence → history |
| Single-session assumption may need revision later | Low | Per-match API already supports multiple sessions via `analyst_id` filter |

## Rollback Plan

1. Delete `MatchReview.tsx` and 5 new component/hook files
2. Revert `match-review-spec.md` and `video-review-workspace/spec.md` to pre-change versions
3. Revert any `client.ts` changes
4. No backend rollback needed (no backend changes)

## Dependencies

- Existing backend: `canonical_analysis_service`, `analysis_session_service`, `VideoSource`, `AnalysisSession`, `TimeAnchor`, `TimeSegment`, `CanonicalEvent`, `CanonicalEvidence`
- Frontend: `reviewShortcuts.ts`, `mapVideoTime`, `videoReview.playerAvailability`, TanStack Query, YouTube iframe API
- Auth: Existing app authentication (no new auth model)

## Success Criteria

- [x] `MatchReview.tsx` renders and loads session/video/anchors/events without errors
- [x] YouTube player loads, plays, pauses, seeks; observed time syncs timeline highlight and paused seek does not issue playback
- [x] Timeline click seeks to `video_time - 2s`; evidence and `clock_unverified` status are visible
- [x] `clock_unverified` badge visible on events without playable segment coverage
- [x] Anchors editor: add/edit/delete, "Set from current position", auto-recalculate mappings
- [x] Evidence modal supports the four backend evidence states and PATCHes an existing event; unsupported confidence, visibility, corrected payload, and chronology are explicitly deferred
- [x] Latest supported revision reason/evidence is shown with a deferred-history explanation
- [x] Keyboard shortcuts (space, ,/./j/l, [/], a, t, s, n/p, u/r, ?) work without capturing text input
- [x] Lint + build + unit/integration tests pass
- [x] Documentation matches actual per-match API contracts end-to-end

## Review Budget & Slices

Target ≤400 lines per PR. Likely chained PR slices:
1. **PR 1**: Docs update + `useYouTubeSync` + basic YouTube player (~150 lines)
2. **PR 2**: `EventTimeline` with evidence badges, click→seek (~180 lines)
3. **PR 3**: `AnchorsEditor` with calibration UI (~120 lines)
4. **PR 4**: `EvidenceModal` + `RevisionHistory` (~200 lines)
5. **PR 5**: `MatchReview.tsx` assembly + integration tests (~150 lines)

Each PR includes its component tests and updates relevant documentation.
