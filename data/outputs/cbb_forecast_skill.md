# NCAA Division I men's basketball — forecast skill

Generated 2026-09-05T15:56:38Z.

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

## Two populations, and which one is the skill measure

A card takes a wager when the model's disagreement with the price clears a threshold, and the bets are therefore the tail of the model's own error distribution — the winner's curse. Regressing outcome on that same disagreement **over the bets alone** builds the curse into the coefficient, and a claimed-edge table over them is tautological: every row is above the threshold by construction. Until 2026-09-05 the graded export was exactly the bets, so this report's regression ran over the slice it exists to avoid. Two populations are now measured, and every number below says which it belongs to.

| Population | What it is | Scorable wagers | Games | Days |
|:---|:---|---:|---:|---:|
| **every settled wager the model had an opinion on** | **the skill measure** | 293,661 | 27,082 | 791 |
| the threshold-selected bets only | the winner's-curse comparison, not the skill measure | 110,316 | 26,141 | 791 |
| graded wagers excluded before the frame was built | in neither population — no complement at their own book, so no hold and no fair price | 2 | — | — |

**2 graded wager(s) are in neither population above.** The frame was built from 566,377 graded wagers: 566,375 paired with the other side of their own book's quote, 0 carried a selection this lab forms no pair key for and were kept unpaired, and 2 (0.000353%) were excluded because their own book hung only one side of the wager, so the quote contains no hold and no fair price can be taken from it. Excluding them is the only honest arithmetic available — there is no hold in a one-sided quote to de-vig — but every count above is therefore a count of a **subset** of the graded set, not of the graded set itself.

They fell by market: alternate_spread (1), team_total (1); by book: betmgm (1), draftkings (1).

Of the 2 excluded, 1 had been marked as the threshold-selected bets only, so that comparison is short by the same number.

The selected subset is 110,316 of 293,661 scorable wagers, cut by the `selected` flag the price backtest stamped with the same predicate it used to count its bets. It is reported **beside** the whole, in its own section, and nothing in it is the skill measure.

## What was measured, and what could not be

**1,132,750 graded wagers supplied.** 587,322 could be de-vigged at the `book` pair scope; 545,428 could not and are counted rather than imputed. A missing price stays missing, and a de-vig is a price.

| Why a wager carries no de-vigged price | Wagers |
|:---|---:|
| the selection is not one this lab pairs | 0 |
| the price could not be read | 0 |
| the other side of the wager is not in the frame | 0 |
| the pair does not hold exactly two opposite sides | 545,428 |
| the two sides sum to 1.0 or less, so there is no hold to remove | 0 |

The identity `supplied = de-vigged + excluded` reconciles. A run that does not reconcile writes no record: a measurement that silently loses a third of its rows still prints an interval, and the interval looks exactly like one that did not.

Of the de-vigged wagers, **293,661 are scorable** and 293,661 are not: 293,661 carry no model probability, 0 pushed, 0 were void and 0 were unsettleable. **A push is not half a win** and is never folded in as one — a score computed over a denominator that quietly includes pushes measures a different quantity from the one it names.

The hold this de-vig removed, measured over 293,661 two-sided pairs: median **1.0475**, mean 1.0502, range 1.0022 to 1.9802. Printed because a de-vig is otherwise invisible, and a population held at 1.02 and one held at 1.09 are different instruments.

## Per conference tier

**Population: every settled wager the model had an opinion on — the skill measure.** Every number in this section and in the pooled section below it is fitted over that population. The threshold-selected bets are measured apart, in their own section further down, and are labelled as what they are.

**6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention. No pooled Division I headline is ever reported; the pooled section below exists only because it is printed beside these.

### high_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 62,163 scorable wagers in 6,268 games over 719 days.*

62,163 graded wagers across 6,268 games and 719 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | +0.001 | -0.019 to +0.021 | -0.031 to +0.033 | 62,163 | 719 days | contains zero |
| market_implied | 1 | +1.013 | +0.973 to +1.054 | +0.948 to +1.078 | 62,163 | 719 days | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.088 | +0.013 to +0.163 | -0.033 to +0.208 | 62,163 | 6,268 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — high_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25118 | 62,163 |
| the market, de-vigged | 0.23432 | 62,163 |
| the market, **raw** (vig left in) | 0.23455 | 62,163 |
| the base rate (50.0% of these wagers won) | 0.25000 | 62,163 |

- **against the de-vigged market:** the model's Brier advantage is -0.01686 over 62,163 wagers across 6,268 games, 95% interval -0.01987 to -0.01384, family-corrected -0.02169 to -0.01202 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01663 over 62,163 wagers across 6,268 games, 95% interval -0.01965 to -0.01361, family-corrected -0.02147 to -0.01179 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — high_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 24,416 | 6,105 | 36.2% | 49.0% | 49.6% [48.9%, 50.2%] | +13.4 pp | — | — | — | — (no settled wager) |
| -10% to -5% | 5,446 | 2,890 | 51.4% | 52.9% | 55.0% [53.7%, 56.3%] | +3.6 pp | — | — | — | — (no settled wager) |
| -5% to +0% | 5,665 | 2,441 | 55.0% | 53.7% | 53.7% [52.4%, 55.0%] | -1.3 pp | — | — | — | — (no settled wager) |
| +0% to +2% | 2,036 | 1,451 | 56.0% | 52.8% | 52.7% [50.5%, 54.9%] | -3.3 pp | — | — | — | — (no settled wager) |
| +2% to +5% | 2,824 | 1,929 | 56.5% | 52.1% | 50.1% [48.3%, 51.9%] | -6.4 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 4,155 | 2,444 | 57.7% | 51.2% | 51.6% [50.1%, 53.1%] | -6.1 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 6,389 | 3,256 | 60.0% | 49.9% | 50.1% [48.9%, 51.4%] | -9.9 pp | — | — | — | — (no settled wager) |
| +20% and above | 11,232 | 4,220 | 63.8% | 42.9% | 45.5% [44.6%, 46.4%] | -18.3 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +13.4 pp in the below -10% bucket (24,416 wagers) and -18.3 pp in the +20% and above bucket (11,232 wagers) — it widens by 31.7 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### mid_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 137,296 scorable wagers in 11,728 games over 740 days.*

137,296 graded wagers across 11,728 games and 740 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.044 | -0.063 to -0.025 | -0.074 to -0.013 | 137,296 | 740 days | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.104 | +1.065 to +1.142 | +1.042 to +1.166 | 137,296 | 740 days | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.122 | +0.036 to +0.207 | -0.015 to +0.259 | 137,296 | 740 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — mid_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24244 | 137,296 |
| the market, de-vigged | 0.23273 | 137,296 |
| the market, **raw** (vig left in) | 0.23282 | 137,296 |
| the base rate (50.0% of these wagers won) | 0.25000 | 137,296 |

- **against the de-vigged market:** the model's Brier advantage is -0.00971 over 137,296 wagers across 11,728 games, 95% interval -0.01172 to -0.00770, family-corrected -0.01293 to -0.00648 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.00962 over 137,296 wagers across 11,728 games, 95% interval -0.01164 to -0.00760, family-corrected -0.01286 to -0.00638 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — mid_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 50,859 | 11,183 | 39.5% | 49.9% | 50.0% [49.6%, 50.5%] | +10.5 pp | — | — | — | — (no settled wager) |
| -10% to -5% | 14,934 | 6,604 | 51.4% | 52.8% | 54.8% [54.0%, 55.6%] | +3.4 pp | — | — | — | — (no settled wager) |
| -5% to +0% | 14,897 | 5,233 | 54.1% | 52.8% | 53.3% [52.5%, 54.1%] | -0.8 pp | — | — | — | — (no settled wager) |
| +0% to +2% | 5,553 | 3,410 | 54.6% | 51.4% | 52.4% [51.0%, 53.7%] | -2.3 pp | — | — | — | — (no settled wager) |
| +2% to +5% | 7,441 | 4,272 | 55.3% | 50.8% | 51.5% [50.4%, 52.6%] | -3.8 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 10,696 | 5,430 | 56.2% | 49.8% | 49.6% [48.7%, 50.6%] | -6.6 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 14,394 | 6,453 | 58.0% | 48.3% | 49.9% [49.1%, 50.7%] | -8.1 pp | — | — | — | — (no settled wager) |
| +20% and above | 18,522 | 6,681 | 58.4% | 40.6% | 42.4% [41.7%, 43.1%] | -16.0 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +10.5 pp in the below -10% bucket (50,859 wagers) and -16.0 pp in the +20% and above bucket (18,522 wagers) — it widens by 26.5 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### low_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 94,182 scorable wagers in 9,084 games over 645 days.*

94,182 graded wagers across 9,084 games and 645 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.021 | -0.046 to +0.004 | -0.061 to +0.019 | 94,182 | 9,084 games | contains zero |
| market_implied | 1 | +1.057 | +1.007 to +1.108 | +0.977 to +1.138 | 94,182 | 9,084 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.046 | -0.064 to +0.156 | -0.130 to +0.223 | 94,182 | 645 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — low_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24582 | 94,182 |
| the market, de-vigged | 0.23782 | 94,182 |
| the market, **raw** (vig left in) | 0.23806 | 94,182 |
| the base rate (50.0% of these wagers won) | 0.25000 | 94,182 |

- **against the de-vigged market:** the model's Brier advantage is -0.00801 over 94,182 wagers across 645 days, 95% interval -0.00985 to -0.00617, family-corrected -0.01096 to -0.00506 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.00776 over 94,182 wagers across 645 days, 95% interval -0.00961 to -0.00591, family-corrected -0.01072 to -0.00479 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — low_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 33,334 | 8,487 | 41.9% | 50.9% | 51.7% [51.2%, 52.2%] | +9.8 pp | — | — | — | — (no settled wager) |
| -10% to -5% | 11,130 | 5,544 | 51.2% | 52.7% | 54.9% [54.0%, 55.8%] | +3.7 pp | — | — | — | — (no settled wager) |
| -5% to +0% | 11,077 | 4,325 | 52.4% | 51.2% | 51.3% [50.3%, 52.2%] | -1.1 pp | — | — | — | — (no settled wager) |
| +0% to +2% | 3,984 | 2,750 | 53.2% | 50.2% | 50.9% [49.3%, 52.4%] | -2.4 pp | — | — | — | — (no settled wager) |
| +2% to +5% | 5,663 | 3,534 | 53.7% | 49.4% | 51.3% [50.0%, 52.6%] | -2.4 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 8,163 | 4,459 | 55.1% | 48.9% | 48.4% [47.4%, 49.5%] | -6.7 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 10,684 | 5,064 | 56.9% | 47.4% | 47.7% [46.8%, 48.7%] | -9.2 pp | — | — | — | — (no settled wager) |
| +20% and above | 10,147 | 4,399 | 54.9% | 39.2% | 40.2% [39.3%, 41.2%] | -14.7 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +9.8 pp in the below -10% bucket (33,334 wagers) and -14.7 pp in the +20% and above bucket (10,147 wagers) — it widens by 24.5 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### unplaced

*Population: **every settled wager the model had an opinion on** — the skill measure; 20 scorable wagers in 2 games over 2 days.*

20 graded wagers across 2 games and 2 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | — | — | — | 20 | 2 games | not enough evidence (20 bets, below the 200 declared in advance) |
| market_implied | 1 | — | — | — | 20 | 2 games | not enough evidence (20 bets, below the 200 declared in advance) |
| disagreement | 0 | — | — | — | 20 | 2 games | not enough evidence (20 bets, below the 200 declared in advance) |

There is no number here yet, and that is not a null result — it is a sample below the floor declared in advance.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *not enough evidence (20 bets, below the 200 declared in advance)*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — unplaced

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.30421 | 20 |
| the market, de-vigged | 0.21970 | 20 |
| the market, **raw** (vig left in) | 0.21818 | 20 |
| the base rate (50.0% of these wagers won) | 0.25000 | 20 |

- **against the de-vigged market:** the model's Brier advantage is -0.08451 over 20 wagers across 2 games, 95% interval -0.27866 to +0.10965, family-corrected -0.39595 to +0.22694 — not enough evidence (20 bets, below the 200 declared in advance).
- **against the raw, handicapped market:** the model's Brier advantage is -0.08603 over 20 wagers across 2 games, 95% interval -0.28132 to +0.10925, family-corrected -0.39929 to +0.22722 — not enough evidence (20 bets, below the 200 declared in advance).

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — unplaced

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 8 | 2 | — | — | — | — | — | — | — | — |
| -10% to -5% | 1 | 1 | — | — | — | — | — | — | — | — |
| -5% to +0% | 4 | 2 | — | — | — | — | — | — | — | — |
| +0% to +2% | 1 | 1 | — | — | — | — | — | — | — | — |
| +2% to +5% | 2 | 1 | — | — | — | — | — | — | — | — |
| +5% to +10% | 1 | 1 | — | — | — | — | — | — | — | — |
| +10% to +20% | 0 | 0 | — | — | — | — | — | — | — | — |
| +20% and above | 3 | 1 | — | — | — | — | — | — | — | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**Population: every settled wager the model had an opinion on — the skill measure.**

> **The pooled verdict is `demonstrated edge` and no tier says that.** Every tier that cleared its floor reads *no demonstrated edge*. Three intervals that each span zero can pool into one that does not, because the sample triples while the estimate barely moves — that is arithmetic and not a discovery. It is the reason this lab does not headline a pooled Division I number, and the reason this line is printed here rather than left for a reader to find by comparing two tables.

*Population: **every settled wager the model had an opinion on** — the skill measure; 293,661 scorable wagers in 27,082 games over 791 days.*

293,661 graded wagers across 27,082 games and 791 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.027 | -0.039 to -0.015 | -0.047 to -0.008 | 293,661 | 27,082 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.071 | +1.046 to +1.095 | +1.031 to +1.110 | 293,661 | 27,082 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.094 | +0.044 to +0.144 | +0.014 to +0.175 | 293,661 | 27,082 games | demonstrated edge |

**9% of each point of claimed edge is realised.** The interval excludes zero on the winning side. That is a necessary condition for a real edge and not a sufficient one: `price_backtest.py` decides whether a policy would have made money, and `reachability` decides whether the price could have been taken.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

### Brier — pooled

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24538 | 293,661 |
| the market, de-vigged | 0.23470 | 293,661 |
| the market, **raw** (vig left in) | 0.23487 | 293,661 |
| the base rate (50.0% of these wagers won) | 0.25000 | 293,661 |

- **against the de-vigged market:** the model's Brier advantage is -0.01068 over 293,661 wagers across 27,082 games, 95% interval -0.01195 to -0.00941, family-corrected -0.01272 to -0.00865 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01051 over 293,661 wagers across 27,082 games, 95% interval -0.01178 to -0.00924, family-corrected -0.01255 to -0.00847 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

### Claimed edge against what happened — pooled

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 108,617 | 25,777 | 39.5% | 50.0% | 50.4% [50.2%, 50.7%] | +10.9 pp | — | — | — | — (no settled wager) |
| -10% to -5% | 31,511 | 15,039 | 51.3% | 52.8% | 54.9% [54.3%, 55.4%] | +3.5 pp | — | — | — | — (no settled wager) |
| -5% to +0% | 31,643 | 12,001 | 53.7% | 52.4% | 52.7% [52.1%, 53.2%] | -1.0 pp | — | — | — | — (no settled wager) |
| +0% to +2% | 11,574 | 7,612 | 54.4% | 51.2% | 51.9% [51.0%, 52.8%] | -2.5 pp | — | — | — | — (no settled wager) |
| +2% to +5% | 15,930 | 9,736 | 54.9% | 50.5% | 51.2% [50.4%, 52.0%] | -3.7 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 23,015 | 12,334 | 56.1% | 49.7% | 49.6% [48.9%, 50.2%] | -6.5 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 31,467 | 14,773 | 58.0% | 48.3% | 49.2% [48.6%, 49.7%] | -8.9 pp | — | — | — | — (no settled wager) |
| +20% and above | 39,904 | 15,301 | 59.0% | 40.9% | 42.7% [42.2%, 43.2%] | -16.3 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +10.9 pp in the below -10% bucket (108,617 wagers) and -16.3 pp in the +20% and above bucket (39,904 wagers) — it widens by 27.2 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

## The threshold-selected bets, beside it — the winner's-curse comparison

**Population: the threshold-selected bets only — the winner's-curse comparison, not the skill measure.** These are the rows the model's own disagreement with the price selected. A disagreement coefficient here is fitted on the tail of the model's error distribution and says how much the selection cost, not whether the model knows anything; a bucket table here has nothing below the threshold by construction. Read the section above for the skill measure and this one for the size of the curse.

### high_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 24,600 scorable wagers in 6,122 games over 718 days.*

24,600 graded wagers across 6,122 games and 718 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.026 | -0.050 to -0.002 | -0.065 to +0.013 | 24,600 | 6,122 games | contains zero |
| market_implied | 1 | +1.008 | +0.964 to +1.052 | +0.937 to +1.079 | 24,600 | 718 days | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.239 | +0.109 to +0.370 | +0.030 to +0.449 | 24,600 | 718 days | demonstrated edge |

**24% of each point of claimed edge is realised.** The interval excludes zero on the winning side. That is a necessary condition for a real edge and not a sufficient one: `price_backtest.py` decides whether a policy would have made money, and `reachability` decides whether the price could have been taken.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — high_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25421 | 24,600 |
| the market, de-vigged | 0.23397 | 24,600 |
| the market, **raw** (vig left in) | 0.23410 | 24,600 |
| the base rate (48.3% of these wagers won) | 0.24970 | 24,600 |

- **against the de-vigged market:** the model's Brier advantage is -0.02024 over 24,600 wagers across 6,122 games, 95% interval -0.02414 to -0.01635, family-corrected -0.02649 to -0.01399 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.02011 over 24,600 wagers across 6,122 games, 95% interval -0.02346 to -0.01676, family-corrected -0.02549 to -0.01474 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — high_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 2,824 | 1,929 | 56.5% | 52.1% | 50.1% [48.3%, 51.9%] | -6.4 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 4,155 | 2,444 | 57.7% | 51.2% | 51.6% [50.1%, 53.1%] | -6.1 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 6,389 | 3,256 | 60.0% | 49.9% | 50.1% [48.9%, 51.4%] | -9.9 pp | — | — | — | — (no settled wager) |
| +20% and above | 11,232 | 4,220 | 63.8% | 42.9% | 45.5% [44.6%, 46.4%] | -18.3 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -6.4 pp in the +2% to +5% bucket (2,824 wagers) and -18.3 pp in the +20% and above bucket (11,232 wagers) — it widens by 11.8 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### mid_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 51,053 scorable wagers in 11,315 games over 740 days.*

51,053 graded wagers across 11,315 games and 740 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.062 | -0.086 to -0.039 | -0.100 to -0.024 | 51,053 | 11,315 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.096 | +1.055 to +1.137 | +1.030 to +1.162 | 51,053 | 11,315 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.267 | +0.130 to +0.404 | +0.048 to +0.486 | 51,053 | 740 days | demonstrated edge |

**27% of each point of claimed edge is realised.** The interval excludes zero on the winning side. That is a necessary condition for a real edge and not a sufficient one: `price_backtest.py` decides whether a policy would have made money, and `reachability` decides whether the price could have been taken.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — mid_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24396 | 51,053 |
| the market, de-vigged | 0.23174 | 51,053 |
| the market, **raw** (vig left in) | 0.23163 | 51,053 |
| the base rate (47.3% of these wagers won) | 0.24929 | 51,053 |

- **against the de-vigged market:** the model's Brier advantage is -0.01222 over 51,053 wagers across 11,315 games, 95% interval -0.01498 to -0.00946, family-corrected -0.01665 to -0.00779 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01233 over 51,053 wagers across 11,315 games, 95% interval -0.01461 to -0.01005, family-corrected -0.01599 to -0.00867 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — mid_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 7,441 | 4,272 | 55.3% | 50.8% | 51.5% [50.4%, 52.6%] | -3.8 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 10,696 | 5,430 | 56.2% | 49.8% | 49.6% [48.7%, 50.6%] | -6.6 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 14,394 | 6,453 | 58.0% | 48.3% | 49.9% [49.1%, 50.7%] | -8.1 pp | — | — | — | — (no settled wager) |
| +20% and above | 18,522 | 6,681 | 58.4% | 40.6% | 42.4% [41.7%, 43.1%] | -16.0 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -3.8 pp in the +2% to +5% bucket (7,441 wagers) and -16.0 pp in the +20% and above bucket (18,522 wagers) — it widens by 12.2 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### low_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 34,657 scorable wagers in 8,702 games over 644 days.*

34,657 graded wagers across 8,702 games and 644 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.036 | -0.064 to -0.009 | -0.081 to +0.008 | 34,657 | 8,702 games | contains zero |
| market_implied | 1 | +1.055 | +0.998 to +1.112 | +0.963 to +1.146 | 34,657 | 8,702 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.177 | -0.003 to +0.358 | -0.112 to +0.467 | 34,657 | 644 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — low_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24571 | 34,657 |
| the market, de-vigged | 0.23553 | 34,657 |
| the market, **raw** (vig left in) | 0.23580 | 34,657 |
| the base rate (46.3% of these wagers won) | 0.24861 | 34,657 |

- **against the de-vigged market:** the model's Brier advantage is -0.01019 over 34,657 wagers across 644 days, 95% interval -0.01270 to -0.00767, family-corrected -0.01422 to -0.00615 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.00991 over 34,657 wagers across 644 days, 95% interval -0.01191 to -0.00790, family-corrected -0.01312 to -0.00669 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — low_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 5,663 | 3,534 | 53.7% | 49.4% | 51.3% [50.0%, 52.6%] | -2.4 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 8,163 | 4,459 | 55.1% | 48.9% | 48.4% [47.4%, 49.5%] | -6.7 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 10,684 | 5,064 | 56.9% | 47.4% | 47.7% [46.8%, 48.7%] | -9.2 pp | — | — | — | — (no settled wager) |
| +20% and above | 10,147 | 4,399 | 54.9% | 39.2% | 40.2% [39.3%, 41.2%] | -14.7 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -2.4 pp in the +2% to +5% bucket (5,663 wagers) and -14.7 pp in the +20% and above bucket (10,147 wagers) — it widens by 12.3 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### unplaced — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 6 scorable wagers in 2 games over 2 days.*

6 graded wagers across 2 games and 2 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |
| market_implied | 1 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |
| disagreement | 0 | — | — | — | 6 | 2 games | not enough evidence (6 bets, below the 200 declared in advance) |

There is no number here yet, and that is not a null result — it is a sample below the floor declared in advance.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *not enough evidence (6 bets, below the 200 declared in advance)*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — unplaced — the threshold-selected bets only

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

#### Claimed edge against what happened — unplaced — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 2 | 1 | — | — | — | — | — | — | — | — |
| +5% to +10% | 1 | 1 | — | — | — | — | — | — | — | — |
| +10% to +20% | 0 | 0 | — | — | — | — | — | — | — | — |
| +20% and above | 3 | 1 | — | — | — | — | — | — | — | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

### Pooled — the threshold-selected bets only

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 110,316 scorable wagers in 26,141 games over 791 days.*

110,316 graded wagers across 26,141 games and 791 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.046 | -0.060 to -0.031 | -0.069 to -0.022 | 110,316 | 26,141 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.062 | +1.035 to +1.089 | +1.018 to +1.106 | 110,316 | 26,141 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.235 | +0.154 to +0.316 | +0.105 to +0.364 | 110,316 | 791 days | demonstrated edge |

**23% of each point of claimed edge is realised.** The interval excludes zero on the winning side. That is a necessary condition for a real edge and not a sufficient one: `price_backtest.py` decides whether a policy would have made money, and `reachability` decides whether the price could have been taken.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — pooled — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24680 | 110,316 |
| the market, de-vigged | 0.23343 | 110,316 |
| the market, **raw** (vig left in) | 0.23349 | 110,316 |
| the base rate (47.2% of these wagers won) | 0.24922 | 110,316 |

- **against the de-vigged market:** the model's Brier advantage is -0.01338 over 110,316 wagers across 26,141 games, 95% interval -0.01510 to -0.01165, family-corrected -0.01614 to -0.01061 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01331 over 110,316 wagers across 26,141 games, 95% interval -0.01474 to -0.01188, family-corrected -0.01560 to -0.01102 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — pooled — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 15,930 | 9,736 | 54.9% | 50.5% | 51.2% [50.4%, 52.0%] | -3.7 pp | — | — | — | — (no settled wager) |
| +5% to +10% | 23,015 | 12,334 | 56.1% | 49.7% | 49.6% [48.9%, 50.2%] | -6.5 pp | — | — | — | — (no settled wager) |
| +10% to +20% | 31,467 | 14,773 | 58.0% | 48.3% | 49.2% [48.6%, 49.7%] | -8.9 pp | — | — | — | — (no settled wager) |
| +20% and above | 39,904 | 15,301 | 59.0% | 40.9% | 42.7% [42.2%, 43.2%] | -16.3 pp | — | — | — | — (no settled wager) |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -3.7 pp in the +2% to +5% bucket (15,930 wagers) and -16.3 pp in the +20% and above bucket (39,904 wagers) — it widens by 12.6 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** Fewer than two claimed-edge buckets carry 200 settled wagers, which is the floor declared in advance, and below it there is no return figure to compare. The overconfidence column above is a different quantity and cannot stand in for this one.

## The same fit without the de-vig

The de-vig is a choice, and a choice whose effect nobody can see is an assumption. This is the identical regression run on the **raw** implied probabilities, with the hold still in them.

**Population: every settled wager the model had an opinion on — the skill measure.**

**Under a constant overround the disagreement coefficient is algebraically invariant to a multiplicative de-vig, and this table is how that is checked rather than asserted.** The two designs span the same column space — `span{1, m, p}` either way, because `k·m` is a scalar multiple of `m` — so the fitted values are identical and only the intercept and the market coefficient move. A disagreement coefficient that *does* move between the two tables is therefore a fact about the overround **varying** across the population, not about the de-vig method being wrong, and it is worth understanding before either number is quoted.

| Term | Coefficient | 95% interval | Rows | Clusters |
|:---|---:|:---|---:|---:|
| intercept | -0.027 | -0.040 to -0.015 | 293,661 | 27,082 games |
| market_implied | +1.024 | +1.000 to +1.049 | 293,661 | 27,082 games |
| disagreement | +0.094 | +0.044 to +0.144 | 293,661 | 27,082 games |

The disagreement coefficient moved by **0.0003** between the de-vigged fit and this one. A move of zero is the constant-overround case; anything larger is the overround varying across the population, and the hold summary above says by how much it varies.

## Why raising the edge threshold cannot help

A card takes a wager when the claimed edge clears a threshold, and at a fixed price the claimed edge is monotone in the disagreement `d`. Under the fit above, the realised excess of a wager over the de-vigged price is `(a + (b_market − 1)·market) + b_disagreement·d`, whose derivative in `d` is exactly **b_disagreement**. Raising the threshold is a monotone filter that admits only larger `d`, so:

- `b_disagreement > 0` — a higher threshold selects better wagers, and that coefficient says how much better.
- `b_disagreement = 0` — a higher threshold selects **the same** wagers on average, at a smaller sample and a wider interval. It buys nothing and costs power.
- `b_disagreement < 0` — a higher threshold selects **worse** wagers. The natural response to a disappointing backtest is the one that makes it worse, and nothing in a return figure says so.

This run's pooled disagreement coefficient over **every settled wager the model had an opinion on** is +0.094 [+0.044, +0.144] over 293,661 wagers across 27,082 games — demonstrated edge. The **realised return** column of the claimed-edge buckets above measures the same thing bucket by bucket; the algebra and the table are printed together because either alone is arguable. The realised-minus-model column beside it is overconfidence, which is a different quantity and does not support this section's conclusion on its own.

The threshold `price_backtest.BET_EDGE_THRESHOLD` declares in advance is 2%, and moving it after seeing a number is the defect this repository is arranged against. This section exists so that moving it is not even tempting.

## How this report is corrected, and what it cannot say

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 scored wagers or 30 clusters there is no number**, only the words *not enough evidence*. Both floors were declared in advance. The cluster floor is there because a cluster-robust sandwich is downward biased with few clusters, and this repository's standing failure mode is an interval that is too narrow.

- It cannot say a model **would have made money**. That is `price_backtest.py`'s question, and a disagreement coefficient above zero is a necessary condition for an edge and not a sufficient one.
- It cannot say an edge is **reachable**. An edge living entirely in prices that vanished is reported as not reachable regardless of its size or its significance.
- It cannot rule a model **in**. It is a calibration-family instrument and shares the family's asymmetry: it can kill, and where a priced test exists the priced test decides.
- It cannot say a market is a play. **No market is allowlisted**, and an excluded market is never a pass, an avoid, or a no-value call.
