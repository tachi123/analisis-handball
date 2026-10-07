# SAPA Stats System Overview

## Current system

SAPA Stats is an authenticated handball analysis application. The React SPA uses the FastAPI `/api/v1` API and PostgreSQL-backed operational data. The canonical per-match API is the source for review, the internal timeline, goalkeeper views, statistics warnings, and client PDF export.

## Delivered workflow

1. Prepare a match and official roster/PDF data.
2. Capture or review canonical events for the match.
3. Use `/match/:matchId/review` for YouTube synchronization, anchors, evidence, and complete checkpoints.
4. Use `/match/:matchId/timeline` for the authenticated canonical timeline. `/match/:matchId/reports` is a compatibility redirect.
5. Use statistics warnings and the optional goalkeeper projection to inspect official versus canonical totals.
6. Export a PDF from StatisticsPage in the browser.

## Architectural boundaries

| Decision | Current behavior |
|---|---|
| Canonical API | Sessions and events are addressed by match. There is no session-scoped event facade. |
| Official data | Official PDF totals are immutable. Canonical observations never overwrite them. |
| Discrepancies | Warnings show player and match comparisons with linked evidence and expandable detail. A reconciliation-resolution UI is intentionally not part of the product. |
| Goalkeepers | `shot_zone` is optional and uses IHF zones 1-9. The projection reports observed evidence, not inferred minutes or starter status. |
| PDF | The browser composes the report from canonical API reads. No backend export endpoint exists. |
| Public reports | Google Sheets/GitHub Pages reporting is future scope, not an operational data source. |

## Known limits

- Events expose the latest revision only.
- Confidence, visibility, corrected payload, `revision_of`, and chronological revision history/diffs are not persisted.
- Official timestamps and goalkeeper substitutions are `not_comparable`: official PDFs supply totals only.

## References

- [Current product index](../README.md)
- [API specification](api-spec.md)
- [Canonical data model](data-model.md)
- [Match review workspace](match-review-spec.md)
