# NCAA Division I men's basketball — price backtest

Generated 2026-09-17T09:59:06Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**145,994 graded bets** from 465,378 graded wagers offered, across 26,582 games and 791 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 130 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.81. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Clusters | ROI | 95% interval | Family-corrected | Could detect | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|:---|
| high_major | moneyline | always home | 6,213 | 6,213 games | -0.1% | -2.2% to +2.0% | -4.0% to +3.8% | ±3.9% | no demonstrated edge |
| high_major | moneyline | always away | 6,213 | 695 days | -19.5% | -24.8% to -14.1% | -29.2% to -9.7% | ±9.7% | demonstrated deficit |
| high_major | moneyline | always the favourite | 6,219 | 695 days | +0.2% | -1.3% to +1.8% | -2.5% to +3.0% | ±2.8% | no demonstrated edge |
| high_major | moneyline | always the underdog | 6,207 | 695 days | -19.8% | -25.6% to -14.1% | -30.2% to -9.4% | ±10.4% | demonstrated deficit |
| high_major | spread | always home | 15,267 | 6,299 games | -3.6% | -6.0% to -1.1% | -8.0% to +0.9% | ±4.5% | no demonstrated edge |
| high_major | spread | always away | 15,267 | 6,299 games | -3.3% | -5.8% to -0.8% | -7.8% to +1.2% | ±4.5% | no demonstrated edge |
| high_major | spread | always the favourite | 430 | 135 games | +0.2% | -8.2% to +8.7% | -15.1% to +15.6% | ±15.3% | no demonstrated edge |
| high_major | spread | always the underdog | 236 | 104 games | -13.4% | -29.2% to +2.4% | -42.0% to +15.2% | ±28.6% | no demonstrated edge |
| high_major | team_total | always over | 8,526 | 353 days | -3.4% | -6.6% to -0.2% | -9.2% to +2.3% | ±5.8% | no demonstrated edge |
| high_major | team_total | always under | 8,526 | 353 days | -7.3% | -10.5% to -4.1% | -13.1% to -1.5% | ±5.8% | demonstrated deficit |
| high_major | team_total | always the favourite | 9,091 | 351 days | -4.8% | -6.2% to -3.4% | -7.3% to -2.2% | ±2.6% | demonstrated deficit |
| high_major | team_total | always the underdog | 7,177 | 2,841 games | -6.1% | -7.9% to -4.2% | -9.5% to -2.7% | ±3.4% | demonstrated deficit |
| high_major | total_points | always over | 23,252 | 797 days | -2.7% | -5.0% to -0.4% | -6.8% to +1.5% | ±4.2% | no demonstrated edge |
| high_major | total_points | always under | 23,252 | 797 days | -5.0% | -7.3% to -2.7% | -9.2% to -0.8% | ±4.2% | demonstrated deficit |
| high_major | total_points | always the favourite | 32,227 | 7,773 games | -3.8% | -4.4% to -3.2% | -5.0% to -2.6% | ±1.2% | demonstrated deficit |
| high_major | total_points | always the underdog | 14,277 | 7,270 games | -3.9% | -5.4% to -2.4% | -6.6% to -1.2% | ±2.7% | demonstrated deficit |
| mid_major | moneyline | always home | 12,309 | 734 days | -1.2% | -3.1% to +0.6% | -4.5% to +2.1% | ±3.3% | no demonstrated edge |
| mid_major | moneyline | always away | 12,309 | 734 days | -8.9% | -12.1% to -5.7% | -14.7% to -3.1% | ±5.8% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 12,334 | 734 days | -0.7% | -1.8% to +0.4% | -2.8% to +1.3% | ±2.1% | no demonstrated edge |
| mid_major | moneyline | always the underdog | 12,284 | 734 days | -9.4% | -13.0% to -5.9% | -15.9% to -3.0% | ±6.4% | demonstrated deficit |
| mid_major | spread | always home | 30,048 | 734 days | -3.4% | -5.3% to -1.6% | -6.7% to -0.1% | ±3.3% | demonstrated deficit |
| mid_major | spread | always away | 30,048 | 734 days | -3.3% | -5.2% to -1.5% | -6.6% to -0.0% | ±3.3% | demonstrated deficit |
| mid_major | spread | always the favourite | 1,322 | 392 games | -6.9% | -11.2% to -2.6% | -14.7% to +0.9% | ±7.8% | no demonstrated edge |
| mid_major | spread | always the underdog | 728 | 309 games | +1.0% | -7.1% to +9.0% | -13.7% to +15.6% | ±14.6% | no demonstrated edge |
| mid_major | team_total | always over | 19,741 | 6,748 games | -2.9% | -4.8% to -1.0% | -6.3% to +0.5% | ±3.4% | no demonstrated edge |
| mid_major | team_total | always under | 19,741 | 6,748 games | -8.1% | -10.0% to -6.2% | -11.5% to -4.7% | ±3.4% | demonstrated deficit |
| mid_major | team_total | always the favourite | 20,855 | 380 days | -3.9% | -4.8% to -2.9% | -5.6% to -2.2% | ±1.7% | demonstrated deficit |
| mid_major | team_total | always the underdog | 16,263 | 379 days | -7.6% | -8.9% to -6.3% | -10.0% to -5.3% | ±2.4% | demonstrated deficit |
| mid_major | total_points | always over | 43,265 | 815 days | -3.1% | -4.7% to -1.4% | -6.1% to -0.1% | ±3.0% | demonstrated deficit |
| mid_major | total_points | always under | 43,265 | 815 days | -4.6% | -6.3% to -3.0% | -7.6% to -1.6% | ±3.0% | demonstrated deficit |
| mid_major | total_points | always the favourite | 60,258 | 14,110 games | -3.8% | -4.3% to -3.3% | -4.6% to -3.0% | ±0.8% | demonstrated deficit |
| mid_major | total_points | always the underdog | 26,272 | 13,256 games | -3.9% | -5.0% to -2.9% | -5.9% to -2.0% | ±2.0% | demonstrated deficit |
| low_major | moneyline | always home | 8,952 | 676 days | -2.2% | -4.3% to -0.0% | -6.0% to +1.7% | ±3.9% | no demonstrated edge |
| low_major | moneyline | always away | 8,952 | 676 days | -6.5% | -9.5% to -3.5% | -11.9% to -1.1% | ±5.4% | demonstrated deficit |
| low_major | moneyline | always the favourite | 8,985 | 8,952 games | -1.5% | -2.9% to -0.0% | -4.0% to +1.1% | ±2.6% | no demonstrated edge |
| low_major | moneyline | always the underdog | 8,919 | 676 days | -7.2% | -10.6% to -3.9% | -13.3% to -1.1% | ±6.1% | demonstrated deficit |
| low_major | spread | always home | 21,393 | 676 days | -3.0% | -5.1% to -0.9% | -6.8% to +0.8% | ±3.8% | no demonstrated edge |
| low_major | spread | always away | 21,393 | 676 days | -3.8% | -5.9% to -1.7% | -7.6% to +0.0% | ±3.8% | no demonstrated edge |
| low_major | spread | always the favourite | 1,220 | 374 games | -7.4% | -11.9% to -2.9% | -15.5% to +0.7% | ±8.1% | no demonstrated edge |
| low_major | spread | always the underdog | 660 | 293 games | +3.1% | -5.4% to +11.6% | -12.3% to +18.5% | ±15.4% | no demonstrated edge |
| low_major | team_total | always over | 14,552 | 346 days | -3.3% | -5.8% to -0.9% | -7.7% to +1.1% | ±4.4% | no demonstrated edge |
| low_major | team_total | always under | 14,552 | 346 days | -7.8% | -10.2% to -5.4% | -12.2% to -3.5% | ±4.3% | demonstrated deficit |
| low_major | team_total | always the favourite | 14,639 | 346 days | -4.9% | -6.0% to -3.8% | -6.9% to -3.0% | ±2.0% | demonstrated deficit |
| low_major | team_total | always the underdog | 11,921 | 4,527 games | -6.3% | -7.7% to -4.9% | -8.9% to -3.8% | ±2.5% | demonstrated deficit |
| low_major | total_points | always over | 29,157 | 718 days | -2.4% | -4.4% to -0.3% | -6.1% to +1.4% | ±3.7% | no demonstrated edge |
| low_major | total_points | always under | 29,157 | 718 days | -5.3% | -7.4% to -3.2% | -9.0% to -1.5% | ±3.7% | demonstrated deficit |
| low_major | total_points | always the favourite | 40,713 | 9,787 games | -3.8% | -4.4% to -3.3% | -4.8% to -2.8% | ±1.0% | demonstrated deficit |
| low_major | total_points | always the underdog | 17,601 | 9,132 games | -3.8% | -5.1% to -2.5% | -6.2% to -1.4% | ±2.4% | demonstrated deficit |
| unplaced | moneyline | always home | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 games | — | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 games | — | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 games | — | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 games | — | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 games | — | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 games | — | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. The three tiers are three different distributions, and this lab exists because the third is plausibly priced with less attention.

The tier of a team is **measured, not assigned by conference**: `conferences.tier_table` places it by non-conference margin over the declared lookback, so the count in each tier moves with the data. `data/outputs/cbb_ratings_fit.json` carries the shape the fit behind this record placed.

| Tier | Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Could detect | Verdict |
|:---|:---|---:|---:|---:|:---|:---|---:|:---|
| high_major | moneyline | 4,411 | 606 days | -9.4% | -15.7% to -3.1% | -20.8% to +2.0% | ±11.4% | no demonstrated edge |
| high_major | spread | 10,825 | 4,683 games | -2.8% | -5.7% to +0.1% | -8.0% to +2.4% | ±5.2% | no demonstrated edge |
| high_major | team_total | 5,607 | 2,310 games | -3.6% | -6.6% to -0.7% | -9.0% to +1.7% | ±5.3% | no demonstrated edge |
| high_major | total_points | 12,241 | 688 days | -3.3% | -6.4% to -0.3% | -8.8% to +2.2% | ±5.5% | no demonstrated edge |
| mid_major | moneyline | 8,983 | 650 days | -8.0% | -11.6% to -4.5% | -14.5% to -1.6% | ±6.5% | demonstrated deficit |
| mid_major | spread | 20,191 | 649 days | -2.7% | -4.9% to -0.5% | -6.7% to +1.3% | ±4.0% | no demonstrated edge |
| mid_major | team_total | 11,690 | 345 days | -6.5% | -8.6% to -4.4% | -10.3% to -2.6% | ±3.9% | demonstrated deficit |
| mid_major | total_points | 23,327 | 728 days | -2.3% | -4.5% to -0.2% | -6.3% to +1.6% | ±4.0% | no demonstrated edge |
| low_major | moneyline | 6,972 | 590 days | -9.9% | -13.8% to -6.0% | -17.0% to -2.9% | ±7.1% | demonstrated deficit |
| low_major | spread | 14,826 | 591 days | -0.6% | -3.0% to +1.8% | -5.0% to +3.8% | ±4.4% | no demonstrated edge |
| low_major | team_total | 9,012 | 314 days | -3.8% | -6.6% to -1.1% | -8.8% to +1.2% | ±5.0% | no demonstrated edge |
| low_major | total_points | 17,903 | 7,131 games | -5.2% | -7.5% to -2.8% | -9.5% to -0.8% | ±4.3% | demonstrated deficit |
| unplaced | moneyline | 1 | 1 games | — | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 games | — | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 33,084 | 5,982 games | -4.0% | -6.0% to -2.0% | -7.6% to -0.4% | demonstrated deficit |
| mid_major | 64,191 | 736 days | -4.0% | -5.6% to -2.5% | -6.8% to -1.2% | demonstrated deficit |
| low_major | 48,713 | 646 days | -4.2% | -5.9% to -2.5% | -7.4% to -1.0% | demonstrated deficit |
| unplaced | 6 | 2 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 20,367 | 693 days | -9.0% | -11.5% to -6.4% | -13.6% to -4.3% | demonstrated deficit |
| spread | 45,845 | 20,716 games | -2.0% | -3.4% to -0.7% | -4.6% to +0.5% | no demonstrated edge |
| team_total | 26,309 | 365 days | -5.0% | -6.5% to -3.4% | -7.7% to -2.2% | demonstrated deficit |
| total_points | 53,473 | 21,076 games | -3.5% | -4.9% to -2.1% | -6.0% to -1.0% | demonstrated deficit |
| every market | 145,994 | 788 days | -4.1% | -5.1% to -3.1% | -5.8% to -2.3% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 31,674 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.1%), **4** (6.0%), **2** (5.8%), **8** (5.3%), **7** (5.2%), **6** (5.2%), **9** (4.9%), **10** (4.7%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 87.9% of 144,786 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 1,920 | 18.5% [16.8%, 20.3%] | +11.8 pp | 739 | 2.0% [1.2%, 3.3%] | -5.1 pp |
| 10%–20% | 6,791 | 29.0% [27.9%, 30.1%] | +13.3 pp | 2,190 | 7.5% [6.5%, 8.7%] | -7.8 pp |
| 20%–30% | 16,921 | 41.0% [40.2%, 41.7%] | +15.2 pp | 2,584 | 14.7% [13.4%, 16.2%] | -10.2 pp |
| 30%–40% | 52,824 | 47.5% [47.1%, 47.9%] | +11.6 pp | 2,713 | 23.6% [22.1%, 25.3%] | -11.3 pp |
| 40%–50% | 128,028 | 49.9% [49.6%, 50.1%] | +4.4 pp | 2,805 | 34.3% [32.5%, 36.0%] | -11.0 pp |
| 50%–60% | 121,400 | 50.2% [49.9%, 50.5%] | -4.3 pp | 73,593 | 49.7% [49.3%, 50.0%] | -6.4 pp |
| 60%–70% | 47,236 | 52.7% [52.2%, 53.1%] | -11.3 pp | 43,708 | 51.0% [50.6%, 51.5%] | -12.9 pp |
| 70%–80% | 15,499 | 59.6% [58.9%, 60.4%] | -14.6 pp | 12,123 | 53.0% [52.1%, 53.9%] | -21.0 pp |
| 80%–90% | 6,420 | 72.1% [71.0%, 73.2%] | -12.2 pp | 3,656 | 57.7% [56.1%, 59.3%] | -26.2 pp |
| 90%–100% | 1,838 | 83.1% [81.3%, 84.7%] | -10.2 pp | 675 | 58.7% [54.9%, 62.3%] | -34.3 pp |

- **Overall: 0.4 pp underconfident** over 398,877 graded rows in 10 usable bucket(s).
- **Selected: 10.5 pp overconfident** over 144,786 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 1,208 push, 13,360 unsettleable. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
