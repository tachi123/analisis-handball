# Delta for Competition Team Identity

## MODIFIED Requirements

### Requirement: Match identities conservatively
The system MUST resolve a source label only by an exact approved mapping to a target-stage CompetitionTeam, preserving `B`, `C`, `D`, and `Ce.M.E.F`. It MUST NOT reuse another stage's candidate or merge ambiguity. It MUST NOT use fuzzy matching, prefix stripping, inferred aliases, roster similarity, or opponent similarity.

(Previously: Resolution considered source name, variant, and stage without requiring an approved exact mapping.)

#### Scenario: Similar source names remain distinct
- GIVEN a stage contains "Banfield" and "Banfield B"
- WHEN a source match names "Banfield B"
- THEN only the variant-bearing team is eligible for that side of the match

#### Scenario: Reject an unapproved near match
- GIVEN no exact approved mapping for a source label
- WHEN identity resolution is requested
- THEN it fails without associating any CompetitionTeam
