# Design: Goalkeeper Panel with Shot Zone

## Technical Approach

Add a canonical-only, read-time player projection at `GET /matches/{match_id}/canonical-player-projection`. It replays latest active eligible revisions in sequence, then returns the selected player's observed goalkeeper claims, evidence, IHF target-zone map, and separately unfiltered match context. `shot_zone` is an optional numeric JSON payload field for canonical `shot` commands; historic revisions stay valid and unzoned. This implements the proposal without reading `Event`, `GoalkeeperShot`, or other legacy sources.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Derive projection in `canonical_analysis_service` | React aggregation; persisted projection rows | Reuses authoritative eligibility/revision replay and prevents stale or client-invented totals. `canonical_projections` is not used. |
| Attribute goals and saves only from replayed `goalkeeper_change(active)` | Infer from `lineup_change` or roster | A lineup observation proves participation, not active keeper, minutes, or starts. Missing/ambiguous context stays explicit. |
| Keep `shot_zone` nullable in revision JSON | New column/backfill | `CanonicalEventRevision.payload` already persists JSON; optional data needs validation, not schema mutation. |
| Replace legacy-origin picker semantics with an IHF target picker | Convert old saved origin zones | Origin zones cannot truthfully become goal-target zones. The visual component may be reused, but canonical values are only IHF 1–9. |

## Data Flow

    canonical event/revision + evidence
             │ create/revise validates shot_zone
             ▼
    latest active eligible revisions ──sequence replay──► player projection
             │                                             │
             └── canonical metrics/reconciliation ──────────┤
                                                           ▼
    goalkeeper panel ── timeline selection ──► seekTargetForEvent / mapVideoTime

The endpoint requires `player_id`; optional `team_id`, `period`, `from_regulation_seconds`, and `to_regulation_seconds` are validated against the match and roster. Verified-clock events outside the range are excluded from selected results. Matching unverified-clock events are returned in `clock_unverified`, never treated as in range or merged into ordered precise results. Match-level `canonical_metrics` and `reconciliation` are unfiltered references/results.

## Interfaces / Contracts

```python
ShotZone = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]

class CanonicalEventCommand:
    # existing fields
    shot_zone: ShotZone | None = None  # valid only when kind == "shot"
```

Reject a non-shot command with a zone; accept omitted/null zones for all commands and existing revisions. `revision_payload`, create, revision, evidence-anchor recalibration, and frontend remapping must retain it.

`canonical-player-projection` returns `player` and selected team context; `participation` (lineup event/revision/evidence IDs and observed on/off/substitution counts only); count metrics for `saves` and `goals_conceded`; optional observed-decision save rate (`saves / (saves + goals_conceded)`) only when that denominator is supported; discipline counts; `shot_map` keyed `1..9` plus `recorded`, `missing_zone`, `goalkeeper_unknown`, `excluded`, `unknown`, and `clock_unverified` coverage; and selected event/revision/evidence/video-anchor records. A confirmed opponent `shot` with `save` or `goal` increments the selected keeper only if replay has exactly one opposing active keeper at that event; otherwise its outcome and evidence IDs increment `goalkeeper_unknown`.

Frontend adds `ShotZone`, projection types, and a query-parameter client. A new protected match-scoped goalkeeper panel selects roster goalkeepers, renders participation/coverage disclosures, metric cards, a 3×3 IHF heatmap, and projection evidence through the existing timeline/video utilities. `GkCourtPicker` is refactored from ten origin labels (`6m_*`, `9m_*`, wings, seven-meter, counter) to nine target cells: top `1|2|3`, middle `4|5|6`, bottom `7|8|9`. This is a UI vocabulary replacement, not a data conversion; no legacy raw value is sent or displayed as canonical.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/schemas.py` | Modify | `ShotZone` validation and projection query/response schemas. |
| `backend/app/services/canonical_analysis_service.py` | Modify | Latest-revision eligibility, keeper replay, filters, coverage, evidence projection. |
| `backend/app/api/routes/canonical_analysis.py` | Modify | Authenticated, cutover-protected projection route. |
| `backend/tests/test_canonical_analysis_{service,routes}.py` | Modify | Attribution, filters, evidence, zone compatibility tests. |
| `frontend/src/{types.ts,api/client.ts}` | Modify | Zone and projection contracts/client. |
| `frontend/src/{pages/MatchAnalysis.tsx,pages/MatchReview.tsx,components/EvidenceModal.tsx,components/GkCourtPicker.tsx}` | Modify | Shot-only capture/revision picker and preservation. |
| `frontend/src/pages/GoalkeeperPanel.tsx` | Create | Canonical goalkeeper panel. |
| `frontend/src/components/ShotZoneHeatmap.tsx` | Create | Accessible IHF 1–9 coverage heatmap. |
| `frontend/src/**/*.{test.ts,test.tsx}` | Modify/Create | Client, picker, panel, heatmap, and seek/clock behavior tests. |

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Backend unit | Replay save/goal/unknown, lineup evidence, eligibility/range/clock buckets, zones | `pytest` service fixtures with ordered revisions. |
| Backend integration | Auth, cutover, required player, invalid team/zone, response evidence IDs | FastAPI `TestClient`. |
| Frontend unit/component | Client params, numeric picker, capture/revision preservation, heatmap labels, timeline seek/disclosure | Vitest + Testing Library; mock projection/video hooks. |
| E2E | Not available | Verify build and configured unit/integration runners. |

## Migration / Rollout

No Alembic migration, index, backfill, or payload rewrite: the field is nullable JSON. Roll back slices independently; old and unzoned revisions remain readable. Never migrate legacy `Event.shot_zone` or `GoalkeeperShot` data.

## Delivery Slices

1. **Backend projection + tests** — route/service/contracts and tests; target under 400 changed lines.
2. **Capture/API zone extension + tests** — validation, types/client, picker and revision preservation; target under 400 lines.
3. **Panel/heatmap/timeline UI + tests** — protected panel and existing timeline/video reuse; target under 400 lines.

`ask-always` requires approval of this chained plan before apply; each slice is independently testable and reversible.

## Open Questions

None.
