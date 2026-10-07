# Proposal: Bulk Planilla Preload

## Intent

Produce a trustworthy, reviewable inventory of the 3ª División FEMEBAL match sheets before any historical data enters the application. The current one-sheet preview is first-page-only, while 8 of 138 PDFs have a second page and 72 sheets lack one labelled team name.

## Scope

### In Scope
- Local read-only CLI/batch job scanning `resources/planillas`.
- SHA-256 deduplication and all-page extraction of headers, rosters, and scores.
- Per-file JSON and CSV manifest rows: source path, SHA, tournament, date, teams, score, player rows, and quality flags.
- Aggregate quality report: source/duplicate/page counts and unresolved or degraded fields.
- Parser coverage for observed team-header layouts and multi-page roster continuation.

### Out of Scope
- Database writes, source-file changes, identity creation, or fixture mutation.
- Reviewed identity resolution; fixture derivation/reconciliation; and confirmation into `OfficialSnapshots` linked to `ScheduledMatches`.
- Standings/averages query API and YouTube selection integration via existing `Match.youtube_link`.

## Capabilities

### New Capabilities
- `bulk-planilla-discovery`: Generate deterministic, reviewable manifests and aggregate diagnostics from local FEMEBAL planilla PDFs without persistence.

### Modified Capabilities
- `femebal-pdf-header-import`: Extend extraction coverage from first-page preview data to every PDF page while retaining provenance and no-guess semantics.

## Approach

Implement a local command that recursively discovers PDFs, computes SHA-256 before parsing, emits one canonical record per unique SHA, and records duplicate aliases. Reuse parser primitives across every page, aggregate header evidence and side rosters, and flag missing/conflicting/degraded data rather than resolving it. Write JSON, CSV, and a summary report to an ignored output path; analyst review remains the mandatory gate for every later persistence phase.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/app/services/pdf_service.py` | Modified | All-page read-only parsing helpers |
| `backend/app/services/pdf_header_parser.py` | Modified | Header-layout coverage and provenance |
| `backend` CLI/tests | New/Modified | Batch command, manifest writers, parser tests |
| Frontend | None | No UI in Phase 1 |
| Database | None | No models, migrations, or writes |
| Deployment | None | Local-only command |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Missing team labels (72 sheets) | High | Preserve unresolved flags; prohibit matching |
| Incomplete second-page rosters | Medium | Parse every page and test continuations |
| Duplicate source confusion | Medium | SHA canonical record plus alias paths |

## Rollback Plan

Remove the command and generated ignored outputs. No persisted records or source PDFs are changed.

## Dependencies

- Local `resources/planillas` corpus and existing PDF parser dependencies.

## Success Criteria

- [ ] One JSON/CSV canonical manifest and aggregate report are generated without database writes.
- [ ] All 138 source PDFs are scanned; two duplicate pairs are reported; all 8 two-page files are fully parsed.
- [ ] Every unresolved or degraded field is reviewable, and no identity or fixture is inferred.
