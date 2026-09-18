# NCAA Division I men's basketball — forecast skill

Generated 2026-09-18T03:04:50Z.

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
| **every settled wager the model had an opinion on** | **the skill measure** | 270,504 | 26,795 | 789 |
| the threshold-selected bets only | the winner's-curse comparison, not the skill measure | 100,856 | 25,315 | 781 |
| graded wagers excluded before the frame was built | in neither population — no complement at their own book, so no hold and no fair price | 1 | — | — |

**1 graded wager(s) are in neither population above.** The frame was built from 526,735 graded wagers: 526,734 paired with the other side of their own book's quote, 0 carried a selection this lab forms no pair key for and were kept unpaired, and 1 (0.000190%) were excluded because their own book hung only one side of the wager, so the quote contains no hold and no fair price can be taken from it. Excluding them is the only honest arithmetic available — there is no hold in a one-sided quote to de-vig — but every count above is therefore a count of a **subset** of the graded set, not of the graded set itself.

They fell by market: alternate_spread (1); by book: betmgm (1).

Of the 1 excluded, 1 had been marked as the threshold-selected bets only, so that comparison is short by the same number.

Census: 526,734 paired + 1 excluded + 0 with no pair key = 526,735, against 526,735 graded wagers supplied.

The selected subset is 100,856 of 270,504 scorable wagers, cut by the `selected` flag the price backtest stamped with the same predicate it used to count its bets. It is reported **beside** the whole, in its own section, and nothing in it is the skill measure.

## What was measured, and what could not be

**1,053,468 graded wagers supplied.** 541,008 could be de-vigged at the `book` pair scope; 512,460 could not and are counted rather than imputed. A missing price stays missing, and a de-vig is a price.

| Why a wager carries no de-vigged price | Wagers |
|:---|---:|
| the selection is not one this lab pairs | 0 |
| the price could not be read | 0 |
| the other side of the wager is not in the frame | 0 |
| the pair does not hold exactly two opposite sides | 512,460 |
| the two sides sum to 1.0 or less, so there is no hold to remove | 0 |

The identity `supplied = de-vigged + excluded` reconciles. A run that does not reconcile writes no record: a measurement that silently loses a third of its rows still prints an interval, and the interval looks exactly like one that did not.

Of the de-vigged wagers, **270,504 are scorable** and 270,504 are not: 270,504 carry no model probability, 0 pushed, 0 were void and 0 were unsettleable. **A push is not half a win** and is never folded in as one — a score computed over a denominator that quietly includes pushes measures a different quantity from the one it names.

The hold this de-vig removed, measured over 270,504 two-sided pairs: median **1.0475**, mean 1.0503, range 1.0022 to 1.9802. Printed because a de-vig is otherwise invisible, and a population held at 1.02 and one held at 1.09 are different instruments.

## Per conference tier

**Population: every settled wager the model had an opinion on — the skill measure.** Every number in this section and in the pooled section below it is fitted over that population. The threshold-selected bets are measured apart, in their own section further down, and are labelled as what they are.

**The three tiers are measured from non-conference margin, never assigned by a conference name list** — so the count in each moves with the data. They are three different distributions, and this lab exists because the third is plausibly priced with less attention. No pooled Division I headline is ever reported; the pooled section below exists only because it is printed beside these.

### high_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 53,844 scorable wagers in 6,152 games over 717 days.*

53,844 graded wagers across 6,152 games and 717 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.007 | -0.029 to +0.014 | -0.047 to +0.032 | 53,844 | 717 days | contains zero |
| market_implied | 1 | +1.031 | +0.987 to +1.075 | +0.951 to +1.110 | 53,844 | 717 days | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.046 | -0.036 to +0.129 | -0.104 to +0.196 | 53,844 | 6,152 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — high_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25160 | 53,844 |
| the market, de-vigged | 0.23359 | 53,844 |
| the market, **raw** (vig left in) | 0.23377 | 53,844 |
| the base rate (50.0% of these wagers won) | 0.25000 | 53,844 |

- **against the de-vigged market:** the model's Brier advantage is -0.01801 over 53,844 wagers across 6,152 games, 95% interval -0.02129 to -0.01472, family-corrected -0.02397 to -0.01205 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01783 over 53,844 wagers across 6,152 games, 95% interval -0.02112 to -0.01454, family-corrected -0.02379 to -0.01186 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — high_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 21,290 | 5,802 | 35.6% | 48.3% | 48.9% [48.2%, 49.6%] | +13.3 pp | -3.5% over 21,290 settled, 5,802 games | [-6.5%, -0.4%] | [-9.0%, +2.1%] across 133 looks | no demonstrated edge |
| -10% to -5% | 4,642 | 2,588 | 51.4% | 52.9% | 55.2% [53.8%, 56.6%] | +3.8 pp | -0.8% over 4,642 settled, 606 days | [-5.0%, +3.4%] | [-8.4%, +6.8%] across 133 looks | no demonstrated edge |
| -5% to +0% | 4,847 | 2,173 | 55.7% | 54.4% | 54.5% [53.1%, 55.9%] | -1.1 pp | -5.2% over 4,847 settled, 573 days | [-8.9%, -1.4%] | [-11.9%, +1.6%] across 133 looks | no demonstrated edge |
| +0% to +2% | 1,769 | 1,288 | 56.7% | 53.4% | 52.3% [50.0%, 54.7%] | -4.3 pp | -6.4% over 1,769 settled, 488 days | [-13.7%, +0.8%] | [-19.6%, +6.7%] across 133 looks | no demonstrated edge |
| +2% to +5% | 2,474 | 1,716 | 56.9% | 52.4% | 50.3% [48.3%, 52.3%] | -6.7 pp | -9.5% over 2,474 settled, 534 days | [-14.8%, -4.2%] | [-19.1%, +0.1%] across 133 looks | no demonstrated edge |
| +5% to +10% | 3,654 | 2,205 | 58.4% | 51.8% | 52.0% [50.4%, 53.6%] | -6.4 pp | -4.7% over 3,654 settled, 570 days | [-10.6%, +1.2%] | [-15.4%, +6.0%] across 133 looks | no demonstrated edge |
| +10% to +20% | 5,609 | 2,927 | 60.4% | 50.3% | 51.0% [49.7%, 52.3%] | -9.4 pp | -3.8% over 5,609 settled, 2,927 games | [-8.6%, +0.9%] | [-12.4%, +4.8%] across 133 looks | no demonstrated edge |
| +20% and above | 9,559 | 3,662 | 64.3% | 43.6% | 45.7% [44.7%, 46.7%] | -18.5 pp | -2.9% over 9,559 settled, 634 days | [-7.3%, +1.6%] | [-10.9%, +5.2%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +13.3 pp in the below -10% bucket (21,290 wagers) and -18.5 pp in the +20% and above bucket (9,559 wagers) — it widens by 31.9 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The below -10% bucket returned -3.5% over 21,290 settled wagers across 5,802 games, 95% interval [-6.5%, -0.4%], family-corrected [-9.0%, +2.1%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -2.9% over 9,559 settled wagers across 634 days, 95% interval [-7.3%, +1.6%], family-corrected [-10.9%, +5.2%] across 133 looks — no demonstrated edge. The return does not fall across the range, so this run shows no anti-predictiveness in realised return. That is not evidence of skill — the disagreement coefficient is the test — and it does not contradict the overconfidence column above, which measures a different quantity.
The +2% to +5% bucket returned -9.5% over 2,474 settled wagers across 534 days, 95% interval [-14.8%, -4.2%], family-corrected [-19.1%, +0.1%] across 133 looks — no demonstrated edge.
**The +2% to +5% claimed-edge bucket's return is below zero at the point estimate.** Both things are true and both are said: the point estimate sits on the losing side, and the family-corrected interval printed above includes zero, so the verdict beside it is the one that stands. A negative number under an interval that spans zero is not evidence of a loss; it is also not evidence of anything else.

### mid_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 127,094 scorable wagers in 11,621 games over 735 days.*

127,094 graded wagers across 11,621 games and 735 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.045 | -0.064 to -0.026 | -0.080 to -0.010 | 127,094 | 735 days | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.108 | +1.069 to +1.147 | +1.038 to +1.179 | 127,094 | 735 days | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.032 | -0.057 to +0.121 | -0.130 to +0.194 | 127,094 | 11,621 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — mid_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24295 | 127,094 |
| the market, de-vigged | 0.23221 | 127,094 |
| the market, **raw** (vig left in) | 0.23229 | 127,094 |
| the base rate (50.0% of these wagers won) | 0.25000 | 127,094 |

- **against the de-vigged market:** the model's Brier advantage is -0.01074 over 127,094 wagers across 11,621 games, 95% interval -0.01273 to -0.00875, family-corrected -0.01435 to -0.00713 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01066 over 127,094 wagers across 11,621 games, 95% interval -0.01266 to -0.00867, family-corrected -0.01429 to -0.00704 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — mid_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 46,974 | 10,888 | 39.7% | 49.6% | 50.2% [49.8%, 50.7%] | +10.6 pp | -4.3% over 46,974 settled, 10,888 games | [-6.8%, -1.9%] | [-8.8%, +0.1%] across 133 looks | no demonstrated edge |
| -10% to -5% | 13,774 | 6,170 | 51.3% | 52.7% | 54.8% [53.9%, 55.6%] | +3.4 pp | -1.4% over 13,774 settled, 6,170 games | [-3.6%, +0.9%] | [-5.5%, +2.8%] across 133 looks | no demonstrated edge |
| -5% to +0% | 14,264 | 5,068 | 54.3% | 52.9% | 53.8% [53.0%, 54.7%] | -0.4 pp | -4.0% over 14,264 settled, 5,068 games | [-6.5%, -1.6%] | [-8.6%, +0.5%] across 133 looks | no demonstrated edge |
| +0% to +2% | 5,177 | 3,166 | 54.9% | 51.7% | 51.9% [50.5%, 53.3%] | -3.0 pp | -4.8% over 5,177 settled, 585 days | [-9.0%, -0.7%] | [-12.4%, +2.7%] across 133 looks | no demonstrated edge |
| +2% to +5% | 7,278 | 4,095 | 55.2% | 50.7% | 50.9% [49.8%, 52.1%] | -4.2 pp | -5.1% over 7,278 settled, 4,095 games | [-8.9%, -1.2%] | [-12.0%, +1.9%] across 133 looks | no demonstrated edge |
| +5% to +10% | 10,038 | 5,124 | 56.3% | 49.9% | 49.8% [48.8%, 50.8%] | -6.5 pp | -6.2% over 10,038 settled, 644 days | [-9.8%, -2.5%] | [-12.8%, +0.5%] across 133 looks | no demonstrated edge |
| +10% to +20% | 13,457 | 6,054 | 58.0% | 48.2% | 49.6% [48.8%, 50.5%] | -8.3 pp | -2.7% over 13,457 settled, 6,054 games | [-6.3%, +0.9%] | [-9.2%, +3.8%] across 133 looks | no demonstrated edge |
| +20% and above | 16,132 | 5,987 | 57.9% | 40.6% | 41.2% [40.4%, 42.0%] | -16.7 pp | -5.7% over 16,132 settled, 5,987 games | [-9.6%, -1.8%] | [-12.8%, +1.4%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +10.6 pp in the below -10% bucket (46,974 wagers) and -16.7 pp in the +20% and above bucket (16,132 wagers) — it widens by 27.2 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The below -10% bucket returned -4.3% over 46,974 settled wagers across 10,888 games, 95% interval [-6.8%, -1.9%], family-corrected [-8.8%, +0.1%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -5.7% over 16,132 settled wagers across 5,987 games, 95% interval [-9.6%, -1.8%], family-corrected [-12.8%, +1.4%] across 133 looks — no demonstrated edge. The point estimate falls by 1.4 pp across the range, but the two family-corrected intervals overlap across 133 looks, so **the fall is not demonstrated** and the raw intervals overlap too. No sentence here says raising the threshold makes it worse; the disagreement coefficient is the test that can say so, and the overconfidence column above measures a different quantity.
The +5% to +10% bucket returned -6.2% over 10,038 settled wagers across 644 days, 95% interval [-9.8%, -2.5%], family-corrected [-12.8%, +0.5%] across 133 looks — no demonstrated edge.
**The +5% to +10% claimed-edge bucket's return is below zero at the point estimate.** Both things are true and both are said: the point estimate sits on the losing side, and the family-corrected interval printed above includes zero, so the verdict beside it is the one that stands. A negative number under an interval that spans zero is not evidence of a loss; it is also not evidence of anything else.

### low_major

*Population: **every settled wager the model had an opinion on** — the skill measure; 89,546 scorable wagers in 9,020 games over 642 days.*

89,546 graded wagers across 9,020 games and 642 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.024 | -0.049 to +0.001 | -0.070 to +0.022 | 89,546 | 9,020 games | contains zero |
| market_implied | 1 | +1.065 | +1.013 to +1.116 | +0.972 to +1.157 | 89,546 | 9,020 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.011 | -0.105 to +0.127 | -0.199 to +0.222 | 89,546 | 642 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — low_major

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24560 | 89,546 |
| the market, de-vigged | 0.23754 | 89,546 |
| the market, **raw** (vig left in) | 0.23777 | 89,546 |
| the base rate (50.0% of these wagers won) | 0.25000 | 89,546 |

- **against the de-vigged market:** the model's Brier advantage is -0.00806 over 89,546 wagers across 642 days, 95% interval -0.00991 to -0.00621, family-corrected -0.01142 to -0.00470 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.00782 over 89,546 wagers across 642 days, 95% interval -0.00968 to -0.00596, family-corrected -0.01120 to -0.00444 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — low_major

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 31,462 | 8,321 | 41.9% | 50.7% | 51.7% [51.1%, 52.2%] | +9.8 pp | -3.1% over 31,462 settled, 639 days | [-5.6%, -0.5%] | [-7.7%, +1.6%] across 133 looks | no demonstrated edge |
| -10% to -5% | 10,863 | 5,381 | 51.3% | 52.9% | 55.0% [54.1%, 56.0%] | +3.7 pp | -0.6% over 10,863 settled, 576 days | [-2.9%, +1.7%] | [-4.8%, +3.6%] across 133 looks | no demonstrated edge |
| -5% to +0% | 10,587 | 4,181 | 52.3% | 51.2% | 51.0% [50.0%, 51.9%] | -1.4 pp | -5.3% over 10,587 settled, 4,181 games | [-7.7%, -2.8%] | [-9.7%, -0.8%] across 133 looks | demonstrated deficit |
| +0% to +2% | 3,985 | 2,652 | 53.2% | 50.1% | 51.8% [50.3%, 53.4%] | -1.3 pp | -1.4% over 3,985 settled, 2,652 games | [-5.7%, +2.9%] | [-9.2%, +6.5%] across 133 looks | no demonstrated edge |
| +2% to +5% | 5,418 | 3,383 | 53.9% | 49.6% | 50.1% [48.8%, 51.5%] | -3.7 pp | -4.1% over 5,418 settled, 531 days | [-8.2%, +0.0%] | [-11.5%, +3.3%] across 133 looks | no demonstrated edge |
| +5% to +10% | 7,820 | 4,312 | 55.2% | 48.9% | 49.4% [48.3%, 50.5%] | -5.8 pp | -3.9% over 7,820 settled, 4,312 games | [-7.4%, -0.3%] | [-10.2%, +2.5%] across 133 looks | no demonstrated edge |
| +10% to +20% | 10,186 | 4,921 | 56.9% | 47.4% | 47.2% [46.3%, 48.2%] | -9.7 pp | -5.5% over 10,186 settled, 596 days | [-9.4%, -1.6%] | [-12.6%, +1.6%] across 133 looks | no demonstrated edge |
| +20% and above | 9,225 | 4,109 | 54.5% | 39.2% | 39.9% [38.9%, 40.9%] | -14.6 pp | -5.8% over 9,225 settled, 586 days | [-10.3%, -1.3%] | [-14.0%, +2.3%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +9.8 pp in the below -10% bucket (31,462 wagers) and -14.6 pp in the +20% and above bucket (9,225 wagers) — it widens by 24.3 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The below -10% bucket returned -3.1% over 31,462 settled wagers across 639 days, 95% interval [-5.6%, -0.5%], family-corrected [-7.7%, +1.6%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -5.8% over 9,225 settled wagers across 586 days, 95% interval [-10.3%, -1.3%], family-corrected [-14.0%, +2.3%] across 133 looks — no demonstrated edge. The point estimate falls by 2.7 pp across the range, but the two family-corrected intervals overlap across 133 looks, so **the fall is not demonstrated** and the raw intervals overlap too. No sentence here says raising the threshold makes it worse; the disagreement coefficient is the test that can say so, and the overconfidence column above measures a different quantity.
The -5% to +0% bucket returned -5.3% over 10,587 settled wagers across 4,181 games, 95% interval [-7.7%, -2.8%], family-corrected [-9.7%, -0.8%] across 133 looks — demonstrated deficit.
**The wagers in the -5% to +0% claimed-edge bucket lost money, and the loss survives the correction.** The family-corrected interval printed above lies entirely below zero, so that bucket is a **demonstrated deficit**: the model did worse than no edge in it, which is a stronger statement than failing to demonstrate one, and it is a statement about the money rather than about the size of the sample.

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
| the model | 0.30561 | 20 |
| the market, de-vigged | 0.21970 | 20 |
| the market, **raw** (vig left in) | 0.21818 | 20 |
| the base rate (50.0% of these wagers won) | 0.25000 | 20 |

- **against the de-vigged market:** the model's Brier advantage is -0.08590 over 20 wagers across 2 games, 95% interval -0.27827 to +0.10646, family-corrected -0.43496 to +0.26315 — not enough evidence (20 bets, below the 200 declared in advance).
- **against the raw, handicapped market:** the model's Brier advantage is -0.08743 over 20 wagers across 2 games, 95% interval -0.28093 to +0.10606, family-corrected -0.43853 to +0.26367 — not enough evidence (20 bets, below the 200 declared in advance).

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — unplaced

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 7 | 2 | — | — | — | — | — | — | — | — |
| -10% to -5% | 2 | 2 | — | — | — | — | — | — | — | — |
| -5% to +0% | 4 | 2 | — | — | — | — | — | — | — | — |
| +0% to +2% | 1 | 1 | — | — | — | — | — | — | — | — |
| +2% to +5% | 2 | 1 | — | — | — | — | — | — | — | — |
| +5% to +10% | 1 | 1 | — | — | — | — | — | — | — | — |
| +10% to +20% | 0 | 0 | — | — | — | — | — | — | — | — |
| +20% and above | 3 | 1 | — | — | — | — | — | — | — | — |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** No claimed-edge bucket of the 7 with any wager in them carries a readable return, so there is nothing to compare and nothing to read a sign off.
7 hold fewer than 30 wagers in total, which is the row floor this table prints no frequency below.
The overconfidence column above is a different quantity and cannot stand in for this one.

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**Population: every settled wager the model had an opinion on — the skill measure.**

*Population: **every settled wager the model had an opinion on** — the skill measure; 270,504 scorable wagers in 26,795 games over 789 days.*

270,504 graded wagers across 26,795 games and 789 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.031 | -0.044 to -0.019 | -0.054 to -0.008 | 270,504 | 26,795 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.080 | +1.054 to +1.105 | +1.033 to +1.126 | 270,504 | 26,795 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.032 | -0.022 to +0.086 | -0.067 to +0.131 | 270,504 | 26,795 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

### Brier — pooled

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24555 | 270,504 |
| the market, de-vigged | 0.23425 | 270,504 |
| the market, **raw** (vig left in) | 0.23440 | 270,504 |
| the base rate (50.0% of these wagers won) | 0.25000 | 270,504 |

- **against the de-vigged market:** the model's Brier advantage is -0.01130 over 270,504 wagers across 26,795 games, 95% interval -0.01259 to -0.01002, family-corrected -0.01363 to -0.00898 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01115 over 270,504 wagers across 26,795 games, 95% interval -0.01244 to -0.00987, family-corrected -0.01349 to -0.00882 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

### Claimed edge against what happened — pooled

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 99,733 | 25,013 | 39.5% | 49.7% | 50.4% [50.1%, 50.7%] | +10.9 pp | -3.7% over 99,733 settled, 25,013 games | [-5.3%, -2.2%] | [-6.5%, -1.0%] across 133 looks | demonstrated deficit |
| -10% to -5% | 29,281 | 14,141 | 51.3% | 52.8% | 54.9% [54.4%, 55.5%] | +3.6 pp | -1.0% over 29,281 settled, 14,141 games | [-2.5%, +0.5%] | [-3.7%, +1.7%] across 133 looks | no demonstrated edge |
| -5% to +0% | 29,702 | 11,424 | 53.8% | 52.5% | 52.9% [52.4%, 53.5%] | -0.9 pp | -4.7% over 29,702 settled, 11,424 games | [-6.2%, -3.1%] | [-7.5%, -1.8%] across 133 looks | demonstrated deficit |
| +0% to +2% | 10,932 | 7,107 | 54.6% | 51.4% | 52.0% [51.0%, 52.9%] | -2.6 pp | -3.8% over 10,932 settled, 7,107 games | [-6.5%, -1.1%] | [-8.8%, +1.1%] across 133 looks | no demonstrated edge |
| +2% to +5% | 15,172 | 9,195 | 55.0% | 50.6% | 50.6% [49.8%, 51.3%] | -4.4 pp | -5.4% over 15,172 settled, 9,195 games | [-7.9%, -2.9%] | [-10.0%, -0.9%] across 133 looks | demonstrated deficit |
| +5% to +10% | 21,513 | 11,642 | 56.3% | 49.9% | 50.0% [49.4%, 50.7%] | -6.2 pp | -5.1% over 21,513 settled, 723 days | [-7.5%, -2.7%] | [-9.4%, -0.8%] across 133 looks | demonstrated deficit |
| +10% to +20% | 29,252 | 13,902 | 58.1% | 48.3% | 49.1% [48.5%, 49.6%] | -9.0 pp | -3.9% over 29,252 settled, 13,902 games | [-6.2%, -1.6%] | [-8.1%, +0.3%] across 133 looks | no demonstrated edge |
| +20% and above | 34,919 | 13,759 | 58.7% | 41.1% | 42.1% [41.6%, 42.6%] | -16.6 pp | -5.0% over 34,919 settled, 13,759 games | [-7.5%, -2.5%] | [-9.5%, -0.5%] across 133 looks | demonstrated deficit |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is +10.9 pp in the below -10% bucket (99,733 wagers) and -16.6 pp in the +20% and above bucket (34,919 wagers) — it widens by 27.5 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The below -10% bucket returned -3.7% over 99,733 settled wagers across 25,013 games, 95% interval [-5.3%, -2.2%], family-corrected [-6.5%, -1.0%] across 133 looks — demonstrated deficit; the +20% and above bucket returned -5.0% over 34,919 settled wagers across 13,759 games, 95% interval [-7.5%, -2.5%], family-corrected [-9.5%, -0.5%] across 133 looks — demonstrated deficit. The point estimate falls by 1.2 pp across the range, but the two family-corrected intervals overlap across 133 looks, so **the fall is not demonstrated** and the raw intervals overlap too. No sentence here says raising the threshold makes it worse; the disagreement coefficient is the test that can say so, and the overconfidence column above measures a different quantity.
The -5% to +0% bucket returned -4.7% over 29,702 settled wagers across 11,424 games, 95% interval [-6.2%, -3.1%], family-corrected [-7.5%, -1.8%] across 133 looks — demonstrated deficit.
The +2% to +5% bucket returned -5.4% over 15,172 settled wagers across 9,195 games, 95% interval [-7.9%, -2.9%], family-corrected [-10.0%, -0.9%] across 133 looks — demonstrated deficit.
The +5% to +10% bucket returned -5.1% over 21,513 settled wagers across 723 days, 95% interval [-7.5%, -2.7%], family-corrected [-9.4%, -0.8%] across 133 looks — demonstrated deficit.
**The wagers in the below -10%, -5% to +0%, +2% to +5%, +5% to +10%, +20% and above claimed-edge buckets lost money, and the loss survives the correction.** The family-corrected intervals printed above lie entirely below zero, so each of those buckets is a **demonstrated deficit**: the model did worse than no edge in them, which is a stronger statement than failing to demonstrate one, and it is a statement about the money rather than about the size of the sample.

## The threshold-selected bets, beside it — the winner's-curse comparison

**Population: the threshold-selected bets only — the winner's-curse comparison, not the skill measure.** These are the rows the model's own disagreement with the price selected. A disagreement coefficient here is fitted on the tail of the model's error distribution and says how much the selection cost, not whether the model knows anything; a bucket table here has nothing below the threshold by construction. Read the section above for the skill measure and this one for the size of the curse.

### high_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 21,296 scorable wagers in 5,792 games over 703 days.*

21,296 graded wagers across 5,792 games and 703 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.028 | -0.056 to -0.001 | -0.078 to +0.021 | 21,296 | 703 days | contains zero |
| market_implied | 1 | +1.042 | +0.994 to +1.090 | +0.955 to +1.129 | 21,296 | 703 days | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.130 | -0.008 to +0.269 | -0.120 to +0.381 | 21,296 | 703 days | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — high_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.25501 | 21,296 |
| the market, de-vigged | 0.23329 | 21,296 |
| the market, **raw** (vig left in) | 0.23336 | 21,296 |
| the base rate (48.7% of these wagers won) | 0.24984 | 21,296 |

- **against the de-vigged market:** the model's Brier advantage is -0.02172 over 21,296 wagers across 5,792 games, 95% interval -0.02597 to -0.01747, family-corrected -0.02944 to -0.01400 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.02165 over 21,296 wagers across 5,792 games, 95% interval -0.02528 to -0.01802, family-corrected -0.02824 to -0.01507 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — high_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 2,474 | 1,716 | 56.9% | 52.4% | 50.3% [48.3%, 52.3%] | -6.7 pp | -9.5% over 2,474 settled, 534 days | [-14.8%, -4.2%] | [-19.1%, +0.1%] across 133 looks | no demonstrated edge |
| +5% to +10% | 3,654 | 2,205 | 58.4% | 51.8% | 52.0% [50.4%, 53.6%] | -6.4 pp | -4.7% over 3,654 settled, 570 days | [-10.6%, +1.2%] | [-15.4%, +6.0%] across 133 looks | no demonstrated edge |
| +10% to +20% | 5,609 | 2,927 | 60.4% | 50.3% | 51.0% [49.7%, 52.3%] | -9.4 pp | -3.8% over 5,609 settled, 2,927 games | [-8.6%, +0.9%] | [-12.4%, +4.8%] across 133 looks | no demonstrated edge |
| +20% and above | 9,559 | 3,662 | 64.3% | 43.6% | 45.7% [44.7%, 46.7%] | -18.5 pp | -2.9% over 9,559 settled, 634 days | [-7.3%, +1.6%] | [-10.9%, +5.2%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -6.7 pp in the +2% to +5% bucket (2,474 wagers) and -18.5 pp in the +20% and above bucket (9,559 wagers) — it widens by 11.9 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The +2% to +5% bucket returned -9.5% over 2,474 settled wagers across 534 days, 95% interval [-14.8%, -4.2%], family-corrected [-19.1%, +0.1%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -2.9% over 9,559 settled wagers across 634 days, 95% interval [-7.3%, +1.6%], family-corrected [-10.9%, +5.2%] across 133 looks — no demonstrated edge. The return does not fall across the range, so this run shows no anti-predictiveness in realised return. That is not evidence of skill — the disagreement coefficient is the test — and it does not contradict the overconfidence column above, which measures a different quantity.
**The +2% to +5% claimed-edge bucket's return is below zero at the point estimate.** Both things are true and both are said: the point estimate sits on the losing side, and the family-corrected interval printed above includes zero, so the verdict beside it is the one that stands. A negative number under an interval that spans zero is not evidence of a loss; it is also not evidence of anything else.

### mid_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 46,905 scorable wagers in 11,005 games over 730 days.*

46,905 graded wagers across 11,005 games and 730 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.053 | -0.077 to -0.028 | -0.097 to -0.008 | 46,905 | 11,005 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.107 | +1.065 to +1.150 | +1.030 to +1.185 | 46,905 | 11,005 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.083 | -0.060 to +0.227 | -0.177 to +0.344 | 46,905 | 11,005 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — mid_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24493 | 46,905 |
| the market, de-vigged | 0.23110 | 46,905 |
| the market, **raw** (vig left in) | 0.23126 | 46,905 |
| the base rate (47.0% of these wagers won) | 0.24908 | 46,905 |

- **against the de-vigged market:** the model's Brier advantage is -0.01383 over 46,905 wagers across 11,005 games, 95% interval -0.01657 to -0.01108, family-corrected -0.01881 to -0.00884 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01367 over 46,905 wagers across 11,005 games, 95% interval -0.01589 to -0.01144, family-corrected -0.01770 to -0.00963 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — mid_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 7,278 | 4,095 | 55.2% | 50.7% | 50.9% [49.8%, 52.1%] | -4.2 pp | -5.1% over 7,278 settled, 4,095 games | [-8.9%, -1.2%] | [-12.0%, +1.9%] across 133 looks | no demonstrated edge |
| +5% to +10% | 10,038 | 5,124 | 56.3% | 49.9% | 49.8% [48.8%, 50.8%] | -6.5 pp | -6.2% over 10,038 settled, 644 days | [-9.8%, -2.5%] | [-12.8%, +0.5%] across 133 looks | no demonstrated edge |
| +10% to +20% | 13,457 | 6,054 | 58.0% | 48.2% | 49.6% [48.8%, 50.5%] | -8.3 pp | -2.7% over 13,457 settled, 6,054 games | [-6.3%, +0.9%] | [-9.2%, +3.8%] across 133 looks | no demonstrated edge |
| +20% and above | 16,132 | 5,987 | 57.9% | 40.6% | 41.2% [40.4%, 42.0%] | -16.7 pp | -5.7% over 16,132 settled, 5,987 games | [-9.6%, -1.8%] | [-12.8%, +1.4%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -4.2 pp in the +2% to +5% bucket (7,278 wagers) and -16.7 pp in the +20% and above bucket (16,132 wagers) — it widens by 12.5 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The +2% to +5% bucket returned -5.1% over 7,278 settled wagers across 4,095 games, 95% interval [-8.9%, -1.2%], family-corrected [-12.0%, +1.9%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -5.7% over 16,132 settled wagers across 5,987 games, 95% interval [-9.6%, -1.8%], family-corrected [-12.8%, +1.4%] across 133 looks — no demonstrated edge. The point estimate falls by 0.7 pp across the range, but the two family-corrected intervals overlap across 133 looks, so **the fall is not demonstrated** and the raw intervals overlap too. No sentence here says raising the threshold makes it worse; the disagreement coefficient is the test that can say so, and the overconfidence column above measures a different quantity.
The +5% to +10% bucket returned -6.2% over 10,038 settled wagers across 644 days, 95% interval [-9.8%, -2.5%], family-corrected [-12.8%, +0.5%] across 133 looks — no demonstrated edge.
**The +5% to +10% claimed-edge bucket's return is below zero at the point estimate.** Both things are true and both are said: the point estimate sits on the losing side, and the family-corrected interval printed above includes zero, so the verdict beside it is the one that stands. A negative number under an interval that spans zero is not evidence of a loss; it is also not evidence of anything else.

### low_major — the threshold-selected bets only

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 32,649 scorable wagers in 8,516 games over 639 days.*

32,649 graded wagers across 8,516 games and 639 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.039 | -0.068 to -0.011 | -0.091 to +0.012 | 32,649 | 8,516 games | contains zero |
| market_implied | 1 | +1.072 | +1.014 to +1.131 | +0.966 to +1.179 | 32,649 | 8,516 games | contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable |
| disagreement | 0 | +0.104 | -0.093 to +0.300 | -0.254 to +0.461 | 32,649 | 8,516 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *contains 1.0 — the de-vigged price is calibrated at this sample size, which is what makes the disagreement coefficient readable*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — low_major — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24539 | 32,649 |
| the market, de-vigged | 0.23496 | 32,649 |
| the market, **raw** (vig left in) | 0.23532 | 32,649 |
| the base rate (46.2% of these wagers won) | 0.24853 | 32,649 |

- **against the de-vigged market:** the model's Brier advantage is -0.01044 over 32,649 wagers across 639 days, 95% interval -0.01297 to -0.00790, family-corrected -0.01503 to -0.00584 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01007 over 32,649 wagers across 639 days, 95% interval -0.01207 to -0.00807, family-corrected -0.01370 to -0.00644 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — low_major — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 5,418 | 3,383 | 53.9% | 49.6% | 50.1% [48.8%, 51.5%] | -3.7 pp | -4.1% over 5,418 settled, 531 days | [-8.2%, +0.0%] | [-11.5%, +3.3%] across 133 looks | no demonstrated edge |
| +5% to +10% | 7,820 | 4,312 | 55.2% | 48.9% | 49.4% [48.3%, 50.5%] | -5.8 pp | -3.9% over 7,820 settled, 4,312 games | [-7.4%, -0.3%] | [-10.2%, +2.5%] across 133 looks | no demonstrated edge |
| +10% to +20% | 10,186 | 4,921 | 56.9% | 47.4% | 47.2% [46.3%, 48.2%] | -9.7 pp | -5.5% over 10,186 settled, 596 days | [-9.4%, -1.6%] | [-12.6%, +1.6%] across 133 looks | no demonstrated edge |
| +20% and above | 9,225 | 4,109 | 54.5% | 39.2% | 39.9% [38.9%, 40.9%] | -14.6 pp | -5.8% over 9,225 settled, 586 days | [-10.3%, -1.3%] | [-14.0%, +2.3%] across 133 looks | no demonstrated edge |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -3.7 pp in the +2% to +5% bucket (5,418 wagers) and -14.6 pp in the +20% and above bucket (9,225 wagers) — it widens by 10.8 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The +2% to +5% bucket returned -4.1% over 5,418 settled wagers across 531 days, 95% interval [-8.2%, +0.0%], family-corrected [-11.5%, +3.3%] across 133 looks — no demonstrated edge; the +20% and above bucket returned -5.8% over 9,225 settled wagers across 586 days, 95% interval [-10.3%, -1.3%], family-corrected [-14.0%, +2.3%] across 133 looks — no demonstrated edge. The point estimate falls by 1.7 pp across the range, but the two family-corrected intervals overlap across 133 looks, so **the fall is not demonstrated** and the raw intervals overlap too. No sentence here says raising the threshold makes it worse; the disagreement coefficient is the test that can say so, and the overconfidence column above measures a different quantity.
**The +20% and above claimed-edge bucket's return is below zero at the point estimate.** Both things are true and both are said: the point estimate sits on the losing side, and the family-corrected interval printed above includes zero, so the verdict beside it is the one that stands. A negative number under an interval that spans zero is not evidence of a loss; it is also not evidence of anything else.

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
| the model | 0.37180 | 6 |
| the market, de-vigged | 0.22698 | 6 |
| the market, **raw** (vig left in) | 0.23900 | 6 |
| the base rate (16.7% of these wagers won) | 0.13889 | 6 |

- **against the de-vigged market:** the model's Brier advantage is -0.14481 over 6 wagers across 2 games, 95% interval -0.39075 to +0.10112, family-corrected -0.59107 to +0.30144 — not enough evidence (6 bets, below the 200 declared in advance).
- **against the raw, handicapped market:** the model's Brier advantage is -0.13280 over 6 wagers across 2 games, 95% interval -0.37083 to +0.10524, family-corrected -0.56472 to +0.29913 — not enough evidence (6 bets, below the 200 declared in advance).

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

**Anti-predictiveness — the realised return falling as the claimed edge rises — is not measured here.** No claimed-edge bucket of the 3 with any wager in them carries a readable return, so there is nothing to compare and nothing to read a sign off.
3 hold fewer than 30 wagers in total, which is the row floor this table prints no frequency below.
The overconfidence column above is a different quantity and cannot stand in for this one.

### Pooled — the threshold-selected bets only

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

*Population: **the threshold-selected bets only** — the winner's-curse comparison, not the skill measure; 100,856 scorable wagers in 25,315 games over 781 days.*

100,856 graded wagers across 25,315 games and 781 slate days.

| Term | Null | Coefficient | 95% interval | Family-corrected | Rows | Clusters | Reading |
|:---|---:|---:|:---|:---|---:|---:|:---|
| intercept | 0 | -0.044 | -0.059 to -0.028 | -0.071 to -0.016 | 100,856 | 25,315 games | excludes zero, below it — a level the de-vigged price does not account for, which is a fact about the fit rather than a claim about the model |
| market_implied | 1 | +1.082 | +1.054 to +1.111 | +1.030 to +1.134 | 100,856 | 25,315 games | excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why |
| disagreement | 0 | +0.104 | +0.019 to +0.190 | -0.051 to +0.260 | 100,856 | 25,315 games | no demonstrated edge |

**The model knows nothing the price does not.** The interval on the disagreement includes zero, so none of the claimed edge is demonstrably realised.

The market coefficient is a diagnostic, not a headline. Its null is 1.0 rather than zero, and its reading is: *excludes 1.0 (over-responsive) — the de-vigged price is not calibrated on this population, so read the disagreement coefficient only after understanding why*. The intercept is read the same way. Neither is ever described as an edge, because the words *demonstrated edge* are a claim about a **model**, and a coefficient of 0.97 on the **market** excludes zero on the positive side.

#### Brier — pooled — the threshold-selected bets only

| Forecaster | Brier score | Rows |
|:---|---:|---:|
| the model | 0.24721 | 100,856 |
| the market, de-vigged | 0.23281 | 100,856 |
| the market, **raw** (vig left in) | 0.23302 | 100,856 |
| the base rate (47.1% of these wagers won) | 0.24915 | 100,856 |

- **against the de-vigged market:** the model's Brier advantage is -0.01440 over 100,856 wagers across 25,315 games, 95% interval -0.01616 to -0.01265, family-corrected -0.01758 to -0.01122 — demonstrated deficit.
- **against the raw, handicapped market:** the model's Brier advantage is -0.01420 over 100,856 wagers across 25,315 games, 95% interval -0.01563 to -0.01276, family-corrected -0.01679 to -0.01160 — demonstrated deficit.

Positive is the model being **more** accurate. A Brier score is better when it is lower, so the quantity clustered is `brier_market − brier_model` — the sign is chosen that way so the shared verdict function reads it correctly rather than announcing an edge on a model that is measurably worse than the price.

**The model loses to the market even with the vig left in.** That is decisive: the raw implied probability over-estimates every side by construction, so it was being scored with a handicap, and it still won. No de-vig argument recovers this.

#### Claimed edge against what happened — pooled — the threshold-selected bets only

| Claimed edge | Wagers | Games | Model said | De-vigged price said | Actually won | Realised − model | Realised return | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|
| below -10% | 0 | 0 | — | — | — | — | — | — | — | — |
| -10% to -5% | 0 | 0 | — | — | — | — | — | — | — | — |
| -5% to +0% | 0 | 0 | — | — | — | — | — | — | — | — |
| +0% to +2% | 0 | 0 | — | — | — | — | — | — | — | — |
| +2% to +5% | 15,172 | 9,195 | 55.0% | 50.6% | 50.6% [49.8%, 51.3%] | -4.4 pp | -5.4% over 15,172 settled, 9,195 games | [-7.9%, -2.9%] | [-10.0%, -0.9%] across 133 looks | demonstrated deficit |
| +5% to +10% | 21,513 | 11,642 | 56.3% | 49.9% | 50.0% [49.4%, 50.7%] | -6.2 pp | -5.1% over 21,513 settled, 723 days | [-7.5%, -2.7%] | [-9.4%, -0.8%] across 133 looks | demonstrated deficit |
| +10% to +20% | 29,252 | 13,902 | 58.1% | 48.3% | 49.1% [48.5%, 49.6%] | -9.0 pp | -3.9% over 29,252 settled, 13,902 games | [-6.2%, -1.6%] | [-8.1%, +0.3%] across 133 looks | no demonstrated edge |
| +20% and above | 34,919 | 13,759 | 58.7% | 41.1% | 42.1% [41.6%, 42.6%] | -16.6 pp | -5.0% over 34,919 settled, 13,759 games | [-7.5%, -2.5%] | [-9.5%, -0.5%] across 133 looks | demonstrated deficit |

A bucket below 30 wagers prints its count and no frequency — the point estimate of nine observations invites a reader to follow the shape of the line rather than the intervals around it.

**The model over-estimates more where it claims more.** The shortfall against model-implied is -4.4 pp in the +2% to +5% bucket (15,172 wagers) and -16.6 pp in the +20% and above bucket (34,919 wagers) — it widens by 12.2 pp across the range. That is **overconfidence**, which is what this column measures, and it is the winner's curse: the biggest claimed edges are the biggest over-estimates by construction. It is not by itself anti-predictiveness — that is a claim about realised return, and it is measured in its own right below.

**Realised return by claimed edge — the anti-predictive statistic.** The +2% to +5% bucket returned -5.4% over 15,172 settled wagers across 9,195 games, 95% interval [-7.9%, -2.9%], family-corrected [-10.0%, -0.9%] across 133 looks — demonstrated deficit; the +20% and above bucket returned -5.0% over 34,919 settled wagers across 13,759 games, 95% interval [-7.5%, -2.5%], family-corrected [-9.5%, -0.5%] across 133 looks — demonstrated deficit. The return does not fall across the range, so this run shows no anti-predictiveness in realised return. That is not evidence of skill — the disagreement coefficient is the test — and it does not contradict the overconfidence column above, which measures a different quantity.
The +5% to +10% bucket returned -5.1% over 21,513 settled wagers across 723 days, 95% interval [-7.5%, -2.7%], family-corrected [-9.4%, -0.8%] across 133 looks — demonstrated deficit.
**The wagers in the +2% to +5%, +5% to +10%, +20% and above claimed-edge buckets lost money, and the loss survives the correction.** The family-corrected intervals printed above lie entirely below zero, so each of those buckets is a **demonstrated deficit**: the model did worse than no edge in them, which is a stronger statement than failing to demonstrate one, and it is a statement about the money rather than about the size of the sample.

## The same fit without the de-vig

The de-vig is a choice, and a choice whose effect nobody can see is an assumption. This is the identical regression run on the **raw** implied probabilities, with the hold still in them.

**Population: every settled wager the model had an opinion on — the skill measure.**

**Under a constant overround the disagreement coefficient is algebraically invariant to a multiplicative de-vig, and this table is how that is checked rather than asserted.** The two designs span the same column space — `span{1, m, p}` either way, because `k·m` is a scalar multiple of `m` — so the fitted values are identical and only the intercept and the market coefficient move. A disagreement coefficient that *does* move between the two tables is therefore a fact about the overround **varying** across the population, not about the de-vig method being wrong, and it is worth understanding before either number is quoted.

| Term | Coefficient | 95% interval | Rows | Clusters |
|:---|---:|:---|---:|---:|
| intercept | -0.032 | -0.044 to -0.019 | 270,504 | 26,795 games |
| market_implied | +1.030 | +1.005 to +1.055 | 270,504 | 26,795 games |
| disagreement | +0.032 | -0.023 to +0.086 | 270,504 | 26,795 games |

The disagreement coefficient moved by **0.0003** between the de-vigged fit and this one. A move of zero is the constant-overround case; anything larger is the overround varying across the population, and the hold summary above says by how much it varies.

## Why raising the edge threshold cannot help

A card takes a wager when the claimed edge clears a threshold, and at a fixed price the claimed edge is monotone in the disagreement `d`. Under the fit above, the realised excess of a wager over the de-vigged price is `(a + (b_market − 1)·market) + b_disagreement·d`, whose derivative in `d` is exactly **b_disagreement**. Raising the threshold is a monotone filter that admits only larger `d`, so:

- `b_disagreement > 0` — a higher threshold selects better wagers, and that coefficient says how much better.
- `b_disagreement = 0` — a higher threshold selects **the same** wagers on average, at a smaller sample and a wider interval. It buys nothing and costs power.
- `b_disagreement < 0` — a higher threshold selects **worse** wagers. The natural response to a disappointing backtest is the one that makes it worse, and nothing in a return figure says so.

This run's pooled disagreement coefficient over **every settled wager the model had an opinion on** is +0.032 [-0.022, +0.086] over 270,504 wagers across 26,795 games — no demonstrated edge. The **realised return** column of the claimed-edge buckets above measures the same thing bucket by bucket; the algebra and the table are printed together because either alone is arguable. The realised-minus-model column beside it is overconfidence, which is a different quantity and does not support this section's conclusion on its own.

The threshold `price_backtest.BET_EDGE_THRESHOLD` declares in advance is 2%, and moving it after seeing a number is the defect this repository is arranged against. This section exists so that moving it is not even tempting.

## How this report is corrected, and what it cannot say

**Family correction: 133 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.81. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 scored wagers or 30 clusters there is no number**, only the words *not enough evidence*. Both floors were declared in advance. The cluster floor is there because a cluster-robust sandwich is downward biased with few clusters, and this repository's standing failure mode is an interval that is too narrow.

- It cannot say a model **would have made money**. That is `price_backtest.py`'s question, and a disagreement coefficient above zero is a necessary condition for an edge and not a sufficient one.
- It cannot say an edge is **reachable**. An edge living entirely in prices that vanished is reported as not reachable regardless of its size or its significance.
- It cannot rule a model **in**. It is a calibration-family instrument and shares the family's asymmetry: it can kill, and where a priced test exists the priced test decides.
- It cannot say a market is a play. **No market is allowlisted**, and an excluded market is never a pass, an avoid, or a no-value call.
