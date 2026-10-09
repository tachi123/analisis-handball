---
name: export-public-report
description: "Trigger: export report, public report, publish match report, GitHub Pages report. Generate and validate the privacy-safe static report for a completed match."
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
- Record `passive` only when observed in video; it is a turnover cause, never an inferred pass count.
- Do not commit, push, or deploy unless explicitly requested.

## Decision Gates

| Condition | Action |
|---|---|
| Coverage is incomplete | Export only if the user accepts a partial report; preserve the coverage disclosure. |
| Backend Python changed | Restart the local backend container before browser validation. |
| Public build/tests fail | Stop; do not publish a stale or invalid report. |

## Execution Steps

1. Inspect canonical coverage, period markers, and the final score for the requested match.
2. Export Match 99:

   ```powershell
   docker exec -e PUBLIC_REPORT_OUTPUT=/tmp/report.json "analisis-handball-backend-1" python /app/scripts/export_report.py
   docker cp "analisis-handball-backend-1:/tmp/report.json" "reports/public/report.json"
   ```

3. Inspect the generated JSON for complete/partial coverage and public-safe fields only.
4. Run:

   ```powershell
   npm --prefix reports test
   npm --prefix reports run build
   ```

5. Report coverage, score, incident count, validation results, and whether publication remains pending.

## Output Contract

State the exported match, coverage status, score, report path, test/build result, and any reason publication is blocked. Do not claim Pages was updated until a requested push/deploy completes.

## References

- `AGENTS.md`
- `docs/operations/match-report-workflow.md`
- `docs/operations/public-reports-pages.md`
