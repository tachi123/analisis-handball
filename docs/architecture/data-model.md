# SAPA Stats Data Model

## Source boundary

The operational source of truth is the authenticated API and its database. This document describes the current canonical analysis boundary; it is not a migration inventory.

## Match records

| Record | Purpose | Rule |
|---|---|---|
| Match and MatchSquad | Match context and eligible roster, including official player totals. | A roster-listed player can be captured even when lineup, substitution, or active goalkeeper context is unknown. |
| Official snapshot | Parsed official PDF totals and provenance. | Immutable competition reference; canonical analysis never changes it. |
| Analysis session | Authenticated analyst checkpoint for one match. | `GET`/`PUT /matches/{id}/analysis-session`; PUT replaces the complete checkpoint, including video source, position, filters, drafts, anchors, and segments. |
| Canonical event | Observed event and its latest revision. | Addressed by match for reads/creation and by event ID for revision. |

## Canonical event facts

Canonical events support evidence state, video anchors, period/regulation-time mapping, player responsibility, and optional `shot_zone` using IHF zones 1-9. A missing reliable clock mapping remains `clock_unverified`; it is not inferred.

Only the latest revision is returned. The database does not persist confidence, visibility, corrected payload, `revision_of`, or a chronological revision history/diff.

## Derived views

| View | API | Boundary |
|---|---|---|
| Match state and metrics | `GET /matches/{id}/canonical-state`, `GET /matches/{id}/canonical-metrics` | Derived canonical observations. |
| Official comparison | `GET /matches/{id}/canonical-reconciliation` | Read-only comparison with immutable official totals. |
| Warnings | `GET /matches/{id}/warnings-summary` | Player and match totals, evidence IDs, and source limitations. Official timestamps and goalkeeper substitutions are `not_comparable`. |
| Goalkeeper projection | `GET /matches/{id}/canonical-player-projection` | Optional player projection from canonical events; observed participation does not infer minutes or starter status. |

Warnings are the product discrepancy flow. There is no reconciliation-resolution record or separate resolution UI.

See [api-spec.md](api-spec.md) for routes and [../README.md](../README.md) for current product scope.
