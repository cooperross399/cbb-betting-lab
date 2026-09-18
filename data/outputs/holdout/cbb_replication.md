# NCAA Division I men's basketball — replication on a held-out season

Generated 2026-09-18T00:22:10Z.

**A window that merely fails to contradict is not confirmation.** A cell here replicates only when the held-out season's return carries the **same sign** as the discovery result **and** the held-out season's **own** interval excludes zero after the family-wise correction. A held-out interval that includes zero is **no demonstrated edge** and its state is *did not replicate* — never 'consistent with', never 'directionally in line'. The NHL lab reported a market as having held because a second window with a sample far too small to exclude anything did not contradict the first; an interval spanning zero is equally compatible with the discovery result, with no effect, and with the opposite effect.

**Held out: 2025, 2026. Selected on: 2021, 2022, 2023, 2024.** The bought population is 2021, 2022, 2023, 2024, labelled by the year each season ENDS. The rule was not fitted on the held-out season and was not chosen on it.

**This is not the split declared in advance.** 2026-09-03 declared discovery [2021, 2022, 2023] and holdout [2024]. A holdout chosen after the discovery numbers were seen is a second look at the data rather than a pre-registered test, and every state below should be read as one.

**The same rule, not a similar one.** The model is `cbb_betting_lab.models.ratings:matchups_for`, the snapshot window is `card` and the edge threshold is 2% — the discovery run's own threshold, read from its record rather than re-chosen here. The held-out season is scored by `price_backtest`'s own walk-forward, one-bet-per-wager and clustering code, called rather than reimplemented: a replication with its own scorer is not a test of the rule, it is a comparison of two scorers.

**The discovery record does not name the model that priced it.** The agreement between the two runs on that one point is asserted by the operator who passed `--model`, not verified by this report, and it is said here rather than left implicit.

**Family correction: 133 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.81. That is the ledger's **cumulative** count and never the day's — a search that runs every week is not twelve tests, it is twelve tests a week, forever. 32 of them are this run's own holdout looks: putting a discovery finding to the holdout **is** a second look and is counted as one.

**Below 2,000 held-out bets there is no number**, only the words *not enough evidence*. That floor is `promotion.Criteria.minimum_bets`, declared 2026-09-01 in `/Users/cooperross/Projects/cbb-betting-lab/data/manual/promotion_criteria.json`. This module reads that bar rather than inventing a second one — a bar written here would be a bar chosen after the first one existed.

## The verdict, per market and per conference tier

32 cell(s) from the discovery record, re-scored on 65,008 graded held-out bets across 9,810 games and 278 slate days. **The three tiers are measured from non-conference margin, never assigned by a conference name list** — so the count in each moves with the data — and they are three different distributions, never pooled into one headline.

The **Discovery** column quotes the backtest's own figure at the backtest's own floor of 200 bets; every held-out column is withheld below the 2,000-bet floor `promotion.py` pre-registered per season. Two floors, both declared in advance, each applied to the report that owns it — re-judging the backtest's numbers here would be inventing a third.

| Tier | Market | Discovery | Held-out bets | Games | Held-out ROI | 95% interval | Family-corrected | Held-out verdict | State |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|
| high_major | alternate_spread | -4.5% over 2,213 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | alternate_total_points | +0.3% over 2,136 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| high_major | moneyline | -6.0% over 2,827 (no claim) | 1,566 | 217 | — | — | — | not enough evidence (1,566 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| high_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| high_major | spread | -2.3% over 6,410 (no claim) | 4,498 | 1,755 | -3.7% | -8.4% to +1.0% | -12.2% to +4.8% | no demonstrated edge | **nothing to replicate** |
| high_major | spread_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| high_major | team_total | -4.2% over 983 (no claim) | 4,587 | 1,799 | -3.6% | -6.9% to -0.3% | -9.6% to +2.4% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points | -3.1% over 7,346 (no claim) | 4,956 | 246 | -3.6% | -8.3% to +1.2% | -12.2% to +5.1% | no demonstrated edge | **nothing to replicate** |
| high_major | total_points_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_spread | -6.8% over 8,349 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | alternate_total_points | -15.6% over 7,598 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | moneyline | -7.8% over 5,854 (no claim) | 3,019 | 229 | -8.6% | -15.0% to -2.1% | -20.3% to +3.2% | no demonstrated edge | **not enough evidence** |
| mid_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | spread | -2.5% over 12,821 (no claim) | 7,147 | 3,053 | -3.6% | -7.2% to +0.0% | -10.1% to +2.9% | no demonstrated edge | **nothing to replicate** |
| mid_major | spread_h1 | -15.2% over 693 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| mid_major | team_total | -5.2% over 3,768 (no claim) | 7,850 | 229 | -6.8% | -9.5% to -4.1% | -11.6% to -2.0% | demonstrated deficit | **nothing to replicate** |
| mid_major | total_points | -0.2% over 15,250 (no claim) | 8,267 | 253 | -6.5% | -10.2% to -2.9% | -13.1% to +0.0% | no demonstrated edge | **nothing to replicate** |
| mid_major | total_points_h1 | -2.1% over 607 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_spread | -4.4% over 3,214 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_team_total | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | alternate_total_points | -10.0% over 3,763 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | moneyline | -9.6% over 4,226 | 2,741 | 2,740 | -10.0% | -15.8% to -4.2% | -20.5% to +0.5% | no demonstrated edge | **not enough evidence** |
| low_major | moneyline_h1 | — | 0 | 0 | — | — | — | — | **untestable** |
| low_major | spread | -1.0% over 8,690 (no claim) | 5,906 | 2,705 | -0.3% | -4.2% to +3.5% | -7.3% to +6.7% | no demonstrated edge | **nothing to replicate** |
| low_major | spread_h1 | +5.2% over 370 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| low_major | team_total | -4.9% over 1,861 (no claim) | 7,181 | 212 | -3.5% | -6.8% to -0.3% | -9.5% to +2.4% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points | -5.3% over 10,688 (no claim) | 7,290 | 226 | -5.1% | -8.9% to -1.2% | -12.0% to +1.9% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points_h1 | -11.2% over 321 (no claim) | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | moneyline | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | spread | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | total_points | — | 0 | 0 | — | — | — | — | **untestable** |

**0 replicated, 0 did not replicate, 0 reversed, 3 not enough evidence, 9 nothing to replicate, 20 untestable.**

**10 cell(s) have a held-out interval that includes zero. Each of those is no demonstrated edge**, in those words: high_major / spread at -3.7% over 4,498 bets; high_major / team_total at -3.6% over 4,587 bets; high_major / total_points at -3.6% over 4,956 bets; mid_major / moneyline at -8.6% over 3,019 bets; mid_major / spread at -3.6% over 7,147 bets; mid_major / total_points at -6.5% over 8,267 bets; low_major / moneyline at -10.0% over 2,741 bets; low_major / spread at -0.3% over 5,906 bets; low_major / team_total at -3.5% over 7,181 bets; low_major / total_points at -5.1% over 7,290 bets.

**Nothing replicated.** That is the ordinary outcome and it is not a surprise: clearing a correction in the window a result was found in, and then failing to hold on a window it was not, is what most findings do. Every cell whose held-out interval includes zero is **no demonstrated edge**.

### Why each cell landed where it did

Every state below carries its sample size, and every cell whose held-out interval includes zero says **no demonstrated edge** in those words.

- **high_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / moneyline — not enough evidence**: 2025: 862 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 704 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **high_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,456 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,042 bets.
- **high_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **high_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,224 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,363 bets.
- **high_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,660 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,296 bets.
- **high_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / moneyline — not enough evidence**: 2025: 1,528 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,491 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **mid_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,665 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,482 bets.
- **mid_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **mid_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,421 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce — and the held-out season's own -6.9% over 4,429 bets excludes zero. That is a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication: the only clean season this lab had is now spent on it, and it has no held-out test of its own.
- **mid_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,220 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,047 bets.
- **mid_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_team_total — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / alternate_total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / moneyline — not enough evidence**: 2025: 1,252 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.; 2026: 1,489 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **low_major / moneyline_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / spread — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,716 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,190 bets.
- **low_major / spread_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **low_major / team_total — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,656 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 4,525 bets.
- **low_major / total_points — nothing to replicate**: 2025: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,308 bets.; 2026: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 3,982 bets.
- **low_major / total_points_h1 — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / moneyline — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / spread — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / total_points — untestable**: 2025: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.; 2026: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.

### Found on the holdout, which is not a replication

1 cell(s) demonstrated nothing in the discovery window and demonstrate something on the held-out season. **That is a new discovery made on the only clean data this lab had left**, not a confirmation of anything: the cell has no held-out test of its own, and the season it would have been tested on has now been spent. It is counted in the experiment ledger like any other look and it is not a candidate for a receipt.

- mid_major / team_total: -6.8% over 7,850 held-out bets — demonstrated deficit.

### Every held-out season on its own

`must_clear_every_season` is pre-registered: a cell replicates only if it replicates in **all 2** of these, never on their pooled average. The football lab's verdict for one policy flipped depending on which season had been scored last — same policy, same script, opposite verdicts.

| Tier | Market | Season | Bets | Games | ROI | 95% interval | Family-corrected | State |
|:---|:---|---:|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline | 2025 | 862 | 111 | — | — | — | not enough evidence |
| high_major | moneyline | 2026 | 704 | 106 | — | — | — | not enough evidence |
| high_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | spread | 2025 | 2,456 | 938 | -1.7% | -8.1% to +4.6% | -13.3% to +9.8% | nothing to replicate |
| high_major | spread | 2026 | 2,042 | 817 | -6.1% | -13.1% to +0.8% | -18.7% to +6.5% | nothing to replicate |
| high_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| high_major | team_total | 2025 | 2,224 | 966 | -4.1% | -8.6% to +0.3% | -12.2% to +3.9% | nothing to replicate |
| high_major | team_total | 2026 | 2,363 | 833 | -3.1% | -8.0% to +1.8% | -11.9% to +5.8% | nothing to replicate |
| high_major | total_points | 2025 | 2,660 | 127 | -4.6% | -11.0% to +1.8% | -16.3% to +7.1% | nothing to replicate |
| high_major | total_points | 2026 | 2,296 | 119 | -2.4% | -9.5% to +4.7% | -15.3% to +10.5% | nothing to replicate |
| high_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| high_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline | 2025 | 1,528 | 115 | — | — | — | not enough evidence |
| mid_major | moneyline | 2026 | 1,491 | 1,491 | — | — | — | not enough evidence |
| mid_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | spread | 2025 | 3,665 | 1,541 | -2.2% | -7.3% to +2.8% | -11.4% to +6.9% | nothing to replicate |
| mid_major | spread | 2026 | 3,482 | 114 | -5.0% | -10.8% to +0.7% | -15.4% to +5.4% | nothing to replicate |
| mid_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| mid_major | team_total | 2025 | 3,421 | 115 | -6.6% | -10.6% to -2.7% | -13.8% to +0.5% | nothing to replicate |
| mid_major | team_total | 2026 | 4,429 | 1,659 | -6.9% | -10.6% to -3.2% | -13.6% to -0.2% | nothing to replicate |
| mid_major | total_points | 2025 | 4,220 | 129 | -8.5% | -13.8% to -3.2% | -18.1% to +1.1% | nothing to replicate |
| mid_major | total_points | 2026 | 4,047 | 1,592 | -4.5% | -9.5% to +0.5% | -13.6% to +4.5% | nothing to replicate |
| mid_major | total_points_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| mid_major | total_points_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_spread | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_team_total | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | alternate_total_points | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline | 2025 | 1,252 | 1,252 | — | — | — | not enough evidence |
| low_major | moneyline | 2026 | 1,489 | 1,488 | — | — | — | not enough evidence |
| low_major | moneyline_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | moneyline_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | spread | 2025 | 2,716 | 1,221 | -1.6% | -7.3% to +4.1% | -11.9% to +8.7% | nothing to replicate |
| low_major | spread | 2026 | 3,190 | 1,484 | +0.8% | -4.5% to +6.0% | -8.8% to +10.3% | nothing to replicate |
| low_major | spread_h1 | 2025 | 0 | 0 | — | — | — | untestable |
| low_major | spread_h1 | 2026 | 0 | 0 | — | — | — | untestable |
| low_major | team_total | 2025 | 2,656 | 104 | -3.8% | -8.9% to +1.2% | -13.0% to +5.4% | nothing to replicate |
| low_major | team_total | 2026 | 4,525 | 108 | -3.4% | -7.6% to +0.9% | -11.1% to +4.4% | nothing to replicate |
| low_major | total_points | 2025 | 3,308 | 114 | -6.8% | -13.0% to -0.5% | -18.1% to +4.6% | nothing to replicate |
| low_major | total_points | 2026 | 3,982 | 1,604 | -3.6% | -8.6% to +1.4% | -12.7% to +5.4% | nothing to replicate |
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
| high_major | 15,607 | 2,270 games | -5.3% | -8.2% to -2.4% | -10.6% to -0.0% | demonstrated deficit |
| mid_major | 26,283 | 254 days | -6.0% | -8.5% to -3.6% | -10.5% to -1.6% | demonstrated deficit |
| low_major | 23,118 | 227 days | -4.0% | -6.7% to -1.2% | -9.0% to +1.1% | no demonstrated edge |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**No pooled row carries a replication state**, and none is written into the `markets` list the claims document reads. A row with no tier is treated there as applying to every tier of that market, so a pooled state would become a per-tier claim about a distribution it was never measured on.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 7,326 | 242 days | -11.6% | -15.7% to -7.5% | -19.0% to -4.2% | demonstrated deficit |
| spread | 17,551 | 7,513 games | -2.5% | -4.8% to -0.2% | -6.7% to +1.6% | no demonstrated edge |
| team_total | 19,618 | 244 days | -4.8% | -6.7% to -3.0% | -8.2% to -1.5% | demonstrated deficit |
| total_points | 20,513 | 8,043 games | -5.3% | -7.5% to -3.1% | -9.3% to -1.3% | demonstrated deficit |
| every market | 65,008 | 9,641 games | -5.1% | -6.6% to -3.7% | -7.8% to -2.5% | demonstrated deficit |

## What this report cannot say

- It cannot say a replicated result is **real**. **A constant settlement offset replicates by construction.** The football lab's single largest false finding returned +11.7% over 3,109 held-out bets and survived split-half, fragility and a Bonferroni correction across twenty markets, because a systematic settlement error is present in every window and so reproduces in all of them. Second-half markets settle including overtime at most US books and not at all of them; this lab wires the majority rule and cannot read a book's rulebook. Replication is not evidence against a settlement artefact — replication is what one does.
- It cannot say a replicated result is **good**. A replicated loss is a more credible loss: `demonstrated deficit` is a finding, and the NHL lab announced one as good news because its headline predicate tested measured, survives-correction and replicated without ever reading which side of zero the number sat on.
- It cannot say a *did not replicate* cell is **wrong**. An interval that includes zero is the absence of evidence for the discovery result, not evidence against it, and this report does not convert one into the other in either direction.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size or its significance.
- It cannot say a market is a play. **No market is allowlisted**, and a replicated result is a candidate for a receipt Cooper signs and nothing more. Claude may withdraw an allowlist and may never grant one.
