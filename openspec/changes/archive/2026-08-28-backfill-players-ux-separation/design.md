# Technical Design: backfill-players-ux-separation

## Overview

This design covers the implementation of:
1. **Backfill Script** — one-off script to execute confirmation for the blocked PDF `7164158c7b0e9b17.pdf`
2. **Backend API Changes** — new endpoints and filter modifications
3. **Frontend Route Changes** — new page, simplified matches page, route updates
4. **Data Flow Integrity** — ensuring the full entity chain is created
5. **Testing Strategy** — verification approach

---

## 1. Backfill Script (`scripts/backfill_planilla_7164158c7b0e9b17.py`)

### Location
`backend/scripts/backfill_planilla_7164158c7b0e9b17.py`

### Architecture
Standalone script using existing `PDFService` methods. Runs outside the HTTP layer with direct database session.

### Steps

```python
# Pseudocode structure
def run_backfill():
    # 1. Locate PDF by SHA256 in manifest.json / derived-fixtures.json
    # 2. Find FixtureImportEntry → ScheduledMatch → fixture_key
    # 3. Load PDF bytes from resources/planillas/.../7164158c7b0e9b17.pdf
    # 4. Call confirm_fixture() with auto team confirmation (teams already matched in derivation)
    # 5. For each roster row with player_id = null:
    #    - Find candidate Player by (team_id, normalized name match)
    #    - Present to analyst (script pauses for input OR reads from CSV mapping)
    #    - Call resolve_fixture_roster() per row
    # 6. Verify: Match created, OfficialSnapshot linked, MatchSquad populated, StageRoster upserted
```

### Idempotency Logic
```python
# Check if ScheduledMatch.analysis_match exists
if fixture.analysis_match:
    # Update path: reuse existing Match + OfficialSnapshot
    # Re-read roster, resolve remaining unresolved players
    pass
else:
    # Create path: full confirmation flow
    pass
```

### Analyst Interaction Modes
1. **Interactive CLI** — prompts for each unresolved player with candidate list
2. **CSV Mapping** — reads `backfill_mapping.csv` with columns: `snapshot_player_id, decision, existing_player_id|new_player_name`

### Integration Points
- Uses `PDFService.fixture_preview()` → `PDFService.confirm_fixture()` → `PDFService.resolve_fixture_roster()`
- Direct DB session via `get_db()` dependency override pattern
- No new service methods — only existing public methods

---

## 2. Backend API Changes (`backend/app/api/routes/pdf.py`)

### New Endpoint: `GET /fixtures/{fixtureKey}/review`
```python
@router.get("/fixtures/{fixture_key}/review", response_model=FixturePreviewResult)
async def review_fixture_pdf(
    fixture_key: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Returns FixturePreviewData (existing FixturePreviewResult from pdf_service.fixture_preview()).
    Reads PDF from indexed location (resources/planillas/.../7164158c7b0e9b17.pdf).
    Rejects 409 if result_status == 'confirmed' or kind == 'bye'.
    """
```

**Implementation notes:**
- Load PDF bytes from disk using the indexed path (from `FixtureImportEntry` or derived fixtures)
- Call `PDFService.fixture_preview(db, fixture_key, file_bytes, filename, content_type)`
- Return the `FixturePreviewResult` schema (already matches `FixturePreviewData`)

### New Endpoint: `POST /fixtures/{fixtureKey}/review`
```python
@router.post("/fixtures/{fixture_key}/review", response_model=FixtureConfirmResult, status_code=201)
async def confirm_fixture_review(
    fixture_key: str,
    confirmation: FixtureConfirmation,  # JSON body (not form)
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("superadmin", "admin")),
):
    """
    Calls PDFService.confirm_fixture() with confirmation data.
    Returns match_id, snapshot_id, reused flag.
    Frontend redirects to /fixtures/{fixtureKey}/roster on success.
    """
```

**Key differences from existing `/pdf/fixture-confirm`:**
- Accepts `FixtureConfirmation` as JSON body (not multipart form)
- PDF bytes loaded from indexed location (not uploaded)
- Used by the review flow where PDF is already known

### Modified Endpoint: `GET /pdf/fixtures`
```python
@router.get("/fixtures", response_model=list[ScheduledFixtureRead])
def list_fixtures(
    status: str = Query("pending", pattern="^(pending|all)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    Added query param `status=pending` (default) filters to result_status != 'confirmed'.
    status=all returns all fixtures (for admin/debug).
    """
    query = PDFService.list_fixtures(db)
    if status == "pending":
        query = [f for f in query if f.result_status != "confirmed"]
    return [PDFService.fixture_read(f) for f in query]
```

### Existing Endpoints (unchanged)
- `GET /fixtures/{fixture_key}/roster` — returns `FixtureRosterRead`
- `POST /fixtures/{fixture_key}/roster-resolution` — calls `resolve_fixture_roster()`
- `POST /fixture-preview` — multipart upload for ad-hoc preview
- `POST /fixture-confirm` — multipart upload for ad-hoc confirm

---

## 3. Frontend Route Changes

### New Route: `/fixtures/:fixtureKey/review`
**File:** `frontend/src/pages/FixtureReviewPage.tsx` (new)

```tsx
// FixtureReviewPage.tsx
export default function FixtureReviewPage() {
  const { fixtureKey } = useParams();
  const navigate = useNavigate();
  
  // 1. Load preview via GET /fixtures/{key}/review
  // 2. Display: parsed PDF data vs fixture registration (compatibility, scores)
  // 3. "Confirmar" button → POST /fixtures/{key}/review with FixtureConfirmation
  //    - Auto-fills home_team_id/away_team_id from fixture registrations
  //    - Player confirmations left empty (identity resolution deferred to roster page)
  // 4. On success: navigate to /fixtures/{fixtureKey}/roster
}
```

**UI Components:**
- Side-by-side: Parsed PDF teams/players vs Registered fixture teams
- Score reconciliation badge (match/mismatch/unknown)
- Compatibility badges per side (compatible/incompatible/unresolved)
- "Confirmar" button (disabled if incompatible)

### Modified: `MatchesPage.tsx`
**Strip to list + search only:**
- Remove: create match form (`showCreate`, date, team selectors, score inputs, tournament selector)
- Remove: "Resolver planilla" link (Wrench button)
- Remove: "Abrir análisis" button (Play button)
- Keep: search input, stage filter, pagination
- Keep: roster_status badge (not_confirmed | needs_identity_resolution | ready)
- Keep: unresolved_roster_players count
- Rows become informational only (teams, date, score, stage, status badge)

### Modified: `App.tsx` Routes
```tsx
<Route path="/matches" element={<MatchesPage />} />
<Route path="/fixtures/:fixtureKey/review" element={<FixtureReviewPage />} />
<Route path="/fixtures/:fixtureKey/roster" element={<FixtureRosterPage />} />
<Route path="/match/:matchId/analysis" element={<MatchAnalysis />} />
// ... other match routes unchanged
```

### Modified: `FixtureRosterPage.tsx`
- Accept navigation from review flow (no code change needed, already uses `fixtureKey` param)
- Ensure it loads roster via `GET /pdf/fixtures/{fixtureKey}/roster` (existing)

---

## 4. Data Flow Integrity

### Entity Creation Chain (Verification Points)

```
PDF (SHA256: 7164158c7b0e9b17)
    ↓ [FixtureImportEntry links to ScheduledMatch]
ScheduledMatch (fixture_key, result_status)
    ↓ [confirm_fixture() creates]
Match (scheduled_match_id=fixture.id, home_team_id, away_team_id, scores)
    ↓ [creates]
OfficialSnapshot (id=uuid, match_id, source_path, source_sha256, is_confirmed=true, home/away team names, scores)
    ↓ [creates per parsed player]
OfficialSnapshotPlayer[] (snapshot_id, side, name, jersey_number, player_id=NULL, official_*)
    ↓ [resolve_fixture_roster() per row]
    ├─→ Player (existing or new) → OfficialSnapshotPlayer.player_id SET
    ├─→ MatchSquad (match_id, player_id, jersey_number, official_*)  ← _upsert_roster_entries()
    └─→ StageRoster (registration_id, player_id, jersey_number)     ← _upsert_roster_entries()
```

### Verification Checklist (Post-Backfill)

| Entity | Query | Expected |
|--------|-------|----------|
| `ScheduledMatch` | `analysis_match_id` not null | ✓ |
| `Match` | `scheduled_match_id` = fixture.id | ✓ |
| `OfficialSnapshot` | `match_id` = match.id, `is_confirmed`=true, `source_sha256`=7164158c7b0e9b17 | ✓ |
| `OfficialSnapshotPlayer` | all rows `player_id` not null | ✓ |
| `MatchSquad` | count = players per side, jersey matches | ✓ |
| `StageRoster` | count = registrations × resolved players, jersey unique per registration | ✓ |

### `_upsert_roster_entries()` — Already Implemented
The method in `pdf_service.py` (lines 212-238) handles:
- `MatchSquad` upsert (create or update official stats)
- `StageRoster` upsert with jersey conflict validation
- Cross-checks: player belongs to fixture side, no duplicate player assignment

**No changes needed** — backfill uses existing `resolve_fixture_roster()` which calls this.

---

## 5. Testing Strategy

### Backfill Script — Integration Test
```python
# backend/tests/test_backfill_7164158c7b0e9b17.py
def test_backfill_creates_full_chain(tmp_path):
    # 1. Run script with test DB seeded with fixture + PDF
    # 2. Verify Match created
    # 3. Verify OfficialSnapshot created with correct SHA256
    # 4. Verify MatchSquad populated (both sides)
    # 5. Verify StageRoster upserted per registration
    # 6. Verify /match/{id}/analysis loads with squad dropdowns
```

**Fixtures needed:**
- Seeded `Season` → `TournamentStage` → `Club` → `CompetitionTeam` → `TeamRegistration` → `ScheduledMatch`
- `FixtureImport` + `FixtureImportEntry` linking PDF SHA256 to ScheduledMatch
- PDF file at `resources/planillas/.../7164158c7b0e9b17.pdf`

### API Contract Tests
```python
# backend/tests/test_pdf_routes.py additions

def test_review_fixture_pdf_returns_preview(tmp_path):
    # GET /fixtures/{key}/review returns FixturePreviewResult
    # Includes compatibility, score_reconciliation

def test_review_fixture_pdf_rejects_confirmed(tmp_path):
    # fixture with result_status='confirmed' → 409 fixture_already_confirmed

def test_review_fixture_pdf_rejects_bye(tmp_path):
    # FixtureImportEntry.kind='bye' → 404

def test_confirm_fixture_review_creates_chain(tmp_path):
    # POST /fixtures/{key}/review with FixtureConfirmation
    # Returns match_id, snapshot_id, reused=false
    # Match + OfficialSnapshot + OfficialSnapshotPlayer[] created

def test_confirm_fixture_review_idempotent(tmp_path):
    # Second POST returns reused=true, no duplicates

def test_list_fixtures_filter_pending(tmp_path):
    # GET /pdf/fixtures?status=pending excludes confirmed
    # GET /pdf/fixtures?status=all includes all
```

### Frontend Component Tests
```tsx
// frontend/src/pages/__tests__/FixtureReviewPage.test.tsx
test('renders preview with compatibility badges', () => {
  // Mock GET /fixtures/{key}/review response
  // Verify home/away compatibility, score reconciliation displayed
});

test('confirm button calls POST and navigates to roster', () => {
  // Mock POST /fixtures/{key}/review success
  // Verify navigate('/fixtures/{key}/roster')
});

// frontend/src/pages/__tests__/MatchesPage.test.tsx
test('shows only list+search, no create form', () => {
  // Verify no date picker, team selectors, score inputs
});

test('shows roster_status badge and unresolved count', () => {
  // Verify badge colors/text for not_confirmed/needs_identity_resolution/ready
});

test('no action buttons on rows', () => {
  // Verify no "Resolver planilla" or "Abrir análisis" links
});
```

---

## 6. File Summary

### New Files
| Path | Purpose |
|------|---------|
| `backend/scripts/backfill_planilla_7164158c7b0e9b17.py` | One-off backfill script |
| `frontend/src/pages/FixtureReviewPage.tsx` | New review page |
| `backend/tests/test_backfill_7164158c7b0e9b17.py` | Backfill integration test |

### Modified Files
| Path | Changes |
|------|---------|
| `backend/app/api/routes/pdf.py` | Add GET/POST `/fixtures/{key}/review`, add `status` filter to `GET /fixtures` |
| `backend/app/schemas.py` | No changes (schemas already exist) |
| `frontend/src/pages/MatchesPage.tsx` | Strip create form, remove action buttons |
| `frontend/src/pages/FixtureRosterPage.tsx` | Accept review flow navigation (no code change) |
| `frontend/src/App.tsx` | Add `/fixtures/:fixtureKey/review` route |
| `frontend/src/api/client.ts` | Add `reviewFixturePDF`, `confirmFixturePDF` helpers; add `status` param to `getFixtures` |

### Unchanged (Verified Working)
- `backend/app/services/pdf_service.py` — all required methods exist
- `backend/app/models.py` — schema supports full chain
- `frontend/src/pages/MatchAnalysis.tsx` — no changes needed

---

## 7. Rollback Plan

1. Revert `App.tsx` routes to previous state
2. Restore `MatchesPage.tsx` with create form and roster actions
3. Delete `FixtureReviewPage.tsx`
4. Revert `getFixtures` filter change in `client.ts` and `pdf.py`
5. If backfill ran: delete created `Match`, `OfficialSnapshot`, `MatchSquad`, `StageRoster` for the fixture; reset `linked_match_id` and `official_snapshot_id` to null on `ScheduledMatch`

---

## 8. Dependencies & Prerequisites

- ✅ Backend endpoints `/pdf/fixture-preview`, `/pdf/fixture-confirm`, `/pdf/fixtures/{key}/roster-resolution` exist
- ✅ PDF `7164158c7b0e9b17.pdf` present in `resources/planillas/2026_Apertura_Zona_A _Mayores_3º_División_Masculino/`
- ✅ PDF indexed in `manifest.json` and `derived-fixtures.json`
- ✅ `FixtureImportEntry` links PDF SHA256 to `ScheduledMatch`
- ✅ `PDFService._upsert_roster_entries()` creates `MatchSquad` + `StageRoster`

---

## 9. Success Criteria (from Spec)

- [ ] Backfill completes: PDF → Match + OfficialSnapshot + MatchSquad (both sides) + StageRoster → `/match/{id}/analysis` loads with full squad dropdowns
- [ ] `/matches` shows only fixture list with search/filter, no create form, no action buttons
- [ ] `/fixtures/{key}/review` shows PDF preview → confirm with explicit identity resolution → navigates to `/fixtures/{key}/roster` or `/match/{id}/analysis`
- [ ] Fixture list excludes `result_status === 'confirmed'`
- [ ] Audit trail verified: PDF → FixtureImportEntry → ScheduledMatch → Match → OfficialSnapshot → OfficialSnapshotPlayer → MatchSquad/StageRoster all linked