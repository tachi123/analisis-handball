# Rollback Documentation: backfill-players-ux-separation

**Change**: backfill-players-ux-separation  
**Date**: 2026-08-28  
**Purpose**: Exact SQL and steps to rollback the backfill if needed

---

## Context

The backfill script created the following entities for fixture `planilla:333556da:1` (PDF: 7164158c7b0e9b17.pdf, SHA256: 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3):

| Entity | ID(s) |
|--------|-------|
| Match | 98 |
| OfficialSnapshot | 11cc224a-939f-4566-979d-a5348379def8 |
| OfficialSnapshotPlayer | 2757–2786 (30 rows) |
| MatchSquad | 2–31 (30 rows) |
| StageRoster | 1–30 (30 rows, registrations 139 & 122) |
| Player | 2–31 (30 players created during backfill) |
| ScheduledMatch link | fixture.id=95 → analysis_match_id=98 |

---

## Rollback SQL (Execute in Order)

### Step 1: Delete MatchSquad entries
```sql
DELETE FROM match_squad WHERE match_id = 98;
```
**Expected**: 30 rows deleted

### Step 2: Delete StageRoster entries
```sql
DELETE FROM stage_rosters WHERE registration_id IN (139, 122);
```
**Expected**: 30 rows deleted (14 for reg 139, 16 for reg 122)

### Step 3: Delete OfficialSnapshotPlayer entries
```sql
DELETE FROM official_snapshot_players WHERE snapshot_id = '11cc224a-939f-4566-979d-a5348379def8';
```
**Expected**: 30 rows deleted

### Step 4: Delete OfficialSnapshot
```sql
DELETE FROM official_snapshots WHERE id = '11cc224a-939f-4566-979d-a5348379def8';
```
**Expected**: 1 row deleted

### Step 5: Delete Match
```sql
DELETE FROM matches WHERE id = 98;
```
**Expected**: 1 row deleted

### Step 6: Reset ScheduledMatch links
```sql
UPDATE scheduled_matches 
SET analysis_match_id = NULL 
WHERE id = 95;
```
**Expected**: 1 row updated (analysis_match_id set to NULL)

### Step 7: Delete Players (Optional — only if players were created solely for this backfill)

**Check if players have other references first:**
```sql
SELECT p.id, p.name, p.team_id,
       (SELECT COUNT(*) FROM match_squad WHERE player_id = p.id) as match_squad_count,
       (SELECT COUNT(*) FROM stage_rosters WHERE player_id = p.id) as stage_roster_count,
       (SELECT COUNT(*) FROM official_snapshot_players WHERE player_id = p.id) as snapshot_player_count
FROM players p
WHERE p.id BETWEEN 2 AND 31;
```

If all counts are 0 (after steps 1–5), safe to delete:
```sql
DELETE FROM players WHERE id BETWEEN 2 AND 31;
```
**Expected**: 30 rows deleted (only if no other references exist)

---

## Verification After Rollback

```sql
-- Verify ScheduledMatch link cleared
SELECT id, fixture_key, result_status, analysis_match_id 
FROM scheduled_matches WHERE id = 95;
-- Expect: analysis_match_id = NULL

-- Verify no orphaned entities
SELECT COUNT(*) FROM matches WHERE scheduled_match_id = 95;
-- Expect: 0

SELECT COUNT(*) FROM official_snapshots WHERE match_id = 98;
-- Expect: 0

SELECT COUNT(*) FROM match_squad WHERE match_id = 98;
-- Expect: 0

SELECT COUNT(*) FROM stage_rosters WHERE registration_id IN (139, 122);
-- Expect: 0 (or original pre-backfill count if any)
```

---

## Frontend Rollback (If Frontend Changes Reverted)

If the frontend changes from Phase 3 are reverted, the `MatchesPage` should revert to previous state:

### Files to Restore (from git history)
| File | Action |
|------|--------|
| `frontend/src/pages/MatchesPage.tsx` | Restore create match form (`showCreate`, date picker, team selectors, score inputs, tournament selector) |
| `frontend/src/pages/MatchesPage.tsx` | Restore "Resolver planilla" (Wrench) and "Abrir análisis" (Play) action buttons |
| `frontend/src/pages/FixtureReviewPage.tsx` | **Delete** this file (new page) |
| `frontend/src/App.tsx` | Remove route: `<Route path="/fixtures/:fixtureKey/review" element={<FixtureReviewPage />} />` |
| `frontend/src/api/client.ts` | Remove `reviewFixturePDF`, `confirmFixturePDF` helpers; remove `status` param from `getFixtures` |

### Backend Rollback (If API Changes Reverted)

| File | Action |
|------|--------|
| `backend/app/api/routes/pdf.py` | Remove `GET /fixtures/{fixtureKey}/review` endpoint |
| `backend/app/api/routes/pdf.py` | Remove `POST /fixtures/{fixtureKey}/review` endpoint |
| `backend/app/api/routes/pdf.py` | Revert `GET /pdf/fixtures` — remove `status` query param filter |
| `backend/tests/test_pdf_routes.py` | Remove test additions for new endpoints |

### Backfill Script & Tests
| File | Action |
|------|--------|
| `backend/scripts/backfill_planilla_7164158c7b0e9b17.py` | Delete (one-off script) |
| `backend/tests/test_backfill_7164158c7b0e9b17.py` | Delete |
| `backend/scripts/backfill_7164158c7b0e9b17_mapping.csv` | Delete if exists |

---

## Rollback Boundaries by Task

| Task Range | Rollback Action |
|------------|-----------------|
| 1.1–1.2 | Run SQL Steps 1–7 above; delete backfill script & test |
| 2.1–2.4 | Revert `pdf.py` endpoints; revert `test_pdf_routes.py` |
| 3.1–3.5 | Delete `FixtureReviewPage.tsx`; revert `MatchesPage.tsx`; revert `App.tsx` routes; revert `client.ts` |
| 4.1–4.2 | Delete test files |
| 5.1–5.4 | N/A (verification only) |

---

## Safety Notes

1. **Always backup database** before running rollback SQL
2. **Run in transaction** if possible:
   ```sql
   BEGIN;
   -- Steps 1-6
   COMMIT; -- or ROLLBACK if issues
   ```
3. **Player deletion (Step 7)** is optional and risky — only run if confirmed no other matches/rosters reference these players
4. **Frontend rollback** requires git revert or manual restore — coordinate with deployment
5. **FixtureImportEntry and derived fixtures** are NOT modified by backfill — no rollback needed

---

## Quick Rollback Script (Bash)

```bash
#!/bin/bash
# rollback-backfill.sh
# Run from repo root with DATABASE_URL set

DB_URL="postgresql://postgres:postgres@localhost:5435/sapa_stats"

psql "$DB_URL" << 'EOF'
BEGIN;

-- Step 1: MatchSquad
DELETE FROM match_squad WHERE match_id = 98;

-- Step 2: StageRoster
DELETE FROM stage_rosters WHERE registration_id IN (139, 122);

-- Step 3: OfficialSnapshotPlayer
DELETE FROM official_snapshot_players WHERE snapshot_id = '11cc224a-939f-4566-979d-a5348379def8';

-- Step 4: OfficialSnapshot
DELETE FROM official_snapshots WHERE id = '11cc224a-939f-4566-979d-a5348379def8';

-- Step 5: Match
DELETE FROM matches WHERE id = 98;

-- Step 6: Reset ScheduledMatch
UPDATE scheduled_matches SET analysis_match_id = NULL WHERE id = 95;

COMMIT;
EOF

echo "Rollback complete. Verify with:"
echo "  psql \"$DB_URL\" -c \"SELECT id, analysis_match_id FROM scheduled_matches WHERE id = 95;\""
```