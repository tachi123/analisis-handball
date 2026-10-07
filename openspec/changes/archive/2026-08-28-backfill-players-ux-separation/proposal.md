# Proposal: backfill-players-ux-separation

## Intent

Fix the blocked PDF (7164158c7b0e9b17.pdf) that never completed the analyst confirmation step with explicit identity resolution, leaving `MatchSquad` and `StageRoster` empty. Separate the conflated `/matches` UX into three distinct flows to make the analyst workflow usable.

## Scope

### In Scope
- **Backfill**: Execute confirmation for the specific PDF → resolve player identities via explicit analyst decisions (link existing OR create new, NO auto-match) → create Match + OfficialSnapshot + MatchSquad + StageRoster → unlock analysis
- **UX Separation**:
  - `/matches` → list + search only (no create form, no review actions)
  - `/fixtures/:fixtureKey/review` → pending PDF review (fixture-preview equivalent)
  - `/match/:matchId/analysis` → analysis only (unchanged)
- **Confirmation Selector Fix**: Filter fixtures to `result_status != confirmed` so already-confirmed fixtures don't reopen a blocked flow

### Out of Scope
- Automated player matching by name/jersey (explicit analyst decision required per constraint)
- Changes to the competition layer schema (Season→Stage→Club→CompetitionTeam→TeamRegistration→ScheduledMatch)
- Legacy match creation flow (`createMatch` API) — keep for manual matches
- PDF parsing/derivation pipeline (already working)

## Capabilities

### New Capabilities
- `fixture-review`: PDF review flow for pending fixtures (fixture-preview + fixture-confirm equivalent on a dedicated route)
- `matches-list`: Clean match list page with only search/filter capabilities

### Modified Capabilities
- `fixture-roster`: Extend to accept `fixtureKey` from review flow; ensure identity resolution creates Match + OfficialSnapshot + MatchSquad + StageRoster
- `match-analysis`: No spec change; ensure it receives fully populated squads from backfill

## Approach

1. **Backfill script** (one-off): Locate the PDF by SHA256 in `manifest.json`/`derived-fixtures.json`, invoke the existing `/pdf/fixture-confirm` endpoint with the stored confirmation data, then run `/pdf/fixtures/{key}/roster-resolution` for each unresolved player using explicit analyst choices (link existing or create new). Verify `MatchSquad` and `StageRoster` populated.

2. **Route restructuring**:
   - Add `/fixtures/:fixtureKey/review` route → new `FixtureReviewPage` component
   - Move fixture preview/confirm logic from backend-only to this page
   - Strip `/matches` to only list/search (remove create form, remove roster action buttons)
   - Keep `/match/:matchId/analysis` unchanged

3. **Fixture list filter**: In `getFixtures` query, add `result_status != 'confirmed'` filter so the list only shows fixtures needing action.

4. **Audit trail preservation**: Ensure PDF → ScheduledMatch → Match → OfficialSnapshot → MatchSquad/StageRoster chain remains intact; no shortcuts.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/App.tsx` | Modified | Add `/fixtures/:fixtureKey/review` route; remove create form from `/matches` |
| `frontend/src/pages/MatchesPage.tsx` | Modified | Remove create match form, remove roster action buttons, keep only list+search |
| `frontend/src/pages/FixtureReviewPage.tsx` | New | New page for PDF review (preview → confirm with identity resolution) |
| `frontend/src/pages/FixtureRosterPage.tsx` | Modified | Accept navigation from review flow; ensure full entity creation on resolve |
| `frontend/src/api/client.ts` | Modified | Add `reviewFixturePDF`, `confirmFixturePDF` helpers; ensure filter param on `getFixtures` |
| `backend/pdf_routes.py` | Modified | Add `result_status != 'confirmed'` filter to `/pdf/fixtures`; ensure confirm creates full chain |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Backfill creates duplicate Match/OfficialSnapshot if run twice | Medium | Idempotency check: if `linked_match_id` exists, skip or update in place |
| Analyst identity decisions lost if page refreshes mid-flow | Low | Persist choices to localStorage until resolution submitted |
| Breaking existing manual match creation | Low | Keep `/matches` create form as separate "Nuevo partido manual" route if needed |
| Competition layer traceability broken | Low | Explicitly verify `official_snapshot_id` and `linked_match_id` set on ScheduledFixture |

## Rollback Plan

1. Revert `App.tsx` routes to previous state
2. Restore `MatchesPage.tsx` with create form and roster actions
3. Delete `FixtureReviewPage.tsx`
4. Revert `getFixtures` filter change in `client.ts` and backend
5. If backfill ran: delete created Match, OfficialSnapshot, MatchSquad, StageRoster records for the specific fixture; reset `linked_match_id` and `official_snapshot_id` to null on ScheduledFixture

## Dependencies

- Backend endpoints `/pdf/fixture-preview`, `/pdf/fixture-confirm`, `/pdf/fixtures/{key}/roster-resolution` must exist and work (confirmed in codebase)
- PDF `7164158c7b0e9b17.pdf` must be present in `resources/planillas/` and indexed

## Success Criteria

- [ ] Backfill completes: PDF `7164158c7b0e9b17.pdf` → Match created + OfficialSnapshot created + MatchSquad populated (both sides) + StageRoster populated → `/match/{id}/analysis` loads with full squad dropdowns
- [ ] `/matches` shows only fixture list with search/filter, no create form, no "Resolver planilla" buttons
- [ ] `/fixtures/{key}/review` shows PDF preview → confirm step with explicit identity resolution → on success navigates to `/fixtures/{key}/roster` or directly to `/match/{id}/analysis` if roster ready
- [ ] Fixture list on `/matches` and `/fixtures/{key}/review` excludes `result_status === 'confirmed'`
- [ ] Audit trail verified: PDF → ScheduledMatch → Match → OfficialSnapshot → MatchSquad/StageRoster all linked