# Public tournament forecast

The public tournament view gives a **statistical estimate** of each pending
match and each club's chance of becoming champion. It is not betting advice,
an official FEMEBAL prediction, or a guarantee of a result.

## Quick path

1. Load and reconcile the new official planillas.
2. Export `tournament.json` again.
3. Validate the report build before publishing.

The export recalculates standings, individual match probabilities, and
championship probabilities from the data currently recorded in the stage.

## What the model uses

| Signal | Use |
|---|---|
| Confirmed score | Preferred historical score when an official snapshot exists. |
| Reported score | Used when a fixture has a recorded score but its official planilla is still pending; the public coverage disclosure remains visible. |
| Goals scored and conceded | Fits each team's attacking and defensive strengths. |
| Recency | More recent rounds have more influence; the weight halves every eight rounds. |
| Home team | Estimates a regularized home-advantage term from the tournament's results. |
| Remaining fixture | Supplies the opponent, round, date, and home/away status for every simulation. |
| Competition rules | Resolves points as 3/2/1 and ties as points, goal difference, then goals for. |

## Calculation

The exporter fits a regularized independent-Poisson attack/defense model to the
stage scorelines. Regularization and zero-centering keep short samples from
creating extreme team ratings.

For every pending fixture, it derives the distribution of plausible scorelines
and rolls it up into home-win, draw, and away-win probabilities. It then runs
20,000 deterministic Monte Carlo season finishes with a fixed seed. Each finish
applies the real point rule and tiebreak order before assigning a champion.

The fixed seed makes an unchanged data set reproduce the same public artifact.
A changed score, fixture, or result status changes the next export's estimate.

## Reading the UI

The tournament dashboard shows:

- SAPA's current table position and championship estimate first.
- A comparison matrix for clubs with a simulated championship chance: champion
  chance, then one win/draw/loss cell per remaining round.
- SAPA's next matches separately for quick reading.
- A club filter for top scorers.

`<0,1%` means the simulation produced a positive but very small estimate. A
displayed zero is not a claim that a sporting outcome is impossible; it means no
championship finish for that club occurred in the finite simulation run.

## Guardrails

- Do not call the estimate a quota, betting line, certainty, or tactical
  diagnosis.
- Do not add injuries, private notes, player tracking, or any unverified
  narrative as model inputs.
- The fixture is public-safe, but database IDs, raw imports, credentials,
  private URLs, and operational paths must never enter `tournament.json`.
- The browser only reads the static artifact; it never calls the backend API.
- With only a partial tournament sample, estimates must retain their uncertainty
  disclosure. Backtesting against completed historical stages is a future
  calibration improvement, not a property to claim today.

## Public artifact contract

`reports/public/tournament.json` uses `tournament-v2`. Its `forecast` field is
allowlisted by `reports/src/tournamentProjection.ts` and contains only:

- simulation count and plain-language methodology;
- club name plus championship probability;
- pending round/date, public team names, and win/draw/loss probabilities.

## Implementation map

| Need | File |
|---|---|
| Goal model and season simulation | `backend/app/services/tournament_forecast_service.py` |
| Public export | `backend/scripts/export_public_tournament.py` |
| Public allowlist decoder | `reports/src/tournamentProjection.ts` |
| Tournament dashboard | `reports/src/Tournament.tsx` |
| Forecast tests | `backend/tests/test_tournament_forecast_service.py` |
