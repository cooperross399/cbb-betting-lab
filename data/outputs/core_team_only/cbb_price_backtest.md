# NCAA Division I men's basketball — price backtest

Generated 2026-09-05T14:13:25Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**159,354 graded bets** from 505,287 graded wagers offered, across 26,582 games and 791 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | moneyline | always home | 7,687 | 797 days | +2.4% | -0.1% to +4.9% | -1.6% to +6.4% | no demonstrated edge |
| high_major | moneyline | always away | 7,687 | 7,687 games | -13.8% | -18.6% to -8.9% | -21.5% to -6.0% | demonstrated deficit |
| high_major | moneyline | always the favourite | 7,699 | 797 days | -1.5% | -2.9% to -0.0% | -3.8% to +0.8% | no demonstrated edge |
| high_major | moneyline | always the underdog | 7,675 | 797 days | -9.9% | -15.3% to -4.6% | -18.5% to -1.3% | demonstrated deficit |
| high_major | spread | always home | 18,780 | 7,773 games | -2.8% | -5.0% to -0.6% | -6.4% to +0.7% | no demonstrated edge |
| high_major | spread | always away | 18,780 | 7,773 games | -4.0% | -6.3% to -1.8% | -7.6% to -0.4% | demonstrated deficit |
| high_major | spread | always the favourite | 587 | 184 games | -1.2% | -8.4% to +5.9% | -12.7% to +10.3% | no demonstrated edge |
| high_major | spread | always the underdog | 323 | 140 games | -9.9% | -23.4% to +3.5% | -31.5% to +11.6% | no demonstrated edge |
| high_major | team_total | always over | 10,756 | 406 days | -2.9% | -5.7% to -0.1% | -7.4% to +1.6% | no demonstrated edge |
| high_major | team_total | always under | 10,757 | 406 days | -7.8% | -10.6% to -4.9% | -12.3% to -3.2% | demonstrated deficit |
| high_major | team_total | always the favourite | 11,627 | 3,585 games | -4.7% | -5.9% to -3.5% | -6.7% to -2.8% | demonstrated deficit |
| high_major | team_total | always the underdog | 8,901 | 3,522 games | -6.1% | -7.8% to -4.4% | -8.8% to -3.4% | demonstrated deficit |
| high_major | total_points | always over | 23,252 | 797 days | -2.7% | -5.0% to -0.4% | -6.3% to +1.0% | no demonstrated edge |
| high_major | total_points | always under | 23,252 | 797 days | -5.0% | -7.3% to -2.7% | -8.7% to -1.3% | demonstrated deficit |
| high_major | total_points | always the favourite | 32,227 | 7,773 games | -3.8% | -4.4% to -3.2% | -4.8% to -2.8% | demonstrated deficit |
| high_major | total_points | always the underdog | 14,277 | 7,270 games | -3.9% | -5.4% to -2.4% | -6.3% to -1.5% | demonstrated deficit |
| mid_major | moneyline | always home | 14,064 | 815 days | -0.0% | -1.8% to +1.8% | -2.9% to +2.9% | no demonstrated edge |
| mid_major | moneyline | always away | 14,064 | 815 days | -6.8% | -9.8% to -3.8% | -11.6% to -1.9% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 14,091 | 815 days | -2.0% | -3.1% to -0.9% | -3.8% to -0.3% | demonstrated deficit |
| mid_major | moneyline | always the underdog | 14,037 | 815 days | -4.8% | -8.2% to -1.4% | -10.2% to +0.7% | no demonstrated edge |
| mid_major | spread | always home | 34,384 | 815 days | -3.6% | -5.2% to -1.9% | -6.2% to -0.9% | demonstrated deficit |
| mid_major | spread | always away | 34,384 | 815 days | -3.2% | -4.9% to -1.6% | -5.9% to -0.5% | demonstrated deficit |
| mid_major | spread | always the favourite | 1,591 | 472 games | -5.1% | -9.0% to -1.2% | -11.4% to +1.1% | no demonstrated edge |
| mid_major | spread | always the underdog | 867 | 372 games | -2.1% | -9.5% to +5.3% | -13.9% to +9.8% | no demonstrated edge |
| mid_major | team_total | always over | 22,392 | 7,669 games | -3.5% | -5.2% to -1.7% | -6.3% to -0.7% | demonstrated deficit |
| mid_major | team_total | always under | 22,392 | 417 days | -7.4% | -9.2% to -5.7% | -10.3% to -4.6% | demonstrated deficit |
| mid_major | team_total | always the favourite | 23,727 | 417 days | -3.9% | -4.8% to -3.0% | -5.4% to -2.5% | demonstrated deficit |
| mid_major | team_total | always the underdog | 18,373 | 415 days | -7.4% | -8.7% to -6.2% | -9.4% to -5.4% | demonstrated deficit |
| mid_major | total_points | always over | 43,265 | 815 days | -3.1% | -4.7% to -1.4% | -5.7% to -0.4% | demonstrated deficit |
| mid_major | total_points | always under | 43,265 | 815 days | -4.6% | -6.3% to -3.0% | -7.3% to -2.0% | demonstrated deficit |
| mid_major | total_points | always the favourite | 60,258 | 14,110 games | -3.8% | -4.3% to -3.3% | -4.5% to -3.1% | demonstrated deficit |
| mid_major | total_points | always the underdog | 26,272 | 13,256 games | -3.9% | -5.0% to -2.9% | -5.7% to -2.2% | demonstrated deficit |
| low_major | moneyline | always home | 9,785 | 718 days | -1.4% | -3.5% to +0.8% | -4.8% to +2.0% | no demonstrated edge |
| low_major | moneyline | always away | 9,785 | 9,785 games | -4.6% | -7.6% to -1.6% | -9.5% to +0.2% | no demonstrated edge |
| low_major | moneyline | always the favourite | 9,820 | 9,785 games | -1.9% | -3.3% to -0.5% | -4.1% to +0.3% | no demonstrated edge |
| low_major | moneyline | always the underdog | 9,750 | 718 days | -4.1% | -7.6% to -0.6% | -9.7% to +1.5% | no demonstrated edge |
| low_major | spread | always home | 23,392 | 718 days | -3.4% | -5.4% to -1.4% | -6.6% to -0.2% | demonstrated deficit |
| low_major | spread | always away | 23,392 | 718 days | -3.3% | -5.3% to -1.3% | -6.6% to -0.1% | demonstrated deficit |
| low_major | spread | always the favourite | 1,320 | 405 games | -7.5% | -11.8% to -3.2% | -14.4% to -0.6% | demonstrated deficit |
| low_major | spread | always the underdog | 720 | 318 games | +3.1% | -5.0% to +11.2% | -9.9% to +16.1% | no demonstrated edge |
| low_major | team_total | always over | 15,715 | 367 days | -3.8% | -6.0% to -1.5% | -7.4% to -0.1% | demonstrated deficit |
| low_major | team_total | always under | 15,715 | 367 days | -7.3% | -9.6% to -5.0% | -11.0% to -3.7% | demonstrated deficit |
| low_major | team_total | always the favourite | 15,867 | 367 days | -4.8% | -5.9% to -3.8% | -6.5% to -3.2% | demonstrated deficit |
| low_major | team_total | always the underdog | 12,851 | 366 days | -6.4% | -7.7% to -5.0% | -8.6% to -4.2% | demonstrated deficit |
| low_major | total_points | always over | 29,157 | 718 days | -2.4% | -4.4% to -0.3% | -5.7% to +0.9% | no demonstrated edge |
| low_major | total_points | always under | 29,157 | 718 days | -5.3% | -7.4% to -3.2% | -8.6% to -2.0% | demonstrated deficit |
| low_major | total_points | always the favourite | 40,713 | 9,787 games | -3.8% | -4.4% to -3.3% | -4.7% to -3.0% | demonstrated deficit |
| low_major | total_points | always the underdog | 17,601 | 9,132 games | -3.8% | -5.1% to -2.5% | -5.9% to -1.7% | demonstrated deficit |
| unplaced | moneyline | always home | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 games | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 games | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 games | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 games | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 games | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 games | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. **6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention.

| Tier | Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | moneyline | 5,510 | 712 days | -3.5% | -9.3% to +2.4% | -12.9% to +6.0% | no demonstrated edge |
| high_major | spread | 13,242 | 712 days | -1.7% | -4.4% to +0.9% | -5.9% to +2.5% | no demonstrated edge |
| high_major | team_total | 7,109 | 2,933 games | -2.8% | -5.5% to -0.2% | -7.1% to +1.4% | no demonstrated edge |
| high_major | total_points | 12,241 | 688 days | -3.3% | -6.4% to -0.3% | -8.2% to +1.5% | no demonstrated edge |
| mid_major | moneyline | 10,194 | 736 days | -4.5% | -7.9% to -1.1% | -10.0% to +1.0% | no demonstrated edge |
| mid_major | spread | 22,891 | 732 days | -1.5% | -3.6% to +0.6% | -4.9% to +1.9% | no demonstrated edge |
| mid_major | team_total | 13,478 | 384 days | -5.8% | -7.9% to -3.8% | -9.1% to -2.6% | demonstrated deficit |
| mid_major | total_points | 23,327 | 728 days | -2.3% | -4.5% to -0.2% | -5.9% to +1.2% | no demonstrated edge |
| low_major | moneyline | 7,561 | 632 days | -7.9% | -11.8% to -4.1% | -14.2% to -1.7% | demonstrated deficit |
| low_major | spread | 16,090 | 634 days | -0.1% | -2.4% to +2.3% | -3.8% to +3.7% | no demonstrated edge |
| low_major | team_total | 9,802 | 334 days | -4.1% | -6.7% to -1.5% | -8.3% to +0.1% | no demonstrated edge |
| low_major | total_points | 17,903 | 7,131 games | -5.2% | -7.5% to -2.8% | -9.0% to -1.3% | demonstrated deficit |
| unplaced | moneyline | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 games | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 38,102 | 718 days | -2.7% | -4.7% to -0.7% | -5.9% to +0.4% | no demonstrated edge |
| mid_major | 69,890 | 740 days | -3.1% | -4.6% to -1.5% | -5.5% to -0.6% | demonstrated deficit |
| low_major | 51,356 | 646 days | -3.8% | -5.5% to -2.1% | -6.5% to -1.0% | demonstrated deficit |
| unplaced | 6 | 2 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 23,266 | 789 days | -5.4% | -7.9% to -2.8% | -9.5% to -1.3% | demonstrated deficit |
| spread | 52,226 | 789 days | -1.1% | -2.4% to +0.2% | -3.2% to +1.0% | no demonstrated edge |
| team_total | 30,389 | 412 days | -4.6% | -6.0% to -3.1% | -6.9% to -2.2% | demonstrated deficit |
| total_points | 53,473 | 21,076 games | -3.5% | -4.9% to -2.1% | -5.7% to -1.3% | demonstrated deficit |
| every market | 159,354 | 791 days | -3.2% | -4.2% to -2.2% | -4.8% to -1.6% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 31,674 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.1%), **4** (6.0%), **2** (5.8%), **8** (5.3%), **7** (5.2%), **6** (5.2%), **9** (4.9%), **10** (4.7%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 85.7% of 158,046 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 2,196 | 17.4% [15.9%, 19.0%] | +10.8 pp | 761 | 2.0% [1.2%, 3.2%] | -5.2 pp |
| 10%–20% | 7,464 | 28.7% [27.7%, 29.8%] | +13.0 pp | 2,282 | 7.4% [6.4%, 8.5%] | -8.0 pp |
| 20%–30% | 18,757 | 40.4% [39.7%, 41.1%] | +14.6 pp | 2,926 | 14.9% [13.6%, 16.2%] | -10.1 pp |
| 30%–40% | 57,925 | 47.3% [46.9%, 47.7%] | +11.3 pp | 3,373 | 23.8% [22.4%, 25.3%] | -11.2 pp |
| 40%–50% | 137,322 | 49.8% [49.6%, 50.1%] | +4.4 pp | 3,563 | 34.8% [33.3%, 36.4%] | -10.4 pp |
| 50%–60% | 130,361 | 50.2% [49.9%, 50.5%] | -4.3 pp | 78,960 | 49.6% [49.3%, 50.0%] | -6.4 pp |
| 60%–70% | 51,931 | 53.0% [52.6%, 53.4%] | -11.1 pp | 47,621 | 51.1% [50.7%, 51.6%] | -12.8 pp |
| 70%–80% | 17,234 | 60.2% [59.5%, 61.0%] | -14.0 pp | 13,474 | 53.8% [52.9%, 54.6%] | -20.3 pp |
| 80%–90% | 7,046 | 72.4% [71.4%, 73.5%] | -11.9 pp | 4,182 | 59.6% [58.1%, 61.0%] | -24.4 pp |
| 90%–100% | 2,091 | 84.0% [82.4%, 85.5%] | -9.3 pp | 904 | 66.6% [63.5%, 69.6%] | -26.7 pp |

- **Overall: 0.4 pp underconfident** over 432,327 graded rows in 10 usable bucket(s).
- **Selected: 10.4 pp overconfident** over 158,046 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 1,308 push. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
