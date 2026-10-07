# Tasks: Bulk Planilla Preload

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | 750–1,000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 parser → PR 2 scanner → PR 3 artifacts/CLI and end-to-end guard |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | All-page extraction and real-layout tests | PR 1 | Base: main; parser behavior and tests together. |
| 2 | Pure discovery scanner and SHA canonicalization | PR 2 | Base: PR 1; no DB/model imports; scanner tests included. |
| 3 | Deterministic artifacts, CLI, report, corpus guard | PR 3 | Base: PR 2; writers, CLI, and end-to-end test together. |

## Phase 1: All-page parser foundation

- [x] 1.1 Modify `backend/app/services/pdf_header_parser.py` to aggregate labelled candidates from every page, resolve only one non-conflicting value, and retain page/table/label evidence for split or irregular labels.
- [x] 1.2 Modify `backend/app/services/pdf_service.py` so `parse_femebal_sheet()` extracts every page, merges continuation rosters with page provenance, and preserves the existing preview shape and no-guess score behavior.
- [x] 1.3 Extend `backend/tests/test_pdf_service.py` with real `resources/planillas` layouts: all eight multi-page PDFs, missing-team-label sheets, split labels, degraded text, later-page provenance, and unresolved conflicts.

## Phase 2: Canonical discovery

- [x] 2.1 Create `backend/app/services/planilla_discovery_service.py` as a pure service that recursively case-insensitively discovers PDFs, streams SHA-256, orders paths by `casefold()`/original value, and selects the lexical canonical path with aliases.
- [x] 2.2 Add `backend/tests/test_planilla_discovery_service.py` cases for nested PDFs, duplicate aliases, SHA/path record order, per-file parse-error continuation, and an import guard proving no database or model dependency.

## Phase 3: Review artifacts and local entry point

- [x] 3.1 Implement deterministic UTF-8 `manifest.json` and fixed-column `manifest.csv` writers in `planilla_discovery_service.py`, including schema v1 evidence, rosters, aliases, and JSON-encoded nested columns.
- [x] 3.2 Derive stable quality flags (`multi-page`, missing labels/court, conflicts, degraded text, parse errors) and generate `report.md` with counts plus sorted affected source paths.
- [x] 3.3 Create `backend/scripts/discover_planillas.py SOURCE OUTPUT`; validate inputs, write only the three output files, return non-success on invalid discovery, and keep output under the already-ignored `backend/data/` convention.

## Phase 4: Corpus-level verification

- [x] 4.1 Add a read-only end-to-end CLI test over `resources/planillas` that asserts 138 sources, two duplicate pairs, eight multi-page records, deterministic artifact bytes, source hashes unchanged, and no persistence calls.
