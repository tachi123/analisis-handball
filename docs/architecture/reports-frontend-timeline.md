# Match Reports Timeline

## Current behavior

`/match/:matchId/timeline` is an authenticated, internal, read-only timeline backed by the canonical match API. It loads the match, canonical events, state, metrics, reconciliation context, and the analyst's per-match session. It supports filters, evidence selection, and video seeking when a playable anchor is available.

`/match/:matchId/reports` is a protected compatibility redirect to `/match/:matchId/timeline`.

## Data source and boundaries

The timeline does not read Google Sheets and is not a GitHub Pages public report. Its source is the canonical API:

- `GET /matches/{id}/canonical-events`
- `GET /matches/{id}/canonical-state`
- `GET /matches/{id}/canonical-metrics`
- `GET /matches/{id}/canonical-reconciliation`
- `GET /matches/{id}/analysis-session`

The displayed event is the latest canonical revision only. Missing video or an unusable anchor does not hide the evidence.

## Future public reports

A public Google Sheets/GitHub Pages report remains unimplemented future scope. It requires a separately designed public projection, privacy boundary, deployment, and API/data contract. It must not replace or be described as the source for the internal timeline.
