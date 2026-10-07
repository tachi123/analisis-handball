## Exploration: warnings-panel-expandable-detail

### Current State
`WarningsPanel` already receives server-derived canonical-versus-official totals from `warnings-summary`. Each comparison includes the official total plus linked canonical event and evidence IDs. It lazily fetches the existing `canonical-events` and analysis session only after a comparison is activated, then opens a broad, read-only `ReportEventTimeline` and uses the established YouTube seek path.

The canonical-event response already contains every requested event field: player ID, kind, period, regulation time/clock state, evidence state, and evidence records with a video anchor. The official source exposes totals but not event timestamps, which matches the requested official counterpart boundary. No API or persistence change is required.

### Affected Areas
- `frontend/src/components/WarningsPanel.tsx` — replace the broad timeline drill-down with an independently expandable comparison detail that filters to its linked canonical events and shows the official total.
- `frontend/src/components/WarningsPanel.test.tsx` — cover expansion, native Enter/Space activation, ARIA state/linkage, the required event fields, and per-event video seeking/unavailable evidence.
- `frontend/src/timelineInteractions.ts` — reuse its existing seek-target helper; modification is not expected unless the panel needs a small exported presentation helper.
- `frontend/src/hooks/useYouTubeSync.ts` — reuse its existing player readiness and seek behavior; modification is not expected.

### Approaches
1. **Inline comparison disclosure** — Make each linked warning comparison a native button with `aria-expanded` and `aria-controls`; render a detail region directly beneath the comparison with its official total and only the linked canonical events. Each event presents player, kind, period, regulation time, video time, and evidence type, with a separate action that selects/seeks its video evidence.
   - Pros: Directly satisfies the per-warning review flow; limits the analyst to relevant evidence; uses the existing two reads and seek behavior; native buttons provide Enter/Space behavior without custom keyboard handlers.
   - Cons: `WarningsPanel` remains a relatively dense component and must carefully manage one or more expanded comparisons and player readiness.
   - Effort: Medium

2. **Keep the existing timeline drill-down and add a summary above it** — Retain `ReportEventTimeline`, add the official total and linked-event list above it, and preselect the first event.
   - Pros: Reuses an established timeline/detail UI with less new presentation code.
   - Cons: The timeline includes unrelated canonical events and filters, so it is not a focused per-warning expandable detail; it increases cognitive load during planilla review.
   - Effort: Low

### Recommendation
Use **inline comparison disclosure** in `WarningsPanel`. Keep `warnings-summary` authoritative for the official counterpart and canonical IDs, lazily fetch the already available canonical events on first expansion, and filter them by `canonical_event_ids`. Render the official figure as a total only—never add or infer timestamps. For every linked event, show the requested fields explicitly and list all available evidence types; where a video evidence anchor exists, reuse `seekTargetForEvent` and `useYouTubeSync` to seek only after the player is ready.

The expansion control should be a native `button` with `aria-expanded` and a stable `aria-controls` target. Do not add an `onKeyDown` Enter/Space shim: native buttons already implement that behavior and the existing shim risks duplicate activation. Detail viewing and seeking remain read-only; no revision, resolution, or official-data mutation controls belong in this change.

### Risks
- A comparison can have no canonical IDs (for example, an official-only total); its detail must state that there are no linked canonical events rather than offering a dead expansion action.
- Some canonical events lack a video anchor or have PDF/unavailable evidence. Their details remain visible, but seek must not run and must explain why.
- Existing table cells are dense. An inline expansion must preserve valid table semantics and unique ARIA IDs; a full-width detail row after the owning player/total row is safer than nesting a section directly in a cell.
- The frontend component and focused tests may approach the 400-line review guideline. `size:exception` is approved, but the later task plan should still forecast the actual diff and keep this read-only UI slice reviewable.

### Ready for Proposal
Yes — propose a frontend-only, read-only expansion of `WarningsPanel`; reuse `warnings-summary`, `canonical-events`, evidence, and video seeking with no backend endpoint or schema work.
