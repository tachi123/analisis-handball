# Official Planilla Preload Specification

## Purpose

Load an approved local corpus as fixture-linked official evidence without changing source PDFs.

## Requirements

### Requirement: Gate a batch by its reviewed inputs
The system MUST load a batch only when one approval file binds the exact manifest and team-mapping SHA-256 values. A failed approval MUST reject the entire batch before any persistent change and retain an auditable rejection reason.

#### Scenario: Reject an approval hash mismatch
- GIVEN an approval whose mapping hash differs from the supplied mapping
- WHEN the batch is requested
- THEN the system rejects every record and creates no fixture or snapshot

### Requirement: Create idempotent official fixture evidence
The system MUST derive deterministic fixture keys, seed non-bye fixtures idempotently, and create one `OfficialSnapshot` per fixture from the local PDF path and SHA-256 without uploading PDF bytes. Each snapshot MUST link to its `ScheduledMatch` and record the official result status.

#### Scenario: Rerun an approved batch
- GIVEN a successfully loaded approved batch
- WHEN the same batch is run again
- THEN no duplicate fixture, ScheduledMatch, or OfficialSnapshot is created

### Requirement: Preserve mapped fixture authority
The system MUST reject a sheet whose reported teams contradict its mapped fixture and MUST NOT silently relink or replace either team. The rejection MUST identify the fixture key and conflicting values.

#### Scenario: Detect contradictory sheet teams
- GIVEN a sheet mapped to fixture key `K` with a different home team
- WHEN the loader validates the sheet
- THEN fixture `K` remains unchanged and that sheet is rejected
