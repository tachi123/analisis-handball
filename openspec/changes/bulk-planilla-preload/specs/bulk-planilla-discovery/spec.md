# Bulk Planilla Discovery Specification

## Purpose

Provide a local, read-only, reviewable inventory of FEMEBAL planilla PDFs before any import decision.

## Requirements

### Requirement: Scan corpus and identify duplicate sources
The system MUST recursively scan a caller-selected `resources/planillas` directory for PDFs and MUST compute SHA-256 for every discovered source. It MUST emit one canonical manifest entry per unique SHA and report every other path with that SHA as a duplicate alias.

#### Scenario: Report duplicate aliases
- GIVEN two discovered PDFs have identical bytes
- WHEN discovery completes
- THEN one canonical entry contains their SHA
- AND the report identifies the other source path as a duplicate alias

#### Scenario: Scan nested folders
- GIVEN PDFs exist in nested tournament folders
- WHEN the local command is run against the corpus root
- THEN each PDF is included in discovery

### Requirement: Emit complete per-file manifest facts
The system MUST emit JSON and CSV manifest representations for each canonical source, including source path, SHA-256, page count, header facts, scores, side roster rows, raw tournament/stage source text, and quality flags. It MUST parse every page; continuation roster rows on page two or later MUST be included. Tournament and stage text MUST remain source text and MUST NOT be mapped to application entities.

#### Scenario: Include continuation roster rows
- GIVEN a two-page planilla with roster rows on page two
- WHEN its canonical manifest entry is generated
- THEN the entry contains rows from both pages
- AND its `multi-page` quality flag is set

#### Scenario: Preserve incomplete headers
- GIVEN a sheet lacks a labelled team or court
- WHEN its entry is generated
- THEN the unavailable field is unresolved
- AND the matching `missing-team-label` or `missing-court` flag is set

### Requirement: Report discovery quality
The system MUST generate an aggregate summary report with discovered-source, canonical, duplicate, and page counts, plus counts and paths for each quality flag and unresolved/degraded field. It MUST report parsing failures without suppressing successfully processed sources.

#### Scenario: Surface degraded corpus data
- GIVEN one or more canonical entries have quality flags
- WHEN the summary is generated
- THEN the summary groups the affected paths by flag

### Requirement: Be deterministic and locally usable
The local CLI MUST accept a source directory and output destination, create only generated output at that destination, and return a non-success status for invalid input or discovery failure. Given unchanged source bytes and equivalent command inputs, it MUST produce equivalent canonical manifest and summary content.

#### Scenario: Repeat a discovery run
- GIVEN unchanged source PDFs and command inputs
- WHEN discovery runs twice
- THEN both runs produce equivalent manifests and summaries

### Requirement: Prohibit Phase 1 persistence
The system MUST NOT write to the database, create or update identities, fixtures, matches, snapshots, or roster records, and MUST NOT modify source PDFs. Identity resolution, fixture derivation or reconciliation, import confirmation, standings/averages APIs, and video-selection integration are out of scope.

#### Scenario: Run against application infrastructure
- GIVEN database access is configured
- WHEN the discovery command completes
- THEN no persistent application record is created or changed
