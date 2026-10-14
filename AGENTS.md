# analisis-handball — Agent Guide

## Start here

This repository contains two deliberately isolated products:

| Product | Path | Audience | Source of truth |
|---|---|---|---|
| Private review application | `frontend/` + `backend/` | Authenticated analysts | Canonical events in the backend database |
| Public static reports | `reports/` | Anyone with the Pages URL | Privacy-safe JSON artifacts in `reports/public/` |

The public report must never depend on the private frontend, backend runtime, private API, database IDs, credentials, raw events, notes, or untracked files.

## Non-negotiable rules

1. Canonical events are append/revise data. Never mutate historical payloads in place.
2. Report only observed facts. `passive` is an observed turnover outcome, never an inferred pass count.
3. Never infer tactical causes from chronology alone. “Quick concession” is an observed sequence; it is not automatically a retreat or concentration error.
4. Public JSON must contain only the allowlisted projection. Do not expose IDs, raw payloads, notes, tokens, URLs, operational paths, or backend details.
5. The Pages workflow deploys only `reports/dist`. Do not deploy `frontend/` as Pages.
6. Never commit, push, deploy, or change Pages configuration unless explicitly requested.
7. Uvicorn does not use `--reload`: restart `analisis-handball-backend-1` after backend Python changes.

## Analysis-run lifecycle

Each match can have independent immutable analysis runs:

| Status | Meaning | Writes | Reads/exports |
|---|---|---|---|
| `draft` | Analyst work in progress | Creator or admin only | Review with `?run=<id>` |
| `active` | Explicit canonical run | Read-only | Metrics, private timeline, public export |
| `superseded` | Historical prior canonical run | Read-only | Historical only |

- Run mode is immutable: `video`, `manual`, or `live`.
- Promote only the intended complete draft. Promotion preserves its events and session; it does not rewrite them.
- `video` uses a YouTube source, `manual` records local-video time manually, and `live` uses observed live time with explicit unavailable-video evidence.

See [docs/architecture/analysis-run-lifecycle.md](docs/architecture/analysis-run-lifecycle.md).

## Private review quick path

1. Import and confirm the official sheet.
2. Create or resume the intended draft at `/matches/:matchId/prepare`.
3. Review at `/match/:matchId/review?run=:runId`.
4. Calibrate `kickoff` at observed `0:00`, capture only observed events with evidence, and close both periods with `period_end`.
5. Promote the completed draft to `active` before exporting.

For a complete match, periods 1 and 2 require both `kickoff` and `period_end`.

## Public report quick path

The exporter derives all report analytics statically. The public UI never calls private APIs or needs an API token.

```powershell
# Optional: approve only confirmed sheets that may be copied to the public catalog.
docker exec "analisis-handball-backend-1" python /app/scripts/set_official_sheet_publication.py --publish 99 101

# Export or refresh multiple active matches into one catalog directory.
docker exec -e PUBLIC_REPORT_MATCH_IDS=99,101 -e PUBLIC_REPORT_OUTPUT=/tmp/report.json -e PUBLIC_REPORT_CATALOG_OUTPUT=/tmp/public-report "analisis-handball-backend-1" python /app/scripts/export_public_report_catalog.py
docker cp "analisis-handball-backend-1:/tmp/public-report/." "reports/public"

npm --prefix reports test
npm --prefix reports run build
```

`reports/public/` must contain `report.json` (fallback), `reports.json` (catalog), and each `report_<public-key>.json`. Approved, hash-verified sheets are copied as derived `planillas/planilla_<public-key>.pdf` files. Inspect all catalog entries, referenced reports, and referenced PDFs before publication.

See [docs/operations/match-report-workflow.md](docs/operations/match-report-workflow.md).

## Public report analytics

- Momentum uses chronological goal events; filters only affect markers, never the score curve.
- Goalkeeper team totals use all observed on-target shots; player save rates use assigned shots. “Sin arquero asignado” is an explicit team remainder, not a named player performance or proof of an empty goal.
- Defensive context separates the rival's total shots, goals, conversion, on-target shots, outside/woodwork, and blocked shots. These are team facts, not inferred goalkeeper influence.
- Zones: `7` is seven metres; `8` is counterattack.
- Phase 1 derives 10-minute mini-matches, runs, quick concessions, goalkeeper context, and guarded possession tempo during export.
- Events beyond a half’s nominal clock stay in its final 20–30 block and are disclosed as clock overrun; never wrap them into 0–10.
- Possession tempo is only coach-readable at sufficient observed coverage. Do not infer a tactical cause from a partial sample.

See [docs/architecture/public-report-phase-1.md](docs/architecture/public-report-phase-1.md).

## Validation

```powershell
npm --prefix reports test
npm --prefix reports run build
docker exec "analisis-handball-backend-1" pytest -q tests/test_canonical_analysis_service.py tests/test_analysis_events.py tests/test_analysis_run_service.py tests/test_migrations.py
```

## Project skills

| Skill | Use it when |
|---|---|
| `skills/export-public-report/SKILL.md` | Exporting, validating, or preparing static public report artifacts. |
| `skills/handball-report-analytics/SKILL.md` | Changing Phase 1 metrics, goalkeeper/possession analysis, mini-match blocks, or moment interpretation. |

## Key files

| Need | File |
|---|---|
| Private review | `frontend/src/pages/MatchReview.tsx` |
| Prepare/promote analysis runs | `frontend/src/pages/ManualMatchPreparationPage.tsx`, `backend/app/services/analysis_run_service.py` |
| Canonical validation/state | `backend/app/services/canonical_analysis_service.py` |
| Public report UI | `reports/src/App.tsx` |
| Public schema/privacy decoder | `reports/src/projection.ts` |
| Momentum | `reports/src/Timeline.tsx`, `reports/src/timelineDerivation.ts` |
| Public export | `backend/scripts/export_report.py` |
| Multi-match catalog export | `backend/scripts/export_public_report_catalog.py` |
| Public-sheet approval | `backend/scripts/set_official_sheet_publication.py` |
| Pages workflow | `.github/workflows/deploy-frontend.yml` |
