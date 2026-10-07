# Design: Local Canonical PDF Report

Generate a bounded, local PDF from existing canonical read projections. `StatisticsPage` keeps its current display queries; a focused export component coordinates the complete export snapshot and lazy-loads PDF code only when the analyst requests a ready report.

## Technical Approach

`PdfReportExport` is rendered in the StatisticsPage header. It uses the existing React Query keys for match, canonical state/metrics/reconciliation/events, and warnings. Cache sharing avoids a second network request for projections already displayed by the page. It owns the optional goalkeeper selection and enables that projection only after an eligible roster player is selected.

On export, the component passes the settled projections to a pure report view-model/PDF module through a dynamic import. The module creates a jsPDF document, uses AutoTable for pageable tables, calls `save(filename)`, and returns no domain data to the server.

## Architecture Decisions

| Decision | Choice | Alternative / tradeoff | Rationale |
|---|---|---|---|
| Report source | Explicit view model, not page DOM | HTML/canvas capture is quicker but fragile and can capture UI state | Makes included fields auditable, selectable, bounded, and independent of responsive layout. |
| Query ownership | Export component issues all required read queries using existing keys | Thread page query results through props | Guarantees its complete readiness contract while React Query deduplicates cached reads. |
| GK data | Local optional selector filtered by `match.squad[].is_goalkeeper`; query enabled only with a chosen ID | Infer the active GK or preload each projection | Avoids unsupported attribution and unnecessary reads. |
| Key-event ranking | `confirmed`, then fewer uncertainty flags, then video-backed, then canonical sequence | Numeric “confidence” | The contract has no confidence field; sequence makes ties deterministic. |
| Bounds | Cap comparison rows at 20, linked IDs per summary at 5, and key events at 30; disclose each omitted count | Unlimited rows | Keeps pages readable and makes omission visible rather than silent. |

## Data Flow

```text
StatisticsPage
  └─ PdfReportExport
       ├─ React Query: match + state + metrics + reconciliation + warnings + events
       ├─ selected GK? ──> canonical-player-projection
       └─ ready click ──> dynamic import(reportPdf) ──> jsPDF.save()
```

Required queries must all be successful before the button enables. Loading keeps it disabled. Any required-query error shows an actionable alert and keeps it unavailable. A selected GK loading state disables export; its error shows an alert and blocks export. With no selection, the GK section is omitted.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/package.json`, `frontend/package-lock.json` | Modify | Add `jspdf` and `jspdf-autotable`. |
| `frontend/src/pages/StatisticsPage.tsx` | Modify | Mount the export control in the header; existing page content remains unchanged. |
| `frontend/src/components/PdfReportExport.tsx` | Create | Read orchestration, readiness/error UI, roster GK selector, lazy GK query, and download trigger. |
| `frontend/src/pdf/reportPdf.ts` | Create | Typed input/model helpers, deterministic ordering, bounded summaries, AutoTable layout, and filename/download. |
| `frontend/src/components/PdfReportExport.test.tsx` | Create | Control readiness, lazy GK/error behavior, and download invocation. |
| `frontend/src/pdf/reportPdf.test.ts` | Create | Ordering, caps/omission text, filename, and section/model tests with mocked PDF libraries. |

## Interfaces / Contracts

```ts
export type PdfReportInput = {
  match: Match; state: CanonicalMatchState; metrics: ReviewedMetrics
  reconciliation: { official: ReviewedMetrics['official']; reconciliation: ReviewedMetrics['reconciliation']; discipline: NonNullable<ReviewedMetrics['discipline']> }
  warnings: WarningsSummary; events: CanonicalEvent[]
  goalkeeper?: CanonicalPlayerProjection
}

export function buildPdfReport(input: PdfReportInput): { filename: string; save(): void }
```

The report includes match identity, official score plus observed/analytical reconciliation, coverage/state, denominator-aware metrics, reconciliation and discipline, warning comparison/detail summaries, optional GK saves/zones/coverage, and capped active canonical events. Event rows retain period, verified/unverified clock state, evidence state, uncertainty, and evidence kinds. No video URLs, notes, raw payloads, credentials, legacy records, or confidence values are mapped. The filename is a filesystem-safe `reporte-canonico-{match.id}-{match.date}.pdf`, with a fixed fallback when the date is absent.

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Unit | ranking/ties, caps, omission disclosures, safe filename, exclusion mapping | Test exported pure helpers with canonical fixtures. |
| Component | disabled loading/error states, roster-only selector, lazy GK read, selected-GK failure, no-GK export | Vitest + Testing Library with API and PDF builder mocks. |
| Integration | complete ready snapshot invokes browser download | Extend StatisticsPage test with mocked `buildPdfReport`; run frontend test, lint, and build. |

## Migration / Rollout

No migration required. This is frontend-only: no API, schema, backend, deployment, publication, recovery-attestation, or mobile-client change. Roll back by removing the control, modules, and dependencies.

## Review Scope

One frontend work unit, targeted below the 400 changed-line review budget (including tests); keep helpers compact and avoid refactoring the existing statistics view. The requested `size:exception` remains recorded only as contingency if dependency lockfile churn makes the measured diff exceed that budget.

## Open Questions

None.
