# NCAA Division I men's basketball — replication on a held-out season

Generated 2026-09-04T05:58:32Z.

**A window that merely fails to contradict is not confirmation.** A cell here replicates only when the held-out season's return carries the **same sign** as the discovery result **and** the held-out season's **own** interval excludes zero after the family-wise correction. A held-out interval that includes zero is **no demonstrated edge** and its state is *did not replicate* — never 'consistent with', never 'directionally in line'. The NHL lab reported a market as having held because a second window with a sample far too small to exclude anything did not contradict the first; an interval spanning zero is equally compatible with the discovery result, with no effect, and with the opposite effect.

**Held out: 2024. Selected on: 2021, 2022, 2023.** The bought population is 2021, 2022, 2023, 2024, labelled by the year each season ENDS. The rule was not fitted on the held-out season and was not chosen on it.

**The same rule, not a similar one.** The model is `cbb_betting_lab.models.ratings:matchups_for`, the snapshot window is `card` and the edge threshold is 2% — the discovery run's own threshold, read from its record rather than re-chosen here. The held-out season is scored by `price_backtest`'s own walk-forward, one-bet-per-wager and clustering code, called rather than reimplemented: a replication with its own scorer is not a test of the rule, it is a comparison of two scorers.

**The discovery record does not name the model that priced it.** The agreement between the two runs on that one point is asserted by the operator who passed `--model`, not verified by this report, and it is said here rather than left implicit.

**Family correction: 2 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.14. That is the ledger's **cumulative** count and never the day's — a search that runs every week is not twelve tests, it is twelve tests a week, forever. 2 of them are this run's own holdout looks: putting a discovery finding to the holdout **is** a second look and is counted as one.

**Below 2,000 held-out bets there is no number**, only the words *not enough evidence*. That floor is `promotion.Criteria.minimum_bets`, declared 2026-09-01 in `/Users/cooperross/Projects/cbb-betting-lab/data/manual/promotion_criteria.json`. This module reads that bar rather than inventing a second one — a bar written here would be a bar chosen after the first one existed.

## The verdict, per market and per conference tier

12 cell(s) from the discovery record, re-scored on 31,468 graded held-out bets across 4,628 games and 136 slate days. **6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions and are never pooled into one headline.

The **Discovery** column quotes the backtest's own figure at the backtest's own floor of 200 bets; every held-out column is withheld below the 2,000-bet floor `promotion.py` pre-registered per season. Two floors, both declared in advance, each applied to the report that owns it — re-judging the backtest's numbers here would be inventing a third.

| Tier | Market | Discovery | Held-out bets | Games | Held-out ROI | 95% interval | Family-corrected | Held-out verdict | State |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|
| high_major | moneyline | -1.0% over 2,848 (no claim) | 618 | 116 | — | — | — | not enough evidence (618 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| high_major | spread | -0.1% over 6,062 (no claim) | 1,583 | 117 | — | — | — | not enough evidence (1,583 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| high_major | total_points | -3.1% over 5,611 (no claim) | 1,633 | 112 | — | — | — | not enough evidence (1,633 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| mid_major | moneyline | -5.9% over 4,337 | 2,279 | 2,278 | -1.4% | -8.7% to +5.9% | -9.8% to +6.9% | no demonstrated edge | **did not replicate** |
| mid_major | spread | -1.9% over 8,944 (no claim) | 5,478 | 130 | -1.5% | -6.4% to +3.3% | -7.1% to +4.0% | no demonstrated edge | **nothing to replicate** |
| mid_major | total_points | +0.3% over 9,166 (no claim) | 5,739 | 129 | -0.4% | -5.5% to +4.6% | -6.2% to +5.4% | no demonstrated edge | **nothing to replicate** |
| low_major | moneyline | -7.6% over 3,450 | 1,134 | 108 | — | — | — | not enough evidence (1,134 held-out bets, below the 2,000 declared in advance) | **not enough evidence** |
| low_major | spread | -0.2% over 6,900 (no claim) | 2,612 | 108 | -0.2% | -6.3% to +5.9% | -7.2% to +6.8% | no demonstrated edge | **nothing to replicate** |
| low_major | total_points | -2.5% over 7,559 (no claim) | 2,973 | 1,087 | -12.1% | -18.1% to -6.0% | -19.0% to -5.2% | demonstrated deficit | **nothing to replicate** |
| unplaced | moneyline | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | spread | — | 0 | 0 | — | — | — | — | **untestable** |
| unplaced | total_points | — | 0 | 0 | — | — | — | — | **untestable** |

**0 replicated, 1 did not replicate, 0 reversed, 4 not enough evidence, 4 nothing to replicate, 3 untestable.**

**4 cell(s) have a held-out interval that includes zero. Each of those is no demonstrated edge**, in those words: mid_major / moneyline at -1.4% over 2,279 bets; mid_major / spread at -1.5% over 5,478 bets; mid_major / total_points at -0.4% over 5,739 bets; low_major / spread at -0.2% over 2,612 bets.

**Nothing replicated.** That is the ordinary outcome and it is not a surprise: clearing a correction in the window a result was found in, and then failing to hold on a window it was not, is what most findings do. Every cell whose held-out interval includes zero is **no demonstrated edge**.

### Why each cell landed where it did

Every state below carries its sample size, and every cell whose held-out interval includes zero says **no demonstrated edge** in those words.

- **high_major / moneyline — not enough evidence**: 2024: 618 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **high_major / spread — not enough evidence**: 2024: 1,583 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **high_major / total_points — not enough evidence**: 2024: 1,633 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **mid_major / moneyline — did not replicate**: 2024: the held-out season returned -1.4% over 2,279 bets across 2,278 games, family-corrected interval -9.8% to +6.9%, which includes zero — no demonstrated edge. It is compatible with the discovery result, with no effect and with the opposite effect alike, and a window that merely fails to contradict is not confirmation.
- **mid_major / spread — nothing to replicate**: 2024: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 5,478 bets.
- **mid_major / total_points — nothing to replicate**: 2024: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 5,739 bets.
- **low_major / moneyline — not enough evidence**: 2024: 1,134 held-out bets is below the 2,000 declared in advance in the promotion criteria, so this cell prints a phrase and not a number. A +12% return over 40 bets and a coin flip are the same claim at that sample size.
- **low_major / spread — nothing to replicate**: 2024: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce. The held-out season is no demonstrated edge as well, over 2,612 bets.
- **low_major / total_points — nothing to replicate**: 2024: the discovery window demonstrated nothing here (no demonstrated edge), so there is no result to reproduce — and the held-out season's own -12.1% over 2,973 bets excludes zero. That is a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication: the only clean season this lab had is now spent on it, and it has no held-out test of its own.
- **unplaced / moneyline — untestable**: 2024: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / spread — untestable**: 2024: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.
- **unplaced / total_points — untestable**: 2024: the held-out season carries no graded bet in this cell, so no test was run. That is not a failure to replicate — those are different claims and this lab does not report them the same way.

### Found on the holdout, which is not a replication

1 cell(s) demonstrated nothing in the discovery window and demonstrate something on the held-out season. **That is a new discovery made on the only clean data this lab had left**, not a confirmation of anything: the cell has no held-out test of its own, and the season it would have been tested on has now been spent. It is counted in the experiment ledger like any other look and it is not a candidate for a receipt.

- low_major / total_points: -12.1% over 2,973 held-out bets — demonstrated deficit.

### Per tier, across markets

The held-out season's own return per tier. It carries no replication state: a state is a claim about a specific (market, tier) cell that the discovery window made, and a tier roll-up is not one of those.

| Tier | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 5,044 | 119 | -3.6% | -9.9% to +2.6% | -10.8% to +3.5% | no demonstrated edge |
| mid_major | 17,732 | 132 | -1.9% | -5.4% to +1.5% | -5.9% to +2.0% | no demonstrated edge |
| low_major | 8,692 | 1,343 | -6.4% | -10.4% to -2.4% | -11.0% to -1.8% | demonstrated deficit |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

**No pooled row carries a replication state**, and none is written into the `markets` list the claims document reads. A row with no tier is treated there as applying to every tier of that market, so a pooled state would become a per-tier claim about a distribution it was never measured on.

| Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| moneyline | 4,031 | 136 | -2.9% | -8.9% to +3.1% | -9.7% to +4.0% | no demonstrated edge |
| spread | 9,673 | 136 | -1.7% | -4.9% to +1.5% | -5.4% to +1.9% | no demonstrated edge |
| team_total | 7,419 | 134 | -5.1% | -7.6% to -2.6% | -8.0% to -2.2% | demonstrated deficit |
| total_points | 10,345 | 136 | -4.1% | -7.5% to -0.7% | -8.0% to -0.2% | demonstrated deficit |
| every market | 31,468 | 136 | -3.4% | -5.9% to -1.0% | -6.2% to -0.7% | demonstrated deficit |

## What this report cannot say

- It cannot say a replicated result is **real**. **A constant settlement offset replicates by construction.** The football lab's single largest false finding returned +11.7% over 3,109 held-out bets and survived split-half, fragility and a Bonferroni correction across twenty markets, because a systematic settlement error is present in every window and so reproduces in all of them. Second-half markets settle including overtime at most US books and not at all of them; this lab wires the majority rule and cannot read a book's rulebook. Replication is not evidence against a settlement artefact — replication is what one does.
- It cannot say a replicated result is **good**. A replicated loss is a more credible loss: `demonstrated deficit` is a finding, and the NHL lab announced one as good news because its headline predicate tested measured, survives-correction and replicated without ever reading which side of zero the number sat on.
- It cannot say a *did not replicate* cell is **wrong**. An interval that includes zero is the absence of evidence for the discovery result, not evidence against it, and this report does not convert one into the other in either direction.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size or its significance.
- It cannot say a market is a play. **No market is allowlisted**, and a replicated result is a candidate for a receipt Cooper signs and nothing more. Claude may withdraw an allowlist and may never grant one.
