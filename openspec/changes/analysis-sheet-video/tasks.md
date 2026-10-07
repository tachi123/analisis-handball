# Tasks: Official Sheet Access and Video Review Entry

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 560–720 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 evidence API → PR 2 analysis and review UI |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Protected confirmed-sheet metadata and inline PDF | PR 1 | Base: main; backend tests/config included; independently deployable. |
| 2 | Analysis sheet viewer and review-source setup | PR 2 | Base: PR 1 branch; frontend tests included; depends on sheet contract. |

## Phase 1: Protected Evidence Contract

- [ ] 1.1 Add read-only official-sheet/player schemas in `backend/app/schemas.py`; omit `source_path` and keep `Match` unchanged.
- [ ] 1.2 Extend `backend/app/services/pdf_service.py` to select the newest confirmed snapshot with players and resolve only readable `.pdf` files contained in configured evidence roots.
- [ ] 1.3 Add authenticated `GET /matches/{id}/official-sheet` and `/official-sheet/pdf` in `backend/app/api/routes/matches.py`; return 404 for no confirmed sheet and 409 `source_unavailable` for unsafe evidence with inline PDF headers.
- [ ] 1.4 Document `OFFICIAL_EVIDENCE_ROOTS` and managed PDF-root behavior in `backend/.env.example` and `backend/.env.local.example`, without local paths.
- [ ] 1.5 Extend `backend/tests/test_pdf_routes.py` for auth, match isolation, latest confirmed selection, path omission, approved inline PDF, and unavailable/escaping PDFs.

## Phase 2: Analysis Sheet Viewer

- [ ] 2.1 Add `OfficialSheet` DTOs and authenticated Blob request helpers in `frontend/src/types.ts` and `frontend/src/api/client.ts`.
- [ ] 2.2 Add loading, absent-sheet, immutable facts, and PDF-open UI to `frontend/src/pages/MatchAnalysis.tsx`; revoke Blob URLs on close and unmount.
- [ ] 2.3 Add the `/match/:matchId/review` entry action in `frontend/src/pages/MatchAnalysis.tsx` without adding a player or URL form there.
- [ ] 2.4 Extend `frontend/src/pages/MatchAnalysis.test.tsx` for loading, no-sheet, facts, Blob cleanup, and review handoff.

## Phase 3: Review Source Setup

- [ ] 3.1 Update `frontend/src/pages/MatchReview.tsx` to offer initial non-empty YouTube URL setup through the existing analysis-session mutation, with actionable validation feedback.
- [ ] 3.2 Preserve source-less setup, existing nocookie playback, retry/replacement, and no-playback review actions in `frontend/src/pages/MatchReview.tsx`.
- [ ] 3.3 Extend `frontend/src/pages/MatchReview.test.tsx` for valid first save, invalid-source blocking, empty setup, and provider-unavailable review actions.

## Phase 4: Verification

- [ ] 4.1 Run `python -m pytest` from `backend` and `npm --prefix frontend test -- --run`; resolve failures in the affected work unit.
- [ ] 4.2 Run `npm --prefix frontend run lint` and `npm --prefix frontend run build`; verify the protected sheet and review workflow against all delta-spec scenarios.
