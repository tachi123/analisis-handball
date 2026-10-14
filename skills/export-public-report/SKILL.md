---
name: export-public-report
description: "Trigger: export report, public report, report catalog, publish match report. Generate and validate privacy-safe static reports for active matches."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Use this skill when exporting or preparing a completed match for the public static report. Do not use it for private review capture or GitHub publishing alone.

## Hard Rules

- Require `kickoff` and `period_end` for periods 1 and 2 before claiming complete coverage.
- Export only the public projection. Never add private IDs, notes, raw event payloads, credentials, or backend URLs to `reports/public/report.json`.
- Official sheets are private by default. Export a PDF only when its confirmed snapshot has explicit public approval; verify its SHA-256 and publish only a derived public-key filename.
- Record `passive` only when observed in video; it is a turnover cause, never an inferred pass count.
- Do not commit, push, or deploy unless explicitly requested.

## Decision Gates

| Condition | Action |
|---|---|
| Coverage is incomplete | Export only if the user accepts a partial report; preserve the coverage disclosure. |
| Backend Python changed | Restart the local backend container before browser validation. |
| Public build/tests fail | Stop; do not publish a stale or invalid report. |
| Approved sheet has no complete or partial observed coverage | Do not emit a report or public PDF link; importing a sheet is not match analysis. |

## Execution Steps

1. Inspect canonical coverage, period markers, active run, and final score for every requested match.
2. If a public FEMEBAL sheet is required, approve it explicitly (or confirm its approval):

   ```powershell
   docker exec "analisis-handball-backend-1" python /app/scripts/set_official_sheet_publication.py --publish 99 101
   ```

3. Export one or more active matches into one temporary catalog directory:

   ```powershell
   docker exec -e PUBLIC_REPORT_MATCH_IDS=99,101 -e PUBLIC_REPORT_OUTPUT=/tmp/report.json -e PUBLIC_REPORT_CATALOG_OUTPUT=/tmp/public-report "analisis-handball-backend-1" python /app/scripts/export_public_report_catalog.py
   docker cp "analisis-handball-backend-1:/tmp/public-report/." "reports/public"
   ```

4. Inspect `reports/public/reports.json`, the fallback `report.json`, every referenced per-match JSON, and `reports/public/planillas/` for complete/partial coverage, referenced PDFs, and public-safe fields only.
5. Run:

   ```powershell
   npm --prefix reports test
   npm --prefix reports run build
   ```

6. Report catalog entries, coverage, score, incident count, approved sheet status, validation results, and whether publication remains pending.

## Output Contract

State the exported match, coverage status, score, report path, test/build result, and any reason publication is blocked. Do not claim Pages was updated until a requested push/deploy completes.

## References

- `AGENTS.md`
- `docs/operations/match-report-workflow.md`
- `docs/operations/public-reports-pages.md`
