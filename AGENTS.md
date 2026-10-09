# analisis-handball — Agent Guide

## Start here

This repository has two deliberately separate products:

| Product | Path | Audience | Source of truth |
|---|---|---|---|
| Private review application | `frontend/` + `backend/` | Authenticated analysts | Canonical events in the backend database |
| Public static report | `reports/` | Anyone with the GitHub Pages URL | `reports/public/report.json` |

Do not make the public report depend on the private frontend, backend runtime, Docker, private APIs, database IDs, credentials, or untracked files.

## Non-negotiable rules

1. Keep public and private data boundaries separate. Public JSON must not contain IDs, raw payloads, private notes, tokens, URLs, or operational details.
2. Canonical events are append/revise data. Do not edit historical event payloads in place.
3. Do not infer sports facts from incomplete evidence. Record `passive` only when it is observed in the video; it is a `turnover` outcome, not a count of passes.
4. Preserve the public dashboard structure when changing `reports/`: comparison pyramid, field-player table, goalkeeper cards, momentum timeline, and video review are independent sections.
5. The GitHub Pages workflow deploys only `reports/dist`. Do not deploy `frontend/` as Pages.
6. Never commit, push, deploy, or alter GitHub Pages configuration unless explicitly requested.

## Match-review workflow

1. Open `/match/:matchId/review` in the private application.
2. Choose the active period and calibrate its kickoff at video time `0:00`.
3. Record observed canonical events with evidence. Close each period with `period_end`.
4. For a complete match, require `kickoff` and `period_end` for periods 1 and 2 before exporting.
5. If backend Python code changed locally, restart the backend container because the configured Uvicorn command does not use `--reload`.

## Public-report workflow

1. Confirm canonical coverage is complete.
2. Export Match 99 from the backend container:

   ```powershell
   docker exec -e PUBLIC_REPORT_OUTPUT=/tmp/report.json "analisis-handball-backend-1" python /app/scripts/export_report.py
   docker cp "analisis-handball-backend-1:/tmp/report.json" "reports/public/report.json"
   ```

3. Validate the static application:

   ```powershell
   npm --prefix reports test
   npm --prefix reports run build
   ```

4. Inspect `reports/public/report.json` before publishing. It is the exact static data that Vite copies to `reports/dist/report.json`.

See `docs/operations/match-report-workflow.md` for details and recovery checks.

## Public-report conventions

- Video review uses a persistent YouTube iframe. Seek it with the incident's `video_seconds`; do not remount the iframe for every incident.
- The momentum chart derives the score only from chronological goal events. Its curve always keeps both teams; filters affect marker overlays only.
- Unverified game clocks may use video time, but the UI must disclose that distinction.
- Goalkeeper save rates use assigned on-target shots only: `saves / (saves + goals conceded)`.
- Zones: `7` is seven metres; `8` is counterattack. Show split goalkeeper rates only when that goalkeeper has faced at least one assigned on-target shot in the zone.

## Useful validation

```powershell
npm --prefix reports test
npm --prefix reports run build
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py
```

## Project skills

| Skill | Use it when |
|---|---|
| `skills/export-public-report/SKILL.md` | Exporting, validating, or preparing a completed match for the public static report. |

## Key files

| Need | File |
|---|---|
| Public report UI | `reports/src/App.tsx` |
| Momentum chart | `reports/src/Timeline.tsx`, `reports/src/timelineDerivation.ts` |
| Public schema/privacy decoder | `reports/src/projection.ts` |
| Static report exporter | `backend/scripts/export_report.py` |
| Canonical outcome validation | `backend/app/services/canonical_analysis_service.py` |
| Private event capture | `frontend/src/components/IncidentWizard.tsx` |
| Pages deployment | `.github/workflows/deploy-frontend.yml` |
