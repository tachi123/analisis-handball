# Backend scripts reference

Use scripts for repeatable imports and static report generation. Do not use a script to bypass canonical validation or private/public boundaries.

## Public report scripts

| Script | Purpose | Inputs |
|---|---|---|
| `export_report.py` | Export one active match into public-safe JSON and update a catalog directory | `PUBLIC_REPORT_MATCH_ID`, `PUBLIC_REPORT_OUTPUT`, `PUBLIC_REPORT_CATALOG_OUTPUT` |
| `export_public_report_catalog.py` | Export one or more active matches into the same catalog directory | `PUBLIC_REPORT_MATCH_IDS` plus the output variables |
| `set_official_sheet_publication.py` | Explicitly approve or revoke confirmed official-sheet PDFs for public export | `--publish` or `--unpublish`, followed by match IDs |

### One match

```powershell
docker exec -e PUBLIC_REPORT_MATCH_ID=101 -e PUBLIC_REPORT_OUTPUT=/tmp/report.json -e PUBLIC_REPORT_CATALOG_OUTPUT=/tmp/public-report "analisis-handball-backend-1" python /app/scripts/export_report.py
```

### Multiple matches

```powershell
docker exec -e PUBLIC_REPORT_MATCH_IDS=99,101 -e PUBLIC_REPORT_OUTPUT=/tmp/report.json -e PUBLIC_REPORT_CATALOG_OUTPUT=/tmp/public-report "analisis-handball-backend-1" python /app/scripts/export_public_report_catalog.py
docker cp "analisis-handball-backend-1:/tmp/public-report/." "reports/public"
```

The catalog directory contains the fallback `report.json`, public catalog `reports.json`, and one deterministic public-key report file per match. Copy the complete directory.

### Official-sheet publication

```powershell
docker exec "analisis-handball-backend-1" python /app/scripts/set_official_sheet_publication.py --publish 99 101
```

Approval is per confirmed snapshot and defaults to private. The exporter verifies
the stored source SHA-256 before copying an approved PDF to the derived public
`planillas/` directory. Run the catalog export after publishing or revoking.

## Import and fixture scripts

| Script | Purpose |
|---|---|
| `discover_planillas.py` | Discover official-sheet candidates. |
| `index_planillas.py` | Index planilla source metadata. |
| `load_planilla_official.py` | Load/confirm official-sheet data. |
| `derive_planilla_fixtures.py` | Derive fixtures from imported official data. |
| `group_planilla_players.py` | Group official player data. |
| `seed_fixture.py` | Development fixture seed only. |
| `bootstrap_official_3m_competition.py` | Bootstrap a known competition import. |

Treat one-off `backfill_*.py` files as migration/recovery artifacts, not normal operational commands.

## Validate after a script changes data

```powershell
npm --prefix reports test
npm --prefix reports run build
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py tests/test_analysis_run_service.py tests/test_migrations.py
```
