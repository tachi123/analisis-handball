# SAPA Stats - Canonical Handball Taxonomy

## Scope

The canonical taxonomy records manual, observable facts for a match. It does not infer lineup state, active goalkeeper, suspension duration, injury recovery, tactical opportunities, or unavailable video context.

Every canonical event has a `kind`, `period`, `evidence_state`, and optional observed context such as team, player, clock position, uncertainty, and source evidence. The supported kinds are:

| Kind | Observable fact |
|---|---|
| `shot` | A shot with terminal outcome `goal`, `save`, `miss`, `woodwork`, or `blocked`. |
| `turnover` | A turnover observed during an open possession. |
| `recovery` | A visible recovery of possession. |
| `lineup_change` | An explicit player `on`, `off`, or `substitution` change. |
| `goalkeeper_change` | An explicitly observed active goalkeeper, or an explicit unknown goalkeeper state. |
| `foul_sanction` | `foul`, `seven_meter`, `yellow_card`, `red_card`, `blue_card`, or `two_minute_exclusion`. |
| `other` | Another observed fact, including `kickoff` where applicable. |

## Shot zones

`shot_zone` is optional and is valid only when `kind` is `shot`. Its only valid values are the numeric IHF zones `1` through `9`.

Do not use legacy categorical zones such as `Extremo`, `9m`, `6m`, `Contra`, or `7 Metros`. If the zone was not observed, omit `shot_zone`; do not substitute a category or infer one from the attack phase.

## Evidence states and unknown context

| State | Treatment |
|---|---|
| `confirmed` | Eligible for derived analysis when the event is otherwise eligible. |
| `no_visible` | Unknown because the source or angle does not show the fact. |
| `ambiguous` | Unknown because the fact cannot be determined. |
| `replay` | Excluded from derived analysis. |

`clock_unverified` states that a clock position cannot be verified; it does not authorize an estimated time. A roster-listed player may be recorded when the observation supports responsibility even if lineup changes or the active goalkeeper are unknown.

Goalkeeper responsibility for a saved shot is derived only from an explicitly observed active goalkeeper. The system does not automatically assign a goalkeeper from possession, squad role, or team side. When the goalkeeper is unknown, that uncertainty remains in the result.

## Unsupported claims

The current taxonomy does not provide automatic goalkeeper assignment, suspension timers or carryover, automatic disciplinary escalation, injury tracking, or a three-attacks return rule. Those may be handball rules, but they are not canonical event functionality.

Canonical responses expose only the latest revision of an event. They do not provide persisted confidence, visibility, corrected payload, `revision_of`, or a chronological revision history/diff contract.
