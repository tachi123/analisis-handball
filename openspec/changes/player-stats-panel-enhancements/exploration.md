## Exploration: Player Stats Panel Enhancements

### Current State
`StatisticsPage` is now canonical-first: it renders server-derived metrics and match-level reconciliation, but has no player drill-down. Its retained `LegacyStatisticsPage` locally aggregates legacy `Event` rows (including `attack_phase` and `shot_zone`), which cannot be the source for a canonical match. The canonical contracts expose current events, eligible metric evidence, reconciliation, roster context, and video anchors; `ReportEventTimeline` already demonstrates accessible filtering and seek-on-select.

The existing canonical event payload supports period, kind, player/related player, outcome, evidence state, regulation time, and evidence. It does **not** support `attack_phase`, shot zone, assist attribution, or richer shot outcomes. `canonical-metrics` only derives player metrics for shots, turnovers, recoveries, and discipline; it is not filterable by time and does not provide a player projection. Observed `lineup_change` events can show recorded on/off context, but cannot establish minutes played or participation when no starting/substitution observations exist.

### Affected Areas
- `frontend/src/pages/StatisticsPage.tsx` — canonical statistics page and likely host for the player detail panel.
- `frontend/src/components/ReportEventTimeline.tsx` and `frontend/src/reportTimeline.ts` — reusable accessible event filtering, rows, and selection patterns.
- `frontend/src/pages/MatchReportsTimeline.tsx` — proven composition of canonical events, session, player labels, video seek, metrics, and reconciliation.
- `frontend/src/timelineInteractions.ts` and `frontend/src/videoReview.ts` — use `seekTargetForEvent` (two-second preroll) and `mapVideoTime` to preserve evidence/time uncertainty.
- `frontend/src/api/client.ts`, `frontend/src/types.ts` — existing canonical reads plus any narrowly extended projection/types.
- `backend/app/services/canonical_analysis_service.py` and `backend/app/api/routes/canonical_analysis.py` — only if the chosen scope requires new canonical fields or a server-owned filtered player projection.

### Approaches
1. **Canonical event-driven panel with current contracts** — Fetch match, canonical events, metrics, reconciliation, and analysis session; derive player event lists and period/time filters in the client.
   - Pros: no backend change; reuses evidence/video timeline primitives; preserves canonical events as the displayed source.
   - Cons: only period/kind/time/evidence filters and existing canonical metric families are truthful; no zone, attack-phase, assist, or complete participation/minutes view.
   - Effort: Medium

2. **Canonical player projection plus a minimal event-context extension** — Add optional, observable event fields for `attack_phase` and shot zone (and explicitly scoped related-player semantics if assist attribution is required), then expose a server-derived per-player, time-filterable projection with metric coverage and evidence IDs.
   - Pros: fulfills the requested breakdowns without client-authoritative metrics; makes sup/inf and zone analysis possible; scales beyond one screen.
   - Cons: requires schema/API/migration and capture UI work; each added field needs codebook rules, eligibility handling, and tests.
   - Effort: High

3. **Blend legacy event fields into the canonical panel** — Use `/events` for zones/phases while showing canonical metrics and reconciliation.
   - Pros: fastest route to legacy rich fields.
   - Cons: violates canonical cutover semantics and can present incompatible totals/evidence; legacy rows are explicitly read-only/unreviewed in canonical mode.
   - Effort: Low, but not recommended

### Recommendation
Deliver this as a canonical-first panel in two honest layers. The initial MEDIO slice should reuse the existing endpoints and Timeline behavior: roster-listed vs observed-participation status (never minutes), canonical action breakdown by period/kind/outcome, selectable time window over verified regulation time with an explicit separate `clock_unverified` bucket, evidence rows, video seek through `seekTargetForEvent`, `mapVideoTime` clock disclosure, and match-level canonical metric/reconciliation context.

Do not manufacture zone, `attack_phase`, superiority/inferiority, assists, or per-player official deltas from the current canonical payload. If those are non-negotiable acceptance criteria, choose Approach 2 and make the smallest backend addition a canonical event-context extension plus a server-owned filtered player projection. Reconciliation should remain team-level until immutable official player rows are exposed through a dedicated canonical reconciliation projection; `Match.squad` values are not sufficient evidence that they are the current official snapshot.

### Risks
- Mixing legacy `Event` aggregation with canonical metrics creates contradictory totals after canonical cutover.
- A time filter must not silently order or include `clock_unverified` events as precise regulation time; retain sequence/audit visibility and label the limitation.
- Lineup changes are optional context, so inferred minutes, starts, or full match participation would be unsupported claims.
- Existing canonical shot outcomes are only `goal`, `save`, and `miss`; the legacy zone/result table cannot be reproduced faithfully without a contract extension.
- A full backend extension likely exceeds the 400-line review budget and should be planned as chained slices under `delivery_strategy=ask-always`.

### Ready for Proposal
Yes — if the proposal explicitly selects either (a) the no-backend canonical-first scope above or (b) a contract-extension slice before claiming phase/zone and richer per-player reconciliation. The orchestrator should ask the user whether phase/zone/superiority data is mandatory for this change; that decision determines whether minimal existing-contract delivery is sufficient.
