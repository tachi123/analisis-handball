# Public tournament forecast

The public tournament view gives a **statistical estimate** of each pending
match and each club's chance of becoming champion. It is not betting advice,
an official FEMEBAL prediction, or a guarantee of a result.

## Quick path

1. Load and reconcile the new official planillas.
2. Run `backend/scripts/export_public_competitions.py` to regenerate the catalog,
   the three tournament artifacts, the forecast, and the legacy fallback.
3. Copy the output into `reports/public` and validate the report build before
   publishing.

The export recalculates standings, match probabilities, podium probabilities,
round-by-round results, scorer tables, discipline, marks, and the annual blocks
from the data currently recorded in each stage.

## What the model uses

| Signal | Use |
|---|---|
| Confirmed score | Preferred historical score when an official snapshot exists. |
| Reported score | Used when a fixture has a recorded score but its official planilla is still pending; the public coverage disclosure remains visible. |
| Goals scored and conceded | Fits each team's attacking and defensive strengths. |
| Recency | More recent rounds have more influence; the weight halves every eight rounds. |
| Home team | Estimates a regularized home-advantage term from the tournament's results. |
| Remaining fixture | Supplies the opponent, round, date, and home/away status for every simulation. Suspended and cancelled fixtures are not projected. |
| Competition rules | Resolves points from the versioned configuration (3/2/1, suspended 3/0). Ties use the handball Olympic tiebreak: the matches between the level clubs first, then overall goal difference and goals for. |

## Calculation

The exporter fits a regularized independent-Poisson attack/defense model to the
stage scorelines. Regularization and zero-centering keep short samples from
creating extreme team ratings.

For every pending fixture, it derives the distribution of plausible scorelines
and rolls it up into home-win, draw, and away-win probabilities. It then runs
20,000 deterministic Monte Carlo season finishes with a fixed seed. Each finish
rebuilds the whole table, applies the versioned point rule, ranks **every**
club with the Olympic tiebreak, and records positions 1, 2, and 3.

The Olympic tiebreak ranks clubs level on points by the matches played between
them (points, goal difference, goals for). If that separates only some of them,
the same procedure is repeated among the clubs still level. Overall goal
difference and goals for only apply when it cannot separate them. This is the
competition rule the standings table uses; it is not a forecast-specific
heuristic.

If a residual exact tie survives all criteria, the tied clubs share the positions
they jointly occupy. Podium probability is the sum of the first-, second-, and
third-place shares from the same counts, never a sum of rounded percentages.

The fixed seed makes an unchanged data set reproduce the same public artifact.
A changed score, fixture, or result status changes the next export's estimate.

## What the model deliberately ignores

The completed Apertura tournaments were tested as a prior for Permanencia.
Adding them did not improve predictive log-loss on held-out rounds (difference
≈ −0.001 ± 0.007). Roster turnover and the change of competition dilute that
signal, so Apertura stays a historical context surface and an annual-profile
block, not a forecast input.

The optimizer was also checked against a converged Newton implementation; the
current fitted goal means are already at the optimum. The improvement work is
in ranking every club, publishing podium probabilities, and reusing the real
points rule, not in adding new signals.

## Reading the UI

The public hub now has three surfaces:

- **Torneos 2026** (`tournaments.json`): a catalog with coverage, SAPA's
  position, the next match, and a link to each tournament detail.
- **Detalle de torneo** (`tournament_<key>.json`): SAPA spotlight, full
  standings with the points rule, round-by-round results with a coverage badge,
  scorers, discipline, and the competition marks.
- **Pronóstico de cierre** (`forecast_permanencia-2026.json`): SAPA's finish
  probabilities, the podium table, each contender's campaign as a G/E/P strip,
  expandable match lists, and the pending fixtures.
- **Temporada del rival** (`SeasonProfile.tsx`): all matches of the year from
  Apertura Zona B and Permanencia, annual totals, competition blocks, scorer
  splits, squad continuity, and the main marks.

The podium table shows first/second/third and podium probability, ordered by
podium and then by championship. Podium is folded from simulation counts, not
from the displayed percentages. Each campaign pill is a round: green G, yellow
E, red P, with the opponent and score in the title and the full list under
«Campañas». Color is a reinforcement; the letter and the visible text always
carry the meaning.

`<0,1%` means the simulation produced a positive but very small estimate. A
displayed zero is not a claim that a sporting outcome is impossible; it means no
such finish occurred in the finite simulation run.

## Guardrails

- Do not call the estimate a quota, betting line, certainty, or tactical
  diagnosis.
- Do not add injuries, private notes, player tracking, or any unverified
  narrative as model inputs.
- The fixture is public-safe, but database IDs, raw imports, credentials,
  private URLs, and operational paths must never enter `tournament.json`.
- The browser only reads the static artifacts; it never calls the backend API.
- With only a partial tournament sample, estimates must retain their uncertainty
  disclosure. The model was backtested on the completed Apertura stages: it
  beats the home/draw/away frequency baseline, and the Apertura data was tested
  as a prior without a measurable gain.

## Public artifact contract

`reports/public/forecast_permanencia-2026.json` uses `forecast-v1` and is
allowlisted by `reports/src/publicCompetitions.ts`. It contains only:

- competition, season, update date, coverage, simulation count, and
  plain-language methodology;
- the versioned points rule (`win`, `draw`, `loss`, `suspended_win`,
  `suspended_loss`);
- club name, championship probability, `finish_probabilities` (`first`,
  `second`, `third`), `podium_probability`, and `expected_position`;
- pending round/date, public team names, and win/draw/loss probabilities;
- each club's completed public campaign: round/date, opponent, home/away,
  score, and result;
- the rival profile: the next SAPA rival and the public competitions that can be
  combined into the annual profile.

`reports/public/tournament_<key>.json` uses `tournament-v3` and contains
standings, scorers, club discipline, rounds with a per-match coverage badge,
points rule, coverage, and the insights block (marks, streaks, splits, tiers,
biggest results). `reports/public/tournaments.json` uses `tournaments-v1` and
carries catalog metadata only. `reports/public/tournament.json` remains the
`tournament-v2` legacy fallback.

No artifact contains database IDs, raw payloads, notes, private URLs, or
operational paths.

## Implementation map

| Need | File |
|---|---|
| Goal model and season simulation | `backend/app/services/tournament_forecast_service.py` |
| Olympic ranking shared with standings | `backend/app/services/competition_ranking.py` |
| Descriptive marks and annual blocks | `backend/app/services/tournament_insights_service.py` |
| Catalog and artifact export | `backend/scripts/export_public_competitions.py` |
| Legacy single-file export | `backend/scripts/export_public_tournament.py` |
| Public allowlist decoders | `reports/src/publicCompetitions.ts` |
| Catalog, detail, forecast, season views | `reports/src/Competitions.tsx`, `CompetitionDetail.tsx`, `Forecast.tsx`, `SeasonProfile.tsx` |
| Forecast tests | `backend/tests/test_tournament_forecast_service.py`, `backend/tests/test_competition_ranking.py` |
| Public contract tests | `reports/src/publicCompetitions.test.ts`, `realArtifacts.test.ts`, `renderSmoke.test.tsx` |
