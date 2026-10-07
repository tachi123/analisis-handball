# Tasks: PDF Report Export

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 430–560 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | One approved `size:exception` slice; split only if the exception is withdrawn |
| Delivery strategy | exception-ok (preflight: auto, ask-always) |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Local PDF export, control, integration, and focused tests | Single PR | Approved size exception; keep tests with behavior. |

## Phase 1: Dependencies and Report Foundation

- [x] 1.1 Add `jspdf` and `jspdf-autotable` to `frontend/package.json` and regenerate `frontend/package-lock.json`; verify TypeScript-compatible imports.
- [x] 1.2 Create `frontend/src/pdf/reportPdf.ts` with typed `PdfReportInput`, safe `reporte-canonico-{match.id}-{date}.pdf` naming and a date-absent fallback.
- [x] 1.3 Build pure report-model helpers in `reportPdf.ts` for server-derived match/score, metrics, reconciliation, warnings, optional GK, and restricted-field exclusion.

## Phase 2: Bounded PDF Generation

- [x] 2.1 Implement `buildPdfReport()` in `frontend/src/pdf/reportPdf.ts` using jsPDF and AutoTable, pageable headers, required sections, and `save(filename)`.
- [x] 2.2 Apply report caps: 20 comparison rows, 5 linked IDs per summary, and 30 key events; emit omitted-item counts for every truncated collection.
- [x] 2.3 Rank events confirmed first, then fewer uncertainty flags, then video-backed, then canonical sequence; render period, clock state, evidence state, uncertainty, evidence kinds, and an ordering-not-confidence disclosure.
- [x] 2.4 Add `frontend/src/pdf/reportPdf.test.ts` with mocked PDF libraries for sections/exclusions, filename/download, event ordering, caps, and omission disclosures.

## Phase 3: Export Control and Statistics Wiring

- [x] 3.1 Create `frontend/src/components/PdfReportExport.tsx` using existing React Query keys for all required canonical reads and dynamic-import `reportPdf` only on a ready export click.
- [x] 3.2 Add the roster-goalkeeper-only selector and an enabled-only-after-selection player projection query; omit GK data without a selection.
- [x] 3.3 Keep export disabled while any required or selected-GK query loads; expose actionable required/GK errors and block downloads on either failure.
- [x] 3.4 Mount `PdfReportExport` in the `frontend/src/pages/StatisticsPage.tsx` header without refactoring existing statistics reads or changing backend/API behavior.

## Phase 4: Component and Integration Verification

- [x] 4.1 Add `frontend/src/components/PdfReportExport.test.tsx`: disabled until reads succeed, required-read error, roster filtering/lazy GK request, selected-GK error, and export without GK.
- [x] 4.2 Extend the relevant `StatisticsPage` test to mock `buildPdfReport` and prove a complete ready snapshot invokes the download with selected GK data when available.
- [x] 4.3 Run `npm --prefix frontend test -- --run`, `npm --prefix frontend run lint`, and `npm --prefix frontend run build`; record any dependency-lockfile size contribution before review.

## Phase 5: Verification Gap Remediation

- [x] 5.1 Add runtime PDF assertions for the explicit confirmed → fewer-uncertainty → video-backed ordering disclosure and omitted counts after warning/event table caps.
- [x] 5.2 Assert a selected-goalkeeper projection failure surfaces its alert, keeps export disabled, and never invokes the PDF builder.

## Phase 6: Final Verification Gap Remediation

- [x] 6.1 Add a mocked-PDF builder runtime test asserting all required report sections, optional goalkeeper zone summary, static warning detail, ordering disclosure, and capped omission counts.
- [x] 6.2 Prove the PDF match header preserves distinct official and observed scores in the same runtime builder test.
