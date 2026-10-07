# Design: Canonical Warnings Panel

## Technical Approach

Add one authenticated, cutover-gated read endpoint that derives warnings from the same eligible canonical revision events used by `read_metrics` and the latest immutable `OfficialSnapshot` used by reconciliation. `StatisticsPage` consumes that contract only; a new read-only panel selects its canonical evidence in `ReportEventTimeline` and reuses the established video seek path.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Derive in `canonical_analysis_service` | Browser aggregation; new persistence | Keeps eligibility, matching, tolerance, and provenance authoritative; no migration or legacy reads. |
| Zero-tolerance count policy | Per-metric fuzzy counts | Goals, yellow, 2-minute, red, and blue are discrete official totals; unequal comparable values never qualify as `within_tolerance`. The enum remains forward-compatible. |
| Add canonical `blue_card` sanction outcome | Infer blue from red; mark blue unavailable | Red and blue are distinct official fields. The service must recognize observed `blue_card` facts; JSON payload storage needs no schema migration. |
| Explicit player IDs only | Name/jersey matching | Official rows with no resolved `player_id` remain official-only; no identity guess can create a false warning. |
| Compose, do not alter, `ReportEventTimeline` | Reuse mutating `EvidenceModal` | The timeline already provides selection, keyboard navigation, and detail; `EvidenceModal` saves revisions and is forbidden here. |

## Data Flow

```text
eligible canonical revisions + latest OfficialSnapshot.players
                    │
                    ▼
 read_warnings_summary: bucket, union by explicit player_id, compare
                    │                         │
                    ▼                         ▼
 GET /matches/{id}/warnings-summary      event/evidence IDs
                    │
                    ▼
 StatisticsPage → WarningsPanel → ReportEventTimeline → seekTargetForEvent
                                                     └→ mapVideoTime + player.seekTo
```

Eligibility is `active`, `fact_kind == observed`, and `evidence_state == confirmed`. Bucket goal shots and sanction outcomes (`yellow_card`, `two_minute_exclusion`, `red_card`, `blue_card`) by player and match; retain each contributing canonical event ID and current-revision evidence ID. Match totals include eligible playerless canonical events; player rows do not invent a player for them. Official totals come directly from the selected snapshot players. Union rows by non-null explicit player ID, plus distinct official-only rows. No legacy `Event`, `AnalysisEvent`, or `GoalkeeperShot` data participates.

## Interfaces / Contracts

```ts
type WarningStatus = 'exact' | 'within_tolerance' | 'missing_in_canonical' |
  'missing_in_official' | 'not_comparable'
type WarningMetric = 'goals' | 'yellow' | 'two_minute' | 'red' | 'blue'
type WarningComparison = {
  canonical: number | null; official: number | null; status: WarningStatus
  tolerance: 0; canonical_event_ids: number[]; evidence_ids: number[]
}
type WarningsSummary = {
  match_id: number; official_snapshot_id: string | null
  players: Array<{ player: { id: number | null; name: string; jersey_number: number | null; side: 'home' | 'away' | null }; metrics: Record<WarningMetric, WarningComparison> }>
  match_totals: { metrics: Record<WarningMetric, WarningComparison> }
  limitations: Array<{ check: 'goal_timestamps' | 'card_timestamps' | 'goalkeeper_substitutions'; status: 'not_comparable'; reason: string }>
}
```

`GET /matches/{match_id}/warnings-summary` uses `get_current_user` and `_require_cutover`, then returns `WarningsSummary`. Equal present values are `exact`; unequal present values cannot be `within_tolerance` under tolerance `0`. An absent canonical/official player counterpart yields `missing_in_canonical`/`missing_in_official`; missing snapshot returns an empty official side rather than a fabricated value. The three immutable-source limitations are always `not_comparable`; no temporal or goalkeeper inference is attempted.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/services/canonical_analysis_service.py` | Modify | Add blue sanction support and pure warnings aggregation/comparison helpers. |
| `backend/app/api/routes/canonical_analysis.py` | Modify | Add authenticated, cutover-gated GET route. |
| `backend/tests/test_canonical_analysis_service.py` | Modify | Test eligibility, identities, zero tolerance, evidence, totals, and limitations. |
| `backend/tests/test_canonical_analysis_routes.py` | Modify | Test auth, cutover, response, and immutable snapshot behavior. |
| `frontend/src/types.ts` | Modify | Add warnings contract types. |
| `frontend/src/api/client.ts` | Modify | Add typed `getWarningsSummary`. |
| `frontend/src/components/WarningsPanel.tsx` | Create | Accessible match-scoped summary plus read-only timeline/video drill-down. |
| `frontend/src/components/WarningsPanel.test.tsx` | Create | Test semantic statuses, keyboard activation, selection, seek, and unavailable media. |
| `frontend/src/pages/StatisticsPage.tsx` | Modify | Fetch summary with `['warnings-summary', id]` and mount the panel. |
| `frontend/src/pages/StatisticsPage.test.tsx` | Modify | Mock and assert match-scoped panel integration. |

## Frontend Interaction and Accessibility

`WarningsPanel` renders match totals and player rows as semantic tables/lists. Every status has visible text, a Lucide icon with `aria-hidden`, and an accessible label that includes status and canonical/official values; color is supplementary. A row with event IDs is a native button (Enter/Space work natively) with `aria-describedby` pointing to its status. Activation loads canonical events/session, selects the first linked event, renders `ReportEventTimeline`, and announces the selection in a `role=status` live region. It calls `seekTargetForEvent`; only a usable anchor and ready player call `seekTo`. `mapVideoTime` adds clock-coverage context. PDF-only or unavailable media keeps timeline detail available and announces why seeking did not occur. No mutation controls render.

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Backend unit | Buckets, blue, exact/missing statuses, tolerance zero, IDs, temporal/GK limitations | Service fixtures with eligible and excluded revisions plus official-only players. |
| Backend integration | Auth, 409 cutover, route shape, official immutability | Extend canonical route client fixture. |
| Frontend unit | Typed GET path and panel semantics/keyboard/read-only seek | Vitest mocks for API, `useYouTubeSync`, timeline selection, and media states. |
| E2E | Not available | Existing project has no E2E runner. |

## Delivery Slices

1. **Backend derivation and tests** — service, route, service/route tests; target under 400 changed lines, independently deployable and read-only.
2. **Frontend panel and drill-down tests** — types/client, panel, StatisticsPage integration, tests; target under 400 changed lines, depends on slice 1.

`ask-always` remains the delivery gate: before applying either slice, request approval even though `size:exception` is recorded. Keep tests with each work unit; do not combine slices or mix legacy sources.

## Migration / Rollout

No database migration, feature flag, or deployment change. The existing match-level canonical cutover is the rollout boundary; removing the route/panel rolls back without changing canonical or official records.

## Open Questions

None.
