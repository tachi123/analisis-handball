# Design: Bulk Planilla Preload

## Technical Approach

Add a read-only discovery pipeline that hashes every PDF before parsing, parses each canonical PDF across all pages, and writes deterministic review artifacts. It extends the existing conservative header extraction without changing confirmation, identity, fixture, or model flows. The batch code imports neither `SessionLocal` nor models, so Phase 1 cannot write the database.

## Architecture Decisions

| Decision | Alternatives considered | Rationale |
|---|---|---|
| Keep discovery separate from `PDFService` confirmation paths | Add a batch loop to `PDFService` | `PDFService` contains DB and file-copy operations. A pure `planilla_discovery_service` creates a hard no-persistence boundary while reusing its parsing primitives. |
| Aggregate page candidates before resolving fields | Resolve page 1 only; choose a later-page value | This preserves labelled provenance and makes conflicting labelled values unresolved rather than guessed. |
| Canonicalize by SHA-256, retain aliases | Parse every pathname | Identical PDFs are parsed once and aliases remain auditable; the observed corpus has two duplicate pairs. |
| Emit UTF-8 JSON/CSV and preserve raw text | Repair replacement characters | Samples contain `�` in category text. Preserve the raw token, add an encoding flag, and never silently alter evidence. |

## Data Flow

```text
source root --sorted PDF paths--> SHA-256 grouping --canonical PDFs-->
all-page extractor --> canonical manifest records --> JSON + CSV + report
                         |                                      |
                         +--> aliases / quality flags <----------+
```

`discover_planillas.py SOURCE OUTPUT` validates paths, calls the pure service, and writes only `manifest.json`, `manifest.csv`, and `report.md` below `OUTPUT`. It processes 137/138-sized corpora sequentially: hashing streams fixed-size chunks, then opens only one canonical PDF at a time. This bounds memory, avoids redundant duplicate parsing, and is sufficient for this small local corpus; parallel `pdfplumber` extraction is deliberately deferred for reproducibility and easier diagnostics.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/app/services/pdf_header_parser.py` | Modify | Collect labelled candidates from all pages and resolve one evidenced field set; support split/irregular labels without guessing. |
| `backend/app/services/pdf_service.py` | Modify | Make read-only sheet parsing iterate every page, merge continuation rosters, and retain existing preview shape. |
| `backend/app/services/planilla_discovery_service.py` | Create | Pure scanner, SHA grouping, manifest/report construction, flags, and deterministic writers. |
| `backend/scripts/discover_planillas.py` | Create | Local argparse entry point following `seed_fixture.py` path setup; no DB imports. |
| `backend/tests/test_pdf_service.py` | Modify | Cover multi-page evidence and continuation rows. |
| `backend/tests/test_planilla_discovery_service.py` | Create | Cover aliases, ordering, output schema, flags, failures, and no-persistence boundary. |
| `.gitignore` | Modify | Ignore the local discovery output directory under already-ignored `backend/data/`. |

## Interfaces / Contracts

```python
CanonicalSheet = {
  "schema_version": 1, "sha256": str, "source_path": str,
  "duplicate_aliases": list[str], "page_count": int,
  "fields": dict[str, Evidence], "rosters": {"local": list[PlayerRow], "visitante": list[PlayerRow]},
  "quality_flags": list[str], "parse_error": str | None,
}
Evidence = {"value": str | int | None, "raw": str | None,
            "source": {"page": int, "table": int | None, "label": str} | None,
            "confidence": "high" | "unresolved", "warnings": list[str]}
```

`manifest.json` contains `schema_version`, sorted `records`, and source-relative POSIX paths. `manifest.csv` has one canonical row with scalar header columns, `duplicate_aliases_json`, `local_players_json`, `visitante_players_json`, and `quality_flags_json`; JSON columns retain player-page provenance without lossy flattening. `report.md` groups sorted source paths by flag and reports source, canonical, duplicate, page, unresolved, degraded, and parse-error counts.

Stable flags include `multi-page`, `missing-team-label`, `missing-court`, `conflicting-labelled-field`, `encoding-degraded-source-text`, and `parse-error`. Paths are recursively discovered as `.pdf` case-insensitively, rendered relative with `/`, sorted by `casefold()` then original value; canonical records sort by SHA then path. Writers use UTF-8, `newline="\n"`, `ensure_ascii=False`, fixed CSV column order, and no timestamps. The lexically first path is canonical; later same-SHA paths are aliases.

Later import/review phases consume `schema_version: 1` records keyed by SHA and source aliases, including fields, raw evidence, rosters, and flags. They MUST reject unresolved/conflicting records until an explicit reviewed mapping is added; they do not reopen or reparse PDFs.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | All-page header/roster merge, split labels, malformed encoding | Synthetic table/page fixtures plus representative PDFs. |
| Integration | Scanner outputs, SHA aliases, deterministic rerun, per-file error continuation | Temporary nested corpus and output directory; compare artifact bytes. |
| Guard | No database/model access or source mutation | Monkeypatch DB/model entry points; hash source files before/after; invoke CLI. |

## Migration / Rollout

No migration required. Run locally into `backend/data/planilla-discovery/`; delete that generated directory to roll back. No frontend, API, mobile, deployment, database schema, model, or source-PDF change is involved.

## Open Questions

None.
