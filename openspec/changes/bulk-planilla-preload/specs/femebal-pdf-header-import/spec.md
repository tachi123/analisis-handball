# Delta for Femebal PDF Header Import

## MODIFIED Requirements

### Requirement: Extract and evidence labelled facts
The system MUST extract labelled tournament, venue, court, date, time, category, match number, teams, and scores from every PDF page. Fields MUST expose provenance, confidence, and warnings. It MUST preserve degraded text, normalize valid time to `HH:MM`, and MUST NOT guess. Sides MUST use only `local` and `visitante`; conflicts MUST warn and be unresolved. Read-only extraction MUST NOT write.

(Previously: extraction was specified for preview data without an explicit all-page requirement.)

#### Scenario: Extract Banfield B versus SAPA
- GIVEN the Banfield B versus SAPA fixture is previewed
- WHEN labelled regions are extracted across its pages
- THEN `Lanus Este`, `CI.DE.CO Gimnasio 1`, `2026-05-31`, `19:45`, category, match `10`, and `Metropolitano Apertura Zona A` are returned
- AND local `C.A. Banfield B` and visitor `S.A.P.A.` each have score `31` with provenance

#### Scenario: Tolerate layout and encoding
- GIVEN split labels or values, irregular whitespace, or split `Equipo local`
- WHEN normalized labels uniquely identify values
- THEN evidence and labelled values MUST be returned
- AND degraded category text MUST retain its raw token and an encoding warning

#### Scenario: Leave score unresolved
- GIVEN a label is absent or has zero or multiple plausible scores
- WHEN read-only extraction is produced
- THEN its score MUST be unresolved with a warning
- AND it MUST NOT emit `0-0` or use roster or period totals
- AND it MUST NOT write a database record or source file

#### Scenario: Ignore visual order
- GIVEN visitor text precedes local text
- WHEN both labelled regions are parsed
- THEN local MUST be home and visitor MUST be away

#### Scenario: Retain later-page evidence
- GIVEN a planilla has a later page containing labelled or roster evidence
- WHEN extraction processes all pages
- THEN that evidence retains its page provenance
