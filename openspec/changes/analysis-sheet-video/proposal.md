# Proposal: Official Sheet Access and Video Review Entry

## Intent

Make official imported evidence discoverable from match analysis without exposing server files, and let analysts attach a validated YouTube source and play it in the established review workspace.

## Scope

### In Scope
- Add analysis-page actions to view the latest confirmed official sheet/imported roster facts and open video review.
- Provide authenticated, match-scoped official-sheet metadata/player facts and safe inline PDF delivery.
- Support first-time YouTube URL entry in review through the validated analysis-session contract; embed playback in that workspace.

### Out of Scope
- PDF import/extraction changes, arbitrary local-file download, or exposing `source_path`.
- A second player or video-capture workflow inside `MatchAnalysis`.
- Guaranteed YouTube playback, media proxying/downloading, or new authorization roles.

## Capabilities

### New Capabilities
- `official-sheet-access`: Protected retrieval of the latest confirmed match snapshot, imported player facts, and safely resolved inline source PDF.

### Modified Capabilities
- `video-review-workspace`: Analysis links to review; review clearly supports source setup before playback for a match with no saved link.
- `video-source-management`: The existing validated, persisted analysis-session source path is the only URL-write contract for this flow.

## Approach

Keep `MatchAnalysis` as canonical capture. Add explicit sheet and review entry points. A backend read contract selects only the latest confirmed snapshot for the requested authenticated match; its PDF variant derives and resolves the server-side source below approved evidence roots, never from client input. Reuse `MatchReview` for URL setup, persisted source state, availability recovery, and its `youtube-nocookie.com` player.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/pages/MatchAnalysis.tsx` | Modified | Sheet and review entry points. |
| `frontend/src/pages/MatchReview.tsx` | Modified | First-time source setup and existing embedded player. |
| `frontend/src/api/client.ts`, `frontend/src/types.ts` | Modified | Protected sheet DTO/PDF contracts. |
| `backend/app/api/routes/matches.py`, `backend/app/services/pdf_service.py`, `backend/app/schemas.py` | Modified | Authorized confirmed-snapshot lookup and safe PDF response. |
| `backend/tests/`, `frontend/src/pages/*.test.tsx` | Modified | Access, missing evidence, setup, and UI states. |
| Database | Unchanged | Reuse immutable snapshots and analysis-session video fields. |
| Deployment | Unchanged | Configure/verify approved evidence-root access only. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legacy absolute evidence paths are unsafe/unreadable | Medium | Approved-root containment; return a useful unavailable state while facts remain visible. |
| YouTube embedding is denied | Medium | Preserve existing retry, replacement, provider-opening, and no-playback states. |
| Review scope exceeds 400 lines | High | Deliver backend evidence contract and frontend handoff/review setup as separate review slices. |

## Rollback Plan

Remove the new analysis entry points and routes; retain immutable snapshots and saved session sources. Disable PDF streaming if root validation fails while preserving metadata access.

## Dependencies

- Existing authentication, confirmed `OfficialSnapshot` data, analysis-session YouTube validation, and configured approved evidence roots.

## Success Criteria

- [ ] An authenticated analyst can find confirmed sheet facts from analysis without receiving filesystem paths.
- [ ] Only the requested match's latest confirmed snapshot can supply metadata or an inline PDF; missing files return a safe actionable state.
- [ ] A valid YouTube URL is persisted only through the analysis-session validation flow and review embeds/reports availability for the saved source.
