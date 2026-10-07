## Exploration: Goalkeeper Panel with Shot Zone

### Current State
Canonical events are an append-only `canonical_events` ledger whose current revision payload is JSON. `CanonicalEventCommand` carries kind, period, team/player responsibility, optional related player, result, verified/unverified regulation clock, evidence state, uncertainty, note, and revision-owned evidence. It has no `shot_zone`; existing legacy `Event.shot_zone` and the old goalkeeper court picker are not canonical sources.

`canonical-metrics` and `canonical-reconciliation` are server-derived, unfiltered match context. Metrics currently count player shots, turnover/recovery/discipline, and goalkeeper **saves only** when a prior `goalkeeper_change(active)` identifies the opposing keeper. A goal does not retain that opposing-keeper attribution today, so goalkeeper goals conceded needs a derived-projection correction while retaining the current event contract. `lineup_change` records observed on/off/substitution state but cannot substantiate minutes, starts, or exhaustive participation.

The reports timeline already composes match, canonical events, state, metrics, reconciliation, and analysis session. It filters locally, preserves `clock_unverified` chronology semantics, seeks video with `seekTargetForEvent` (two-second preroll), and calls `mapVideoTime` for segment-aware clock disclosure.

### Affected Areas
- `backend/app/schemas.py` — add the optional canonical `shot_zone` IHF 1–9 enum to create and revision commands, valid only for `kind == "shot"`.
- `backend/app/services/canonical_analysis_service.py` — retain `shot_zone` in revision JSON; derive goalkeeper saves/goals conceded, observed lineup participation, eligible coverage, evidence IDs, and zone buckets in a read-only filtered player projection.
- `backend/app/api/routes/canonical_analysis.py` — expose the authenticated, cutover-protected filtered projection endpoint.
- `backend/alembic/versions/` — no data migration is needed: canonical payloads are already JSON and the field is optional. Add an Alembic revision only if implementation introduces a query/index outside the JSON payload; do not backfill or mutate prior revisions.
- `backend/tests/test_canonical_analysis_service.py`, `backend/tests/test_canonical_analysis_routes.py` — validate zone acceptance/rejection, legacy payload compatibility, keeper attribution, filters, coverage, evidence, and no-minute claims.
- `frontend/src/types.ts`, `frontend/src/api/client.ts` — model `ShotZone`, extend canonical commands, and add the projection client/type.
- `frontend/src/pages/StatisticsPage.tsx` or a new match-scoped goalkeeper panel — host per-goalkeeper selection, canonical context, observed-participation disclosure, metric cards, zone heatmap, and evidence timeline.
- `frontend/src/components/ReportEventTimeline.tsx`, `frontend/src/reportTimeline.ts`, `frontend/src/timelineInteractions.ts`, `frontend/src/videoReview.ts` — reuse filtering/selection, explicit unverified-clock display, video seek, and `mapVideoTime`; do not duplicate timeline logic.
- `frontend/src/pages/MatchAnalysis.tsx` and review capture/revision surfaces (`MatchReview.tsx`, `EvidenceModal.tsx`) — optionally present the zone picker only for shot commands and preserve it on revisions/remapping.
- `frontend/src/components/GkCourtPicker.tsx` — reusable visual touch target only after mapping its legacy 10 origin zones to the new, distinct IHF 1–9 target-zone vocabulary; it must not leak legacy values into canonical payloads.

### Approaches
1. **Canonical goalkeeper panel plus a minimal `shot_zone` payload extension** — Add optional IHF zones and one server-owned player projection; build Phase 1 from current event kinds and Phase 2 zone buckets from the same projection.
   - Pros: One coherent canonical read path; retains evidence and official reconciliation; no legacy mixing; old events remain valid; supports both full-match and goalkeeper-only rival-shot maps.
   - Cons: Requires a projection contract and tests; goals-conceded attribution depends on observed active-goalkeeper context and must expose unknowns.
   - Effort: High

2. **Client-derived goalkeeper panel over `canonical-events`** — Reuse the reports timeline and calculate goalkeeper totals/maps in React.
   - Pros: Smaller backend change and rapid visual iteration.
   - Cons: Violates server-authoritative metrics policy, duplicates eligibility/keeper replay logic, and risks incompatible panel/report totals.
   - Effort: Medium

3. **Reuse legacy goalkeeper/shot-zone data** — Join old `Event` or `GoalkeeperShot` rows into canonical reporting.
   - Pros: Existing zones and picker appear immediately.
   - Cons: Legacy rows are excluded/unreviewed after canonical cutover; they lack compatible evidence/revision semantics and would create contradictory results.
   - Effort: Low, not recommended

### Recommendation
Choose Approach 1 and make the server projection the only source for filtered goalkeeper/player claims.

Use `GET /matches/{match_id}/canonical-player-projection` with required `player_id` and optional `team_id`, `period`, `from_regulation_seconds`, and `to_regulation_seconds`. Validate that the player is roster-eligible and any team belongs to the match. Apply the time range only to events with `clock_unverified == false` and a regulation time; return unverified matching events in a separate `clock_unverified` bucket, never silently include them in the range. The response should contain: selected-player identity/team context; `participation` as observed `lineup_change` evidence/counts only (no minutes or inferred starts); `metrics` with saves and goals conceded as count-only plus observed-decision save rate only when its defined denominator is supported; discipline counts; `shot_map` keyed by IHF zones with `recorded`, `missing_zone`, excluded, unknown, and `clock_unverified` coverage; selected evidence event/revision IDs and video anchors; and unfiltered match-level `canonical_metrics`/`reconciliation` context (or references to the existing endpoints).

For goalkeeper attribution, replay eligible current revisions in canonical sequence. For an eligible opponent shot with outcome `save` or `goal`, attach it to exactly one active opposing goalkeeper at that instant; otherwise count it in an explicit `goalkeeper_unknown` coverage bucket. Do not infer an active keeper from a lineup change. This extends a server derivation, not the payload. Rival shot maps filter to opponent shots attributed to the selected goalkeeper; a full-match player view may use player/team/period filters without claiming filtered match metrics beyond the projection response.

Define `ShotZone = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9]` (serialized as a JSON number) in backend and frontend command types. `shot_zone` is nullable and accepted only for `kind: "shot"`; omitted/null is valid for all historic and new events, and non-shot use is rejected. Because each revision payload is JSON, schema/API validation is the exact persistence change; no column, backfill, or destructive migration is warranted. New captures may select a zone; existing events display “zone not recorded” and contribute to coverage, not to a fabricated zone.

Delivery exceeds the 400-line review budget. Under `delivery_strategy=ask-always`, proposal/tasks should require a delivery decision before apply and plan at least: (1) backend projection and tests, (2) canonical capture/type/API zone extension and tests, (3) panel/timeline/heatmap UI and tests.

### Risks
- Current `shot` transition stores a goalkeeper only for saves; a projection that labels goals conceded without replaying observed `goalkeeper_change` context would fabricate attribution.
- `lineup_change` supports observed participation evidence, not minutes, starts, or exhaustive appearance status; goalkeeper identity is separately indicated by `MatchSquad.is_goalkeeper`.
- IHF 1–9 target zones are incompatible with the legacy picker’s 10 origin zones; a visual mapping needs an explicit domain decision and tests.
- A precise time filter must keep `clock_unverified` records separate, including their evidence/video anchors, rather than ordering them as regulation time.
- Revisions replace the complete payload. Capture, evidence revision, and anchor recalibration must preserve `shot_zone` when resubmitting the latest canonical event.
- The endpoint must derive from latest active canonical revisions only and preserve evidence/revision IDs; it must not persist stale values to `canonical_projections` or read legacy rows.

### Ready for Proposal
Yes — propose one canonical-first change with Phase 1 goalkeeper panel and Phase 2 optional IHF 1–9 capture/projection. State explicitly that `attack_phase`, `goalkeeper_action_type`, and `related_player` semantics are out of scope; that unzoned historic events remain compatible and visible as missing coverage; and that the user must approve the chained delivery plan before apply because the 400-line budget is at risk.
