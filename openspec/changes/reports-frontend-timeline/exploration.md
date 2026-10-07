## Exploration: Reports Frontend Timeline

### Current State
Canonical events already provide the timeline read model: `GET /matches/{matchId}/canonical-events` returns sequence-ordered events with period, action kind, player/team IDs, evidence state, active status, current revision metadata, and video evidence anchors. The existing `EventTimeline` in `MatchReview` already selects an event, seeks its linked video evidence, highlights the event nearest the observed player time, and explains when seek is unavailable.

`mapVideoTime` maps video time through verified playable segments and explicitly returns `clock_unverified` outside verified coverage. `canonical-state`, `canonical-metrics`, and `canonical-reconciliation` already expose server-derived context, coverage, metric evidence IDs, and immutable-official comparison. `StatisticsPage` consumes the latter two; `MatchReview` supplies the video/session context and reusable event interaction patterns.

The review route exists at `/match/:matchId/review`, but the match list currently only opens canonical analysis. There is no dedicated reports/timeline route or match-context entry point. The current event-list component has no filters, chronological display-time sort, or read-only detail panel beyond latest revision reason/evidence kind.

### Affected Areas
- `frontend/src/pages/MatchReview.tsx` — reuse video player/session, `mapVideoTime`, and event seek behavior; extract only stable shared timeline interactions rather than duplicating player logic.
- `frontend/src/components/EventTimeline.tsx` — evolve or split into a reusable, filterable timeline list with accessible event selection and details.
- `frontend/src/api/client.ts` and `frontend/src/types.ts` — existing canonical read clients/types are sufficient for the MVP; no new contract is required.
- `frontend/src/pages/StatisticsPage.tsx` — reuse the canonical metrics/reconciliation presentation pattern as match-context summary, without recalculating filtered metrics on the client.
- `frontend/src/pages/MatchesPage.tsx` and/or `frontend/src/App.tsx` — add a protected timeline route and an explicit entry from the selected match context.
- `frontend/src/components/EventTimeline.test.tsx` and new page/component tests — cover ordering, each filter, seek/no-seek behavior, details, keyboard operation, and accessible filter/result announcements.

### Approaches
1. **Dedicated read-only timeline route backed by existing canonical reads** — Add a protected match-scoped timeline page that fetches events, session, state, metrics, and reconciliation; filters and sorts events locally; reuses MatchReview's player/seek interactions where a video source is available.
   - Pros: Meets the reporting use case without changing authoritative backend behavior; filters are immediate; keeps canonical metrics server-derived; cleanly separates reporting from editing review.
   - Cons: Requires extracting or carefully sharing presentational/player logic from `MatchReview`; local filters do not create filtered authoritative metrics.
   - Effort: Medium

2. **Extend `MatchReview` with report filters and summary** — Put the timeline reporting view inside the existing review workspace.
   - Pros: Lowest initial navigation and player-integration cost; reuses the current event list directly.
   - Cons: Mixes capture/revision controls with read-only reporting, makes a large page larger, and weakens the requested reports frontend boundary.
   - Effort: Medium

3. **Add server-side filtered timeline and metrics endpoints** — Introduce queryable timeline projection plus player/action/period/evidence-state metric aggregation.
   - Pros: Supports large datasets and server-authoritative filtered summaries.
   - Cons: Not needed for the requested event visualization; adds API, validation, tests, and future compatibility surface before evidence of scale or a requirement for filtered metrics.
   - Effort: High

### Recommendation
Choose **Approach 1**. Build a protected, read-only timeline in match context using the current canonical contracts. Sort by verified regulation time when available, otherwise by video anchor, then canonical sequence as a stable fallback; label unverified times rather than implying chronology precision. Filter the downloaded canonical events by `player_id`, `kind`, `period`, and `evidence_state`. Selecting a video-evidenced event seeks through the existing player boundary; an event without video evidence opens details without moving playback.

Use `canonical-state`, `canonical-metrics`, and `canonical-reconciliation` for unfiltered match context only. The UI MUST NOT derive or label filtered totals as authoritative metrics. Detail drill-down can show the latest canonical payload, evidence links, revision number/reason, active state, and clock uncertainty from the existing event response.

No backend addition is needed for this MVP. A future endpoint is justified only if product scope requires historical revision drill-down (the event endpoint exposes only the latest revision) or server-authoritative metrics narrowed by timeline filters.

### Risks
- `CanonicalEvent.sequence` is capture order, not guaranteed game-clock order; the timeline needs the explicit sort/fallback policy above and clear `clock_unverified` labels.
- Local filter results must remain a navigation/view concern; presenting recomputed filtered rates as canonical would violate the server-derived metrics policy.
- A video anchor can be missing or playback unavailable; event details and filters must remain usable, with a clear no-seek explanation.
- Player labels require resolving `player_id` against match roster/context; unknown responsibility must remain explicit rather than hidden or fabricated.
- The current `MatchReview` is already a dense integration surface. Share narrow, tested utilities/components to avoid coupling report rendering to review mutations.

### Ready for Proposal
Yes — propose a frontend-only, match-scoped reports timeline with an explicit entry from match context. Scope the first increment to canonical-event filtering, chronology, accessible details, video seek, and read-only canonical state/metrics/reconciliation context; exclude historical revision payloads and filtered authoritative metrics unless a later requirement establishes the minimal backend contract.
