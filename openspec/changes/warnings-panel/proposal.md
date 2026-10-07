# Proposal: Add Canonical Warnings Panel

## Intent

Make per-player mismatches between canonical analysis and immutable official totals visible and traceable from match statistics, without claiming comparisons the official source cannot support.

## Scope

### In Scope
- Authenticated, canonical-cutover-gated `GET /matches/{id}/warnings-summary`.
- Server-derived per-player and match totals for goals, yellow cards, two-minute exclusions, red cards, and blue cards; each returns canonical and official values, tolerance status, canonical event IDs, and evidence IDs.
- Explicit `not_comparable` statuses for goal/card timestamps and goalkeeper substitutions, because official snapshots do not contain those details.
- Read-only StatisticsPage match panel with semantic status text, icons/colors, keyboard-accessible rows, and evidence drill-down through `ReportEventTimeline` and existing seek behavior.

### Out of Scope
- Official event-detail ingestion, timestamp tolerance calculation, or goalkeeper-substitution comparison.
- Legacy-data mixing, warning resolution actions, revision saves, federation synchronization, database migrations, or deployment changes.

## Capabilities

### New Capabilities
- `warnings-summary`: Server-derived canonical-versus-official totals warnings and an accessible, read-only match-statistics evidence view.

### Modified Capabilities
None.

## Approach

Reuse canonical reconciliation eligibility: active, observed, confirmed canonical revisions only; keep official snapshots immutable. Aggregate canonical events by player and match, match official player records without guessing ambiguous identities, and expose unavailable temporal/goalkeeper checks as `not_comparable`. The client renders only the server contract and opens/selects linked timeline evidence without invoking mutation-oriented `EvidenceModal` behavior.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/api/routes/canonical_analysis.py` | Modified | Warnings summary endpoint and access/cutover guards. |
| `backend/app/services/canonical_analysis_service.py` | Modified | Aggregation, matching, statuses, event/evidence references. |
| `backend/tests/test_canonical_analysis_routes.py` | Modified | Route, eligibility, tolerance, and immutable-data coverage. |
| `frontend/src/api/client.ts`, `frontend/src/types.ts` | Modified | Typed endpoint contract. |
| `frontend/src/pages/StatisticsPage.tsx` | Modified | Match-scoped warnings panel. |
| `frontend/src/components/ReportEventTimeline.tsx`, `frontend/src/timelineInteractions.ts` | Modified | Read-only selection and seek drill-down. |

**Database boundary:** none; read existing canonical events and official snapshots.  
**Deployment boundary:** none; existing SPA/API delivery.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Ambiguous official player identity | Medium | Return unmatched; never infer. |
| Temporal status mistaken for mismatch | Medium | Label and expose `not_comparable` explicitly. |
| Oversized review | High | Plan separately under 400 lines; maintainer approved `size:exception`. |

## Rollback Plan

Remove the endpoint and panel; no data migration or mutation requires reversal. Preserve canonical and official records unchanged.

## Dependencies

- Existing canonical reconciliation, official snapshots, timeline selection, and video seek behavior.

## Success Criteria

- [ ] Eligible canonical totals and immutable official player totals are compared server-side with linked evidence.
- [ ] Unavailable temporal and goalkeeper checks return `not_comparable`, never fabricated mismatches.
- [ ] The panel is keyboard operable and opens read-only evidence navigation.
