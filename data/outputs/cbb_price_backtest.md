# NCAA Division I men's basketball — price backtest

Generated 2026-09-04T04:09:30Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**86,351 graded bets** from 278,246 graded wagers offered, across 16,625 games and 513 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | moneyline | always home | 4,837 | 513 | +3.2% | +0.1% to +6.3% | -1.8% to +8.2% | no demonstrated edge |
| high_major | moneyline | always away | 4,837 | 4,837 | -10.8% | -17.3% to -4.2% | -21.3% to -0.3% | demonstrated deficit |
| high_major | moneyline | always the favourite | 4,844 | 4,837 | -1.2% | -3.0% to +0.5% | -4.1% to +1.6% | no demonstrated edge |
| high_major | moneyline | always the underdog | 4,830 | 4,830 | -6.3% | -13.3% to +0.6% | -17.4% to +4.7% | no demonstrated edge |
| high_major | spread | always home | 11,071 | 513 | -1.8% | -4.6% to +1.1% | -6.4% to +2.8% | no demonstrated edge |
| high_major | spread | always away | 11,071 | 513 | -5.2% | -8.0% to -2.3% | -9.7% to -0.6% | demonstrated deficit |
| high_major | spread | always the favourite | 332 | 95 | -3.5% | -12.4% to +5.5% | -17.8% to +10.9% | no demonstrated edge |
| high_major | spread | always the underdog | 170 | 71 | — | — | — | not enough evidence (170 bets, below the 200 declared in advance) |
| high_major | team_total | always over | 1,995 | 735 | +3.1% | -2.7% to +8.8% | -6.2% to +12.3% | no demonstrated edge |
| high_major | team_total | always under | 1,995 | 735 | -13.9% | -19.8% to -8.0% | -23.4% to -4.5% | demonstrated deficit |
| high_major | team_total | always the favourite | 2,297 | 722 | -6.7% | -9.4% to -4.0% | -11.1% to -2.4% | demonstrated deficit |
| high_major | team_total | always the underdog | 1,529 | 689 | -3.5% | -7.9% to +0.9% | -10.5% to +3.6% | no demonstrated edge |
| high_major | total_points | always over | 14,269 | 513 | -2.1% | -5.0% to +0.7% | -6.7% to +2.4% | no demonstrated edge |
| high_major | total_points | always under | 14,269 | 513 | -5.6% | -8.5% to -2.8% | -10.2% to -1.1% | demonstrated deficit |
| high_major | total_points | always the favourite | 20,279 | 4,856 | -4.0% | -4.8% to -3.2% | -5.3% to -2.7% | demonstrated deficit |
| high_major | total_points | always the underdog | 8,259 | 4,497 | -3.6% | -5.6% to -1.6% | -6.9% to -0.4% | demonstrated deficit |
| mid_major | moneyline | always home | 9,170 | 536 | +1.4% | -0.8% to +3.7% | -2.2% to +5.1% | no demonstrated edge |
| mid_major | moneyline | always away | 9,170 | 536 | -7.6% | -11.3% to -3.9% | -13.5% to -1.7% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 9,188 | 536 | -1.8% | -3.2% to -0.5% | -4.0% to +0.3% | no demonstrated edge |
| mid_major | moneyline | always the underdog | 9,152 | 536 | -4.3% | -8.6% to -0.1% | -11.1% to +2.5% | no demonstrated edge |
| mid_major | spread | always home | 21,764 | 536 | -2.3% | -4.3% to -0.2% | -5.6% to +1.1% | no demonstrated edge |
| mid_major | spread | always away | 21,764 | 536 | -4.6% | -6.7% to -2.5% | -7.9% to -1.3% | demonstrated deficit |
| mid_major | spread | always the favourite | 839 | 181 | -5.4% | -10.5% to -0.3% | -13.6% to +2.8% | no demonstrated edge |
| mid_major | spread | always the underdog | 403 | 146 | -2.1% | -13.0% to +8.8% | -19.6% to +15.4% | no demonstrated edge |
| mid_major | team_total | always over | 7,161 | 2,761 | -2.8% | -5.7% to +0.1% | -7.5% to +1.8% | no demonstrated edge |
| mid_major | team_total | always under | 7,161 | 2,761 | -8.2% | -11.1% to -5.2% | -12.9% to -3.4% | demonstrated deficit |
| mid_major | team_total | always the favourite | 8,185 | 138 | -4.2% | -5.9% to -2.6% | -6.9% to -1.6% | demonstrated deficit |
| mid_major | team_total | always the underdog | 5,533 | 137 | -7.4% | -10.1% to -4.7% | -11.7% to -3.1% | demonstrated deficit |
| mid_major | total_points | always over | 28,296 | 536 | -2.4% | -4.5% to -0.3% | -5.7% to +0.9% | no demonstrated edge |
| mid_major | total_points | always under | 28,296 | 536 | -5.4% | -7.5% to -3.3% | -8.7% to -2.1% | demonstrated deficit |
| mid_major | total_points | always the favourite | 40,215 | 9,183 | -3.8% | -4.4% to -3.3% | -4.7% to -2.9% | demonstrated deficit |
| mid_major | total_points | always the underdog | 16,377 | 8,536 | -4.0% | -5.4% to -2.6% | -6.3% to -1.8% | demonstrated deficit |
| low_major | moneyline | always home | 5,930 | 466 | -2.3% | -5.2% to +0.6% | -7.0% to +2.4% | no demonstrated edge |
| low_major | moneyline | always away | 5,930 | 5,930 | -4.3% | -8.0% to -0.6% | -10.2% to +1.7% | no demonstrated edge |
| low_major | moneyline | always the favourite | 5,954 | 5,930 | -1.4% | -3.1% to +0.4% | -4.2% to +1.4% | no demonstrated edge |
| low_major | moneyline | always the underdog | 5,906 | 466 | -5.2% | -9.6% to -0.8% | -12.3% to +1.9% | no demonstrated edge |
| low_major | spread | always home | 13,773 | 466 | -5.0% | -7.6% to -2.3% | -9.2% to -0.7% | demonstrated deficit |
| low_major | spread | always away | 13,773 | 466 | -1.9% | -4.5% to +0.8% | -6.1% to +2.4% | no demonstrated edge |
| low_major | spread | always the favourite | 669 | 221 | -5.6% | -11.3% to +0.1% | -14.7% to +3.5% | no demonstrated edge |
| low_major | spread | always the underdog | 307 | 160 | +0.3% | -12.5% to +13.0% | -20.1% to +20.7% | no demonstrated edge |
| low_major | team_total | always over | 3,093 | 1,312 | -4.4% | -8.6% to -0.3% | -11.1% to +2.2% | no demonstrated edge |
| low_major | team_total | always under | 3,093 | 1,312 | -6.5% | -10.6% to -2.3% | -13.1% to +0.2% | no demonstrated edge |
| low_major | team_total | always the favourite | 3,565 | 115 | -6.2% | -8.7% to -3.7% | -10.3% to -2.1% | demonstrated deficit |
| low_major | team_total | always the underdog | 2,369 | 114 | -4.4% | -8.4% to -0.4% | -10.8% to +2.0% | no demonstrated edge |
| low_major | total_points | always over | 17,750 | 466 | -1.9% | -4.6% to +0.8% | -6.3% to +2.4% | no demonstrated edge |
| low_major | total_points | always under | 17,750 | 466 | -5.8% | -8.5% to -3.1% | -10.2% to -1.5% | demonstrated deficit |
| low_major | total_points | always the favourite | 25,302 | 5,931 | -4.1% | -4.8% to -3.4% | -5.2% to -2.9% | demonstrated deficit |
| low_major | total_points | always the underdog | 10,198 | 5,489 | -3.4% | -5.2% to -1.6% | -6.3% to -0.6% | demonstrated deficit |
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
| high_major | moneyline | 3,466 | 458 | -0.6% | -8.1% to +6.9% | -12.6% to +11.4% | no demonstrated edge |
| high_major | spread | 7,645 | 457 | -1.1% | -4.5% to +2.2% | -6.5% to +4.3% | no demonstrated edge |
| high_major | team_total | 1,210 | 622 | -6.1% | -12.2% to -0.0% | -15.9% to +3.7% | no demonstrated edge |
| high_major | total_points | 7,244 | 441 | -2.9% | -6.7% to +0.9% | -9.0% to +3.2% | no demonstrated edge |
| mid_major | moneyline | 6,616 | 483 | -4.4% | -8.6% to -0.2% | -11.1% to +2.3% | no demonstrated edge |
| mid_major | spread | 14,422 | 480 | -1.8% | -4.4% to +0.9% | -6.1% to +2.6% | no demonstrated edge |
| mid_major | team_total | 4,236 | 130 | -4.8% | -8.1% to -1.5% | -10.1% to +0.6% | no demonstrated edge |
| mid_major | total_points | 14,905 | 476 | +0.0% | -2.7% to +2.8% | -4.4% to +4.4% | no demonstrated edge |
| low_major | moneyline | 4,584 | 409 | -7.7% | -13.0% to -2.4% | -16.2% to +0.7% | no demonstrated edge |
| low_major | spread | 9,512 | 409 | -0.2% | -3.2% to +2.8% | -5.1% to +4.6% | no demonstrated edge |
| low_major | team_total | 1,973 | 107 | -5.1% | -10.1% to -0.1% | -13.1% to +2.9% | no demonstrated edge |
| low_major | total_points | 10,532 | 4,206 | -5.2% | -8.3% to -2.1% | -10.2% to -0.2% | demonstrated deficit |
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
| high_major | 19,565 | 462 | -2.0% | -4.7% to +0.7% | -6.3% to +2.3% | no demonstrated edge |
| mid_major | 40,179 | 486 | -1.9% | -3.8% to +0.1% | -5.0% to +1.3% | no demonstrated edge |
| low_major | 26,601 | 418 | -3.9% | -6.1% to -1.6% | -7.4% to -0.3% | demonstrated deficit |
| unplaced | 6 | 2 | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 14,667 | 512 | -4.5% | -7.7% to -1.4% | -9.6% to +0.6% | no demonstrated edge |
| spread | 31,582 | 511 | -1.1% | -2.8% to +0.6% | -3.9% to +1.6% | no demonstrated edge |
| team_total | 7,419 | 134 | -5.1% | -7.6% to -2.6% | -9.1% to -1.0% | demonstrated deficit |
| total_points | 32,683 | 12,933 | -2.3% | -4.1% to -0.6% | -5.2% to +0.5% | no demonstrated edge |
| every market | 86,351 | 513 | -2.5% | -3.8% to -1.2% | -4.6% to -0.4% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 19,974 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.0%), **2** (6.0%), **4** (5.8%), **8** (5.4%), **7** (5.3%), **6** (5.2%), **9** (4.9%), **10** (4.8%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 83.8% of 85,556 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 1,056 | 15.2% [13.1%, 17.4%] | +8.3 pp | 411 | 2.2% [1.2%, 4.1%] | -5.2 pp |
| 10%–20% | 4,357 | 27.4% [26.1%, 28.8%] | +11.6 pp | 1,452 | 7.4% [6.1%, 8.8%] | -8.1 pp |
| 20%–30% | 10,553 | 39.1% [38.2%, 40.1%] | +13.4 pp | 1,803 | 14.8% [13.2%, 16.5%] | -10.2 pp |
| 30%–40% | 30,674 | 46.6% [46.0%, 47.1%] | +10.6 pp | 2,170 | 24.6% [22.8%, 26.4%] | -10.3 pp |
| 40%–50% | 76,153 | 49.7% [49.3%, 50.0%] | +4.2 pp | 2,252 | 34.1% [32.2%, 36.1%] | -11.1 pp |
| 50%–60% | 71,479 | 50.4% [50.0%, 50.8%] | -4.0 pp | 43,412 | 49.9% [49.4%, 50.4%] | -6.1 pp |
| 60%–70% | 26,910 | 53.8% [53.2%, 54.4%] | -10.3 pp | 24,174 | 51.7% [51.0%, 52.3%] | -12.3 pp |
| 70%–80% | 9,601 | 61.8% [60.8%, 62.8%] | -12.5 pp | 7,264 | 54.7% [53.6%, 55.9%] | -19.3 pp |
| 80%–90% | 4,079 | 73.8% [72.4%, 75.1%] | -10.4 pp | 2,256 | 59.6% [57.5%, 61.6%] | -24.3 pp |
| 90%–100% | 997 | 86.6% [84.3%, 88.5%] | -6.6 pp | 362 | 68.8% [63.8%, 73.3%] | -24.2 pp |

- **Overall: 0.5 pp underconfident** over 235,859 graded rows in 10 usable bucket(s).
- **Selected: 9.9 pp overconfident** over 85,556 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 795 push. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
