# Integration Verification Checklist: backfill-players-ux-separation

**Change**: backfill-players-ux-separation  
**Date**: 2026-08-28  
**Verified By**: SDD Apply Phase 5

---

## 5.1 Backfill Script Idempotency Verification

### Command Executed
```bash
python backend/scripts/backfill_planilla_7164158c7b0e9b17.py --database-url postgresql://postgres:postgres@localhost:5435/sapa_stats --auto-create
```

### Results
- ✅ **Idempotent path triggered**: "Idempotent path: Match already exists"
- ✅ **Match reused**: Match ID 98
- ✅ **OfficialSnapshot reused**: ID 11cc224a-939f-4566-979d-a5348379def8
- ✅ **No new entities created** (reused=true equivalent)
- ✅ **All verifications passed**:
  - MatchSquad entries: 30 (14 home + 16 away)
  - StageRoster entries: 30 (14 home + 16 away)
  - All OfficialSnapshotPlayer rows have player_id ✓
  - SHA256 matches PDF: 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3 ✓

---

## 5.2 End-to-End Manual Verification Checklist

### Step 1: Navigate `/matches` — Verify List Only

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Page loads without create match form | No date picker, no team selectors, no score inputs, no tournament selector | | ☐ |
| Search input works | Filter fixtures by text | | ☐ |
| Stage filter works | Filter by tournament stage | | ☐ |
| Pagination works | Navigate between pages | | ☐ |
| `roster_status` badge displayed | Shows: not_confirmed / needs_identity_resolution / ready | | ☐ |
| `unresolved_roster_players` count displayed | Numeric count per row | | ☐ |
| No "Resolver planilla" (Wrench) button | Action button removed | | ☐ |
| No "Abrir análisis" (Play) button | Action button removed | | ☐ |
| Rows are informational only | Teams, date, score, stage, status badge | | ☐ |

**Notes**: Frontend changes from Phase 3 (tasks 3.3, 3.4) must be deployed for this to work.

---

### Step 2: Navigate `/fixtures/{key}/review` — Preview & Confirm

**Fixture Key**: `planilla:333556da:1`

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Page loads preview data | GET /fixtures/{key}/review returns FixturePreviewResult | | ☐ |
| Home compatibility badge shown | compatible / incompatible / unresolved | | ☐ |
| Away compatibility badge shown | compatible / incompatible / unresolved | | ☐ |
| Score reconciliation badge shown | match / mismatch / unknown | | ☐ |
| Parsed PDF teams displayed | S.A.P.A. (home) vs Villa Calzada (away) | | ☐ |
| Registered fixture teams displayed | S.A.P.A. vs Villa Calzada | | ☐ |
| "Confirmar" button enabled | When compatible | | ☐ |
| Click "Confirmar" → POST /fixtures/{key}/review | Returns {match_id, snapshot_id, reused: true} | | ☐ |
| Redirect to `/fixtures/{key}/roster` | Navigation works | | ☐ |

---

### Step 3: Navigate `/fixtures/{key}/roster` — Resolve Identities

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Page loads roster data | GET /pdf/fixtures/{key}/roster returns FixtureRosterRead | | ☐ |
| All 30 players shown (14 home + 16 away) | Player names, jerseys, sides | | ☐ |
| Player identity resolution UI works | Link to existing or create new | | ☐ |
| POST /fixtures/{key}/roster-resolution succeeds | MatchSquad + StageRoster updated | | ☐ |
| MatchSquad created for both sides | 30 entries | | ☐ |
| StageRoster created per registration | 14 home (reg 139) + 16 away (reg 122) | | ☐ |

---

### Step 4: Navigate `/match/{id}/analysis` — Squad Dropdowns & Event Tagging

**Match ID**: 98

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Page loads without errors | /match/98/analysis renders | | ☐ |
| Home squad dropdown populated | 14 players with names + jerseys | | ☐ |
| Away squad dropdown populated | 16 players with names + jerseys | | ☐ |
| Event tagging enabled | Can add goals, cards, 2min suspensions | | ☐ |
| Player selection works | Dropdown selection triggers events | | ☐ |

---

## 5.3 Audit Trail Integrity Verification

See [Audit Trail Verification](audit-trail-verification.md) for detailed SQL queries and results.

### Summary
| Link | Verified |
|------|----------|
| ScheduledMatch.analysis_match → Match | ✅ |
| Match → OfficialSnapshot (is_confirmed=true) | ✅ |
| OfficialSnapshot → OfficialSnapshotPlayer[] (30 players) | ✅ |
| OfficialSnapshotPlayer.player_id → Player (all 30 resolved) | ✅ |
| OfficialSnapshotPlayer → MatchSquad (30 entries) | ✅ |
| OfficialSnapshotPlayer → StageRoster (30 entries, 2 registrations) | ✅ |
| OfficialSnapshot.source_sha256 = PDF SHA256 | ✅ |

---

## 5.4 Rollback Validation

See [Rollback Documentation](rollback-backfill-players-ux-separation.md) for exact SQL statements.

### Rollback Commands Documented
- ✅ Delete MatchSquad entries for Match ID 98
- ✅ Delete StageRoster entries for registrations 139, 122
- ✅ Delete OfficialSnapshotPlayer entries for Snapshot ID 11cc224a-939f-4566-979d-a5348379def8
- ✅ Delete OfficialSnapshot ID 11cc224a-939f-4566-979d-a5348379def8
- ✅ Delete Match ID 98
- ✅ Reset ScheduledMatch.analysis_match to NULL for fixture ID 95
- ✅ Frontend revert: Restore MatchesPage create form, action buttons, FixtureReviewPage removal

---

## Overall Status

| Phase | Task | Status |
|-------|------|--------|
| 5.1 | Backfill idempotency | ✅ Complete |
| 5.2 | E2E manual verification | ☐ Pending (requires frontend deployment) |
| 5.3 | Audit trail integrity | ✅ Complete |
| 5.4 | Rollback documentation | ✅ Complete |

---

**Next Steps**: Deploy frontend changes (Phase 3) and complete manual E2E verification (5.2).