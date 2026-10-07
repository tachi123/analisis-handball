# Goalkeeper Panel Specification

## Purpose

Present an auditable match goalkeeper view backed exclusively by the canonical player projection.

## Requirements

### Requirement: Select and disclose each goalkeeper's canonical view

The panel MUST let an analyst select each roster-eligible goalkeeper independently and MUST render only the selected server projection. It MUST display server-derived saves, goals conceded, defined observed-decision save rate, discipline, participation evidence, coverage, and unfiltered match-level canonical metrics and reconciliation context. It MUST label participation as observed evidence and MUST NOT display inferred minutes, starts, exhaustive appearances, or client-derived metrics.

#### Scenario: Select a goalkeeper

- GIVEN a match has multiple roster-eligible goalkeepers
- WHEN the analyst selects one goalkeeper
- THEN the panel shows that goalkeeper's server-derived projection and disclosures

#### Scenario: Observed participation only

- GIVEN no observed lineup-change evidence exists for the selected goalkeeper
- WHEN the panel is rendered
- THEN it shows no participation claim rather than inferred time or a start

### Requirement: Present evidence-led timeline, time coverage, and zones

The panel MUST present selected projection evidence event/revision IDs and video anchors in a timeline that can seek existing video evidence. It MUST visibly separate `clock_unverified`, `goalkeeper_unknown`, excluded, unknown, and missing-zone coverage from verified precise-time results. When shot-zone data exists, it MUST render only the server-provided IHF 1–9 heatmap buckets; it MUST NOT mix legacy data or assign missing zones.

#### Scenario: Seek an evidence item

- GIVEN a timeline item has a valid video anchor
- WHEN the analyst selects it
- THEN the existing video review behavior seeks that anchor

#### Scenario: Unverified-clock result

- GIVEN the selected projection includes an unverified-clock event
- WHEN a precise time range is active
- THEN the panel displays it in a separate disclosed bucket
