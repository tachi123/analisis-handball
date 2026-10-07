# Proposal: PDF Report Export

## Intent

Let an analyst download a readable, evidence-aware match PDF from `StatisticsPage` without publishing data or requiring a backend report endpoint.

## Scope

### In Scope
- Add a client-side `Exportar reporte PDF` flow using `jspdf` and `jspdf-autotable`.
- Load existing canonical state and events; reuse existing match, metrics, reconciliation, and warning projections.
- Provide an explicit optional roster-goalkeeper selector; fetch its projection only when selected.
- Include match header and score, canonical metrics, reconciliation, warning table/detail summary, optional goalkeeper zone summary, and capped key events.
- Disclose deterministic evidence-priority event ordering; retain uncertainty and official-versus-observed boundaries.

### Out of Scope
- Backend, API, schema, database, deployment, publication, recovery-attestation, or mobile-client changes.
- Video, raw canonical payloads, private notes, credentials, unapproved links, legacy metrics/events, or fabricated confidence values.

## Capabilities

### New Capabilities
- `pdf-report-export`: Generate a local, client-side analytical PDF from server-derived canonical projections with explicit evidence and data-boundary disclosures.

### Modified Capabilities
None.

## Approach

Build a narrow report view model rather than converting page DOM. Add `jspdf` plus `jspdf-autotable`; keep layout helpers pure and load PDF code on export. Required reads must settle before export. A selected goalkeeper projection failure blocks export; no selection omits that section. Order key events deterministically by evidence state/completeness and video backing, label it as export priority, and state omitted-event count after the cap.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/package.json`, lockfile | Modified | Add PDF dependencies. |
| `frontend/src/pages/StatisticsPage.tsx` | Modified | Export readiness, canonical reads, optional GK selector. |
| `frontend/src/components/PdfReportExport.tsx` | New | Export control and projection coordination. |
| `frontend/src/pdf/reportPdf.ts` | New | Pure report model and PDF/table layout. |
| Frontend tests | Modified/New | Cover inputs, ordering, omission, errors, download. |
| Backend/database/deployment | Unchanged | Existing read endpoints only. |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| PDF tables overflow or lose context | Medium | AutoTable pagination, repeated headers, capped rows. |
| Export implies unsupported certainty | Medium | Use server values and disclose priority/uncertainty; never show confidence. |
| Change exceeds review budget | High | Approved size exception; plan focused work units and tests. |

## Rollback Plan

Remove the export control, PDF modules, and dependencies. No persisted data, schema, or server behavior requires migration or recovery.

## Dependencies

- `jspdf` and `jspdf-autotable` browser dependencies.
- Existing canonical projection endpoints remain available.

## Success Criteria

- [ ] Analysts can download a static PDF only after required canonical data is ready.
- [ ] The report contains the scoped sections, preserves server-derived values, and omits restricted/raw data.
- [ ] No goalkeeper selection omits the GK section; selected-projection errors are visible and block export.
- [ ] Key-event ordering and omissions are disclosed without claiming confidence.
