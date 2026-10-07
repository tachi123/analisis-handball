## Exploration: warnings-panel

### Current State
`GET /matches/{id}/canonical-reconciliation` is a server-derived, read-only comparison of eligible canonical goals and discipline against the latest immutable official snapshot. It supplies team score discrepancies, team discipline totals, and canonical revision evidence; it does not compare players or times.

Canonical events retain player, period, regulation time, active/revision state, and evidence IDs. Official snapshots retain player goal/yellow/red totals, but no official goal/card timestamps and no goalkeeper-substitution records. Therefore ±5-minute comparisons and exact goalkeeper-change checks cannot be calculated from the current official source. `StatisticsPage` already fetches reconciliation. `ReportEventTimeline`, video seeking, and `mapVideoTime` provide accessible read-only evidence navigation, while `EvidenceModal` currently saves revisions and cannot be reused unchanged for a read-only drill-down.

### Affected Areas
- `backend/app/api/routes/canonical_analysis.py` — add the authenticated, cutover-gated warnings-summary route beside reconciliation.
- `backend/app/services/canonical_analysis_service.py` — derive warning rows from the same eligible canonical events and reconciliation rules; retain event and evidence references.
- `backend/app/models.py` and official-planilla ingestion/parser services — required only if official timestamps and goalkeeper substitutions must be compared rather than reported unavailable.
- `backend/tests/test_canonical_analysis_routes.py` and service tests — cover tolerance boundaries, aggregation, inactive/unconfirmed exclusions, missing official detail, and immutable official data.
- `frontend/src/api/client.ts` and `frontend/src/types.ts` — add the warnings-summary contract.
- `frontend/src/pages/StatisticsPage.tsx` — render a match-scoped warnings panel and totals without introducing resolution controls.
- `frontend/src/components/ReportEventTimeline.tsx`, `frontend/src/components/EvidenceModal.tsx`, and `frontend/src/timelineInteractions.ts` — provide a read-only evidence drill-down/seek path; do not invoke revision save actions.
- Frontend page/component tests — cover icons/status colors, keyboard activation, focus/announcement behavior, and video/PDF/unavailable evidence.

### Approaches
1. **Extend official ingestion with normalized official event details** — Persist immutable official goal/card timestamps and goalkeeper changes linked to the snapshot, then derive all requested warnings server-side.
   - Pros: Satisfies every stated tolerance; preserves an explicit official provenance chain; keeps tolerance policy authoritative on the server.
   - Cons: Requires a reliable source/parser for event-level official data, schema and migration work, and ambiguity handling when a planilla lacks those details.
   - Effort: High

2. **Ship totals-only warnings with explicit `not_comparable` temporal statuses** — Compare official per-player goal/card totals now; return unavailable temporal/goalkeeper checks rather than fabricating a comparison.
   - Pros: Lightweight; reuses current reconciliation and canonical evidence; no official-data mutation or legacy mixing.
   - Cons: Does not meet the requested ±5-minute or exact goalkeeper-substitution comparisons; needs product approval that unavailable checks are acceptable warnings.
   - Effort: Medium

3. **Calculate warnings in the frontend from existing reads** — Fetch canonical events and reconciliation and aggregate locally.
   - Pros: Lowest backend effort.
   - Cons: Violates the requested endpoint and server-derived comparison boundary; cannot solve missing official temporal data; risks divergent tolerance logic.
   - Effort: Medium

### Recommendation
Choose **Approach 1** if the endpoint MUST enforce all listed tolerances. Define a versioned official-event projection (goal, yellow/red card, goalkeeper change) sourced from the immutable official snapshot/PDF, including a distinct `not_recorded` status when the source has no event detail. The warnings service should call the existing reconciliation/read-event logic, apply the explicit tolerance table server-side, and return only aggregated player rows and totals with canonical/official values, tolerance status, canonical event IDs, official-source references, and canonical evidence IDs.

For the frontend, add the panel to `StatisticsPage`; use semantic status text plus color/icon rather than color alone. Warning rows must be buttons with Enter/Space activation and keyboard focus. The drill-down should select the linked canonical event in `ReportEventTimeline` and seek through the existing video interaction; extend `EvidenceModal` with a read-only mode only if a modal is required for PDF/video evidence. Do not expose save, revision, resolution, federation sync, or new audit actions.

### Risks
- Current official storage cannot support time or goalkeeper-change comparisons. Treating a missing timestamp as a mismatch would fabricate evidence; treat it as `not_comparable` only if explicitly approved.
- Official player identity can be null even when name/jersey are present, so matching must be explicit and ambiguous official players must remain unmatched rather than guessed.
- `canonical-reconciliation` counts only active, observed, confirmed canonical events. Warnings must preserve that policy or document any intentional different coverage.
- `EvidenceModal` currently mutates a revision; using it directly would create the prohibited resolution workflow.
- The complete backend plus accessible frontend slice is likely above the 400-line review budget; later task planning should forecast chained work units.

### Ready for Proposal
No — first confirm whether the official data source can provide timestamped goals/cards and goalkeeper substitutions. If it can, propose the normalized official-event ingestion plus the server-derived warnings endpoint and read-only statistics panel. If it cannot, explicitly narrow the change to totals-only warnings with `not_comparable` temporal checks; that is a different product contract from the stated tolerance dashboard.
