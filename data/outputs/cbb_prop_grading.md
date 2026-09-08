# NCAA Division I men's basketball — the player-prop model, scored

**Every number below is per tier. There is no pooled all-of-Division-I row in this report and no function that computes one: high-major, mid-major and low-major are three distributions and a pooled headline is banned in this repository.**

- Model: `cbb_betting_lab.models.slate:slate_model`
- Control: `identity-blind role-prior control: the same engine, the same minutes lattice and the same lines, with every per-minute rate replaced by `role_prior[stat][projected-minutes bucket]` and the scoring mix replaced by the league `value_pmf` — `player_rates.shrink_rate` at credibility weight zero`
- Store: `/private/tmp/wt-grading/data/processed/cbb_historical_prices__card.csv`, 977,613,435 bytes, sha256 `143d7d307d9bc3b21989d7857aac6a52f8abd010da2c1e0ea2df8c0f0b82b78b`
- Season: 2024; snapshot window `card`
- Subject fold for the athlete clustering: `stores.normalise_subject (casefold)`
- Family correction: 95 cumulative hypotheses (x1.7689), read from the experiment ledger at render time

## What is compared against what

Market-implied probabilities are de-vigged **two ways and the least favourable to the model is the headline**. *Proportional*: the two sides' raw implied probabilities are divided by their sum. *Power*: the exponent `k` solving `p_over^k + p_under^k = 1`, the two-way member of the log-odds family. They disagree by construction on favourites and longshots, this lab has not measured which is right for a college basketball prop, and picking one after seeing which flatters the model is the move the rest of this repository exists to prevent. Both are formed from ONE pairing pass, so they cannot disagree about which rows are a pair.

The two baselines are printed BEFORE the model in every section below: the de-vigged two-sided fair price, and the identity-blind role-prior control — the same engine and the same minutes lattice with every per-minute rate replaced by the role prior at the athlete's projected-minutes bucket, which is the credibility weight set to zero. A model that beats neither has nothing to explain.

**An interval that includes zero is *no demonstrated edge*, in exactly those words. One that excludes zero on the losing side is a *demonstrated deficit*, which is a finding and not a null result.** Advantage is `(baseline mean log loss) − (model mean log loss)`, so positive is the model doing better, which is the direction the thirty registered hypotheses predict.

Intervals cluster **three** ways — by game, by day and by athlete — and the widest wins. The athlete is not optional: one subject supplies a whole ladder across ten markets, and neither the game nor the day absorbs that.

Below 200 wagers, or below 30 clusters, a cell carries the words *not enough evidence* and no number at all.

`player_first_basket`, `player_double_double` are **refused by name**. They are not scored anywhere below, are never given a verdict, and are not a pass, an avoid or a no-value call.

## What one scored row is, and what it is not

A scored row is **one side of one wager at one book**. That is the unit design section 10's de-vig joins on — the same event, market, athlete, line AND book — and it is why the row counts below are larger than the wager counts beside them.

Two consequences are stated rather than left to be found:

1. **Both sides of a pair are scored.** The store's own census counts an over and an under as two wagers, and both are here. Their errors are exactly opposite by construction, which is why the calibration tables below are close to symmetric about 50% — that symmetry is a property of the population and not a finding about the model. The clustering absorbs the dependence: two sides of one pair share a game, a day and an athlete, so they are never two independent observations in any of the three arms.
2. **The declared floor is a floor on WAGERS, not on rows.** A wager quoted at five books is five rows and one bet, and the 200 declared in advance is a number of bets. Every cell below is qualified by its wager count.

## What was scored, and what was not

Both censuses reconcile, and `build_record` refuses to write a record when either does not: a measurement that silently loses rows still prints an interval, and the interval looks fine.

| Step | Rows |
|:---|---:|
| supplied to the de-vig | 484,790 |
| de-vigged (two-sided, same book) | 342,678 |
| no complement at the same book | 142,112 |
| not two-sided | 0 |
| overround not above one | 0 |
| power exponent unsolved | 0 |
| unreadable price | 0 |
| unknown selection | 0 |

| Step | Rows |
|:---|---:|
| de-vigged | 342,678 |
| **scored** | 339,660 |
| push (never half a win) | 0 |
| void (a returned stake) | 2,834 |
| unsettleable (never a loss) | 0 |
| no model probability | 0 |
| no control probability | 0 |
| no tier | 0 |
| past 3 rungs — unbenchmarked, reported apart | 184 |

The hold this de-vig removed: **171,339 pair(s)**, median overround 1.0758, mean 1.0769, range 1.0317 to 1.1296; median power exponent 1.1208.

Probabilities are clipped into [1e-06, 0.999999] before any log is taken, because a probability of exactly zero or one has an infinite log loss. Every clip is a number this report changed, so every clip is counted: **no row was clipped**.

## Per tier

### high_major

46,370 scored wager(s) — 130,988 rows, one per book quoting one — on 392 game(s) over 106 slate day(s), 541 athlete(s) across 10 book(s). 65,494 of the rows won.

*Coverage, in wagers: 97,042 offered, 92,001 priced, 91,225 settled, 46,484 with a two-sided fair price (51.0% of settled), of which 46,370 are within 3 rungs of the money and 114 are past it and unbenchmarked. Those 46,370 wagers are 130,988 scored rows, one per book quoting them.*

| Source | Role | Mean log loss | Brier |
|:---|:---|---:|---:|
| de-vigged fair price (proportional) | baseline, printed first | 0.68265 | 0.24483 |
| de-vigged fair price (power) | baseline, printed first | 0.68291 | 0.24489 |
| identity-blind role-prior control (conditional) | baseline, printed first | 0.80136 | 0.28480 |
| identity-blind role-prior control (unconditional) | baseline, printed first | 0.80136 | 0.28480 |
| **the model (conditional)** | what is being tested | 0.68839 | 0.24754 |
| **the model (unconditional)** | what is being tested | 0.68839 | 0.24754 |

| Comparison | Advantage (baseline − model log loss) | 95% interval | Family-corrected | Wagers | Clusters | Reading |
|:---|---:|:---|:---|---:|---:|:---|
| de-vig proportional / conditional | -0.0057 | -0.0103 to -0.0012 | -0.0138 to +0.0024 | 46,370 | 106 days | no demonstrated edge |
| **de-vig proportional / unconditional — HEADLINE, least favourable to the model** | -0.0057 | -0.0103 to -0.0012 | -0.0139 to +0.0024 | 46,370 | 106 days | no demonstrated edge |
| de-vig power / conditional | -0.0055 | -0.0102 to -0.0007 | -0.0138 to +0.0029 | 46,370 | 106 days | no demonstrated edge |
| de-vig power / unconditional | -0.0055 | -0.0102 to -0.0007 | -0.0138 to +0.0029 | 46,370 | 106 days | no demonstrated edge |
| control / conditional | +0.1130 | +0.0863 to +0.1396 | +0.0659 to +0.1601 | 46,370 | 541 athletes | demonstrated edge |
| control / unconditional | +0.1130 | +0.0863 to +0.1396 | +0.0659 to +0.1601 | 46,370 | 541 athletes | demonstrated edge |

**high_major: no demonstrated edge.**

**Beating the control is not beating the market, and the verdict above is the market comparison only.** The identity-blind role-prior control is a NEGATIVE control: it is the same engine told the athlete's role and not his identity, and a model that beats it has shown that its per-athlete evidence is worth something over a role table. A model can beat that control decisively and still lose to a de-vigged fair price, which is the only comparison that bears on whether anything here could be bet — and nothing here can be bet in any case.

Mean push mass on the scored rows: model 0.0000, control 0.0000. That is how much the choice between the two probability conventions could have been worth, and it is why both are scored rather than one being chosen.

**Calibration by decile — the model.**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 340 | 5.5% | 9.7% | -4.2 |
| 10%-20% | 701 | 16.0% | 25.7% | -9.7 |
| 20%-30% | 3,874 | 26.5% | 36.2% | -9.7 |
| 30%-40% | 17,812 | 36.1% | 42.0% | -5.8 |
| 40%-50% | 42,767 | 45.4% | 48.0% | -2.6 |
| 50%-60% | 42,767 | 54.6% | 52.0% | +2.6 |
| 60%-70% | 17,812 | 63.9% | 58.0% | +5.8 |
| 70%-80% | 3,874 | 73.5% | 63.8% | +9.7 |
| 80%-90% | 701 | 84.0% | 74.3% | +9.7 |
| 90%-100% | 340 | 94.5% | 90.3% | +4.2 |

**Calibration by decile — the de-vigged fair price (proportional).**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 50 | 8.6% | 18.0% | -9.4 |
| 10%-20% | 511 | 15.7% | 20.4% | -4.7 |
| 20%-30% | 623 | 24.6% | 28.9% | -4.3 |
| 30%-40% | 7,145 | 36.9% | 37.3% | -0.4 |
| 40%-50% | 52,391 | 46.3% | 45.8% | +0.5 |
| 50%-60% | 61,939 | 53.2% | 53.6% | -0.4 |
| 60%-70% | 7,145 | 63.1% | 62.7% | +0.4 |
| 70%-80% | 623 | 75.4% | 71.1% | +4.3 |
| 80%-90% | 511 | 84.3% | 79.6% | +4.7 |
| 90%-100% | 50 | 91.4% | 82.0% | +9.4 |

#### high_major — the far ladder, unbenchmarked

**Unbenchmarked.** These rows sit more than 3 rungs from the money, where two-sided coverage collapses: whatever has a fair price out here is a small and selected slice of a much larger offer, and the selection is the book's rather than this lab's. Whatever the interval below says, it is NOT an edge and is not reported as one.

114 scored wager(s) past 3 rungs. Reading: **not enough evidence (114 wagers, below the 200 declared in advance)**.

| Comparison | Advantage (baseline − model log loss) | 95% interval | Family-corrected | Wagers | Clusters | Reading |
|:---|---:|:---|:---|---:|---:|:---|
| de-vig proportional / conditional | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| de-vig proportional / unconditional | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| **de-vig power / conditional — HEADLINE, least favourable to the model** | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| de-vig power / unconditional | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| control / conditional | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| control / unconditional | — | — | — | 114 | 9 days | not enough evidence (9 day cluster(s), below the 30 declared in advance) |

### mid_major

74,174 scored wager(s) — 204,388 rows, one per book quoting one — on 679 game(s) over 124 slate day(s), 709 athlete(s) across 10 book(s). 102,194 of the rows won.

*Coverage, in wagers: 156,710 offered, 150,631 priced, 149,200 settled, 74,244 with a two-sided fair price (49.8% of settled), of which 74,174 are within 3 rungs of the money and 70 are past it and unbenchmarked. Those 74,174 wagers are 204,388 scored rows, one per book quoting them.*

| Source | Role | Mean log loss | Brier |
|:---|:---|---:|---:|
| de-vigged fair price (proportional) | baseline, printed first | 0.68339 | 0.24521 |
| de-vigged fair price (power) | baseline, printed first | 0.68354 | 0.24525 |
| identity-blind role-prior control (conditional) | baseline, printed first | 0.80330 | 0.28813 |
| identity-blind role-prior control (unconditional) | baseline, printed first | 0.80330 | 0.28813 |
| **the model (conditional)** | what is being tested | 0.68793 | 0.24737 |
| **the model (unconditional)** | what is being tested | 0.68793 | 0.24737 |

| Comparison | Advantage (baseline − model log loss) | 95% interval | Family-corrected | Wagers | Clusters | Reading |
|:---|---:|:---|:---|---:|---:|:---|
| **de-vig proportional / conditional — HEADLINE, least favourable to the model** | -0.0045 | -0.0077 to -0.0014 | -0.0102 to +0.0011 | 74,174 | 124 days | no demonstrated edge |
| de-vig proportional / unconditional | -0.0045 | -0.0077 to -0.0014 | -0.0102 to +0.0011 | 74,174 | 124 days | no demonstrated edge |
| de-vig power / conditional | -0.0044 | -0.0076 to -0.0012 | -0.0101 to +0.0013 | 74,174 | 124 days | no demonstrated edge |
| de-vig power / unconditional | -0.0044 | -0.0076 to -0.0012 | -0.0101 to +0.0013 | 74,174 | 124 days | no demonstrated edge |
| control / conditional | +0.1154 | +0.1018 to +0.1290 | +0.0913 to +0.1394 | 74,174 | 709 athletes | demonstrated edge |
| control / unconditional | +0.1154 | +0.1018 to +0.1290 | +0.0913 to +0.1394 | 74,174 | 709 athletes | demonstrated edge |

**mid_major: no demonstrated edge.**

**Beating the control is not beating the market, and the verdict above is the market comparison only.** The identity-blind role-prior control is a NEGATIVE control: it is the same engine told the athlete's role and not his identity, and a model that beats it has shown that its per-athlete evidence is worth something over a role table. A model can beat that control decisively and still lose to a de-vigged fair price, which is the only comparison that bears on whether anything here could be bet — and nothing here can be bet in any case.

Mean push mass on the scored rows: model 0.0000, control 0.0000. That is how much the choice between the two probability conventions could have been worth, and it is why both are scored rather than one being chosen.

**Calibration by decile — the model.**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 321 | 5.4% | 7.2% | -1.7 |
| 10%-20% | 766 | 15.9% | 24.8% | -8.9 |
| 20%-30% | 5,512 | 26.5% | 33.5% | -7.0 |
| 30%-40% | 27,215 | 36.1% | 42.2% | -6.1 |
| 40%-50% | 68,380 | 45.4% | 48.3% | -2.9 |
| 50%-60% | 68,380 | 54.6% | 51.7% | +2.9 |
| 60%-70% | 27,215 | 63.9% | 57.8% | +6.1 |
| 70%-80% | 5,512 | 73.5% | 66.5% | +7.0 |
| 80%-90% | 766 | 84.1% | 75.2% | +8.9 |
| 90%-100% | 321 | 94.6% | 92.8% | +1.7 |

**Calibration by decile — the de-vigged fair price (proportional).**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 59 | 8.4% | 6.8% | +1.6 |
| 10%-20% | 545 | 15.6% | 21.1% | -5.5 |
| 20%-30% | 631 | 24.8% | 27.6% | -2.7 |
| 30%-40% | 11,056 | 37.0% | 35.9% | +1.1 |
| 40%-50% | 83,197 | 46.3% | 46.3% | -0.1 |
| 50%-60% | 96,609 | 53.2% | 53.2% | +0.0 |
| 60%-70% | 11,056 | 63.0% | 64.1% | -1.1 |
| 70%-80% | 631 | 75.2% | 72.4% | +2.7 |
| 80%-90% | 545 | 84.4% | 78.9% | +5.5 |
| 90%-100% | 59 | 91.6% | 93.2% | -1.6 |

#### mid_major — the far ladder, unbenchmarked

**Unbenchmarked.** These rows sit more than 3 rungs from the money, where two-sided coverage collapses: whatever has a fair price out here is a small and selected slice of a much larger offer, and the selection is the book's rather than this lab's. Whatever the interval below says, it is NOT an edge and is not reported as one.

70 scored wager(s) past 3 rungs. Reading: **not enough evidence (70 wagers, below the 200 declared in advance)**.

| Comparison | Advantage (baseline − model log loss) | 95% interval | Family-corrected | Wagers | Clusters | Reading |
|:---|---:|:---|:---|---:|---:|:---|
| de-vig proportional / conditional | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |
| de-vig proportional / unconditional | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |
| **de-vig power / conditional — HEADLINE, least favourable to the model** | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |
| de-vig power / unconditional | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |
| control / conditional | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |
| control / unconditional | — | — | — | 70 | 11 days | not enough evidence (11 day cluster(s), below the 30 declared in advance) |

### low_major

2,060 scored wager(s) — 4,284 rows, one per book quoting one — on 19 game(s) over 10 slate day(s), 101 athlete(s) across 9 book(s). 2,142 of the rows won.

*Coverage, in wagers: 3,722 offered, 3,586 priced, 3,584 settled, 2,060 with a two-sided fair price (57.5% of settled), of which 2,060 are within 3 rungs of the money and 0 are past it and unbenchmarked. Those 2,060 wagers are 4,284 scored rows, one per book quoting them.*

| Source | Role | Mean log loss | Brier |
|:---|:---|---:|---:|
| de-vigged fair price (proportional) | baseline, printed first | 0.67379 | 0.24043 |
| de-vigged fair price (power) | baseline, printed first | 0.67304 | 0.23998 |
| identity-blind role-prior control (conditional) | baseline, printed first | 0.72444 | 0.25922 |
| identity-blind role-prior control (unconditional) | baseline, printed first | 0.72444 | 0.25922 |
| **the model (conditional)** | what is being tested | 0.67955 | 0.24301 |
| **the model (unconditional)** | what is being tested | 0.67955 | 0.24301 |

| Comparison | Advantage (baseline − model log loss) | 95% interval | Family-corrected | Wagers | Clusters | Reading |
|:---|---:|:---|:---|---:|---:|:---|
| de-vig proportional / conditional | -0.0058 | -0.0238 to +0.0123 | -0.0376 to +0.0261 | 2,060 | 101 athletes | no demonstrated edge |
| de-vig proportional / unconditional | -0.0058 | -0.0238 to +0.0123 | -0.0376 to +0.0261 | 2,060 | 101 athletes | no demonstrated edge |
| **de-vig power / conditional — HEADLINE, least favourable to the model** | -0.0065 | -0.0246 to +0.0116 | -0.0386 to +0.0256 | 2,060 | 101 athletes | no demonstrated edge |
| de-vig power / unconditional | -0.0065 | -0.0246 to +0.0116 | -0.0386 to +0.0256 | 2,060 | 101 athletes | no demonstrated edge |
| control / conditional | +0.0449 | -0.0010 to +0.0908 | -0.0364 to +0.1262 | 2,060 | 101 athletes | no demonstrated edge |
| control / unconditional | +0.0449 | -0.0010 to +0.0908 | -0.0364 to +0.1262 | 2,060 | 101 athletes | no demonstrated edge |

**low_major: no demonstrated edge.**

**Beating the control is not beating the market, and the verdict above is the market comparison only.** The identity-blind role-prior control is a NEGATIVE control: it is the same engine told the athlete's role and not his identity, and a model that beats it has shown that its per-athlete evidence is worth something over a role table. A model can beat that control decisively and still lose to a de-vigged fair price, which is the only comparison that bears on whether anything here could be bet — and nothing here can be bet in any case.

Mean push mass on the scored rows: model 0.0000, control 0.0000. That is how much the choice between the two probability conventions could have been worth, and it is why both are scored rather than one being chosen.

**Calibration by decile — the model.**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 5 | — | — | below the 30-row floor, so no frequency |
| 10%-20% | 22 | — | — | below the 30-row floor, so no frequency |
| 20%-30% | 92 | 26.6% | 43.5% | -16.9 |
| 30%-40% | 626 | 35.8% | 37.1% | -1.2 |
| 40%-50% | 1,397 | 45.2% | 44.7% | +0.5 |
| 50%-60% | 1,397 | 54.8% | 55.3% | -0.5 |
| 60%-70% | 626 | 64.2% | 62.9% | +1.2 |
| 70%-80% | 92 | 73.4% | 56.5% | +16.9 |
| 80%-90% | 22 | — | — | below the 30-row floor, so no frequency |
| 90%-100% | 5 | — | — | below the 30-row floor, so no frequency |

**Calibration by decile — the de-vigged fair price (proportional).**

| Predicted band | Wagers | Mean predicted | Realised | Gap (pp) |
|:---|---:|---:|---:|---:|
| 0%-10% | 1 | — | — | below the 30-row floor, so no frequency |
| 10%-20% | 17 | — | — | below the 30-row floor, so no frequency |
| 20%-30% | 19 | — | — | below the 30-row floor, so no frequency |
| 30%-40% | 265 | 37.0% | 30.6% | +6.5 |
| 40%-50% | 1,714 | 46.3% | 42.5% | +3.8 |
| 50%-60% | 1,966 | 53.2% | 56.5% | -3.3 |
| 60%-70% | 265 | 63.0% | 69.4% | -6.5 |
| 70%-80% | 19 | — | — | below the 30-row floor, so no frequency |
| 80%-90% | 17 | — | — | below the 30-row floor, so no frequency |
| 90%-100% | 1 | — | — | below the 30-row floor, so no frequency |

## Per market and tier

| Market / tier | Wagers | Headline comparison | Advantage | Family-corrected | Clusters | Coverage (two-sided of settled) | Verdict |
|:---|---:|:---|---:|:---|---:|---:|:---|
| player_points / high_major | 9,612 | de-vig proportional / unconditional | -0.0036 | -0.0245 to +0.0173 | 106 days | 33.7% | no demonstrated edge |
| player_rebounds / high_major | 7,400 | de-vig power / conditional | -0.0045 | -0.0174 to +0.0085 | 105 days | 38.7% | no demonstrated edge |
| player_assists / high_major | 6,040 | de-vig power / conditional | -0.0054 | -0.0216 to +0.0109 | 104 days | 52.2% | no demonstrated edge |
| player_threes / high_major | 4,304 | de-vig proportional / conditional | -0.0112 | -0.0270 to +0.0047 | 403 athletes | 49.5% | no demonstrated edge |
| player_steals / high_major | 3,720 | de-vig proportional / conditional | +0.0020 | -0.0117 to +0.0157 | 298 games | 89.0% | no demonstrated edge |
| player_turnovers / high_major | 3,904 | de-vig power / conditional | -0.0016 | -0.0156 to +0.0123 | 361 athletes | 100.0% | no demonstrated edge |
| player_pra / high_major | 4,308 | de-vig power / conditional | -0.0167 | -0.0311 to -0.0023 | 350 games | 55.3% | demonstrated deficit |
| player_points_rebounds / high_major | 2,720 | de-vig proportional / conditional | -0.0080 | -0.0242 to +0.0082 | 293 athletes | 99.7% | no demonstrated edge |
| player_points_assists / high_major | 2,228 | de-vig proportional / conditional | -0.0140 | -0.0328 to +0.0049 | 254 athletes | 99.7% | no demonstrated edge |
| player_rebounds_assists / high_major | 2,134 | de-vig power / conditional | -0.0015 | -0.0251 to +0.0222 | 44 days | 99.8% | no demonstrated edge |
| player_points / mid_major | 13,038 | de-vig proportional / conditional | -0.0049 | -0.0167 to +0.0068 | 124 days | 29.4% | no demonstrated edge |
| player_rebounds / mid_major | 10,954 | de-vig power / conditional | -0.0039 | -0.0134 to +0.0057 | 677 games | 36.4% | no demonstrated edge |
| player_assists / mid_major | 9,666 | de-vig proportional / conditional | -0.0011 | -0.0125 to +0.0103 | 673 games | 49.7% | no demonstrated edge |
| player_threes / mid_major | 7,230 | de-vig power / conditional | -0.0082 | -0.0189 to +0.0026 | 667 games | 50.4% | no demonstrated edge |
| player_steals / mid_major | 6,364 | de-vig proportional / conditional | +0.0022 | -0.0077 to +0.0120 | 103 days | 95.5% | no demonstrated edge |
| player_turnovers / mid_major | 6,442 | de-vig power / conditional | -0.0089 | -0.0201 to +0.0024 | 103 days | 100.0% | no demonstrated edge |
| player_pra / mid_major | 7,252 | de-vig proportional / conditional | -0.0089 | -0.0204 to +0.0025 | 124 days | 50.6% | no demonstrated edge |
| player_points_rebounds / mid_major | 4,846 | de-vig proportional / conditional | -0.0061 | -0.0204 to +0.0082 | 60 days | 99.8% | no demonstrated edge |
| player_points_assists / mid_major | 4,370 | de-vig proportional / conditional | -0.0072 | -0.0208 to +0.0064 | 60 days | 99.9% | no demonstrated edge |
| player_rebounds_assists / mid_major | 4,012 | de-vig proportional / conditional | -0.0032 | -0.0181 to +0.0117 | 356 games | 100.0% | no demonstrated edge |
| player_points / low_major | 294 | de-vig power / conditional | — | — | 10 days | 31.8% | not enough evidence (10 day cluster(s), below the 30 declared in advance) |
| player_rebounds / low_major | 288 | de-vig power / conditional | -0.0119 | -0.0706 to +0.0468 | 95 athletes | 42.8% | no demonstrated edge |
| player_assists / low_major | 234 | de-vig power / conditional | — | — | 19 games | 53.9% | not enough evidence (19 game cluster(s), below the 30 declared in advance) |
| player_threes / low_major | 190 | de-vig power / conditional | — | — | 82 athletes | 56.5% | not enough evidence (190 wagers, below the 200 declared in advance) |
| player_steals / low_major | 190 | de-vig proportional / conditional | — | — | 80 athletes | 100.0% | not enough evidence (190 wagers, below the 200 declared in advance) |
| player_turnovers / low_major | 190 | de-vig proportional / conditional | — | — | 9 days | 100.0% | not enough evidence (190 wagers, below the 200 declared in advance) |
| player_pra / low_major | 164 | de-vig proportional / conditional | — | — | 70 athletes | 50.2% | not enough evidence (164 wagers, below the 200 declared in advance) |
| player_points_rebounds / low_major | 180 | de-vig power / conditional | — | — | 77 athletes | 100.0% | not enough evidence (180 wagers, below the 200 declared in advance) |
| player_points_assists / low_major | 170 | de-vig proportional / conditional | — | — | 72 athletes | 100.0% | not enough evidence (170 wagers, below the 200 declared in advance) |
| player_rebounds_assists / low_major | 160 | de-vig proportional / conditional | — | — | 67 athletes | 100.0% | not enough evidence (160 wagers, below the 200 declared in advance) |

## The pre-registered hypotheses, answered

33 hypotheses, registered on 2026-09-05 **before the model that answers them existed**, each with a direction fixed then and unchangeable now: the ledger is append-only under its own CI job. Thirty are (market x tier) against the de-vigged two-sided fair price; three are per tier against the identity-blind role-prior control, pooled across the ten priceable markets.

The reading below is the cell's own verdict, not a second judgment of the same interval. A direction that was predicted and not observed is the pre-registration working.

| Search | Hypothesis | Predicted | Wagers | Advantage | Family-corrected | Reading |
|:---|:---|:---|---:|---:|:---|:---|
| player_props_vs_devig | player_points / high_major | lower | 9,612 | -0.0036 | -0.0245 to +0.0173 | no demonstrated edge |
| player_props_vs_devig | player_points / mid_major | lower | 13,038 | -0.0049 | -0.0167 to +0.0068 | no demonstrated edge |
| player_props_vs_devig | player_points / low_major | lower | 294 | — | — | not enough evidence (10 day cluster(s), below the 30 declared in advance) |
| player_props_vs_devig | player_rebounds / high_major | lower | 7,400 | -0.0045 | -0.0174 to +0.0085 | no demonstrated edge |
| player_props_vs_devig | player_rebounds / mid_major | lower | 10,954 | -0.0039 | -0.0134 to +0.0057 | no demonstrated edge |
| player_props_vs_devig | player_rebounds / low_major | lower | 288 | -0.0119 | -0.0706 to +0.0468 | no demonstrated edge |
| player_props_vs_devig | player_assists / high_major | lower | 6,040 | -0.0054 | -0.0216 to +0.0109 | no demonstrated edge |
| player_props_vs_devig | player_assists / mid_major | lower | 9,666 | -0.0011 | -0.0125 to +0.0103 | no demonstrated edge |
| player_props_vs_devig | player_assists / low_major | lower | 234 | — | — | not enough evidence (19 game cluster(s), below the 30 declared in advance) |
| player_props_vs_devig | player_threes / high_major | lower | 4,304 | -0.0112 | -0.0270 to +0.0047 | no demonstrated edge |
| player_props_vs_devig | player_threes / mid_major | lower | 7,230 | -0.0082 | -0.0189 to +0.0026 | no demonstrated edge |
| player_props_vs_devig | player_threes / low_major | lower | 190 | — | — | not enough evidence (190 bets, below the 200 declared in advance) |
| player_props_vs_devig | player_pra / high_major | lower | 4,308 | -0.0167 | -0.0311 to -0.0023 | demonstrated deficit |
| player_props_vs_devig | player_pra / mid_major | lower | 7,252 | -0.0089 | -0.0204 to +0.0025 | no demonstrated edge |
| player_props_vs_devig | player_pra / low_major | lower | 164 | — | — | not enough evidence (164 bets, below the 200 declared in advance) |
| player_props_vs_devig | player_steals / high_major | lower | 3,720 | +0.0020 | -0.0117 to +0.0157 | no demonstrated edge |
| player_props_vs_devig | player_steals / mid_major | lower | 6,364 | +0.0022 | -0.0077 to +0.0120 | no demonstrated edge |
| player_props_vs_devig | player_steals / low_major | lower | 190 | — | — | not enough evidence (190 bets, below the 200 declared in advance) |
| player_props_vs_devig | player_turnovers / high_major | lower | 3,904 | -0.0016 | -0.0156 to +0.0123 | no demonstrated edge |
| player_props_vs_devig | player_turnovers / mid_major | lower | 6,442 | -0.0089 | -0.0201 to +0.0024 | no demonstrated edge |
| player_props_vs_devig | player_turnovers / low_major | lower | 190 | — | — | not enough evidence (9 day cluster(s), below the 30 declared in advance) |
| player_props_vs_devig | player_points_rebounds / high_major | lower | 2,720 | -0.0080 | -0.0242 to +0.0082 | no demonstrated edge |
| player_props_vs_devig | player_points_rebounds / mid_major | lower | 4,846 | -0.0061 | -0.0204 to +0.0082 | no demonstrated edge |
| player_props_vs_devig | player_points_rebounds / low_major | lower | 180 | — | — | not enough evidence (180 bets, below the 200 declared in advance) |
| player_props_vs_devig | player_points_assists / high_major | lower | 2,228 | -0.0140 | -0.0328 to +0.0049 | no demonstrated edge |
| player_props_vs_devig | player_points_assists / mid_major | lower | 4,370 | -0.0072 | -0.0208 to +0.0064 | no demonstrated edge |
| player_props_vs_devig | player_points_assists / low_major | lower | 170 | — | — | not enough evidence (170 bets, below the 200 declared in advance) |
| player_props_vs_devig | player_rebounds_assists / high_major | lower | 2,134 | -0.0015 | -0.0251 to +0.0222 | no demonstrated edge |
| player_props_vs_devig | player_rebounds_assists / mid_major | lower | 4,012 | -0.0032 | -0.0181 to +0.0117 | no demonstrated edge |
| player_props_vs_devig | player_rebounds_assists / low_major | lower | 160 | — | — | not enough evidence (160 bets, below the 200 declared in advance) |
| player_props_vs_role_prior | high_major | lower | 46,370 | +0.1130 | +0.0659 to +0.1601 | demonstrated edge |
| player_props_vs_role_prior | mid_major | lower | 74,174 | +0.1154 | +0.0913 to +0.1394 | demonstrated edge |
| player_props_vs_role_prior | low_major | lower | 2,060 | +0.0449 | -0.0364 to +0.1262 | no demonstrated edge |

## Two-sided coverage against distance from the money

The ladder, measured. A rung with no opposite side at the same book gets no fair price at all, so this table is what the benchmark could reach rather than what the store offered.

| Rungs from the money | Settled rows | With a two-sided fair price | Coverage | Benchmarked |
|---:|---:|---:|---:|:---|
| 0 | 297,636 | 293,904 | 98.7% | yes |
| 1 | 78,375 | 39,772 | 50.7% | yes |
| 2 | 36,972 | 4,878 | 13.2% | yes |
| 3 | 23,712 | 1,106 | 4.7% | yes |
| 4 | 15,217 | 166 | 1.1% | no — unbenchmarked |
| 5 | 8,806 | 18 | 0.2% | no — unbenchmarked |
| 6 | 7,128 | 0 | 0.0% | no — unbenchmarked |
| 7 | 5,707 | 0 | 0.0% | no — unbenchmarked |
| 8 | 3,804 | 0 | 0.0% | no — unbenchmarked |
| 9 | 2,461 | 0 | 0.0% | no — unbenchmarked |
| 10 | 771 | 0 | 0.0% | no — unbenchmarked |
| 11 | 117 | 0 | 0.0% | no — unbenchmarked |
| 12 | 7 | 0 | 0.0% | no — unbenchmarked |

## The vigged comparison, which is a diagnostic and never a headline

**This section is a diagnostic and is never a headline.** Comparing a model against the VIGGED implied probability hands it the whole hold and turns a losing model into one that appears to win. `forecast_skill` already states why it is printed at all, and its sentence is quoted here rather than reworded so the two reports cannot drift:

> **The raw market column still has the vig in it.** Two sides of a two-way market at -110 imply 52.4% each and sum to 104.8%, so the raw implied probability over-estimates every side by construction and is being scored with a handicap. It is printed for exactly one reason: **if the model loses to the handicapped market, that is decisive** — there is no argument about de-vig methodology left to have.

| Tier | Convention | Advantage over the VIGGED market | Family-corrected | Reading |
|:---|:---|---:|:---|:---|
| high_major | conditional | -0.0025 | -0.0108 to +0.0057 | no demonstrated edge |
| high_major | unconditional | -0.0025 | -0.0108 to +0.0057 | no demonstrated edge |
| mid_major | conditional | -0.0013 | -0.0070 to +0.0043 | no demonstrated edge |
| mid_major | unconditional | -0.0013 | -0.0070 to +0.0043 | no demonstrated edge |
| low_major | conditional | -0.0032 | -0.0351 to +0.0288 | no demonstrated edge |
| low_major | unconditional | -0.0032 | -0.0351 to +0.0288 | no demonstrated edge |

## What this is not

- It is not a recommendation and not a selection. No market in this lab is allowlisted and no player prop can reach `Availability.CONFIRMED`, so nothing here can become a bet.
- It is not a return. Nothing above is a stake, a profit or an ROI; every number is a log loss, a Brier score or a difference between two of them.
- It is not a claim about a market whose cell says *not enough evidence*, and a cell that says so is not a pass, an avoid or a no-value call.

