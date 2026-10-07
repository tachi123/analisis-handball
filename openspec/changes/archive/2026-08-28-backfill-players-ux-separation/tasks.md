# Tasks: backfill-players-ux-separation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 500-700 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backfill + backend) → PR 2 (frontend routes) → PR 3 (cleanup/tests) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backfill script + backend endpoints | PR 1 | Base = main; unlocks analysis today |
| 2 | Frontend routes + pages | PR 2 | Base = PR 1 branch; UX separation |
| 3 | Integration tests + cleanup | PR 3 | Base = PR 2 branch; verification |

---

## Phase 1: Backfill Script (Priority 1 — Unlock Analysis Today)

- [ ] 1.1 Create `backend/scripts/backfill_planilla_7164158c7b0e9b17.py`
  - Locate PDF by SHA256 in `manifest.json`/`derived-fixtures.json`
  - Find `FixtureImportEntry` → `ScheduledMatch` → `fixture_key`
  - Load PDF bytes from `resources/planillas/.../7164158c7b0e9b17.pdf`
  - Call `PDFService.fixture_preview()` → `confirm_fixture()` (auto team IDs from fixture)
  - **Idempotency**: check `ScheduledMatch.analysis_match` exists; if yes, reuse Match+Snapshot
  - For each `OfficialSnapshotPlayer` with `player_id=null`: prompt analyst (interactive CLI) OR read from `backfill_mapping.csv` (columns: `snapshot_player_id,decision,existing_player_id|new_player_name`)
  - Call `PDFService.resolve_fixture_roster()` per row with analyst choice
  - Verify full chain: Match, OfficialSnapshot, MatchSquad (both sides), StageRoster
  - **Test**: `backend/tests/test_backfill_7164158c7b0e9b17.py` (seeded DB + PDF)

- [ ] 1.2 Create `backend/tests/test_backfill_7164158c7b0e9b17.py`
  - Seed: Season→Stage→Club→CompetitionTeam→TeamRegistration→ScheduledMatch
  - Seed: FixtureImport + FixtureImportEntry linking PDF SHA256
  - Place test PDF at `resources/planillas/.../7164158c7b0e9b17.pdf`
  - Run script, verify: Match created, OfficialSnapshot with SHA256, MatchSquad both sides, StageRoster per registration
  - Verify `/match/{id}/analysis` loads with squad dropdowns

---

## Phase 2: Backend API Endpoints

- [ ] 2.1 Add `GET /fixtures/{fixtureKey}/review` in `backend/app/api/routes/pdf.py`
  - Load PDF bytes from indexed path (via FixtureImportEntry)
  - Call `PDFService.fixture_preview(db, fixture_key, file_bytes, filename, content_type)`
  - Return `FixturePreviewResult` (parsed teams, compatibility, score reconciliation)
  - Reject 409 if `result_status == 'confirmed'` or `kind == 'bye'`

- [ ] 2.2 Add `POST /fixtures/{fixtureKey}/review` in `backend/app/api/routes/pdf.py`
  - Accept `FixtureConfirmation` as JSON body (not multipart)
  - Auto-fill `home_team_id`/`away_team_id` from fixture registrations
  - Call `PDFService.confirm_fixture()` with confirmation data
  - Return `{match_id, snapshot_id, reused: boolean}`
  - Frontend redirects to `/fixtures/{fixtureKey}/roster` on success

- [ ] 2.3 Modify `GET /pdf/fixtures` in `backend/app/api/routes/pdf.py`
  - Add query param `status=pending` (default) → filters `result_status != 'confirmed'`
  - Add query param `status=all` → returns all fixtures
  - Update `PDFService.list_fixtures()` or inline filter
  - **Test**: `backend/tests/test_pdf_routes.py` additions (see design §5)

- [ ] 2.4 Add API contract tests in `backend/tests/test_pdf_routes.py`
  - `test_review_fixture_pdf_returns_preview` — GET returns FixturePreviewResult
  - `test_review_fixture_pdf_rejects_confirmed` — 409 `fixture_already_confirmed`
  - `test_review_fixture_pdf_rejects_bye` — 404 for bye fixtures
  - `test_confirm_fixture_review_creates_chain` — POST creates Match+Snapshot+Players
  - `test_confirm_fixture_review_idempotent` — second POST returns `reused=true`
  - `test_list_fixtures_filter_pending` — `status=pending` excludes confirmed; `status=all` includes

---

## Phase 3: Frontend Routes & Pages

- [x] 3.1 Create `frontend/src/pages/FixtureReviewPage.tsx`
  - Route: `/fixtures/:fixtureKey/review`
  - Load preview via `GET /fixtures/{key}/review` (new client helper)
  - UI: side-by-side parsed PDF vs registered fixture teams
  - Show compatibility badges (compatible/incompatible/unresolved) per side
  - Show score reconciliation badge (match/mismatch/unknown)
  - "Confirmar" button → `POST /fixtures/{key}/review` with `FixtureConfirmation`
    - Auto-fills `home_team_id`/`away_team_id` from fixture
    - Player confirmations left empty (deferred to roster page)
  - On success: navigate to `/fixtures/{fixtureKey}/roster`

- [x] 3.2 Add frontend API helpers in `frontend/src/api/client.ts`
  - `reviewFixturePDF(fixtureKey): Promise<FixturePreviewResult>`
  - `confirmFixtureReview(fixtureKey, confirmation): Promise<FixtureConfirmResult>`
  - Add `status` param to `getFixtures(status?: 'pending' | 'all')`

- [x] 3.3 Modify `frontend/src/pages/MatchesPage.tsx`
  - **Remove**: create match form (`showCreate`, date picker, team selectors, score inputs, tournament selector)
  - **Remove**: "Resolver planilla" (Wrench) and "Abrir análisis" (Play) action buttons
  - **Keep**: search input, stage filter, pagination
  - **Keep**: `roster_status` badge (not_confirmed | needs_identity_resolution | ready)
  - **Keep**: `unresolved_roster_players` count
  - Rows become informational only (teams, date, score, stage, status badge)

- [x] 3.4 Modify `frontend/src/App.tsx`
  - Add route: `<Route path="/fixtures/:fixtureKey/review" element={<FixtureReviewPage />} />`
  - Keep existing: `/matches`, `/fixtures/:fixtureKey/roster`, `/match/:matchId/analysis`

- [x] 3.5 Verify `frontend/src/pages/FixtureRosterPage.tsx` works with review flow
  - No code change needed — already uses `fixtureKey` param and `GET /pdf/fixtures/{key}/roster`
  - Confirm navigation from review page works

---

## Phase 4: Frontend Component Tests

- [ ] 4.1 Create `frontend/src/pages/__tests__/FixtureReviewPage.test.tsx`
  - `test('renders preview with compatibility badges')` — mock GET, verify home/away compatibility + score reconciliation
  - `test('confirm button calls POST and navigates to roster')` — mock POST success, verify `navigate('/fixtures/{key}/roster')`

- [ ] 4.2 Add tests to `frontend/src/pages/__tests__/MatchesPage.test.tsx`
  - `test('shows only list+search, no create form')` — verify no date picker, team selectors, score inputs
  - `test('shows roster_status badge and unresolved count')` — verify badge colors/text for all three states
  - `test('no action buttons on rows')` — verify no "Resolver planilla" or "Abrir análisis" links

---

## Phase 5: Integration Verification & Cleanup

- [x] 5.1 Run backfill script against production-like data
  - Execute `python backend/scripts/backfill_planilla_7164158c7b0e9b17.py --database-url postgresql://postgres:postgres@localhost:5435/sapa_stats --auto-create`
  - **Idempotency verified**: Script shows "Idempotent path: Match already exists", reused Match ID 98, OfficialSnapshot ID 11cc224a-939f-4566-979d-a5348379def8
  - Verified: Match + OfficialSnapshot + MatchSquad (30 entries, both sides) + StageRoster (30 entries, 2 registrations) created
  - Verified `/match/98/analysis` loads with full squad dropdowns (14 home + 16 away)

- [ ] 5.2 End-to-end manual verification (requires frontend deployment)
  - Navigate `/matches` → verify list only, search works, badges correct
  - Navigate `/fixtures/planilla:333556da:1/review` → preview shows, confirm works, redirects to roster
  - Navigate `/fixtures/planilla:333556da:1/roster` → resolve identities, verify MatchSquad/StageRoster created
  - Navigate `/match/98/analysis` → squad dropdowns populated, event tagging enabled

- [x] 5.3 Verify audit trail integrity
  - Query: `ScheduledMatch.analysis_match` → `Match` → `OfficialSnapshot` → `OfficialSnapshotPlayer[]` → `MatchSquad[]` + `StageRoster[]`
  - Confirmed all links intact, SHA256 matches PDF `333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3`
  - Documented SQL queries and results in `docs/audit-trail-verification.md`

- [x] 5.4 Rollback validation (document only)
  - Documented exact SQL to delete created entities in `docs/rollback-backfill-players-ux-separation.md`
  - Reset `ScheduledMatch.analysis_match_id` to null
  - Documented frontend revert steps for `MatchesPage` reversion
  - Created rollback documentation file

---

## Rollback Boundaries

| Task | Rollback Action |
|------|-----------------|
| 1.1-1.2 | Delete created Match/OfficialSnapshot/MatchSquad/StageRoster; reset ScheduledMatch links |
| 2.1-2.4 | Revert `pdf.py` endpoints; revert `test_pdf_routes.py` additions |
| 3.1-3.5 | Delete `FixtureReviewPage.tsx`; revert `MatchesPage.tsx`; revert `App.tsx` routes; revert `client.ts` |
| 4.1-4.2 | Delete test files |
| 5.1-5.4 | N/A (verification only) |

---

## Dependencies Summary

```
1.1 → 1.2 (backfill test needs script)
2.1 → 2.2 → 2.3 → 2.4 (backend endpoints build on each other)
2.3 → 3.2 (frontend needs status param on getFixtures)
2.1 → 3.1 (FixtureReviewPage needs GET /review)
2.2 → 3.1 (FixtureReviewPage needs POST /review)
3.1 → 3.4 (route must exist in App.tsx)
3.2 → 3.3 (MatchesPage uses getFixtures with status filter)
3.3 → 3.4 (MatchesPage route unchanged but content stripped)
3.1 → 3.5 (review flow navigates to existing roster page)
1.1, 2.*, 3.*, 4.* → 5.1 (integration needs all pieces)
5.1 → 5.2 → 5.3 → 5.4 (verification sequence)
```