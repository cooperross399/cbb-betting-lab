# NCAA Division I men's basketball — forecast skill

Generated 2026-09-04T17:27:08Z.

**Does the model know anything the price does not?** This report regresses the outcome of every graded wager on the de-vigged market-implied probability and on the model's disagreement with it:

```
outcome = a + b_market · market_implied
            + b_disagreement · (model_implied − market_implied)
```

**The coefficient on the disagreement is the whole answer.** If it is indistinguishable from zero, the model knows nothing the price does not — whatever its calibration plot looks like and whatever its backtest return happens to be at this sample size.

The equivalent unparameterised fit is `outcome ~ market_implied + model_implied`, and the two are the same regression: the coefficient on the disagreement here **is** the coefficient on model-implied there. The reparameterisation puts the answer in its own column instead of leaving a reader to subtract two correlated coefficients.

The honest prior is the NHL lab, which ran this same regression and got **market 0.97, model 0.03 [-0.037, +0.102]** — the model added nothing, and its claimed edge was *anti-predictive*, bigger claimed edge being worse. Because the reparameterisation is an algebraic identity, that 0.03 is directly comparable to the disagreement coefficient below.

Market-implied probabilities are de-vigged by **multiplicative normalisation**: the two sides' raw implied probabilities are divided by their sum. Chosen because it needs no solver, no free parameter and no assumption this lab has not measured; Shin's method and the power method each fit a parameter, and fitting one here would be a hypothesis that belongs in the experiment ledger rather than a preprocessing step nobody counts. Its known bias is favourite-longshot, and it enters through the *level* of the market-implied probability — which is what the market coefficient is there to expose. The same fit on the **raw** probabilities is reported beside it so the reader can see how much the choice moved.

**The raw market column still has the vig in it.** Two sides of a two-way market at -110 imply 52.4% each and sum to 104.8%, so the raw implied probability over-estimates every side by construction and is being scored with a handicap. It is printed for exactly one reason: **if the model loses to the handicapped market, that is decisive** — there is no argument about de-vig methodology left to have.

**Both sides of a wager are in this population, and they are one observation seen twice.** A home ticket and its away complement win and lose together by construction. The intervals are unaffected — the two rows share a game cluster and the sandwich is built from per-cluster sums — but the row count is **not** a count of independent observations, which is why the cluster count is printed beside every coefficient and why the interval rather than the `n` is the thing to read.

## What was measured, and what could not be

**172,702 graded wagers supplied.** 172,702 could be de-vigged at the `book` pair scope; 0 could not and are counted rather than imputed. A missing price stays missing, and a de-vig is a price.

| Why a wager carries no de-vigged price | Wagers |
|:---|---:|
| the selection is not one this lab pairs | 0 |
| the price could not be read | 0 |
| the other side of the wager is not in the frame | 0 |
| the pair does not hold exactly two opposite sides | 0 |
| the two sides sum to 1.0 or less, so there is no hold to remove | 0 |

The identity `supplied = de-vigged + excluded` reconciles. A run that does not reconcile writes no record: a measurement that silently loses a third of its rows still prints an interval, and the interval looks exactly like one that did not.

Of the de-vigged wagers, **85,556 are scorable** and 87,146 are not: 86,351 carry no model probability, 795 pushed, 0 were void and 0 were unsettleable. **A push is not half a win** and is never folded in as one — a score computed over a denominator that quietly includes pushes measures a different quantity from the one it names.

The hold this de-vig removed, measured over 86,351 two-sided pairs: median **1.0471**, mean 1.0453, range 1.0015 to 1.6654. Printed because a de-vig is otherwise invisible, and a population held at 1.02 and one held at 1.09 are different instruments.

## Per conference tier

**6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention. No pooled Division I headline is ever reported; the pooled section below exists only because it is printed beside these.

### high_major

19,384 graded wagers across 3,827 games and 462 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.031 | -0.057 to -0.004 | -0.073 to +0.012 | 19,384 | 462 days | contains zero |
| market_implied | 1 | +1.042 | +0.996 to +1.088 | +0.969 to +1.116 | 19,384 | 462 days | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.177 | +0.044 to +0.310 | -0.037 to +0.390 | 19,384 | 462 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — high_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25698 | 19,384 |
| the market, de-vigged | 0.23819 | 19,384 |
| the market, **raw** (vig left in) | 0.23815 | 19,384 |
| the base rate (49.3% of these wagers won) | 0.24996 | 19,384 |

- **against the de-vigged market:** the model's Brier advantage is -0.01879 over 19,384 wagers across 462 days, 95% interval -0.02275 to -0.01483, family-corrected -0.02514 to -0.01244 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01883 over 19,384 wagers across 462 days, 95% interval -0.02238 to -0.01528, family-corrected -0.02452 to -0.01314 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — high_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return |
|:---|---:|---:|---:|---:|:---|---:|:---|
| below -10% | 0 | 0 | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — |
| +2% to +5% | 2,515 | 1,650 | 55.6% | 51.4% | 50.5% [48.6%, 52.5%] | -5.1 pp | — |
| +5% to +10% | 3,608 | 2,008 | 57.1% | 50.8% | 51.9% [50.3%, 53.5%] | -5.2 pp | — |
| +10% to +20% | 5,118 | 2,226 | 60.1% | 50.2% | 50.4% [49.0%, 51.8%] | -9.7 pp | — |
| +20% and above | 8,143 | 2,569 | 65.3% | 44.5% | 47.1% [46.1%, 48.2%] | -18.1 pp | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The biggest claimed edges do worst.** The shortfall against model-implied is -5.1 pp in the +2% to +5% bucket (2,515 wagers) and -18.1 pp in the +20% and above bucket (8,143 wagers) — it widens by 13.0 pp across the range. That is anti-predictiveness as a table rather than as a minus sign, and it is the shape that makes raising the edge threshold the wrong response.

### mid_major

39,810 graded wagers across 7,463 games and 486 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.026 | -0.046 to -0.005 | -0.058 to +0.007 | 39,810 | 486 days | contains zero |
| market_implied | 1 | +1.057 | +1.021 to +1.093 | +0.999 to +1.114 | 39,810 | 7,463 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.133 | +0.011 to +0.255 | -0.063 to +0.329 | 39,810 | 486 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — mid_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25181 | 39,810 |
| the market, de-vigged | 0.23939 | 39,810 |
| the market, **raw** (vig left in) | 0.23913 | 39,810 |
| the base rate (48.8% of these wagers won) | 0.24986 | 39,810 |

- **against the de-vigged market:** the model's Brier advantage is -0.01242 over 39,810 wagers across 486 days, 95% interval -0.01475 to -0.01010, family-corrected -0.01615 to -0.00870 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01268 over 39,810 wagers across 486 days, 95% interval -0.01468 to -0.01069, family-corrected -0.01588 to -0.00948 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — mid_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return |
|:---|---:|---:|---:|---:|:---|---:|:---|
| below -10% | 0 | 0 | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — |
| +2% to +5% | 6,156 | 3,771 | 54.3% | 50.2% | 49.8% [48.6%, 51.1%] | -4.5 pp | — |
| +5% to +10% | 8,521 | 4,465 | 55.8% | 49.6% | 51.5% [50.5%, 52.6%] | -4.2 pp | — |
| +10% to +20% | 11,265 | 4,591 | 58.7% | 49.0% | 51.4% [50.5%, 52.3%] | -7.3 pp | — |
| +20% and above | 13,868 | 4,351 | 61.2% | 43.0% | 44.5% [43.7%, 45.4%] | -16.7 pp | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The biggest claimed edges do worst.** The shortfall against model-implied is -4.5 pp in the +2% to +5% bucket (6,156 wagers) and -16.7 pp in the +20% and above bucket (13,868 wagers) — it widens by 12.2 pp across the range. That is anti-predictiveness as a table rather than as a minus sign, and it is the shape that makes raising the edge threshold the wrong response.

### low_major

26,356 graded wagers across 5,333 games and 418 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.045 | -0.071 to -0.019 | -0.086 to -0.004 | 26,356 | 5,333 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.054 | +1.005 to +1.104 | +0.975 to +1.133 | 26,356 | 5,333 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.256 | +0.088 to +0.425 | -0.014 to +0.527 | 26,356 | 418 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — low_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24967 | 26,356 |
| the market, de-vigged | 0.23970 | 26,356 |
| the market, **raw** (vig left in) | 0.24001 | 26,356 |
| the base rate (47.1% of these wagers won) | 0.24916 | 26,356 |

- **against the de-vigged market:** the model's Brier advantage is -0.00997 over 26,356 wagers across 418 days, 95% interval -0.01233 to -0.00761, family-corrected -0.01376 to -0.00618 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.00966 over 26,356 wagers across 418 days, 95% interval -0.01166 to -0.00767, family-corrected -0.01286 to -0.00646 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — low_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return |
|:---|---:|---:|---:|---:|:---|---:|:---|
| below -10% | 0 | 0 | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — |
| +2% to +5% | 4,508 | 2,825 | 53.3% | 49.2% | 48.5% [47.0%, 49.9%] | -4.8 pp | — |
| +5% to +10% | 6,427 | 3,301 | 55.0% | 48.9% | 48.7% [47.5%, 49.9%] | -6.3 pp | — |
| +10% to +20% | 8,000 | 3,382 | 57.6% | 48.1% | 48.6% [47.5%, 49.7%] | -9.0 pp | — |
| +20% and above | 7,421 | 2,681 | 57.7% | 41.4% | 43.3% [42.2%, 44.5%] | -14.4 pp | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The biggest claimed edges do worst.** The shortfall against model-implied is -4.8 pp in the +2% to +5% bucket (4,508 wagers) and -14.4 pp in the +20% and above bucket (7,421 wagers) — it widens by 9.6 pp across the range. That is anti-predictiveness as a table rather than as a minus sign, and it is the shape that makes raising the edge threshold the wrong response.

### unplaced

6 graded wagers across 2 games and 2 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |
| market_implied | 1 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |
| disagreement | 0 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |

There is no number here yet, and that is not a null result — it is a sample below the floor declared in advance.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *not enough evidence (6 bets, below the 200 declared in advance)*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — unplaced

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.36992 | 6 |
| the market, de-vigged | 0.22698 | 6 |
| the market, **raw** (vig left in) | 0.23900 | 6 |
| the base rate (16.7% of these wagers won) | 0.13889 | 6 |

- **against the de-vigged market:** the model's Brier advantage is -0.14294 over 6 wagers across 2 games, 95% interval -0.38981 to +0.10394, family-corrected -0.53895 to +0.25307 — not enough evidence (6 bets, below the 200 declared in advance).
- **against the raw, handicapped market:** the model's Brier advantage is -0.13092 over 6 wagers across 2 games, 95% interval -0.36990 to +0.10806, family-corrected -0.51426 to +0.25242 — not enough evidence (6 bets, below the 200 declared in advance).

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — unplaced

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return |
|:---|---:|---:|---:|---:|:---|---:|:---|
| below -10% | 0 | 0 | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — |
| +2% to +5% | 2 | 1 | — | — | — | — | — |
| +5% to +10% | 1 | 1 | — | — | — | — | — |
| +10% to +20% | 0 | 0 | — | — | — | — | — |
| +20% and above | 3 | 1 | — | — | — | — | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

> **The pooled verdict is `demonstrated edge` and no tier says that.** Every tier that cleared its floor reads *no demonstrated edge*. Three intervals that each span zero can pool into one that does not, because the sample triples while the estimate barely moves — that is arithmetic and not a discovery. It is the reason this lab does not headline a pooled Division I number, and the reason this line is printed here rather than left for a reader to find by comparing two tables.

85,556 graded wagers across 16,625 games and 513 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.032 | -0.045 to -0.019 | -0.053 to -0.011 | 85,556 | 513 days | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.053 | +1.028 to +1.077 | +1.013 to +1.092 | 85,556 | 16,625 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.174 | +0.091 to +0.256 | +0.041 to +0.306 | 85,556 | 513 days | demonstrated edge |

**17% of each point of claimed edge is realised.** The interval excludes zero on the winning side. That is a necessary condition for a real edge and not a sufficient one: `price_backtest.py` decides whether a policy would have made money, and `reachability` decides whether the price could have been taken.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

### Brier — pooled

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25233 | 85,556 |
| the market, de-vigged | 0.23921 | 85,556 |
| the market, **raw** (vig left in) | 0.23918 | 85,556 |
| the base rate (48.4% of these wagers won) | 0.24974 | 85,556 |

- **against the de-vigged market:** the model's Brier advantage is -0.01312 over 85,556 wagers across 513 days, 95% interval -0.01468 to -0.01156, family-corrected -0.01562 to -0.01062 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01315 over 85,556 wagers across 513 days, 95% interval -0.01453 to -0.01178, family-corrected -0.01535 to -0.01095 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

### Claimed edge against what happened — pooled

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return |
|:---|---:|---:|---:|---:|:---|---:|:---|
| below -10% | 0 | 0 | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — |
| +2% to +5% | 13,181 | 8,247 | 54.2% | 50.1% | 49.5% [48.6%, 50.3%] | -4.7 pp | — |
| +5% to +10% | 18,557 | 9,775 | 55.8% | 49.6% | 50.6% [49.9%, 51.3%] | -5.1 pp | — |
| +10% to +20% | 24,383 | 10,199 | 58.6% | 49.0% | 50.3% [49.6%, 50.9%] | -8.3 pp | — |
| +20% and above | 29,435 | 9,602 | 61.5% | 43.0% | 44.9% [44.4%, 45.5%] | -16.5 pp | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The biggest claimed edges do worst.** The shortfall against model-implied is -4.7 pp in the +2% to +5% bucket (13,181 wagers) and -16.5 pp in the +20% and above bucket (29,435 wagers) — it widens by 11.8 pp across the range. That is anti-predictiveness as a table rather than as a minus sign, and it is the shape that makes raising the edge threshold the wrong response.

## The same fit without the de-vig

The de-vig is a choice, and a choice whose effect nobody can see is an assumption. This is the identical regression run on the **raw** implied probabilities, with the hold still in them.

**Under a constant overround the disagreement coefficient is algebraically invariant to a multiplicative de-vig, and this table is how that is checked rather than asserted.** The two designs span the same column space — `span{1, m, p}` either way, because `k·m` is a scalar multiple of `m` — so the fitted values are identical and only the intercept and the market coefficient move. A disagreement coefficient that *does* move between the two tables is therefore a fact about the overround **varying** across the population, not about the de-vig method being wrong, and it is worth understanding before either number is quoted.

| Term | Coefficient | 95% interval | Rows | Clusters |
|:---|---:|:---|---:|---:|
| intercept | -0.031 | -0.044 to -0.018 | 85,556 | 513 days |
| market_implied | +1.012 | +0.988 to +1.035 | 85,556 | 16,625 games |
| disagreement | +0.177 | +0.094 to +0.260 | 85,556 | 513 days |

The disagreement coefficient moved by **0.0033** between the de-vigged fit and this one. A move of zero is the constant-overround case; anything larger is the overround varying across the population, and the hold summary above says by how much it varies.

## Why raising the edge threshold cannot help

A card takes a wager when the claimed edge clears a threshold, and at a fixed price the claimed edge is monotone in the disagreement `d`. Under the fit above, the realised excess of a wager over the de-vigged price is `(a + (b_market − 1)·market) + b_disagreement·d`, whose derivative in `d` is exactly **b_disagreement**. Raising the threshold is a monotone filter that admits only larger `d`, so:

- `b_disagreement > 0` — a higher threshold selects better wagers, and that coefficient says how much better.
- `b_disagreement = 0` — a higher threshold selects **the same** wagers on average, at a smaller sample and a wider interval. It buys nothing and costs power.
- `b_disagreement < 0` — a higher threshold selects **worse** wagers. The natural response to a disappointing backtest is the one that makes it worse, and nothing in a return figure says so.

This run's pooled disagreement coefficient is +0.174 [+0.091, +0.256] over 85,556 wagers across 513 days — demonstrated edge. The claimed-edge buckets above are the measurement of the same thing; the algebra and the table are printed together because either alone is arguable.

The threshold `price_backtest.BET_EDGE_THRESHOLD` declares in advance is 2%, and moving it after seeing a number is the defect this repository is arranged against. This section exists so that moving it is not even tempting.

## How this report is corrected, and what it cannot say

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 scored wagers or 30 clusters there is no number**, only the words *not enough evidence*. Both floors were declared in advance. The cluster floor is there because a cluster-robust sandwich is downward biased with few clusters, and this repository's standing failure mode is an interval that is too narrow.

- It cannot say a model **would have made money**. That is `price_backtest.py`'s question, and a disagreement coefficient above zero is a necessary condition for an edge and not a sufficient one.
- It cannot say an edge is **reachable**. An edge living entirely in prices that vanished is reported as not reachable regardless of its size or its significance.
- It cannot rule a model **in**. It is a calibration-family instrument and shares the family's asymmetry: it can kill, and where a priced test exists the priced test decides.
- It cannot say a market is a play. **No market is allowlisted**, and an excluded market is never a pass, an avoid, or a no-value call.
