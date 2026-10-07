# SAPA Stats - Evidence Contracts

## Canonical analysis

Canonical analysis records observed events for one match. A canonical event has a stable event identity and a replacement may be submitted when the observation is corrected. Event reads expose the current, latest revision only; clients must treat that response as the current event and must not reconstruct a revision timeline or diff.

The canonical event command supports the following shared context when it is known:

| Field | Meaning |
|---|---|
| `period` | Match period for the observation. |
| `regulation_seconds` | Match-clock position when known. |
| `clock_unverified` | The clock mapping is unavailable or cannot be verified. |
| `team_id`, `player_id`, `related_player_id` | Match team and roster context when observed. |
| `evidence_state` | `confirmed`, `no_visible`, `ambiguous`, or `replay`. |
| `uncertainty` | Explicit reasons the observation is limited. |
| `evidence` | Fixture, official PDF, video, or unavailable-source references. |

Only `confirmed` eligible observations contribute to derived analytical totals. `no_visible` and `ambiguous` remain unknown; `replay` is excluded. An observation with an unverified clock remains an observation, not an estimated timestamp.

## Official snapshot

The official snapshot is immutable competition evidence derived from the confirmed PDF. It supplies totals by player and match, including the official score and available discipline totals. Canonical analysis never changes it.

Official PDFs do not provide reliable event timestamps or goalkeeper-substitution history. Those details are therefore `not_comparable` against the official source. A canonical timestamp or goalkeeper context can be useful analytical evidence, but it cannot be asserted as an official-PDF match.

## Discrepancy flow

`WarningsPanel` is the discrepancy flow. It compares eligible canonical totals with immutable official totals by match and player, shows a status, and lets the reader inspect linked canonical evidence when available.

| Status | Meaning |
|---|---|
| `exact` | Canonical and official totals agree. |
| `within_tolerance` | The comparison is within its stated tolerance. |
| `missing_in_canonical` | The official total has no matching eligible canonical total. |
| `missing_in_official` | The canonical total has no matching official total. |
| `not_comparable` | The official PDF does not contain comparable detail. |

WarningsPanel is read-only reconciliation, not a resolution workflow. It does not modify the official snapshot, infer unavailable timing or goalkeeper substitutions, or provide revision history/diffs.

## Current limits

- Canonical event responses are latest-revision-only.
- Confidence, visibility, corrected payload, `revision_of`, and chronological or auditable revision chains/diffs are not part of the client contract.
- The official snapshot is totals-only per player; it is not a source for event timing or goalkeeper-substitution comparison.
- Missing video, incomplete roster context, and an unverified clock must remain explicit limitations rather than inferred facts.
