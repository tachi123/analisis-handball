# Design: Official Sheet Access and Video Review Entry

## Technical Approach

Keep canonical capture in `MatchAnalysis`. Add a protected, match-scoped official-sheet read contract for the latest confirmed `OfficialSnapshot`, render its immutable facts in analysis, and hand video work to the existing protected `/review` route. The review workspace remains the sole writer of video URLs through its analysis-session contract and existing YouTube player.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Add `GET /matches/{id}/official-sheet` and `/official-sheet/pdf` | Add snapshots to `GET /matches/{id}`; client-supplied snapshot/path | Keeps the capture payload small and prevents cross-match/path selection. Both endpoints authenticate and select the latest `is_confirmed` snapshot server-side. |
| Stream only a contained source | Return `source_path`; proxy/download PDFs; migrate files | Resolve the selected snapshot path against configured approved evidence roots (`OFFICIAL_EVIDENCE_ROOTS`, including managed `PDF_DIR` as applicable). Return `409 source_unavailable` on absent, unreadable, non-PDF, or escaping paths; facts remain available. |
| Reuse `MatchReview` for setup/playback | Embed a second player/source form in analysis; use `PATCH /matches/{id}` | `AnalysisSessionService._source_identity` already validates supported YouTube URLs and persists provider identity. Reuse its nocookie embed, availability persistence, retry/replacement, and no-playback behavior. |

## Data Flow

    MatchAnalysis ── GET official-sheet ──> matches route ──> PDFService
          │                    │                    └── OfficialSnapshot + players
          │                    └── authenticated DTO (no source_path)
          ├── GET official-sheet/pdf (Axios bearer) ──> Blob URL ──> inline iframe
          └── navigate /match/:id/review ── PUT analysis-session ──> validated VideoSource
                                                               └── nocookie player

The service queries `OfficialSnapshot` by `match_id` and `is_confirmed=True`, ordered newest-first by `created_at`; it eager-loads players. Metadata returns 404 `official_sheet_not_found` if no confirmed snapshot. PDF resolution derives only from that selected row. The API never accepts a snapshot ID, filename, or path from the browser and never serializes `source_path`.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/api/routes/matches.py` | Modify | Add authenticated metadata and inline-PDF endpoints. |
| `backend/app/services/pdf_service.py` | Modify | Select/read DTO data and validate approved-root PDF resolution. |
| `backend/app/schemas.py` | Modify | Add read-only `OfficialSheet`/player schemas; do not extend `Match`. |
| `backend/.env.example`, `backend/.env.local.example` | Modify | Document approved evidence-root configuration without committing local paths. |
| `frontend/src/api/client.ts`, `frontend/src/types.ts` | Modify | Add sheet DTO query and authenticated PDF-blob request. |
| `frontend/src/pages/MatchAnalysis.tsx` | Modify | Add sheet facts/PDF UI and review entry action. |
| `frontend/src/pages/MatchReview.tsx` | Modify | Offer URL input during first-session setup, including clear validation feedback. |
| `backend/tests/test_pdf_routes.py`, `frontend/src/pages/MatchAnalysis.test.tsx`, `frontend/src/pages/MatchReview.test.tsx` | Modify | Cover contract and workspace states. |

## Interfaces / Contracts

```ts
type OfficialSheet = {
  snapshot_id: string; confirmed_date: string
  home: { name: string; score: number; players: OfficialSheetPlayer[] }
  away: { name: string; score: number; players: OfficialSheetPlayer[] }
  provenance: { filename: string; content_type: string; size_bytes: number; sha256: string; page_count: number }
  pdf_available: boolean
}
type OfficialSheetPlayer = { player_id: number | null; name: string; jersey_number: number; official_goals: number; official_yellow: number; official_2min: number; official_red: number; official_blue: number }
```

`GET /api/v1/matches/{id}/official-sheet` returns this DTO. `GET .../official-sheet/pdf` returns `application/pdf` with `Content-Disposition: inline`; the Axios client requests a `Blob` because a direct browser navigation cannot attach the SPA's bearer token. The UI revokes the generated object URL when closed/unmounted.

`MatchReview` submits its initial non-empty URL as `source: { url, availability_state: 'unknown' }` in the existing `PUT /matches/{id}/analysis-session`; an empty URL creates a source-less session for no-playback evidence. The service accepts only `youtube.com`, `youtu.be`, and `youtube-nocookie.com` identities and a valid video ID. Ready playback uses the existing `youtube-nocookie.com` iframe; provider errors retain session data and expose retry/replacement/no-playback controls.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Backend service/route | Auth, match isolation, latest confirmed selection, DTO omission of paths, root containment, missing/unreadable PDF, inline headers | SQLite/TestClient with temporary approved roots and snapshots. |
| Frontend integration | Loading, no-sheet, facts, PDF open/cleanup, review handoff | Vitest/RTL with mocked API/blob URL. |
| Review integration | First setup validates/persists a URL; empty setup and provider outage remain usable | Extend existing `MatchReview` mocks and mutation assertions. |

## Migration / Rollout

No database migration. Before enabling PDF viewing, deployers configure approved roots that cover managed imports and the approved preload corpus; paths outside them intentionally remain unavailable. Deliver backend evidence/viewer and UI handoff/setup as separate review slices to respect the 400-line budget.

## Open Questions

None.
