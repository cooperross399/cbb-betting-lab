# NCAA Division I men's basketball — ratings fit

Generated 2026-09-03T23:46:19+00:00.

**Nothing in this report is a return.** A fit is not a price, forecast error is not profit, and calibration can rule a model out and never in. Where an interval includes zero this report says **no demonstrated edge** in the lab's own words, which for a fitted quantity reads as *no demonstrated effect*. The price backtest is what decides whether any of this is worth money.

**Walk-forward, checked on the stamp.** Every rating that priced a game was fitted on that season's games strictly earlier than the morning of the game, every priced row carries the last game day the fit was allowed to see, and `price_backtest.assert_walk_forward` reads the stamp rather than trusting the code path — because the code path is exactly what was wrong in the lab this guard is ported from.

**Sample floor: 200 observations.** Below it a cell prints an em dash and the words *not enough evidence*, never a figure.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's.

## The fit population, reconciled

94,194 team-game rows were read from `/Users/cooperross/Projects/cbb-betting-lab/data/processed`, and the seasons this run fits are [2026] with a prior window of 3 earlier seasons.

> 42,658 fittable team-games of 50,090 supplied (reconciles): not countable 4,194, venue unknown 0, overtime 2,670, period count missing 568, possessions below 40 0.

Every exclusion is a count and not a decision. Overtime games are out because `distributions.build` appends overtime itself and fitting on final scores would count it twice; a missing period count is not evidence of a regulation finish and is excluded separately. The identity reconciles: 42,658 fittable + 4,194 not countable + 0 venue unknown + 2,670 overtime + 568 period count missing + 0 below 40 possessions = 50,090 supplied.

10 quasi-neutral team-games have no identified local side and were fitted as neutral, which the measurement says is close to right — and it is counted here so that *close to right* is a number rather than a claim.

## Season 2026

146 fits, one per slate day from 2025-11-03 to 2026-04-06. 4,719 of 5,415 games were priced; the rest were refused and the reasons are below. A refusal is an honest output, and a game the model declines to price is a different thing from a game it prices at no value.

> Season 2026 as of 2026-04-07 (priced through 2026-04-06): 5,415 games, 365 teams, league 108.38 per 100 at 68.39 possessions, residual sd 13.16. Median prior weight: offence 18%, defence 38%, tempo 8%. 5,415 games over 365 teams: 1 component(s), largest 365, algebraic connectivity 4.4135.

> Prior for season 2026 from seasons [2023, 2024, 2025]: 364 teams, league 106.25 per 100 at 68.03 possessions. offence: carryover 0.672, with roster terms, prior sd 2.939 (out-of-sample), observation sd 13.112 -> lambda 19.9 games, 723 team-season pairs. defence: carryover 0.650, with roster terms, prior sd 2.543 (out-of-sample), observation sd 13.112 -> lambda 26.6 games, 723 team-season pairs. tempo: carryover 0.542, carryover only, prior sd 1.620 (out-of-sample), observation sd 3.751 -> lambda 5.4 games, 723 team-season pairs.

> Home advantage per 100 possessions of margin: league +7.87 (high_major=+12.36, low_major=+3.90, mid_major=+7.34, unplaced=+7.87). Quasi-neutral +0.56. 409 venues, between-venue sd 1.32 per side, shrinkage 39.9 home games. Fitted on 31,828 team-games from seasons [2023, 2024, 2025].

Venue-level departures: no `venue_home_effect` verdict is recorded, so the tier effect prices and the per-venue departures are reported, not applied.

### The prior's weight over time — season 2026

The share of a rating that is still the preseason prior, as the median across teams, per component. It is read off the posterior rather than assumed: the ridge's penalty centre **is** the prior, so `prior_weight` is the row sum of `A⁻¹Λ` — the fraction of the rating that would move if the whole prior moved by one. Cooper's rule is that this number is printed in every price so that *a November number can never be printed as if it were a February one*, and the rule is only worth anything if the number behaves.

| Day | Games fitted on | Teams | Offence | Defence | Tempo | Residual sd |
|:---|---:|---:|---:|---:|---:|---:|
| 2025-11-03 | 0 | 364 | 100.0% | 100.0% | 100.0% | 0.00 |
| 2025-11-05 | 121 | 365 | 90.8% | 93.1% | 72.8% | 14.09 |
| 2025-11-10 | 295 | 365 | 82.9% | 87.2% | 57.6% | 13.99 |
| 2025-11-15 | 485 | 365 | 76.4% | 82.4% | 48.7% | 13.33 |
| 2025-11-20 | 696 | 365 | 70.4% | 77.9% | 40.7% | 13.20 |
| 2025-11-25 | 919 | 365 | 65.2% | 74.0% | 34.9% | 13.19 |
| 2025-12-01 | 1,186 | 365 | 56.7% | 67.6% | 28.5% | 13.34 |
| 2025-12-05 | 1,316 | 365 | 56.3% | 67.3% | 27.1% | 13.27 |
| 2025-12-10 | 1,499 | 365 | 52.6% | 64.5% | 24.4% | 13.19 |
| 2025-12-15 | 1,648 | 365 | 49.5% | 62.1% | 22.7% | 13.20 |
| 2025-12-20 | 1,785 | 365 | 46.6% | 60.0% | 21.1% | 13.15 |
| 2026-01-01 | 2,099 | 365 | 41.5% | 56.2% | 18.6% | 13.22 |
| 2026-01-05 | 2,315 | 365 | 39.2% | 54.5% | 17.3% | 13.24 |
| 2026-01-10 | 2,477 | 365 | 37.2% | 53.0% | 16.4% | 13.19 |
| 2026-01-15 | 2,740 | 365 | 35.0% | 51.3% | 15.1% | 13.20 |
| 2026-01-20 | 2,970 | 365 | 32.9% | 49.7% | 14.0% | 13.28 |
| 2026-01-25 | 3,248 | 365 | 30.0% | 47.6% | 13.0% | 13.20 |
| 2026-02-01 | 3,542 | 365 | 27.8% | 45.9% | 12.1% | 13.22 |
| 2026-02-05 | 3,669 | 365 | 27.1% | 45.4% | 11.7% | 13.22 |
| 2026-02-10 | 3,907 | 365 | 25.0% | 43.8% | 11.0% | 13.20 |
| 2026-02-15 | 4,172 | 365 | 23.5% | 42.8% | 10.4% | 13.19 |
| 2026-02-20 | 4,356 | 365 | 22.4% | 41.9% | 10.0% | 13.22 |
| 2026-02-25 | 4,569 | 365 | 21.4% | 41.1% | 9.6% | 13.20 |
| 2026-03-01 | 4,833 | 365 | 19.7% | 39.9% | 9.1% | 13.18 |
| 2026-03-05 | 4,960 | 365 | 19.3% | 39.5% | 8.9% | 13.19 |
| 2026-03-10 | 5,164 | 365 | 18.1% | 38.7% | 8.6% | 13.20 |
| 2026-03-15 | 5,313 | 365 | 17.6% | 38.3% | 8.4% | 13.17 |
| 2026-03-20 | 5,351 | 365 | 17.6% | 38.2% | 8.3% | 13.17 |
| 2026-03-25 | 5,392 | 365 | 17.6% | 38.3% | 8.3% | 13.16 |
| 2026-04-01 | 5,406 | 365 | 17.6% | 38.3% | 8.3% | 13.16 |
| 2026-04-06 | 5,414 | 365 | 17.6% | 38.3% | 8.3% | 13.16 |

Monotone decay over November through February **holds**: 23 printed days out of 115 fit days, and no day-to-day rise as large as 0.5% — which is the resolution this quantity is rendered at everywhere it appears, so a smaller one cannot reach a reader.

| Component | First | Last | Printed series falls | Median rises (day to day) | Largest | Rises a reader could see | Team-days that rose | Largest single team |
|:---|---:|---:|:---|---:|---:|---:|:---|---:|
| offence | 100.0% (2025-11-03) | 20.6% (2026-02-28) | yes | 4 of 114 | 0.000237 | 0 | 21,566 of 41,610 (52%) | 0.0090 |
| defence | 100.0% (2025-11-03) | 40.6% (2026-02-28) | yes | 5 of 114 | 0.000269 | 0 | 21,956 of 41,610 (53%) | 0.0094 |
| tempo | 100.0% (2025-11-03) | 9.4% (2026-02-28) | yes | 3 of 114 | 0.000372 | 0 | 21,183 of 41,610 (51%) | 0.0546 |

The last two columns are reported and decide nothing, and they are **team-days rather than teams** — one team on one day is one step. `prior_weight` is the row sum of `A⁻¹Λ` and `A⁻¹` has negative off-diagonal entries, so a team's own prior share depends on games played by the teams it is connected to and is **not** a monotone function of its own game count. Roughly half of all team-days move the wrong way by a fraction of a point, which is what a coupled ridge does and not a defect; it is counted here so that it is a number in the record rather than a paragraph. 1 team(s) joined the fit during the window, each entering at a weight near 1.0, which is the other thing that moves an order statistic.

### The seam prices a different fit — season 2026

`ratings.matchups_for` hands `fit` every season of history it was given, and `run_price_backtest.py` gives it all of them, so the design matrix on the opening Monday already holds several seasons of each team's games. `ratings.fit`'s own contract is the other one — *history filtered to the season being priced*, because *a team is not the team it was last March* — and this report fits that way. Both are refitted on the days below **from the same prior and the same tier table**, so the only thing that differs between the two columns is where the history was cut. The seam's other departure — a tier table built over the season it is pricing — is a separate finding and is counted separately below.

| Day | Team-games (season) | Prior weight (season) | Team-games (seam) | Prior weight (seam) |
|:---|---:|---:|---:|---:|
| 2025-11-03 | 0 | 100.0% | 31,828 | 0.0% |
| 2025-11-05 | 242 | 90.8% | 32,070 | 0.0% |
| 2025-11-10 | 590 | 82.9% | 32,418 | 0.0% |
| 2025-11-15 | 970 | 76.4% | 32,798 | 0.0% |
| 2025-11-20 | 1,392 | 70.4% | 33,220 | 0.0% |
| 2025-11-25 | 1,838 | 65.2% | 33,666 | 0.0% |
| 2025-12-01 | 2,372 | 56.7% | 34,200 | 0.0% |
| 2025-12-05 | 2,632 | 56.3% | 34,460 | 0.0% |
| 2025-12-10 | 2,998 | 52.6% | 34,826 | 0.0% |
| 2025-12-15 | 3,296 | 49.5% | 35,124 | 0.0% |
| 2025-12-20 | 3,570 | 46.6% | 35,398 | 0.0% |
| 2026-01-01 | 4,198 | 41.5% | 36,026 | 0.0% |
| 2026-01-05 | 4,630 | 39.2% | 36,458 | 0.0% |
| 2026-01-10 | 4,954 | 37.2% | 36,782 | 0.0% |
| 2026-01-15 | 5,480 | 35.0% | 37,308 | 0.0% |
| 2026-01-20 | 5,940 | 32.9% | 37,768 | 0.0% |
| 2026-01-25 | 6,496 | 30.0% | 38,324 | 0.0% |
| 2026-02-01 | 7,084 | 27.8% | 38,912 | 0.0% |
| 2026-02-05 | 7,338 | 27.1% | 39,166 | 0.0% |
| 2026-02-10 | 7,814 | 25.0% | 39,642 | 0.0% |
| 2026-02-15 | 8,344 | 23.5% | 40,172 | 0.0% |
| 2026-02-20 | 8,712 | 22.4% | 40,540 | 0.0% |
| 2026-02-25 | 9,138 | 21.4% | 40,966 | 0.0% |
| 2026-03-01 | 9,666 | 19.7% | 41,494 | 0.0% |
| 2026-03-05 | 9,920 | 19.3% | 41,748 | 0.0% |
| 2026-03-10 | 10,328 | 18.1% | 42,156 | 0.0% |
| 2026-03-15 | 10,626 | 17.6% | 42,454 | 0.0% |
| 2026-03-20 | 10,702 | 17.6% | 42,530 | 0.0% |
| 2026-03-25 | 10,784 | 17.6% | 42,612 | 0.0% |
| 2026-04-01 | 10,812 | 17.6% | 42,640 | 0.0% |
| 2026-04-06 | 10,828 | 17.6% | 42,656 | 0.0% |

Offence's median is printed for compactness and every component is in the record; offence and defence differ, and both are there. **The right-hand column is the number a card produced through the seam would print**, and it does not move all season.

**Tier table:** 34 of 367 teams (9.3%) change tier when the priced season is allowed into `conferences.tier_table`. This report builds it from seasons strictly earlier, which is that module's own rule; the seam builds it over every season it holds a schedule for. A tier is not a label — it chooses which home-court effect is applied — so a team on the wrong side of a cut point is a multi-point error on every market on its home games.

- strictly before: Tiers from seasons [2023, 2024, 2025]: high_major=61, low_major=174, mid_major=131 (33 conferences).
- including the priced season: Tiers from seasons [2023, 2024, 2025, 2026]: high_major=61, low_major=156, mid_major=150 (33 conferences).

### Connectivity, and the refusal — season 2026

Effective resistance on the games-played graph, re-derived by `ratings.connectivity_timeline` rather than quoted. It is not a metaphor for identifiability, it **is** it: under a paired-comparison model with no prior, the variance of an estimated rating *difference* is proportional to the effective resistance between the two teams. The bar is 1.00 — exactly one head-to-head meeting, and exactly two independent common opponents.

| Day | Games | Teams | Components | Largest | Median resistance | Share priceable |
|:---|---:|---:|---:|---:|---:|---:|
| 2025-11-03 | 0 | 0 | 0 | 0 | — | 0.0% |
| 2025-11-05 | 121 | 242 | 121 | 2 | 1.000 | 0.4% |
| 2025-11-10 | 295 | 351 | 59 | 51 | 6.000 | 0.2% |
| 2025-11-15 | 485 | 362 | 1 | 362 | 1.967 | 1.0% |
| 2025-11-20 | 696 | 364 | 1 | 364 | 0.828 | 78.3% |
| 2025-11-25 | 919 | 365 | 1 | 365 | 0.542 | 99.3% |
| 2025-12-01 | 1,186 | 365 | 1 | 365 | 0.383 | 100.0% |
| 2025-12-05 | 1,316 | 365 | 1 | 365 | 0.335 | 100.0% |
| 2025-12-10 | 1,499 | 365 | 1 | 365 | 0.287 | 100.0% |
| 2025-12-15 | 1,648 | 365 | 1 | 365 | 0.257 | 100.0% |
| 2025-12-20 | 1,785 | 365 | 1 | 365 | 0.231 | 100.0% |
| 2026-01-01 | 2,099 | 365 | 1 | 365 | 0.194 | 100.0% |
| 2026-01-05 | 2,315 | 365 | 1 | 365 | 0.174 | 100.0% |
| 2026-01-10 | 2,477 | 365 | 1 | 365 | 0.162 | 100.0% |
| 2026-01-15 | 2,740 | 365 | 1 | 365 | 0.145 | 100.0% |
| 2026-01-20 | 2,970 | 365 | 1 | 365 | 0.133 | 100.0% |
| 2026-01-25 | 3,248 | 365 | 1 | 365 | 0.122 | 100.0% |
| 2026-02-01 | 3,542 | 365 | 1 | 365 | 0.112 | 100.0% |
| 2026-02-05 | 3,669 | 365 | 1 | 365 | 0.108 | 100.0% |
| 2026-02-10 | 3,907 | 365 | 1 | 365 | 0.102 | 100.0% |
| 2026-02-15 | 4,172 | 365 | 1 | 365 | 0.096 | 100.0% |
| 2026-02-20 | 4,356 | 365 | 1 | 365 | 0.092 | 100.0% |
| 2026-02-25 | 4,569 | 365 | 1 | 365 | 0.089 | 100.0% |
| 2026-03-01 | 4,833 | 365 | 1 | 365 | 0.084 | 100.0% |
| 2026-03-05 | 4,960 | 365 | 1 | 365 | 0.083 | 100.0% |
| 2026-03-10 | 5,164 | 365 | 1 | 365 | 0.080 | 100.0% |
| 2026-03-15 | 5,313 | 365 | 1 | 365 | 0.078 | 100.0% |
| 2026-03-20 | 5,351 | 365 | 1 | 365 | 0.077 | 100.0% |
| 2026-03-25 | 5,392 | 365 | 1 | 365 | 0.077 | 100.0% |
| 2026-04-01 | 5,406 | 365 | 1 | 365 | 0.077 | 100.0% |
| 2026-04-06 | 5,414 | 365 | 1 | 365 | 0.077 | 100.0% |

A component count stops refusing days before the evidence arrives — the graph becomes one component while the typical pair is still joined by about half a common opponent's worth of results — which is the whole argument for resistance over components, and it is visible in the two columns above rather than asserted.

Why a game was not priced, commonest first. Grouped by the reason and not by its wording: every refusal carries that morning's component count and that pair's resistance, so counting raw strings turns one refusal into a hundred rows.

- **306 x** less connecting evidence than one head-to-head meeting (effective resistance at or above the bar)
  - as it reaches a reader: *the effective resistance between them is 2.00 against a bar of 1.00 — less connecting evidence than a single head-to-head meeting, or than two common opponents*
- **224 x** a team has played no countable game this season, so its rating is the preseason prior and nothing else
  - as it reaches a reader: *team 248 has played no countable game this season, so its rating is the preseason prior and nothing else*
- **165 x** the two teams are in different components of the games-played graph
  - as it reaches a reader: *the two teams are in different components of the games-played graph (121 components over 242 teams, 121 games) — no chain of results connects them and any difference between their ratings is the prior's opinion*
- **1 x** a quasi-neutral game whose local participant could not be identified
  - as it reaches a reader: *this game is flagged neutral in a participant's own city and the lab cannot tell whose. The designation is the wrong team 32.5% of the time, so it is refused rather than guessed*

### Per tier — season 2026

The fitted columns describe the model at the end of the season; the measured columns are walk-forward, every game scored by the fit that existed on its own morning. A game belongs to a tier only when **both** teams are in it — a high-major hosting a low-major is `mixed`, because folding it into the home team's tier is how a buy-game schedule ends up describing a conference. Intervals are clustered by game and by day and the wider is reported: a hundred-game Tuesday is priced by one fit, so its errors are not a hundred independent observations.

| Tier | Teams | Games priced | Priced share | Prior weight (off/def/tempo) | Margin bias | 95% interval | Family-corrected | Reading | Margin MAE | Total bias | 95% interval | Family-corrected |
|:---|---:|---:|---:|:---|---:|:---|:---|:---|---:|---:|:---|:---|
| high_major | 61 | 687 | 96.5% | 16% / 37% / 8% | +3.84 | +2.70 to +4.98 | +2.01 to +5.67 | excludes zero after the family correction | 10.89 | +2.76 | +1.50 to +4.02 | +0.74 to +4.78 |
| mid_major | 131 | 1,387 | 94.7% | 17% / 38% / 8% | +1.83 | +1.07 to +2.59 | +0.61 to +3.04 | excludes zero after the family correction | 9.40 | +1.87 | +0.96 to +2.77 | +0.41 to +3.32 |
| low_major | 172 | 1,841 | 94.6% | 18% / 39% / 9% | -0.17 | -0.75 to +0.41 | -1.11 to +0.76 | **no demonstrated edge** | 9.24 | +2.86 | +2.11 to +3.61 | +1.66 to +4.06 |
| mixed | — | 804 | 62.2% | — / — / — | -3.39 | -4.57 to -2.20 | -5.28 to -1.49 | excludes zero after the family correction | 11.31 | +1.65 | +0.46 to +2.84 | -0.26 to +3.56 |
| POOLED | 365 | 4,719 | 87.1% | 18% / 38% / 8% | +0.45 | -0.13 to +1.03 | -0.47 to +1.38 | **no demonstrated edge** | 9.88 | +2.35 | +1.86 to +2.84 | +1.56 to +3.13 |

> Pooled across every tier. **This is never the headline.** High-major, mid-major and low-major are three different distributions and this lab exists because the third is plausibly priced with less attention; a pooled row is printed only alongside its tier rows, and only so the tier rows can be read against something.

Bias is **predicted minus actual**, in points of margin from the home side, so a positive figure is a model that expects the home team to win by more than it did.

### The venue audit — season 2026

The tier home-court effect the model applies, beside an estimate of the same quantity taken by subtraction. For every pair of teams that met at **both** home venues in a season, the mean of the two home margins is the home advantage with every team effect cancelling exactly — no shrinkage, no design matrix, no assumption that the opponent's rating was well identified. `ratings._venue_effects` fits its tier effects on the residuals of a season fit whose second stage carries no team effects at all, so the two are independent instruments for one number.

| Tier | Fitted (per 100) | Measured (per 100) | 95% interval | Family-corrected | Pairs | Fitted inside 95% | Fitted inside corrected | Gap |
|:---|---:|---:|:---|:---|---:|:---|:---|---:|
| high_major | +12.36 | +5.58 | +4.52 to +6.63 | +3.89 to +7.27 | 475 | **no** | **no** | +6.78 |
| mid_major | +7.34 | +4.70 | +4.03 to +5.36 | +3.63 to +5.77 | 1,134 | **no** | **no** | +2.64 |
| low_major | +3.90 | +3.69 | +3.15 to +4.23 | +2.82 to +4.56 | 1,728 | yes | yes | +0.22 |
| unplaced | +7.87 | — | — | — | 0 | — | — | — |

Two `inside` columns, because the corrected interval is the wider one and a fitted number can fall outside the raw interval and inside the corrected one. **The corrected column is the one that decides**, and the list below is drawn from it: reading a disagreement off the narrower interval is exactly what a family-wise correction exists to stop.

> Pooled across every tier. **This is never the headline.** High-major, mid-major and low-major are three different distributions and this lab exists because the third is plausibly priced with less attention; a pooled row is printed only alongside its tier rows, and only so the tier rows can be read against something. Pooled over every reciprocal pair: +4.40 per 100 possessions, +4.01 to +4.78, over 3,453 pairs.

**What this estimator's population is, stated rather than glossed.** Reciprocal home-and-home pairs are overwhelmingly conference games. The measurement says nothing about a November non-conference game, and if home advantage genuinely differs between the two then the fitted number and this one are measuring different things rather than disagreeing about one. That possibility is why this section reports a comparison and never applies a correction.

**2 tier(s) have a fitted home effect outside the family-corrected measured interval.** The effect is applied to every market on every game of that tier, which is `CLAUDE.md`'s *multi-point error applied to every market on it* — the same sentence the quasi-neutral finding is filed under, and the same size of number:

- **high_major**: fitted +12.36 per 100 (+8.5 points at this season's league tempo) against a measured +5.58 over 475 reciprocal pairs — a gap of +6.78 per 100.
- **mid_major**: fitted +7.34 per 100 (+5.0 points at this season's league tempo) against a measured +4.70 over 1,134 reciprocal pairs — a gap of +2.64 per 100.

**A second instrument says the same thing**, and it is the walk-forward table above rather than another slice of the same arithmetic. The margin bias per tier is measured on games the fit had not seen, one game at a time, all season; the venue estimate is measured on completed seasons by subtraction. They share no design matrix, no shrinkage and no season, so where the tier with the largest fitted-versus-measured gap is also the tier the model most over-predicts at home, that is two measurements agreeing rather than one measurement twice.

One mechanism would produce exactly this, and it is offered as a **lead and not a finding**: `_venue_effects` regresses the residuals of a shrunk season fit on home indicators with no team effects in the second stage, so a home win over an opponent whose rating was shrunk toward the league mean leaves a positive residual — and only the home side of a schedule that hosts weak opponents ever collects it. `docs/what_we_can_and_cannot_claim.md` is explicit that *a finding that is really a mechanism is the most persuasive kind and the most dangerous*, so the two measurements above are the evidence and this paragraph is not.

## Roster turnover, measured here

The empirical argument for the whole November regime: if a large share of a team's minutes are new, last season's rating is a prior and not a fit. Measured on this lab's own tables — no figure here is quoted from a sibling lab, because turnover in hockey and turnover in football are facts about hockey and football.

Two populations, because the difference between them is large and choosing one silently would be a choice nobody could see. **D-I only** covers the 368 team ids the schedule feed gives a conference to across seasons [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026] — the board this lab prices. **Unrestricted** is every team in the player table, several hundred of which are non-D-I programmes with sparse and unevenly recorded rows, and it is the population `models/ratings.py`'s own docstring quotes. The two answer different questions and the restricted one is the answer to the question this lab asks.

| Season | Teams (D-I) | Returning minutes (D-I) | Incoming transfers (D-I) | Teams (all) | Returning (all) | Incoming (all) |
|:---|---:|---:|---:|---:|---:|---:|
| 2020 | 357 | 52.9% | 6.0% | 652 | 40.7% | 4.4% |
| 2021 | 354 | 51.9% | 10.6% | 663 | 31.9% | 9.2% |
| 2022 | 349 | 57.9% | 21.5% | 493 | 48.7% | 18.2% |
| 2023 | 359 | 47.3% | 21.3% | 679 | 38.1% | 14.5% |
| 2024 | 363 | 44.6% | 23.2% | 706 | 35.6% | 15.7% |
| 2025 | 363 | 38.1% | 30.2% | 717 | 32.9% | 19.2% |
| 2026 | 364 | 27.2% | 35.5% | 701 | 25.3% | 24.0% |

Returning minutes is the share of a team's **previous** season minutes played by athletes back on its roster; incoming transfers is the share of a team's **current** minutes played by athletes who were at another school last season. The two do not sum to one and are not meant to: a freshman is in neither.

**A season's figure is about its own denominator.** Each row divides by the *previous* season's minutes, so a season following a short or disrupted one is measured against a smaller and differently composed base and is not comparable to its neighbours on the same terms. Any row that looks like a reversal of the trend should be read against the season above it before it is read as a change in the sport.

## What this report is not

It is not evidence of an edge. `models/ratings.py` ends its own fit report with the sentence this one takes as its brief: *a table of fitted coefficients reads like a result and is not one.* Fit quality and calibration can rule a model out; only a price backtest against prices the card could actually have taken can say whether any of it would have made money, and no number here is one.
