# Match Preparation Specification

## Purpose

Define trustworthy local preparation of reusable match identities from manual setup or an imported official PDF.

## Requirements

### Requirement: Propose reusable identity matches conservatively

The system MUST propose identity matches from shared normalization and context. It MUST expose candidates, rationale, confidence, and evidence. It MUST NOT merge ambiguous or display-name-only matches. A tournament MAY be high confidence only with unique matching name, category, and year.

#### Scenario: Context-supported proposal

- GIVEN an imported player name normalizes to an existing player and the team and roster context agree
- WHEN the analyst reviews the import preview
- THEN the existing identity is proposed with its supporting context visible

#### Scenario: Ambiguous player proposal

- GIVEN normalized name matching identifies more than one plausible player or conflicting team/roster context
- WHEN the analyst reviews the import preview
- THEN automatic merge is blocked until the local analyst confirms a match or creates a distinct identity

### Requirement: Preserve manual confirmation and official source boundaries

The system MUST allow the analyst to confirm, correct, or decline each identity and finalized header field. It MUST preserve source facts separately from identities and observations. Confirmation MUST revalidate IDs, teams, membership, and metadata in one transaction. It MUST reject incomplete or ambiguous decisions. It MUST create an identity only with no candidate; candidates MUST NOT permit `new`. During fixture-linked match-sheet confirmation, it MUST require explicit existing legacy team and player identities and MUST NOT create legacy identities from fixture or sheet names.

#### Scenario: Analyst declines a proposal

- GIVEN a proposed player match is incorrect
- WHEN the local analyst declines it during review
- THEN the import does not alter the proposed existing player and the analyst can select or create the correct identity

#### Scenario: Distinct tournament candidates

- GIVEN tournament candidates share a name but differ by category or year
- WHEN preview is reviewed
- THEN the proposal MUST be ambiguous and expose all candidates

#### Scenario: Confirm header metadata

- GIVEN the analyst explicitly resolves all identities and header fields
- WHEN confirmation passes server validation
- THEN the match MUST persist approved tournament and header metadata with official snapshot facts

#### Scenario: Reject unsafe creation

- GIVEN an identity has a conservative candidate or confirmation has incompatible IDs
- WHEN confirmation selects `new` or is submitted
- THEN it MUST be rejected without persisting a match or identity

#### Scenario: Fixture-linked confirmation rejects identity creation

- GIVEN fixture-linked match-sheet confirmation has an unresolved identity
- WHEN the analyst requests creation from a fixture or sheet name
- THEN confirmation is rejected without creating a legacy identity

### Requirement: Confirm a scheduled match sheet by stable fixture identity
The system MUST list imported non-bye fixtures with their `fixture_key`, registration-side names and variants, schedule facts, source scores, and result status, and use only the submitted `fixture_key` to select one. It MUST parse one uploaded PDF in that fixture context without persistence, show parsed evidence, compatibility, and `match`, `mismatch`, or `unknown` score reconciliation, and never treat missing scores as zero.

#### Scenario: Preview a compatible sheet
- GIVEN a selected fixture and a parseable compatible PDF
- WHEN the analyst requests preview
- THEN the system returns parsed facts, evidence, and reconciliation without writing a `Match`, snapshot, or squad

#### Scenario: Reject an unknown or bye fixture
- GIVEN the submitted `fixture_key` is unknown or identifies a bye
- WHEN preview or confirmation is requested
- THEN the system rejects the request without creating analysis data

### Requirement: Create one confirmed fixture-linked analysis match
The system MUST re-read the fixture by `fixture_key`, reparse uploaded bytes, validate compatible registration sides and explicit existing identities, and create or link exactly one analysis `Match` with official snapshot and squad. It MUST reject duplicate links safely, preserve fixture scores and result status, require acknowledgement for a known score mismatch, and return the linked `match_id` for video analysis.

#### Scenario: Retry confirmation after success
- GIVEN a fixture already has a linked analysis match
- WHEN the analyst retries the same confirmation
- THEN the system returns the existing `match_id` and creates no additional match, snapshot, or squad

#### Scenario: Block an unacknowledged discrepancy
- GIVEN both fixture and sheet scores are present and differ
- WHEN confirmation omits acknowledgement
- THEN the system rejects the request and leaves all fixture values unchanged
