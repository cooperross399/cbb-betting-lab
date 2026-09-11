# NCAA Division I men's basketball — replication on a held-out season

Generated 2026-09-05T16:56:49Z.

**A window that merely fails to contradict is not confirmation.** A cell here replicates only when the held-out season's return carries the **same sign** as the discovery result **and** the held-out season's **own** interval excludes zero after the family-wise correction. A held-out interval that includes zero is **no demonstrated edge** and its state is *did not replicate* — never 'consistent with', never 'directionally in line'. The NHL lab reported a market as having held because a second window with a sample far too small to exclude anything did not contradict the first; an interval spanning zero is equally compatible with the discovery result, with no effect, and with the opposite effect.

**Held out: 2025, 2026. Selected on: 2021, 2022, 2023, 2024.** The bought population is 2021, 2022, 2023, 2024, labelled by the year each season ENDS. The rule was not fitted on the held-out season and was not chosen on it.

**This is not the split declared in advance.** 2026-09-03 declared discovery [2021, 2022, 2023] and holdout [2024]. A holdout chosen after the discovery numbers were seen is a second look at the data rather than a pre-registered test, and every state below should be read as one.

**The same rule, not a similar one.** The model is `cbb_betting_lab.models.ratings:matchups_for`, the snapshot window is `card` and the edge threshold is 2% — the discovery run's own threshold, read from its record rather than re-chosen here. The held-out season is scored by `price_backtest`'s own walk-forward, one-bet-per-wager and clustering code, called rather than reimplemented: a replication with its own scorer is not a test of the rule, it is a comparison of two scorers.

**The discovery record does not name the model that priced it.** The agreement between the two runs on that one point is asserted by the operator who passed `--model`, not verified by this report, and it is said here rather than left implicit.

**Family correction: 101 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.78. That is the ledger's **cumulative** count and never the day's — a search that runs every week is not twelve tests, it is twelve tests a week, forever. 32 of them are this run's own holdout looks: putting a discovery finding to the holdout **is** a second look and is counted as one.

**The verdicts below are stated at the ledger's count as of this render, not the one this run was scored at.** The run itself was scored at 62 cumulative hypotheses (x1.7095), and `cbb_replication.json` still records that — it is the measurement and it does not move. Every corrected interval and every verdict below is re-derived from that run's own point estimates and standard errors at 101 hypotheses (x1.7773), the ledger's cumulative count at render time. Nothing was re-measured to do it, and a wider correction can only ever retract a claim — never make one.

**Below 2,000 held-out bets there is no number**, only the words *not enough evidence*. That floor is `promotion.Criteria.minimum_bets`, declared 2026-09-01 in `/private/tmp/wt-pipeline2/data/manual/promotion_criteria.json`. This module reads that bar rather than inventing a second one — a bar written here would be a bar chosen after the first one existed.

## The verdict, per market and per conference tier

32 cell(s) from the discovery record, re-scored on 71,778 graded held-out bets across 9,776 games and 278 slate days. **The three tiers are measured from non-conference margin, never assigned by a conference name list** — so the count in each moves with the data — and they are three different distributions, never pooled into one headline.

The **Discovery** column quotes the backtest's own figure at the backtest's own floor of 200 bets; every held-out column is withheld below the 2,000-bet floor `promotion.py` pre-registered per season. Two floors, both declared in advance, each applied to the report that owns it — re-judging the backtest's numbers here would be inventing a third.

| Tier | Market | Discovery | Held-out bets | Games | Held-out ROI | 95% interval | Family-corrected | Held-out verdict | State |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|
| high_major | alternate_spread | -10.4% over 2,551 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | alternate_total_points | -1.1% over 2,114 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | moneyline | -0.8% over 3,489 (no claim) | 2,021 | 253 | -8.0% | -17.8% to +1.7% | -25.3% to +9.3% | no demonstrated edge | **not enough evidence** |
| high_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| high_major | spread | -1.1% over 7,707 (no claim) | 5,535 | 255 | -2.6% | -6.8% to +1.6% | -10.1% to +4.9% | no demonstrated edge | **nothing to replicate** |
| high_major | spread_h1 | -24.7% over 223 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | team_total | -5.7% over 1,261 (no claim) | 5,848 | 2,285 | -2.2% | -5.2% to +0.8% | -7.5% to +3.1% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points | -3.1% over 7,316 (no claim) | 4,925 | 246 | -3.7% | -8.7% to +1.2% | -12.6% to +5.1% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_spread | -3.4% over 9,319 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_total_points | -17.0% over 7,467 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | moneyline | -4.4% over 6,702 (no claim) | 3,492 | 253 | -4.6% | -10.7% to +1.5% | -15.5% to +6.3% | no demonstrated edge | **not enough evidence** |
| mid_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | spread | -1.5% over 14,638 (no claim) | 8,253 | 3,541 | -1.6% | -4.9% to +1.8% | -7.5% to +4.4% | no demonstrated edge | **nothing to replicate** |
| mid_major | spread_h1 | -7.4% over 799 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | team_total | -5.4% over 4,403 (no claim) | 9,075 | 254 | -6.1% | -8.6% to -3.5% | -10.6% to -1.5% | demonstrated deficit | **nothing to replicate** |
| mid_major | total_points | -0.2% over 15,113 (no claim) | 8,214 | 252 | -6.4% | -10.0% to -2.8% | -12.8% to +0.0% | no demonstrated edge | **nothing to replicate** |
| mid_major | total_points_h1 | -2.4% over 594 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_spread | -2.1% over 3,510 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_total_points | -10.5% over 3,785 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | moneyline | -7.8% over 4,631 (no claim) | 2,930 | 2,929 | -8.2% | -14.0% to -2.4% | -18.5% to +2.1% | no demonstrated edge | **not enough evidence** |
| low_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | spread | -0.5% over 9,622 (no claim) | 6,468 | 2,942 | +0.6% | -3.1% to +4.2% | -6.0% to +7.1% | no demonstrated edge | **nothing to replicate** |
| low_major | spread_h1 | +5.0% over 405 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | team_total | -4.7% over 2,054 (no claim) | 7,748 | 226 | -3.9% | -7.0% to -0.8% | -9.3% to +1.5% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points | -5.1% over 10,634 (no claim) | 7,269 | 226 | -5.2% | -9.0% to -1.4% | -12.0% to +1.6% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points_h1 | -11.4% over 326 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | moneyline | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | spread | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | total_points | — | 0 | 0 | — | — | — | — | **untestable** |

**0 replicated, 0 did not replicate, 0 reversed, 3 not enough evidence, 9 nothing to replicate, 20 untestable.**

**11 cell(s) have a held-out interval that includes zero. Each of those is no demonstrated edge**, in those words: high_major / moneyline at -8.0% over 2,021 bets; high_major / spread at -2.6% over 5,535 bets; high_major / team_total at -2.2% over 5,848 bets; high_major / total_points at -3.7% over 4,925 bets; mid_major / moneyline at -4.6% over 3,492 bets; mid_major / spread at -1.6% over 8,253 bets; mid_major / total_points at -6.4% over 8,214 bets; low_major / moneyline at -8.2% over 2,930 bets; low_major / spread at +0.6% over 6,468 bets; low_major / team_total at -3.9% over 7,748 bets; low_major / total_points at -5.2% over 7,269 bets.

**Nothing replicated.** That is the ordinary outcome and it is not a surprise: clearing a correction in the window a result was found in, and then failing to hold on a window it was not, is what most findings do. Every cell whose held-out interval includes zero is **no demonstrated edge**.

### Why each cell landed where it did

Every state below carries its sample size, and every cell whose held-out interval includes zero says **no demonstrated edge** in those words.

- **high_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / moneyline — not enough evidence**: 2025: 1,100 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 921 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **high_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,008 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,527 bets.
- **high_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,875 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,973 bets.
- **high_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,619 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,306 bets.
- **high_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / moneyline — not enough evidence**: 2025: 1,782 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,710 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **mid_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,269 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,984 bets.
- **mid_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,107 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce — and the held-out season's own -6.6% over 4,968 bets excludes zero. That is a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication: the only clean season this lab had is now spent on it, and it has no held-out test of its own.
- **mid_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,180 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,034 bets.
- **mid_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / moneyline — not enough evidence**: 2025: 1,331 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,599 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **low_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,031 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,437 bets.
- **low_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,927 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,821 bets.
- **low_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,294 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,975 bets.
- **low_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / moneyline — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.

### Found on the holdout, which is not a replication

1 cell(s) demonstrated nothing in the discovery window and demonstrate something on the held-out season. **That is a new discovery made on the only clean data this lab had left**, not a confirmation of anything: the cell has no held-out test of its own, and the season it would have been tested on has now been spent. It is counted in the experiment ledger like any other look and it is not a candidate for a receipt.

- mid_major / team_total: -6.1% over 9,075 held-out bets — demonstrated deficit.

### Every held-out season on its own

`must_clear_every_season` is pre-registered: a cell replicates only if it replicates in **all 2** of these, never on their pooled average. The football lab's verdict for one policy flipped depending on which season had been scored last — same policy, same script, opposite verdicts.

| Tier | Market | Season | Bets | Games | ROI | 95% interval | Family-corrected | State |
|:---|:---|---:|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline | 2025 | 1,100 | 132 | — | — | — | not enough evidence |
| high_major | moneyline | 2026 | 921 | 121 | — | — | — | not enough evidence |
| high_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | spread | 2025 | 3,008 | 1,165 | -1.2% | -6.9% to +4.5% | -11.4% to +8.9% | nothing to replicate |
| high_major | spread | 2026 | 2,527 | 123 | -4.2% | -10.7% to +2.3% | -15.7% to +7.4% | nothing to replicate |
| high_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | team_total | 2025 | 2,875 | 133 | -1.8% | -5.9% to +2.4% | -9.2% to +5.7% | nothing to replicate |
| high_major | team_total | 2026 | 2,973 | 1,074 | -2.7% | -7.0% to +1.6% | -10.4% to +5.0% | nothing to replicate |
| high_major | total_points | 2025 | 2,619 | 127 | -4.8% | -11.7% to +2.1% | -17.1% to +7.4% | nothing to replicate |
| high_major | total_points | 2026 | 2,306 | 119 | -2.5% | -9.7% to +4.7% | -15.3% to +10.3% | nothing to replicate |
| high_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline | 2025 | 1,782 | 129 | — | — | — | not enough evidence |
| mid_major | moneyline | 2026 | 1,710 | 1,710 | — | — | — | not enough evidence |
| mid_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | spread | 2025 | 4,269 | 1,786 | -0.7% | -5.3% to +4.0% | -9.0% to +7.6% | nothing to replicate |
| mid_major | spread | 2026 | 3,984 | 124 | -2.5% | -7.6% to +2.6% | -11.6% to +6.5% | nothing to replicate |
| mid_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | team_total | 2025 | 4,107 | 129 | -5.3% | -9.0% to -1.6% | -11.9% to +1.2% | nothing to replicate |
| mid_major | team_total | 2026 | 4,968 | 125 | -6.6% | -10.2% to -3.1% | -13.0% to -0.3% | nothing to replicate |
| mid_major | total_points | 2025 | 4,180 | 129 | -8.2% | -13.5% to -2.9% | -17.7% to +1.3% | nothing to replicate |
| mid_major | total_points | 2026 | 4,034 | 1,577 | -4.4% | -9.5% to +0.6% | -13.3% to +4.5% | nothing to replicate |
| mid_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline | 2025 | 1,331 | 1,331 | — | — | — | not enough evidence |
| low_major | moneyline | 2026 | 1,599 | 110 | — | — | — | not enough evidence |
| low_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | spread | 2025 | 3,031 | 1,343 | -0.1% | -5.5% to +5.3% | -9.7% to +9.5% | nothing to replicate |
| low_major | spread | 2026 | 3,437 | 1,599 | +1.1% | -3.9% to +6.2% | -7.8% to +10.1% | nothing to replicate |
| low_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | team_total | 2025 | 2,927 | 113 | -5.0% | -9.5% to -0.4% | -13.1% to +3.2% | nothing to replicate |
| low_major | team_total | 2026 | 4,821 | 113 | -3.3% | -7.3% to +0.8% | -10.4% to +3.9% | nothing to replicate |
| low_major | total_points | 2025 | 3,294 | 114 | -6.6% | -12.9% to -0.3% | -17.9% to +4.6% | nothing to replicate |
| low_major | total_points | 2026 | 3,975 | 1,589 | -4.0% | -9.0% to +1.0% | -12.9% to +4.9% | nothing to replicate |
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
| high_major | 18,329 | 256 days | -3.4% | -6.3% to -0.5% | -8.5% to +1.8% | no demonstrated edge |
| mid_major | 29,034 | 254 days | -4.7% | -7.0% to -2.4% | -8.8% to -0.6% | demonstrated deficit |
| low_major | 24,415 | 227 days | -3.6% | -6.3% to -1.0% | -8.4% to +1.1% | no demonstrated edge |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**No pooled row carries a replication state**, and none is written into the `markets` list the claims document reads. A row with no tier is treated there as applying to every tier of that market, so a pooled state would become a per-tier claim about a distribution it was never measured on.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 8,443 | 277 days | -6.7% | -11.1% to -2.3% | -14.5% to +1.2% | no demonstrated edge |
| spread | 20,256 | 8,694 games | -1.2% | -3.3% to +1.0% | -5.0% to +2.6% | no demonstrated edge |
| team_total | 22,671 | 278 days | -4.3% | -6.1% to -2.6% | -7.4% to -1.2% | demonstrated deficit |
| total_points | 20,408 | 8,000 games | -5.3% | -7.6% to -3.1% | -9.3% to -1.3% | demonstrated deficit |
| every market | 71,778 | 278 days | -4.0% | -5.5% to -2.5% | -6.6% to -1.4% | demonstrated deficit |

## What this report cannot say

- It cannot say a replicated result is **real**. **A constant settlement offset replicates by construction.** The football lab's single largest false finding returned +11.7% over 3,109 held-out bets and survived split-half, fragility and a Bonferroni correction across twenty markets, because a systematic settlement error is present in every window and so reproduces in all of them. Second-half markets settle including overtime at most US books and not at all of them; this lab wires the majority rule and cannot read a book's rulebook. Replication is not evidence against a settlement artefact — replication is what one does.
- It cannot say a replicated result is **good**. A replicated loss is a more credible loss: `demonstrated deficit` is a finding, and the NHL lab announced one as good news because its headline predicate tested measured, survives-correction and replicated without ever reading which side of zero the number sat on.
- It cannot say a *did not replicate* cell is **wrong**. An interval that includes zero is the absence of evidence for the discovery result, not evidence against it, and this report does not convert one into the other in either direction.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size or its significance.
- It cannot say a market is a play. **No market is allowlisted**, and a replicated result is a candidate for a receipt Cooper signs and nothing more. Claude may withdraw an allowlist and may never grant one.
