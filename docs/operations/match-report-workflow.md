# Complete Match-to-Report Workflow

Use this runbook to turn a reviewed match into a safe public static report.

## Quick path

1. Finish both periods in private review.
2. Confirm coverage and canonical events.
3. Explicitly approve any official-sheet PDFs that may appear publicly.
4. Export the complete public report catalog.
5. Run report tests and build.
6. Review the static report locally before any push.

## Complete-match checklist

| Check | Expected result |
|---|---|
| Period 1 | `kickoff` and `period_end` exist |
| Period 2 | `kickoff` and `period_end` exist |
| Coverage | Public export has `analyzed_periods: [1, 2]` and `status: complete` |
| Evidence | Incidents have video anchors when video review is expected |
| Goalkeepers | Team totals reconcile to player-attributed and explicitly unassigned on-target shots |

Do not claim a match is complete merely because the final score is present.

## Record events correctly

- Select the correct period before capture.
- Calibrate the kickoff for every period so the review clock has a reliable baseline.
- Use **Pérdida → Pasivo** only for an observed passive-attack decision. It is an explicit turnover cause and must not be inferred from passing volume.
- Use shot zone **7** for seven metres and **8** for counterattacks. Those zones feed the goalkeeper split metrics.

## Export the public report

The exporter reads active canonical runs and writes privacy-safe static projections, the fallback `report.json`, deterministic per-match files, and `reports.json`. Copy all artifacts from one temporary directory.

```powershell
docker exec -e PUBLIC_REPORT_MATCH_IDS=99,101 -e PUBLIC_REPORT_OUTPUT=/tmp/report.json -e PUBLIC_REPORT_CATALOG_OUTPUT=/tmp/public-report "analisis-handball-backend-1" python /app/scripts/export_public_report_catalog.py
docker cp "analisis-handball-backend-1:/tmp/public-report/." "reports/public"
```

`PUBLIC_REPORT_OUTPUT` writes a compatible single fallback copy. `PUBLIC_REPORT_CATALOG_OUTPUT` is the directory to copy: it contains `report.json`, `reports.json`, and each `report_<public-key>.json`. Do not copy only `/tmp/report.json`, because the catalog and match files are required for multi-match navigation.

The container name can differ locally. Check `docker ps` if necessary.

### Publish an official FEMEBAL sheet

An imported/confirmed PDF stays private by default. Approve it explicitly before
exporting; this is separate from confirming the imported data.

```powershell
# Approve only sheets that may be copied into the public static report.
docker exec "analisis-handball-backend-1" python /app/scripts/set_official_sheet_publication.py --publish 99 101

# Revoke a prior approval. Re-export the catalog afterwards to remove its public copy.
docker exec "analisis-handball-backend-1" python /app/scripts/set_official_sheet_publication.py --unpublish 101
```

During export, the backend resolves the stored confirmed source, verifies its
SHA-256, and copies it to `reports/public/planillas/planilla_<public-key>.pdf`.
The report exposes only that derived relative link: never `resources/`,
`data/pdfs`, snapshot IDs, source filenames, or operational paths.

A confirmed sheet without observed report coverage does **not** create a public
report or PDF link. Finish the canonical analysis first; this prevents an
empty analysis from being presented as a 0–0 result.

## Validate before publishing

```powershell
npm --prefix reports test
npm --prefix reports run build
```

Expected result: the tests pass and `reports/dist/` contains `index.html`, assets, `report.json`, `reports.json`, and the referenced per-match reports.

For canonical rule changes, also run:

```powershell
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py
```

## Public report behavior

| Area | Contract |
|---|---|
| Comparison | The pyramid compares both teams using totals from `team_summary`. |
| Defense | The compact context shows opponent total attempts, goals, conversion, on-target shots, outside/woodwork, and blocks for each defending team. It is not goalkeeper attribution. |
| Goalkeepers | The compact table groups total/team/player rows. Player save rates use assigned on-target shots; the unassigned row is a team-level remainder and never a player performance. |
| Phase 1 | Mini-matches, scoring runs, quick-concession alerts, goalkeeper context, and guarded possession tempo are derived during export. |
| Momentum | The curve uses chronological goals; filters only hide/show markers, never alter the curve. |
| Video | Incident actions seek the persistent player using `video_seconds`; direct YouTube links remain fallback. |
| Coverage | Video-time positions and partial coverage are explicitly disclosed. |

## Local recovery

The backend service does not run with Uvicorn `--reload`. After editing backend Python files, restart it before checking behavior in the browser:

```powershell
docker restart "analisis-handball-backend-1"
```

Restarting the local container does not publish anything.
