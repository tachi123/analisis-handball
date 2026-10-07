## Exploration: pdf-report-export

### Current State
`StatisticsPage` already loads the match, server-derived `canonical-metrics`, immutable `canonical-reconciliation`, and `warnings-summary`; it renders canonical coverage, metric context, official score comparison, and warning details. `canonical-state`, `canonical-events`, and the goalkeeper projection client already exist, but are not loaded by that page. The selected goalkeeper is currently local only to `GoalkeeperPanel`; StatisticsPage has no goalkeeper selection state.

Canonical metrics, reconciliation, warnings, and goalkeeper data are read-only server projections. `CanonicalEvent` provides evidence state, uncertainty, evidence kinds, and optional video anchors, but it has no evidence-confidence field. Therefore a PDF cannot truthfully claim a server-supplied confidence score. It can transparently prioritize events by evidence state/completeness (for example confirmed, then fewer uncertainty flags, then video-backed) and label that as an export ordering rather than an authoritative metric.

The frontend has no PDF dependency. jsPDF supports browser-side typed PDF generation and download; jsPDF-AutoTable supplies paginated tables with repeatable headers. This fits static summary/table output better than screenshotting the responsive UI and avoids exporting interactive controls, video, or private raw payloads.

### Affected Areas
- `frontend/package.json` and lockfile — add `jspdf` and `jspdf-autotable`; neither is currently installed.
- `frontend/src/pages/StatisticsPage.tsx` — add an export control, export readiness/error state, canonical state/events reads, and an optional roster-goalkeeper selection used only for the export.
- `frontend/src/components/PdfReportExport.tsx` (new) — gather the already-loaded projections, lazily load the selected goalkeeper projection, and invoke the report builder without adding a write/API endpoint.
- `frontend/src/pdf/reportPdf.ts` (new) — pure report layout/data-normalization helpers and jsPDF/AutoTable generation: header/score, canonical metrics, reconciliation/warnings summary, optional goalkeeper zone summary, and ordered key events.
- `frontend/src/pages/StatisticsPage.test.tsx` and new focused PDF helper/component tests — verify report inputs, no-goalkeeper behavior, warning limits/detail summary, event-order disclosure, filename/download, and disabled/error states.

### Approaches
1. **Programmatic PDF builder with jsPDF + AutoTable** — Create a small export component and a testable report-builder module. Tables use server values directly; the goalkeeper selector is explicit and the projection fetch is enabled only after selecting a roster goalkeeper.
   - Pros: Selectable/searchable text, reliable pagination and repeated table headings, controlled static layout, and no DOM/canvas fidelity dependency. Keeps authoritative values server-derived.
   - Cons: Requires layout helpers, dependency additions, and PDF-output tests will need to mock the library rather than inspect a browser-rendered document.
   - Effort: Medium-high; likely exceeds the 400-line review guideline, with the approved size exception.

2. **Export a rendered StatisticsPage section through HTML/canvas conversion** — Render a print-only DOM subtree and convert it with an HTML-to-PDF library.
   - Pros: Faster visual reuse of existing cards/charts.
   - Cons: Fragile pagination and fonts, rasterized/unselectable content, difficult chart/table/accordion capture, and it risks exporting transient interactive state instead of an explicit report projection.
   - Effort: Medium.

### Recommendation
Use **Approach 1**. Add `Exportar reporte PDF` beside the StatisticsPage header and generate the file only after all required canonical reads are settled. Build the PDF from a narrow, explicit report view model—not from the page DOM—and use existing endpoints only: match, `canonical-state`, `canonical-metrics`, `canonical-reconciliation`, `warnings-summary`, `canonical-events`, and, when the analyst selects an eligible goalkeeper, `canonical-player-projection`.

The report should contain: match identity and official/analytical score; canonical coverage/state and the existing denominator-aware metrics table; immutable reconciliation; a compact warnings table (canonical/official/status/linked-event count) followed by limits and only warning detail summaries with linked IDs—PDF output is static, not expandable; an optional goalkeeper section with observed save data, zone counts, and coverage disclosure; and a capped set of key events. The event section must state its deterministic ordering rule and show period/clock state, evidence state, uncertainty, and evidence kinds. It must not call this order “confidence” unless a future API adds an authoritative confidence contract.

Do not use legacy `Event`, `reviewed-metrics`, or legacy goalkeeper rows. Do not embed video, raw canonical payloads, private notes, credentials, or unapproved media links. The export is a local client download, separate from report-package publication and its recovery attestation workflow.

### Risks
- “Top events by evidence confidence” has no canonical confidence field. Relabel it to a disclosed evidence-priority ordering or accept a later backend contract; fabricating a numeric confidence is out of bounds.
- A goalkeeper is not selected in StatisticsPage today. The export flow needs an explicit optional selector, and must omit the section—not infer an active goalkeeper—when none is selected.
- Incomplete/erroring optional reads must not yield a document that looks complete. Disable export until required reads load; if the chosen goalkeeper projection fails, surface the error and do not silently substitute aggregate data.
- PDF is static: warning “expandable detail” can only become concise appended detail, not an interactive disclosure.
- Long warning/event tables require page-break-safe headings and a hard display cap with a stated “remaining events omitted” count to protect readability and file size.
- This is an export, not public publication; it must retain canonical uncertainty/official-source boundaries and must not imply publication or recovery attestation.

### Ready for Proposal
Yes — propose a frontend-only client PDF export using jsPDF + AutoTable, with a transparent event-priority rule, explicit optional goalkeeper selection, no backend/schema changes, and the approved size exception recorded for later task planning.
