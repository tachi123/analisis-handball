# Proposal: Goalkeeper Panel with Shot Zone

Deliver a canonical-first goalkeeper view with video evidence and an optional IHF 1–9 shot-zone extension, without joining legacy analysis data.

## Intent

Give analysts an auditable per-goalkeeper view of observed saves, goals conceded, participation evidence, and rival-shot location while retaining the canonical ledger as the sole source of truth.

## Scope

### In Scope
- Server-owned, authenticated goalkeeper/player projection with filters, evidence/video anchors, coverage, and match metrics/reconciliation context.
- Phase 1 panel: goalkeeper selection, observed participation, saves/goals conceded, evidence timeline, video seek, and explicit clock/coverage disclosure.
- Phase 2: optional numeric IHF `shot_zone` (1–9) on canonical `shot` create/revision payloads, capture/revision preservation, and heatmap buckets.

### Out of Scope
- Legacy `Event`/goalkeeper data or legacy zone values; canonical and legacy data MUST NOT mix.
- `attack_phase`, `goalkeeper_action_type`, and `related_player` semantics.
- Inferred minutes, starts, exhaustive participation, or active keeper from lineup changes.

## Capabilities

### New Capabilities
- `goalkeeper-player-projection`: Filtered canonical projection for player/goalkeeper metrics, evidence, participation, and shot-map coverage.

### Modified Capabilities
- `canonical-live-handball-analysis`: Accept optional IHF 1–9 `shot_zone` only on canonical shots while preserving historic unzoned events.
- `review-statistics`: Derive goalkeeper goals conceded and zone coverage from latest eligible canonical revisions.
- `video-review-workspace`: Capture and preserve an optional shot zone in video-review commands and revisions.

## Approach

Replay ordered eligible current revisions server-side. Attribute each opponent `save`/`goal` only when an observed `goalkeeper_change(active)` identifies exactly one active opposing keeper; otherwise expose `goalkeeper_unknown`. Treat `lineup_change` as participation evidence only. Keep unverified-clock events outside precise time ranges in a separately disclosed bucket. Store nullable `shot_zone` in revision JSON; no backfill or migration is planned.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/{schemas,services,api}/` | Modified | Zone validation and projection endpoint |
| `backend/tests/` | Modified | Attribution, filters, zone, and compatibility tests |
| `frontend/src/{types,api,pages,components}/` | Modified | Capture, panel, heatmap, timeline/video reuse |
| Database | No migration planned | Optional field remains revision JSON |
| Deployment | Modified API consumer only | Existing auth and SPA/API deployment remain |

## Risks

| Risk | Mitigation |
|---|---|
| Fabricated keeper attribution | Require observed active-keeper replay; report unknown coverage |
| Historic missing zones | Preserve and label as missing-zone coverage |
| Review size exceeds 400 lines | Deliver chained, independently testable slices |

## Rollback Plan

Revert each slice independently: remove the projection endpoint/panel or stop sending `shot_zone`. Existing revisions and unzoned events remain readable; no destructive data rollback is required.

## Dependencies

- Existing canonical ledger, roster eligibility, evidence/video mapping, metrics, reconciliation, and authentication.

## Success Criteria

- [ ] Projection returns only server-derived canonical claims with evidence and explicit unknown/clock coverage.
- [ ] Goals conceded require observed active-keeper replay; participation makes no minute/start claim.
- [ ] Shot zones accept only numeric 1–9 for shots; historic unzoned events remain compatible.
- [ ] Panel seeks existing video evidence and renders zone coverage without legacy data.

## Chained Delivery Plan

1. **Backend projection and tests** — endpoint, keeper replay, coverage, and evidence contract.
2. **Capture/API zone extension and tests** — schema, revision JSON, client types, and compatibility.
3. **Panel/heatmap UI and tests** — projection consumer, reusable timeline/video behavior, and zone display.

Decision needed before apply: Yes  
Chained PRs recommended: Yes  
400-line budget risk: High
