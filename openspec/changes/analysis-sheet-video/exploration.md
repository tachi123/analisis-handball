## Exploration: analysis-sheet-video

### Current State
`/match/:matchId/analysis` loads only `GET /api/v1/matches/{id}` and renders the match teams, `home_score`/`away_score`, squad, and canonical events. It has no control or API path for an official snapshot, its imported player facts, or its PDF. This explains why `/match/16/analysis` can show a score labelled “Planilla” but cannot expose the underlying sheet/imported data.

Confirmed imports are persisted as `OfficialSnapshot` plus immutable `OfficialSnapshotPlayer` rows. The PDF remains a server-local `source_path`; current protected `/pdf/fixtures` responses expose only the snapshot ID and a YouTube URL, not sheet contents or a PDF stream. The match response intentionally excludes snapshots.

Video review already exists at `/match/:matchId/review`. It can create a per-analyst session, validates supported YouTube URLs server-side, embeds the saved video through `youtube-nocookie.com`, and supports playback/error recovery. `/analysis` has neither a video-source input nor a player; its “Modo video” merely marks canonical events with an unverified clock.

### Affected Areas
- `frontend/src/pages/MatchAnalysis.tsx` — add discoverable actions for official context and video review; do not imply the score alone is the PDF.
- `frontend/src/pages/MatchReview.tsx` — make first-time URL entry clear when the match has no saved `youtube_link`; reuse the existing player instead of duplicating it in capture.
- `frontend/src/api/client.ts`, `frontend/src/types.ts` — add a protected official-sheet read/download contract and its UI types.
- `backend/app/api/routes/matches.py` (or a focused official-evidence route) — expose confirmed snapshot metadata/player facts and an authenticated inline-PDF response by match ID.
- `backend/app/services/pdf_service.py` — centralize lookup and safe local-file resolution for the confirmed snapshot rather than returning `source_path` to browsers.
- `backend/app/schemas.py` — define a read-only official-sheet DTO; `Match` should remain a lightweight capture payload.
- `backend/tests/test_pdf_routes.py` and new route tests — cover authorization, confirmed-only selection, metadata/player facts, unavailable/missing evidence, and PDF response constraints.
- `frontend/src/pages/MatchAnalysis.test.tsx`, `frontend/src/pages/MatchReview.test.tsx` — cover the new actions, imported-data states, and initial video setup.

### Approaches
1. **Link analysis to the existing review workspace and add a protected sheet view (recommended)** — add “Ver planilla/datos importados” to analysis and an “Abrir revisión con video” action; show snapshot facts in a drawer/page and open the PDF from an authenticated backend endpoint. Let review own URL entry and playback.
   - Pros: reuses tested YouTube/session/evidence behavior; no duplicate player state; makes imported evidence visible without exposing server paths.
   - Cons: video opens on `/review`, not embedded directly in the compact capture page.
   - Effort: Medium.

2. **Embed URL entry/player directly in analysis** — add a player and source/session handling alongside canonical capture.
   - Pros: fulfils a literal single-page workflow.
   - Cons: duplicates `MatchReview` player, error, timing, keyboard, and persistence logic; likely exceeds the 400-line review budget and creates divergent capture semantics.
   - Effort: High.

### Recommendation
Use approach 1. Add two explicit analysis-page entry points: one for the confirmed official sheet/imported facts, and one for the established video-review workspace. In review, present URL entry before/while creating the session so a match without `youtube_link` is not a dead end. Do not use `PATCH /matches/{id}` for URL validation: it currently accepts arbitrary strings; persist video sources through `PUT /matches/{id}/analysis-session`, whose service validates YouTube hosts and video IDs.

The sheet API should select only the latest confirmed snapshot linked to the requested match and return a read-only DTO (provenance, official teams/scores, and player facts). Its PDF variant must authenticate, derive the file solely from that selected snapshot, resolve it beneath the configured/approved evidence root, and return an inline `application/pdf` response. It must never return local paths or accept a client-supplied filename/path. Missing, deleted, or unreadable evidence needs a useful non-200 state while imported facts remain viewable.

### Risks
- YouTube content can be private, restricted, removed, or disabled for embedding; preserve the existing availability states and no-playback evidence workflow. `youtube-nocookie.com` reduces cookie exposure but does not bypass provider rights, embedding, or availability rules.
- The official preload stores absolute local paths while manual import uses `data/pdfs`; a safe streaming implementation needs an explicit approved-root policy (or a migration to managed evidence storage) before serving files.
- `GET /matches/{id}` defaults scores to `0`; consumers must distinguish a snapshot’s confirmed official scores from missing/non-imported match data and never invent an official result.
- PDF streaming and imported roster facts are protected match evidence; endpoints must require the existing authentication and not leak filesystem provenance.
- Scope is likely above the 400-line review budget if it combines backend streaming, UI, and tests; plan a review slice for the backend contract/evidence view and a separate UI handoff/review-entry slice.

### Ready for Proposal
Yes — propose the protected official-evidence viewer plus analysis-to-review handoff, with first-time URL entry in the existing review workspace. Tell the user that playback cannot be guaranteed for every YouTube URL because YouTube/video-owner embedding restrictions remain authoritative.
