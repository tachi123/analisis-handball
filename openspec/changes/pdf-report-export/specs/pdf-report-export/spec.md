# PDF Report Export Specification

## Purpose

Define a local `StatisticsPage` PDF export that presents bounded, server-derived canonical analysis without publishing or extending the API.

## Requirements

### Requirement: Export a bounded canonical match report

The system MUST let an analyst download a local PDF from `StatisticsPage` using existing read projections only. The report MUST include match identity and official/observed score, the canonical denominator-aware metrics table, immutable reconciliation, a warnings table with static detail summaries, and key events. It MUST NOT publish data or require backend, schema, or endpoint changes.

#### Scenario: Download complete report
- GIVEN the required canonical projections are ready
- WHEN the analyst requests the PDF export
- THEN a local PDF download contains every required report section
- AND its filename identifies the exported match

#### Scenario: Preserve analytical boundaries
- GIVEN official and observed values differ
- WHEN the report is generated
- THEN reconciliation retains both values and their distinction

### Requirement: Require ready canonical reads

The system MUST require match, canonical state, canonical metrics, reconciliation, warnings summary, and canonical events to settle successfully before enabling export. It MUST use server-derived values and MUST NOT calculate authoritative metrics in the client.

#### Scenario: Required reads loading
- GIVEN one required projection is loading
- WHEN `StatisticsPage` is displayed
- THEN the export action is disabled

#### Scenario: Required read failure
- GIVEN a required projection fails
- WHEN the analyst views the export control
- THEN the action remains unavailable and exposes an actionable error

### Requirement: Select goalkeeper explicitly and optionally

The system MUST offer an explicit optional selector limited to roster-eligible goalkeepers. It MUST request a goalkeeper projection only after a selection. Without a selection, the PDF MUST omit the goalkeeper section; with a successful selection, it MUST include observed-save, zone-count, and coverage summary data.

#### Scenario: Export without goalkeeper
- GIVEN no goalkeeper is selected and all required reads are ready
- WHEN the analyst exports the report
- THEN the download succeeds without a goalkeeper section

#### Scenario: Selected goalkeeper projection failure
- GIVEN a goalkeeper is selected and its projection fails
- WHEN the analyst attempts export
- THEN the system shows the failure and blocks the download

### Requirement: Disclose evidence-priority key events

The system MUST present key events in a deterministic disclosed export-priority order: confirmed events first, then events with fewer uncertainty flags, then video-backed events. Each event entry MUST retain period, clock state, evidence state, uncertainty, and evidence kinds. The report MUST label this as ordering, not confidence or an authoritative score.

#### Scenario: Disclose event order
- GIVEN eligible key events differ in evidence state, uncertainty, or video backing
- WHEN the report is generated
- THEN their displayed order follows the disclosed priority
- AND the report explains the ordering rule without fabricating confidence

### Requirement: Bound report detail and exclude restricted data

The system MUST apply finite hard caps to warning rows/detail summaries and key events. For every capped collection, it MUST state the omitted-item count when entries are excluded. The PDF MUST NOT embed video, raw canonical payloads, private notes, credentials, unapproved links, legacy records, or fabricated confidence values.

#### Scenario: Report collection exceeds a cap
- GIVEN warnings or key events exceed its report cap
- WHEN the report is generated
- THEN only the capped entries appear
- AND the section states how many items were omitted
