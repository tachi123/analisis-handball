# SAPA Stats Documentation

## Current product state

This index is the current documentation source of truth. Code and tests remain the final implementation evidence.

| Area | Delivered behavior |
|---|---|
| Match review | Authenticated `/match/:matchId/review` uses per-match canonical sessions and events, YouTube synchronization, anchors, evidence, and complete checkpoints. |
| Private timeline | Authenticated `/match/:matchId/timeline` reads canonical API data. `/match/:matchId/reports` redirects there for compatibility. |
| Public static report | `reports/` is a privacy-safe GitHub Pages projection backed by tracked `reports/public/report.json`; it includes comparison, players, goalkeeper splits, momentum, and video review. |
| Goalkeeper analysis | The goalkeeper panel consumes `GET /matches/{id}/canonical-player-projection`; canonical shot `shot_zone` is optional and uses IHF zones 1-9. |
| Statistics warnings | Statistics show official versus canonical player and match totals, linked evidence, and expandable details. Official timestamps and goalkeeper substitutions are `not_comparable` because official PDFs provide totals only. |
| PDF | Statistics export a client-generated PDF, optionally including a goalkeeper projection. There is no backend PDF-export endpoint. |
| Warnings API | `GET /matches/{id}/warnings-summary` supplies the warnings panel. |

## Known limits

- Canonical event responses expose only the latest revision.
- Confidence, visibility, corrected payload, `revision_of`, and chronological revision history/diffs are not persisted.
- Warnings, not a reconciliation-resolution workflow, are the intended discrepancy flow.

## Public-report boundary

The public Pages report is implemented and remains a separate static projection. It is never the data source for authenticated review and must never expose internal identifiers, private notes, raw payloads, credentials, or backend URLs.

## Reference map

| Need | Document |
|---|---|
| System boundaries | [architecture/system-overview.md](architecture/system-overview.md) |
| API contracts | [architecture/api-spec.md](architecture/api-spec.md) |
| Canonical data model | [architecture/data-model.md](architecture/data-model.md) |
| Match review behavior | [architecture/match-review-spec.md](architecture/match-review-spec.md) |
| Timeline and future public reports | [architecture/reports-frontend-timeline.md](architecture/reports-frontend-timeline.md) |
| Match-to-report export and validation | [operations/match-report-workflow.md](operations/match-report-workflow.md) |
| Remaining scope | [architecture/next-slices.md](architecture/next-slices.md) |
| QA evidence | [testing/qa-report.md](testing/qa-report.md) |
| Handball review | [testing/handball-expert-review.md](testing/handball-expert-review.md) |
