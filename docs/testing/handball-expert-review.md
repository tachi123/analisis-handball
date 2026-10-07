# SAPA Stats Handball Expert Review

**Scope:** delivered handball-analysis behavior.

## Product assessment

| Area | Current behavior |
|---|---|
| Video review | MatchReview combines a per-match canonical record with YouTube synchronization, explicit anchors, evidence states, and recoverable checkpoints. |
| Shot zones | `shot_zone` is optional. The canonical goalkeeper flow uses IHF zones 1-9, so lack of a visible zone does not prevent a valid observed event. |
| Goalkeepers | The projection reports observed saves, goals conceded, substitutions, discipline, zones, and evidence. It does not infer minutes, starter status, or complete presence. |
| Official comparison | Statistics compare immutable official totals with eligible canonical totals. Linked evidence is available from expandable warnings. |
| Comparison limits | Official timestamps and goalkeeper substitutions are `not_comparable`, because official PDFs provide aggregate totals rather than event chronology. |

## Methodological limits

- A canonical event exposes only its latest revision.
- Confidence, visibility, corrected payload, `revision_of`, and revision history/diffs are not persisted and must not be inferred by the UI.
- Warnings are the deliberate analyst flow for discrepancies. A reconciliation-resolution interface is not a missing feature.

## Future scope

Public Google Sheets/GitHub Pages reporting is not delivered. It is unrelated to the authenticated canonical timeline and requires a separate public-data decision.

See [../README.md](../README.md) and [../architecture/data-model.md](../architecture/data-model.md).
