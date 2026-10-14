---
name: handball-report-analytics
description: "Trigger: mini-match, goalkeeper analytics, possession tempo, quick concession, Phase 1 report. Change public handball analytics without unsupported tactical claims."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Use this skill when changing static public-report analytics, Phase 1 visualizations, goalkeeper metrics, mini-match blocks, possession tempo, or moment interpretation. Do not use it for private capture UI unless the task changes the observation contract.

## Hard Rules

- Derive public analytics in `backend/scripts/export_report.py`; the public UI must stay static and never call private APIs.
- Use only confirmed observed canonical events. Never expose raw payloads, IDs, notes, evidence paths, or operational fields.
- Do not infer retreat errors, concentration, tactical cause, or goalkeeper influence from chronology alone.
- Keep score curves chronological; filters may hide markers but must not rewrite the underlying match result.
- Save uncertain or insufficient samples as disclosed coverage, not as a confident metric.

## Decision Gates

| Question | Rule |
|---|---|
| Is a clock unverified? | Exclude it from time-binned analytics or disclose video time. |
| Does a clock overrun a half? | Keep it in the final 20–30 block and disclose the overrun; never wrap to 0–10. |
| Are fewer than five closed verified possessions available? | Label possession tempo `cobertura parcial`; do not support a tactical conclusion. |
| Are goalkeeper shots assigned? | Save rate is saves / assigned on-target shots; team shot funnel must distinguish total attempts from on-target shots. |
| Are shots missing a goalkeeper attribution? | Show them as a separate team-level remainder, with totals and percentage derived from team totals minus assigned players; never treat it as a named keeper's 0% performance or proof of an empty goal. |
| Are outside, woodwork, or blocks requested? | Expose them as defending-team context, with a separated `blocked` outcome; never attribute them to an individual goalkeeper or infer their tactical cause. |
| Is a quick concession found? | Describe its observed trigger (goal, shot outcome, turnover); call it an alert for review, not a cause. |

## Execution Steps

1. Update exporter derivation and the allowlisted `reports/src/projection.ts` contract together.
2. Render the result in `reports/src/App.tsx` with coach-readable labels, denominator clarity, sample coverage, a compact team defensive-context row, and team-first goalkeeper grouping (team total → named keepers → unassigned remainder).
3. Add or update projection tests for public fields and privacy boundaries.
4. Regenerate the affected public catalog entries with the catalog exporter.
5. Run `npm --prefix reports test` and `npm --prefix reports run build`.

## Output Contract

State metric definition, denominator, exclusions, coverage threshold, affected public artifacts, and validation result. State explicitly when the data cannot justify the requested tactical interpretation.

## References

- `AGENTS.md`
- `docs/architecture/public-report-phase-1.md`
- `docs/operations/match-report-workflow.md`
- `docs/operations/scripts-reference.md`
