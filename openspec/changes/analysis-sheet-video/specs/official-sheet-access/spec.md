# Official Sheet Access Specification

## Purpose

Expose confirmed imported match evidence to an authenticated analyst without exposing server filesystem provenance.

## Requirements

### Requirement: View the latest confirmed official sheet facts

The system MUST provide authenticated, match-scoped access to the latest confirmed official snapshot's provenance, official teams and scores, and imported player facts. It MUST NOT return `source_path` or other server-local file paths. A match response without confirmed evidence MUST report that absence without representing match scores as official-sheet facts.

#### Scenario: View confirmed imported facts

- GIVEN an authenticated analyst opens the official-sheet view for a match with confirmed snapshots
- WHEN the system retrieves the evidence
- THEN it presents only the latest confirmed snapshot's official facts and player facts
- AND it does not expose server-local paths

#### Scenario: No confirmed evidence

- GIVEN an authenticated analyst opens the official-sheet view for a match without a confirmed snapshot
- WHEN the system retrieves the evidence
- THEN it returns an actionable unavailable state
- AND it does not invent official scores or player facts

### Requirement: Deliver confirmed source PDFs safely inline

The system MUST authenticate PDF access, derive the PDF exclusively from the selected confirmed snapshot, and serve a readable approved-root PDF inline as `application/pdf`. It MUST NOT accept a client-supplied filename or path, nor serve evidence outside approved roots. Unavailable, deleted, unreadable, or unsafe evidence MUST produce a non-success actionable state while confirmed facts remain retrievable.

#### Scenario: Open an approved source PDF

- GIVEN an authenticated analyst requests the PDF for a match whose latest confirmed snapshot resolves to a readable approved-root PDF
- WHEN the system processes the request
- THEN it delivers that PDF inline as `application/pdf`
- AND it does not disclose its filesystem location

#### Scenario: Source PDF is unavailable

- GIVEN the match has a latest confirmed snapshot but its source PDF is missing, unreadable, or outside approved roots
- WHEN the analyst requests the PDF
- THEN the system returns a non-success actionable state
- AND the analyst can still retrieve the confirmed imported facts
