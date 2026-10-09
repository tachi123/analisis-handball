# Complete Match-to-Report Workflow

Use this runbook to turn a reviewed match into a safe public static report.

## Quick path

1. Finish both periods in private review.
2. Confirm coverage and canonical events.
3. Export `reports/public/report.json`.
4. Run report tests and build.
5. Review the static report locally before any push.

## Complete-match checklist

| Check | Expected result |
|---|---|
| Period 1 | `kickoff` and `period_end` exist |
| Period 2 | `kickoff` and `period_end` exist |
| Coverage | Public export has `analyzed_periods: [1, 2]` and `status: complete` |
| Evidence | Incidents have video anchors when video review is expected |
| Goalkeepers | Assigned on-target shots reconcile to saves plus goals conceded |

Do not claim a match is complete merely because the final score is present.

## Record events correctly

- Select the correct period before capture.
- Calibrate the kickoff for every period so the review clock has a reliable baseline.
- Use **Pérdida → Pasivo** only for an observed passive-attack decision. It is an explicit turnover cause and must not be inferred from passing volume.
- Use shot zone **7** for seven metres and **8** for counterattacks. Those zones feed the goalkeeper split metrics.

## Export the public report

The exporter reads canonical eligible events and writes a privacy-safe, static projection.

```powershell
docker exec -e PUBLIC_REPORT_OUTPUT=/tmp/report.json "analisis-handball-backend-1" python /app/scripts/export_report.py
docker cp "analisis-handball-backend-1:/tmp/report.json" "reports/public/report.json"
```

The container name can differ locally. Check `docker ps` if necessary.

## Validate before publishing

```powershell
npm --prefix reports test
npm --prefix reports run build
```

Expected result: the tests pass and `reports/dist/` contains `index.html`, assets, and `report.json`.

For canonical rule changes, also run:

```powershell
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py
```

## Public report behavior

| Area | Contract |
|---|---|
| Comparison | The pyramid compares both teams using totals from `team_summary`. |
| Goalkeepers | Overall, seven-metre, and counterattack save rates use assigned shots on target. |
| Momentum | The curve uses chronological goals; filters only hide/show markers, never alter the curve. |
| Video | Incident actions seek the persistent player using `video_seconds`; direct YouTube links remain fallback. |
| Coverage | Video-time positions and partial coverage are explicitly disclosed. |

## Local recovery

The backend service does not run with Uvicorn `--reload`. After editing backend Python files, restart it before checking behavior in the browser:

```powershell
docker restart "analisis-handball-backend-1"
```

Restarting the local container does not publish anything.
