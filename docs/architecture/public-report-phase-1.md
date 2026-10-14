# Public report Phase 1: match phases

Phase 1 turns the existing public event ledger into a match-phase report. It is generated during export and remains a static, privacy-safe artifact: opening the report never calls the private API.

## Quick path

1. Complete and promote the canonical analysis run.
2. Run the public export for that match.
3. Open the static report and select a 10-minute block, player, goalkeeper, or linked incident.

## What the export derives

| Section | Definition | Evidence rule |
|---|---|---|
| Mini-match | 0–10, 10–20, 20–30 in each period | Only confirmed events with a verified regulation clock. |
| Block winner | Team with more goals inside the block; equal goals is a draw | This is a score result, not a quality judgment. |
| Block efficiency | Goals / attempted shots, plus losses and recoveries | Uses observed canonical shots, turnovers, and recoveries. |
| Momentum run | Consecutive goals by one team in chronological scoring order | A run never assigns tactical cause. |
| Quick concession | Opponent goal immediately after an observed own shot terminal or turnover, within 10 seconds | Describes the sequence only; it is not labelled a retreat error. |
| Goalkeeper context | Opponent attempts, on-target attempts, goals, saves, and save rate | Saves are calculated only from assigned on-target shots. |

## Guardrails

- A report must never infer a tactical cause from timing alone.
- Unverified clocks do not enter 10-minute blocks or quick-concession calculations.
- “Retreat error”, “second wave”, and similar causes require a future explicit analyst tag.
- Public artifacts include names, jersey numbers, public observations, and validated YouTube IDs only; they exclude IDs, raw payloads, notes, and operational data.

## Export contract

The exporter writes `phase_analysis` into each public match JSON. The browser only renders that static JSON; it does not request backend metrics or consume an API token.

## Next phase

Phase 2 adds analyst-observed tactical tags for attack type and conceded-goal cause. That is the prerequisite for causal claims about retreat, defensive mismatch, or second-wave transitions.
