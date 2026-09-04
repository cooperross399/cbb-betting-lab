# NCAA Division I men's basketball — price backtest

Generated 2026-09-04T06:49:50Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**54,883 graded bets** from 176,970 graded wagers offered, across 11,997 games and 377 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | moneyline | always home | 3,983 | 381 | +2.4% | -1.2% to +6.0% | -3.3% to +8.1% | no demonstrated edge |
| high_major | moneyline | always away | 3,983 | 3,983 | -10.3% | -17.4% to -3.2% | -21.6% to +1.0% | no demonstrated edge |
| high_major | moneyline | always the favourite | 3,988 | 3,983 | -0.9% | -2.8% to +1.1% | -4.0% to +2.3% | no demonstrated edge |
| high_major | moneyline | always the underdog | 3,978 | 3,978 | -7.0% | -14.5% to +0.5% | -19.1% to +5.0% | no demonstrated edge |
| high_major | spread | always home | 8,719 | 3,993 | -3.1% | -6.2% to +0.0% | -8.1% to +1.9% | no demonstrated edge |
| high_major | spread | always away | 8,719 | 3,993 | -3.9% | -7.0% to -0.8% | -8.9% to +1.1% | no demonstrated edge |
| high_major | spread | always the favourite | 234 | 77 | -6.6% | -16.7% to +3.6% | -22.9% to +9.7% | no demonstrated edge |
| high_major | spread | always the underdog | 120 | 55 | — | — | — | not enough evidence (120 bets, below the 200 declared in advance) |
| high_major | total_points | always over | 11,334 | 381 | -3.7% | -7.0% to -0.4% | -9.0% to +1.6% | no demonstrated edge |
| high_major | total_points | always under | 11,334 | 381 | -4.2% | -7.5% to -0.9% | -9.4% to +1.1% | no demonstrated edge |
| high_major | total_points | always the favourite | 16,151 | 3,993 | -4.2% | -5.1% to -3.2% | -5.6% to -2.7% | demonstrated deficit |
| high_major | total_points | always the underdog | 6,517 | 3,668 | -3.3% | -5.6% to -1.0% | -7.0% to +0.4% | no demonstrated edge |
| mid_major | moneyline | always home | 6,050 | 391 | +2.0% | -0.9% to +4.8% | -2.7% to +6.6% | no demonstrated edge |
| mid_major | moneyline | always away | 6,050 | 391 | -8.4% | -12.8% to -4.0% | -15.5% to -1.3% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 6,062 | 391 | -2.0% | -3.7% to -0.2% | -4.7% to +0.8% | no demonstrated edge |
| mid_major | moneyline | always the underdog | 6,038 | 391 | -4.5% | -9.8% to +0.7% | -12.9% to +3.9% | no demonstrated edge |
| mid_major | spread | always home | 13,542 | 391 | -3.0% | -5.6% to -0.3% | -7.3% to +1.3% | no demonstrated edge |
| mid_major | spread | always away | 13,542 | 391 | -4.0% | -6.7% to -1.3% | -8.3% to +0.3% | no demonstrated edge |
| mid_major | spread | always the favourite | 493 | 122 | -4.8% | -11.4% to +1.7% | -15.4% to +5.7% | no demonstrated edge |
| mid_major | spread | always the underdog | 229 | 93 | -4.9% | -19.2% to +9.5% | -27.9% to +18.2% | no demonstrated edge |
| mid_major | total_points | always over | 17,595 | 391 | -2.4% | -5.1% to +0.3% | -6.8% to +1.9% | no demonstrated edge |
| mid_major | total_points | always under | 17,595 | 391 | -5.5% | -8.2% to -2.8% | -9.8% to -1.1% | demonstrated deficit |
| mid_major | total_points | always the favourite | 25,073 | 6,052 | -3.6% | -4.4% to -2.9% | -4.8% to -2.5% | demonstrated deficit |
| mid_major | total_points | always the underdog | 10,117 | 5,559 | -4.7% | -6.5% to -2.9% | -7.6% to -1.8% | demonstrated deficit |
| low_major | moneyline | always home | 4,471 | 345 | -0.8% | -4.4% to +2.8% | -6.6% to +5.0% | no demonstrated edge |
| low_major | moneyline | always away | 4,471 | 4,471 | -6.4% | -10.6% to -2.1% | -13.1% to +0.4% | no demonstrated edge |
| low_major | moneyline | always the favourite | 4,486 | 4,471 | -1.5% | -3.5% to +0.5% | -4.7% to +1.7% | no demonstrated edge |
| low_major | moneyline | always the underdog | 4,456 | 345 | -5.6% | -10.8% to -0.5% | -13.9% to +2.6% | no demonstrated edge |
| low_major | spread | always home | 9,941 | 345 | -3.0% | -6.1% to +0.1% | -8.0% to +2.0% | no demonstrated edge |
| low_major | spread | always away | 9,941 | 345 | -3.9% | -7.1% to -0.8% | -9.0% to +1.1% | no demonstrated edge |
| low_major | spread | always the favourite | 473 | 174 | -7.2% | -14.0% to -0.3% | -18.1% to +3.8% | no demonstrated edge |
| low_major | spread | always the underdog | 219 | 121 | +3.6% | -11.5% to +18.8% | -20.7% to +27.9% | no demonstrated edge |
| low_major | total_points | always over | 12,836 | 345 | +0.0% | -3.1% to +3.2% | -5.0% to +5.1% | no demonstrated edge |
| low_major | total_points | always under | 12,836 | 345 | -7.8% | -10.9% to -4.6% | -12.8% to -2.7% | demonstrated deficit |
| low_major | total_points | always the favourite | 18,268 | 4,472 | -4.2% | -5.0% to -3.3% | -5.5% to -2.8% | demonstrated deficit |
| low_major | total_points | always the underdog | 7,404 | 4,122 | -3.1% | -5.3% to -1.0% | -6.6% to +0.3% | no demonstrated edge |
| unplaced | moneyline | always home | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. **6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention.

| Tier | Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | moneyline | 2,848 | 2,847 | -1.0% | -8.8% to +6.7% | -13.5% to +11.4% | no demonstrated edge |
| high_major | spread | 6,062 | 2,914 | -0.1% | -3.8% to +3.6% | -6.0% to +5.8% | no demonstrated edge |
| high_major | total_points | 5,611 | 329 | -3.1% | -7.3% to +1.1% | -9.9% to +3.7% | no demonstrated edge |
| mid_major | moneyline | 4,337 | 353 | -5.9% | -11.0% to -0.9% | -14.1% to +2.2% | no demonstrated edge |
| mid_major | spread | 8,944 | 350 | -1.9% | -5.1% to +1.3% | -7.0% to +3.2% | no demonstrated edge |
| mid_major | total_points | 9,166 | 3,756 | +0.3% | -3.0% to +3.6% | -5.0% to +5.6% | no demonstrated edge |
| low_major | moneyline | 3,450 | 301 | -7.6% | -13.8% to -1.4% | -17.6% to +2.3% | no demonstrated edge |
| low_major | spread | 6,900 | 301 | -0.2% | -3.7% to +3.2% | -5.8% to +5.3% | no demonstrated edge |
| low_major | total_points | 7,559 | 3,119 | -2.5% | -6.1% to +1.1% | -8.3% to +3.3% | no demonstrated edge |
| unplaced | moneyline | 1 | 1 | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 14,521 | 3,128 | -1.4% | -4.4% to +1.5% | -6.2% to +3.3% | no demonstrated edge |
| mid_major | 22,447 | 354 | -1.8% | -4.1% to +0.5% | -5.5% to +1.9% | no demonstrated edge |
| low_major | 17,909 | 308 | -2.6% | -5.3% to +0.0% | -6.9% to +1.6% | no demonstrated edge |
| unplaced | 6 | 2 | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 10,636 | 376 | -5.2% | -8.9% to -1.4% | -11.2% to +0.8% | no demonstrated edge |
| spread | 21,909 | 375 | -0.9% | -2.9% to +1.1% | -4.1% to +2.3% | no demonstrated edge |
| total_points | 22,338 | 9,235 | -1.5% | -3.6% to +0.6% | -4.9% to +1.9% | no demonstrated edge |
| every market | 54,883 | 377 | -2.0% | -3.5% to -0.5% | -4.4% to +0.4% | no demonstrated edge |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 14,521 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.1%), **2** (6.0%), **4** (5.9%), **8** (5.4%), **7** (5.2%), **6** (5.2%), **9** (4.9%), **10** (4.7%), **1** (4.6%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 82.6% of 54,354 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 758 | 15.0% [12.7%, 17.8%] | +8.3 pp | 269 | 0.7% [0.2%, 2.7%] | -6.5 pp |
| 10%–20% | 3,150 | 27.5% [26.0%, 29.1%] | +11.6 pp | 1,026 | 7.3% [5.9%, 9.1%] | -8.2 pp |
| 20%–30% | 7,348 | 38.1% [37.0%, 39.3%] | +12.5 pp | 1,299 | 13.9% [12.1%, 15.8%] | -11.1 pp |
| 30%–40% | 19,545 | 45.9% [45.2%, 46.6%] | +10.0 pp | 1,553 | 24.0% [21.9%, 26.1%] | -10.9 pp |
| 40%–50% | 46,677 | 49.7% [49.2%, 50.1%] | +4.2 pp | 1,570 | 34.3% [32.0%, 36.7%] | -10.9 pp |
| 50%–60% | 43,600 | 50.5% [50.0%, 50.9%] | -4.0 pp | 26,656 | 50.0% [49.4%, 50.6%] | -6.0 pp |
| 60%–70% | 16,985 | 54.6% [53.9%, 55.4%] | -9.5 pp | 15,038 | 52.2% [51.4%, 53.0%] | -11.8 pp |
| 70%–80% | 6,669 | 62.8% [61.6%, 64.0%] | -11.5 pp | 4,996 | 55.6% [54.2%, 57.0%] | -18.5 pp |
| 80%–90% | 2,948 | 73.6% [72.0%, 75.2%] | -10.5 pp | 1,667 | 59.9% [57.5%, 62.2%] | -24.0 pp |
| 90%–100% | 713 | 86.7% [84.0%, 89.0%] | -6.5 pp | 280 | 70.0% [64.4%, 75.1%] | -23.1 pp |

- **Overall: 0.5 pp underconfident** over 148,393 graded rows in 10 usable bucket(s).
- **Selected: 9.9 pp overconfident** over 54,354 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 529 push. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
