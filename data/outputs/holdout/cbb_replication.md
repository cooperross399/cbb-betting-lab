# NCAA Division I men's basketball — replication on a held-out season

Generated 2026-09-17T16:47:13Z.

**A window that merely fails to contradict is not confirmation.** A cell here replicates only when the held-out season's return carries the **same sign** as the discovery result **and** the held-out season's **own** interval excludes zero after the family-wise correction. A held-out interval that includes zero is **no demonstrated edge** and its state is *did not replicate* — never 'consistent with', never 'directionally in line'. The NHL lab reported a market as having held because a second window with a sample far too small to exclude anything did not contradict the first; an interval spanning zero is equally compatible with the discovery result, with no effect, and with the opposite effect.

**Held out: 2025, 2026. Selected on: 2021, 2022, 2023, 2024.** The bought population is 2021, 2022, 2023, 2024, labelled by the year each season ENDS. The rule was not fitted on the held-out season and was not chosen on it.

**This is not the split declared in advance.** 2026-09-03 declared discovery [2021, 2022, 2023] and holdout [2024]. A holdout chosen after the discovery numbers were seen is a second look at the data rather than a pre-registered test, and every state below should be read as one.

**The same rule, not a similar one.** The model is `cbb_betting_lab.models.ratings:matchups_for`, the snapshot window is `card` and the edge threshold is 2% — the discovery run's own threshold, read from its record rather than re-chosen here. The held-out season is scored by `price_backtest`'s own walk-forward, one-bet-per-wager and clustering code, called rather than reimplemented: a replication with its own scorer is not a test of the rule, it is a comparison of two scorers.

**The discovery record does not name the model that priced it.** The agreement between the two runs on that one point is asserted by the operator who passed `--model`, not verified by this report, and it is said here rather than left implicit.

**Family correction: 133 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.81. That is the ledger's **cumulative** count and never the day's — a search that runs every week is not twelve tests, it is twelve tests a week, forever. 32 of them are this run's own holdout looks: putting a discovery finding to the holdout **is** a second look and is counted as one.

**Below 2,000 held-out bets there is no number**, only the words *not enough evidence*. That floor is `promotion.Criteria.minimum_bets`, declared 2026-09-01 in `/Users/cooperross/Projects/cbb-betting-lab/data/manual/promotion_criteria.json`. This module reads that bar rather than inventing a second one — a bar written here would be a bar chosen after the first one existed.

## The verdict, per market and per conference tier

32 cell(s) from the discovery record, re-scored on 65,007 graded held-out bets across 9,776 games and 278 slate days. **The three tiers are measured from non-conference margin, never assigned by a conference name list** — so the count in each moves with the data — and they are three different distributions, never pooled into one headline.

The **Discovery** column quotes the backtest's own figure at the backtest's own floor of 200 bets; every held-out column is withheld below the 2,000-bet floor `promotion.py` pre-registered per season. Two floors, both declared in advance, each applied to the report that owns it — re-judging the backtest's numbers here would be inventing a third.

| Tier | Market | Discovery | Held-out bets | Games | Held-out ROI | 95% interval | Family-corrected | Held-out verdict | State |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|
| high_major | alternate_spread | -4.5% over 2,213 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | alternate_total_points | +0.3% over 2,136 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | moneyline | -6.0% over 2,827 (no claim) | 1,567 | 215 | — | — | — | not enough evidence (1,567 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| high_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| high_major | spread | -2.3% over 6,410 (no claim) | 4,473 | 1,755 | -4.7% | -9.4% to -0.1% | -13.2% to +3.8% | no demonstrated edge | **nothing to replicate** |
| high_major | spread_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| high_major | team_total | -4.2% over 983 (no claim) | 4,623 | 1,796 | -3.4% | -6.7% to -0.1% | -9.3% to +2.6% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points | -3.1% over 7,346 (no claim) | 4,925 | 246 | -3.7% | -8.7% to +1.2% | -12.8% to +5.3% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_spread | -6.8% over 8,349 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_total_points | -15.6% over 7,598 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | moneyline | -7.8% over 5,854 (no claim) | 3,056 | 3,055 | -9.4% | -15.7% to -3.0% | -20.9% to +2.2% | no demonstrated edge | **not enough evidence** |
| mid_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | spread | -2.5% over 12,821 (no claim) | 7,233 | 3,107 | -3.2% | -6.8% to +0.3% | -9.7% to +3.2% | no demonstrated edge | **nothing to replicate** |
| mid_major | spread_h1 | -15.2% over 693 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | team_total | -5.2% over 3,768 (no claim) | 7,896 | 229 | -7.0% | -9.7% to -4.3% | -11.9% to -2.2% | demonstrated deficit | **nothing to replicate** |
| mid_major | total_points | -0.2% over 15,250 (no claim) | 8,214 | 252 | -6.4% | -10.0% to -2.8% | -12.9% to +0.2% | no demonstrated edge | **nothing to replicate** |
| mid_major | total_points_h1 | -2.1% over 607 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_spread | -4.4% over 3,214 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_total_points | -10.0% over 3,763 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | moneyline | -9.6% over 4,226 | 2,691 | 2,690 | -10.6% | -16.4% to -4.8% | -21.2% to +0.0% | no demonstrated edge | **not enough evidence** |
| low_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | spread | -1.0% over 8,690 (no claim) | 5,938 | 2,701 | +0.0% | -3.9% to +3.9% | -7.0% to +7.0% | no demonstrated edge | **nothing to replicate** |
| low_major | spread_h1 | +5.2% over 370 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | team_total | -4.9% over 1,861 (no claim) | 7,122 | 212 | -3.4% | -6.6% to -0.2% | -9.3% to +2.4% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points | -5.3% over 10,688 (no claim) | 7,269 | 226 | -5.2% | -9.0% to -1.4% | -12.2% to +1.7% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points_h1 | -11.2% over 321 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | moneyline | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | spread | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | total_points | — | 0 | 0 | — | — | — | — | **untestable** |

**0 replicated, 0 did not replicate, 0 reversed, 3 not enough evidence, 9 nothing to replicate, 20 untestable.**

**10 cell(s) have a held-out interval that includes zero. Each of those is no demonstrated edge**, in those words: high_major / spread at -4.7% over 4,473 bets; high_major / team_total at -3.4% over 4,623 bets; high_major / total_points at -3.7% over 4,925 bets; mid_major / moneyline at -9.4% over 3,056 bets; mid_major / spread at -3.2% over 7,233 bets; mid_major / total_points at -6.4% over 8,214 bets; low_major / moneyline at -10.6% over 2,691 bets; low_major / spread at +0.0% over 5,938 bets; low_major / team_total at -3.4% over 7,122 bets; low_major / total_points at -5.2% over 7,269 bets.

**Nothing replicated.** That is the ordinary outcome and it is not a surprise: clearing a correction in the window a result was found in, and then failing to hold on a window it was not, is what most findings do. Every cell whose held-out interval includes zero is **no demonstrated edge**.

### Why each cell landed where it did

Every state below carries its sample size, and every cell whose held-out interval includes zero says **no demonstrated edge** in those words.

- **high_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / moneyline — not enough evidence**: 2025: 866 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 701 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **high_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,432 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,041 bets.
- **high_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,250 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,373 bets.
- **high_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,619 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,306 bets.
- **high_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / moneyline — not enough evidence**: 2025: 1,555 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,501 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **mid_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,717 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,516 bets.
- **mid_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,473 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce — and the held-out season's own -7.2% over 4,423 bets excludes zero. That is a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication: the only clean season this lab had is now spent on it, and it has no held-out test of its own.
- **mid_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,180 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,034 bets.
- **mid_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / moneyline — not enough evidence**: 2025: 1,219 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,472 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **low_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,766 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,172 bets.
- **low_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,639 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,483 bets.
- **low_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,294 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,975 bets.
- **low_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / moneyline — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.

### Found on the holdout, which is not a replication

1 cell(s) demonstrated nothing in the discovery window and demonstrate something on the held-out season. **That is a new discovery made on the only clean data this lab had left**, not a confirmation of anything: the cell has no held-out test of its own, and the season it would have been tested on has now been spent. It is counted in the experiment ledger like any other look and it is not a candidate for a receipt.

- mid_major / team_total: -7.0% over 7,896 held-out bets — demonstrated deficit.

### Every held-out season on its own

`must_clear_every_season` is pre-registered: a cell replicates only if it replicates in **all 2** of these, never on their pooled average. The football lab's verdict for one policy flipped depending on which season had been scored last — same policy, same script, opposite verdicts.

| Tier | Market | Season | Bets | Games | ROI | 95% interval | Family-corrected | State |
|:---|:---|---:|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline | 2025 | 866 | 866 | — | — | — | not enough evidence |
| high_major | moneyline | 2026 | 701 | 106 | — | — | — | not enough evidence |
| high_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | spread | 2025 | 2,432 | 932 | -3.1% | -9.5% to +3.3% | -14.7% to +8.4% | nothing to replicate |
| high_major | spread | 2026 | 2,041 | 823 | -6.7% | -13.6% to +0.2% | -19.3% to +5.9% | nothing to replicate |
| high_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | team_total | 2025 | 2,250 | 965 | -3.2% | -7.6% to +1.2% | -11.2% to +4.8% | nothing to replicate |
| high_major | team_total | 2026 | 2,373 | 831 | -3.5% | -8.4% to +1.4% | -12.3% to +5.3% | nothing to replicate |
| high_major | total_points | 2025 | 2,619 | 127 | -4.8% | -11.7% to +2.1% | -17.3% to +7.7% | nothing to replicate |
| high_major | total_points | 2026 | 2,306 | 119 | -2.5% | -9.7% to +4.7% | -15.5% to +10.5% | nothing to replicate |
| high_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline | 2025 | 1,555 | 115 | — | — | — | not enough evidence |
| mid_major | moneyline | 2026 | 1,501 | 1,501 | — | — | — | not enough evidence |
| mid_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | spread | 2025 | 3,717 | 1,561 | -1.6% | -6.6% to +3.4% | -10.7% to +7.4% | nothing to replicate |
| mid_major | spread | 2026 | 3,516 | 113 | -4.9% | -10.5% to +0.6% | -15.0% to +5.1% | nothing to replicate |
| mid_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | team_total | 2025 | 3,473 | 115 | -6.8% | -10.7% to -2.9% | -13.8% to +0.2% | nothing to replicate |
| mid_major | team_total | 2026 | 4,423 | 114 | -7.2% | -10.9% to -3.5% | -14.0% to -0.4% | nothing to replicate |
| mid_major | total_points | 2025 | 4,180 | 129 | -8.2% | -13.5% to -2.9% | -17.9% to +1.5% | nothing to replicate |
| mid_major | total_points | 2026 | 4,034 | 1,577 | -4.4% | -9.5% to +0.6% | -13.5% to +4.6% | nothing to replicate |
| mid_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline | 2025 | 1,219 | 1,219 | — | — | — | not enough evidence |
| low_major | moneyline | 2026 | 1,472 | 1,471 | — | — | — | not enough evidence |
| low_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | spread | 2025 | 2,766 | 1,229 | -0.8% | -6.5% to +4.9% | -11.1% to +9.5% | nothing to replicate |
| low_major | spread | 2026 | 3,172 | 1,472 | +0.7% | -4.6% to +6.0% | -8.9% to +10.3% | nothing to replicate |
| low_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | team_total | 2025 | 2,639 | 104 | -4.4% | -9.4% to +0.5% | -13.3% to +4.4% | nothing to replicate |
| low_major | team_total | 2026 | 4,483 | 108 | -2.8% | -7.0% to +1.4% | -10.4% to +4.8% | nothing to replicate |
| low_major | total_points | 2025 | 3,294 | 114 | -6.6% | -12.9% to -0.3% | -18.1% to +4.8% | nothing to replicate |
| low_major | total_points | 2026 | 3,975 | 1,589 | -4.0% | -9.0% to +1.0% | -13.1% to +5.1% | nothing to replicate |
| low_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| unplaced | moneyline | 2025 | 0 | 0 | — | — | — | untestable |
| unplaced | moneyline | 2026 | 0 | 0 | — | — | — | untestable |
| unplaced | spread | 2025 | 0 | 0 | — | — | — | untestable |
| unplaced | spread | 2026 | 0 | 0 | — | — | — | untestable |
| unplaced | total_points | 2025 | 0 | 0 | — | — | — | untestable |
| unplaced | total_points | 2026 | 0 | 0 | — | — | — | untestable |

### Per tier, across markets

The held-out season's own return per tier. It carries no replication state: a state is a claim about a specific (market, tier) cell that the discovery window made, and a tier roll-up is not one of those.

| Tier | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 15,588 | 2,268 games | -5.5% | -8.4% to -2.6% | -10.8% to -0.2% | demonstrated deficit |
| mid_major | 26,399 | 254 days | -6.1% | -8.5% to -3.6% | -10.4% to -1.7% | demonstrated deficit |
| low_major | 23,020 | 227 days | -3.9% | -6.7% to -1.2% | -8.9% to +1.0% | no demonstrated edge |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**No pooled row carries a replication state**, and none is written into the `markets` list the claims document reads. A row with no tier is treated there as applying to every tier of that market, so a pooled state would become a per-tier claim about a distribution it was never measured on.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 7,314 | 242 days | -12.0% | -16.0% to -8.0% | -19.2% to -4.7% | demonstrated deficit |
| spread | 17,644 | 7,563 games | -2.5% | -4.8% to -0.2% | -6.7% to +1.6% | no demonstrated edge |
| team_total | 19,641 | 244 days | -4.9% | -6.7% to -3.0% | -8.2% to -1.5% | demonstrated deficit |
| total_points | 20,408 | 8,000 games | -5.3% | -7.6% to -3.1% | -9.4% to -1.3% | demonstrated deficit |
| every market | 65,007 | 9,601 games | -5.2% | -6.6% to -3.7% | -7.8% to -2.5% | demonstrated deficit |

## What this report cannot say

- It cannot say a replicated result is **real**. **A constant settlement offset replicates by construction.** The football lab's single largest false finding returned +11.7% over 3,109 held-out bets and survived split-half, fragility and a Bonferroni correction across twenty markets, because a systematic settlement error is present in every window and so reproduces in all of them. Second-half markets settle including overtime at most US books and not at all of them; this lab wires the majority rule and cannot read a book's rulebook. Replication is not evidence against a settlement artefact — replication is what one does.
- It cannot say a replicated result is **good**. A replicated loss is a more credible loss: `demonstrated deficit` is a finding, and the NHL lab announced one as good news because its headline predicate tested measured, survives-correction and replicated without ever reading which side of zero the number sat on.
- It cannot say a *did not replicate* cell is **wrong**. An interval that includes zero is the absence of evidence for the discovery result, not evidence against it, and this report does not convert one into the other in either direction.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size or its significance.
- It cannot say a market is a play. **No market is allowlisted**, and a replicated result is a candidate for a receipt Cooper signs and nothing more. Claude may withdraw an allowlist and may never grant one.
