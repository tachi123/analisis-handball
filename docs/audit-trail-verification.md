# Audit Trail Verification: backfill-players-ux-separation

**Change**: backfill-players-ux-separation  
**Date**: 2026-08-28  
**Fixture**: `planilla:333556da:1` (PDF: 7164158c7b0e9b17.pdf)  
**SHA256**: 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3

---

## Entity Chain Verification

```
PDF (SHA256: 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3)
    ↓ [FixtureImportEntry links to ScheduledMatch]
ScheduledMatch (id=95, fixture_key=planilla:333556da:1, result_status=reported)
    ↓ [analysis_match_id=98]
Match (id=98, scheduled_match_id=95, home_team_id=8, away_team_id=25, 24-25)
    ↓ [creates]
OfficialSnapshot (id=11cc224a-939f-4566-979d-a5348379def8, match_id=98, is_confirmed=true)
    ↓ [creates per parsed player]
OfficialSnapshotPlayer[] (30 players, all player_id SET)
    ↓ [resolve_fixture_roster() per row]
    ├─→ Player (30 players created/linked) → OfficialSnapshotPlayer.player_id SET
    ├─→ MatchSquad (30 entries)  ← _upsert_roster_entries()
    └─→ StageRoster (30 entries, 2 registrations)  ← _upsert_roster_entries()
```

---

## SQL Queries and Results

### 1. ScheduledMatch → analysis_match

```sql
SELECT 
    id,
    fixture_key,
    result_status,
    analysis_match_id
FROM scheduled_matches
WHERE fixture_key = 'planilla:333556da:1';
```

**Result**:
| id | fixture_key | result_status | analysis_match_id |
|----|-------------|---------------|-------------------|
| 95 | planilla:333556da:1 | reported | 98 |

✅ **Link intact**: `analysis_match_id = 98` points to Match

---

### 2. Match ← scheduled_match_id

```sql
SELECT 
    id,
    scheduled_match_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score
FROM matches
WHERE id = 98;
```

**Result**:
| id | scheduled_match_id | home_team_id | away_team_id | home_score | away_score |
|----|-------------------|--------------|--------------|------------|------------|
| 98 | 95 | 8 | 25 | 24 | 25 |

✅ **Link intact**: `scheduled_match_id = 95` points back to ScheduledMatch

---

### 3. OfficialSnapshot → match_id + SHA256

```sql
SELECT 
    id,
    match_id,
    source_sha256,
    is_confirmed,
    home_team_name,
    away_team_name,
    home_score,
    away_score
FROM official_snapshots
WHERE match_id = 98 AND is_confirmed = true;
```

**Result**:
| id | match_id | source_sha256 | is_confirmed | home_team_name | away_team_name | home_score | away_score |
|----|----------|---------------|--------------|----------------|----------------|------------|------------|
| 11cc224a-939f-4566-979d-a5348379def8 | 98 | 333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3 | true | S.A.P.A. | C.A. y S. Villa Calzada | 24 | 25 |

✅ **Link intact**: `match_id = 98`, `is_confirmed = true`, `source_sha256` matches PDF

---

### 4. OfficialSnapshotPlayer → snapshot_id + player_id (all resolved)

```sql
SELECT 
    id,
    snapshot_id,
    side,
    name,
    jersey_number,
    player_id,
    official_goals,
    official_yellow,
    official_2min,
    official_red,
    official_blue
FROM official_snapshot_players
WHERE snapshot_id = '11cc224a-939f-4566-979d-a5348379def8'
ORDER BY side, jersey_number;
```

**Result** (30 rows, all `player_id` NOT NULL):
| id | side | name | jersey | player_id | goals | yellow | 2min | red | blue |
|----|------|------|--------|-----------|-------|--------|------|-----|------|
| 2757 | home | Ramirez Lorca, Jaime Nahuel | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| 2758 | home | Ruano, Matheo | 2 | 3 | 2 | 0 | 0 | 0 | 0 |
| 2759 | home | Gonzalez, Ezequiel Matias | 10 | 4 | 1 | 0 | 0 | 0 | 0 |
| 2760 | home | Sarrailh, Pablo Eduardo | 11 | 5 | 2 | 0 | 1 | 0 | 0 |
| 2761 | home | Ramirez, Nicolas | 13 | 6 | 1 | 0 | 0 | 0 | 0 |
| 2762 | home | Correa, Marcos Isauro | 33 | 7 | 0 | 0 | 0 | 0 | 0 |
| 2763 | home | Delpieri, Mateo | 38 | 8 | 3 | 0 | 1 | 0 | 0 |
| 2764 | home | Peralta, Juan Ignacio | 43 | 9 | 0 | 0 | 0 | 0 | 0 |
| 2765 | home | Chavez, Alexis Ezequiel | 66 | 10 | 0 | 0 | 0 | 0 | 0 |
| 2766 | home | Gayoso Silva, Michel Javier | 76 | 11 | 0 | 0 | 0 | 0 | 0 |
| 2767 | home | Ramirez, Gaston | 80 | 12 | 0 | 0 | 1 | 0 | 0 |
| 2768 | home | Mollo Skripnik Strelecki, Lucian... | 87 | 13 | 0 | 0 | 0 | 0 | 0 |
| 2769 | home | Ferrari, Jonas Horacio | 97 | 14 | 6 | 0 | 0 | 0 | 0 |
| 2770 | home | Romero Boeris, Sebastian | 98 | 15 | 9 | 0 | 0 | 0 | 0 |
| 2771 | away | Robledo, Franco Daniel | 3 | 16 | 9 | 0 | 0 | 0 | 0 |
| 2772 | away | Martinese, Tadeo Ricardo | 5 | 17 | 0 | 0 | 0 | 0 | 0 |
| 2773 | away | Paez Martinez, Leandro Marcel... | 8 | 18 | 1 | 0 | 1 | 0 | 0 |
| 2774 | away | Sosa, Juan Ignacio | 9 | 19 | 1 | 0 | 1 | 0 | 0 |
| 2775 | away | Navarro, Maximiliano Agustin | 13 | 20 | 0 | 0 | 0 | 0 | 0 |
| 2776 | away | Gerez, Nicolas Ezequiel | 18 | 21 | 0 | 0 | 0 | 0 | 0 |
| 2777 | away | Sandoval, Gonzalo Matias | 19 | 22 | 2 | 0 | 1 | 0 | 0 |
| 2778 | away | Seip, Benegas Gustavo Gabriel | 21 | 23 | 1 | 0 | 0 | 0 | 0 |
| 2779 | away | Solis, Demian Nicolas | 22 | 24 | 2 | 0 | 0 | 0 | 0 |
| 2780 | away | Belizan Quiroga, Matias Agusti... | 24 | 25 | 0 | 0 | 0 | 0 | 0 |
| 2781 | away | Bandeo, Alexis Agustin | 25 | 26 | 7 | 0 | 0 | 0 | 0 |
| 2782 | away | Coronel Besada, Ciro | 31 | 27 | 1 | 0 | 0 | 0 | 0 |
| 2783 | away | Galvan, Lautaro Andres | 32 | 28 | 0 | 0 | 0 | 0 | 0 |
| 2784 | away | Alvarez, Rodrigo Yamil | 40 | 29 | 0 | 0 | 0 | 0 | 0 |
| 2785 | away | Astorga, Mauricio Adrian | 44 | 30 | 1 | 0 | 1 | 0 | 0 |
| 2786 | away | Di Pilato, Lucas Gabriel | 99 | 31 | 0 | 0 | 0 | 0 | 0 |

✅ **All 30 players resolved**: `player_id` ranges 2–31, no NULLs

---

### 5. MatchSquad → match_id (official stats upserted)

```sql
SELECT 
    id,
    match_id,
    player_id,
    jersey_number,
    official_goals,
    official_yellow,
    official_2min,
    official_red,
    official_blue
FROM match_squad
WHERE match_id = 98
ORDER BY id;
```

**Result** (30 rows):
| id | match_id | player_id | jersey | goals | yellow | 2min | red | blue |
|----|----------|-----------|--------|-------|--------|------|-----|------|
| 2 | 98 | 2 | 1 | 0 | 0 | 0 | 0 | 0 |
| 3 | 98 | 3 | 2 | 2 | 0 | 0 | 0 | 0 |
| 4 | 98 | 4 | 10 | 1 | 0 | 0 | 0 | 0 |
| 5 | 98 | 5 | 11 | 2 | 0 | 1 | 0 | 0 |
| 6 | 98 | 6 | 13 | 1 | 0 | 0 | 0 | 0 |
| 7 | 98 | 7 | 33 | 0 | 0 | 0 | 0 | 0 |
| 8 | 98 | 8 | 38 | 3 | 0 | 1 | 0 | 0 |
| 9 | 98 | 9 | 43 | 0 | 0 | 0 | 0 | 0 |
| 10 | 98 | 10 | 66 | 0 | 0 | 0 | 0 | 0 |
| 11 | 98 | 11 | 76 | 0 | 0 | 0 | 0 | 0 |
| 12 | 98 | 12 | 80 | 0 | 0 | 1 | 0 | 0 |
| 13 | 98 | 13 | 87 | 0 | 0 | 0 | 0 | 0 |
| 14 | 98 | 14 | 97 | 6 | 0 | 0 | 0 | 0 |
| 15 | 98 | 15 | 98 | 9 | 0 | 0 | 0 | 0 |
| 16 | 98 | 16 | 3 | 9 | 0 | 0 | 0 | 0 |
| 17 | 98 | 17 | 5 | 0 | 0 | 0 | 0 | 0 |
| 18 | 98 | 18 | 8 | 1 | 0 | 1 | 0 | 0 |
| 19 | 98 | 19 | 9 | 1 | 0 | 1 | 0 | 0 |
| 20 | 98 | 20 | 13 | 0 | 0 | 0 | 0 | 0 |
| 21 | 98 | 21 | 18 | 0 | 0 | 0 | 0 | 0 |
| 22 | 98 | 22 | 19 | 2 | 0 | 1 | 0 | 0 |
| 23 | 98 | 23 | 21 | 1 | 0 | 0 | 0 | 0 |
| 24 | 98 | 24 | 22 | 2 | 0 | 0 | 0 | 0 |
| 25 | 98 | 25 | 24 | 0 | 0 | 0 | 0 | 0 |
| 26 | 98 | 26 | 25 | 7 | 0 | 0 | 0 | 0 |
| 27 | 98 | 27 | 31 | 1 | 0 | 0 | 0 | 0 |
| 28 | 98 | 28 | 32 | 0 | 0 | 0 | 0 | 0 |
| 29 | 98 | 29 | 40 | 0 | 0 | 0 | 0 | 0 |
| 30 | 98 | 30 | 44 | 1 | 0 | 1 | 0 | 0 |
| 31 | 98 | 31 | 99 | 0 | 0 | 0 | 0 | 0 |

✅ **30 MatchSquad entries**: Matches roster count (14 home + 16 away)

---

### 6. StageRoster → registration_id (per team registration)

```sql
SELECT 
    sr.id,
    sr.registration_id,
    sr.player_id,
    sr.jersey_number,
    tr.competition_team_id,
    ct.club_id,
    c.name as club_name
FROM stage_rosters sr
JOIN team_registrations tr ON sr.registration_id = tr.id
JOIN competition_teams ct ON tr.competition_team_id = ct.id
JOIN clubs c ON ct.club_id = c.id
WHERE tr.id IN (
    SELECT home_registration_id FROM scheduled_matches WHERE id = 95
    UNION
    SELECT away_registration_id FROM scheduled_matches WHERE id = 95
)
ORDER BY sr.registration_id, sr.jersey_number;
```

**Result** (30 rows):
| id | registration_id | player_id | jersey | competition_team_id | club_id | club_name |
|----|-----------------|-----------|--------|---------------------|---------|-----------|
| 1 | 139 | 2 | 1 | 23 | 8 | S.A.P.A. |
| 2 | 139 | 3 | 2 | 23 | 8 | S.A.P.A. |
| 3 | 139 | 4 | 10 | 23 | 8 | S.A.P.A. |
| 4 | 139 | 5 | 11 | 23 | 8 | S.A.P.A. |
| 5 | 139 | 6 | 13 | 23 | 8 | S.A.P.A. |
| 6 | 139 | 7 | 33 | 23 | 8 | S.A.P.A. |
| 7 | 139 | 8 | 38 | 23 | 8 | S.A.P.A. |
| 8 | 139 | 9 | 43 | 23 | 8 | S.A.P.A. |
| 9 | 139 | 10 | 66 | 23 | 8 | S.A.P.A. |
| 10 | 139 | 11 | 76 | 23 | 8 | S.A.P.A. |
| 11 | 139 | 12 | 80 | 23 | 8 | S.A.P.A. |
| 12 | 139 | 13 | 87 | 23 | 8 | S.A.P.A. |
| 13 | 139 | 14 | 97 | 23 | 8 | S.A.P.A. |
| 14 | 139 | 15 | 98 | 23 | 8 | S.A.P.A. |
| 15 | 122 | 16 | 3 | 24 | 9 | Villa Calzada |
| 16 | 122 | 17 | 5 | 24 | 9 | Villa Calzada |
| 17 | 122 | 18 | 8 | 24 | 9 | Villa Calzada |
| 18 | 122 | 19 | 9 | 24 | 9 | Villa Calzada |
| 19 | 122 | 20 | 13 | 24 | 9 | Villa Calzada |
| 20 | 122 | 21 | 18 | 24 | 9 | Villa Calzada |
| 21 | 122 | 22 | 19 | 24 | 9 | Villa Calzada |
| 22 | 122 | 23 | 21 | 24 | 9 | Villa Calzada |
| 23 | 122 | 24 | 22 | 24 | 9 | Villa Calzada |
| 24 | 122 | 25 | 24 | 24 | 9 | Villa Calzada |
| 25 | 122 | 26 | 25 | 24 | 9 | Villa Calzada |
| 26 | 122 | 27 | 31 | 24 | 9 | Villa Calzada |
| 27 | 122 | 28 | 32 | 24 | 9 | Villa Calzada |
| 28 | 122 | 29 | 40 | 24 | 9 | Villa Calzada |
| 29 | 122 | 30 | 44 | 24 | 9 | Villa Calzada |
| 30 | 122 | 31 | 99 | 24 | 9 | Villa Calzada |

✅ **30 StageRoster entries**: 14 for registration 139 (S.A.P.A.), 16 for registration 122 (Villa Calzada)

---

## SHA256 Verification

```sql
SELECT source_sha256 FROM official_snapshots WHERE id = '11cc224a-939f-4566-979d-a5348379def8';
```

**Result**: `333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3`

**Expected**: `333556da08f99ab942a23426cad608f619fdd5dc4675be6d464f5583e4cac8a3`

✅ **MATCH CONFIRMED**

---

## Summary: All Links Intact

| Link | Source | Target | Verified |
|------|--------|--------|----------|
| ScheduledMatch → Match | `analysis_match_id = 98` | Match.id = 98 | ✅ |
| Match → ScheduledMatch | `scheduled_match_id = 95` | ScheduledMatch.id = 95 | ✅ |
| Match → OfficialSnapshot | `match_id = 98` | OfficialSnapshot.match_id = 98 | ✅ |
| OfficialSnapshot → Players | `snapshot_id` | 30 OfficialSnapshotPlayer rows | ✅ |
| OfficialSnapshotPlayer → Player | `player_id` (2–31) | Player.id | ✅ |
| OfficialSnapshotPlayer → MatchSquad | `player_id` | MatchSquad.player_id | ✅ |
| OfficialSnapshotPlayer → StageRoster | `player_id` + registration | StageRoster.player_id | ✅ |
| PDF SHA256 → OfficialSnapshot | `source_sha256` | 333556da...cac8a3 | ✅ |

---

## Counts Verification

| Entity | Expected | Actual | Status |
|--------|----------|--------|--------|
| OfficialSnapshotPlayer | 30 (14 home + 16 away) | 30 | ✅ |
| MatchSquad | 30 | 30 | ✅ |
| StageRoster (home/reg 139) | 14 | 14 | ✅ |
| StageRoster (away/reg 122) | 16 | 16 | ✅ |
| StageRoster total | 30 | 30 | ✅ |
| Players with player_id=NULL | 0 | 0 | ✅ |