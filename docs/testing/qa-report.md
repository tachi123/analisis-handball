# SAPA Stats QA Report

**Scope:** documentation-aligned delivered product state.

## Verified delivered behavior

| Area | Evidence |
|---|---|
| MatchReview | Protected `/match/:matchId/review` uses per-match sessions/events, YouTube sync, anchors, evidence, and checkpoints. |
| Internal timeline | Protected `/match/:matchId/timeline` loads canonical API data. `/match/:matchId/reports` redirects to it. |
| Goalkeepers | The panel uses `GET /matches/{id}/canonical-player-projection`; optional canonical `shot_zone` supports IHF 1-9. |
| Warnings | Statistics renders official/canonical player and match totals, linked evidence, and expandable warning details via `GET /matches/{id}/warnings-summary`. |
| PDF | StatisticsPage generates the PDF in the client and can include an optional goalkeeper projection. |

## Contract limits

- Canonical event reads return the latest revision only.
- Confidence, visibility, corrected payload, `revision_of`, and chronological history/diffs are not persisted.
- Official timestamps and goalkeeper substitutions are `not_comparable` because the official PDFs contain totals only.
- The warnings panel is the intended discrepancy flow; full reconciliation resolution was deliberately discarded.
- There is no backend PDF-export endpoint.

## Out of scope

Public Google Sheets/GitHub Pages reports are future scope only. They are not the current timeline implementation or its data source.

See [../README.md](../README.md), [../architecture/api-spec.md](../architecture/api-spec.md), and [../architecture/match-review-spec.md](../architecture/match-review-spec.md).
