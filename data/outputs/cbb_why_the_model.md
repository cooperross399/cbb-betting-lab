# Why the model does not have a demonstrated edge

Every figure below is read from a record on disk by `scripts/run_why_the_model.py`, never typed. The records, and the moment each stamped itself with:

- **price backtest** — `data/outputs/cbb_price_backtest.json`, generated 2026-09-05T13:13:24Z
- **forecast skill** — `data/outputs/cbb_forecast_skill.json`, generated 2026-09-05T15:56:38Z
- **held-out replication** — `data/outputs/holdout/cbb_replication.json`, generated 2026-09-05T16:56:49Z

Read `docs/what_we_can_and_cannot_claim.md` first. This says what the evidence *is*; that says how to read it.

## The answer

**No demonstrated edge in any of the 3 measured tiers** (high-major 43,228 bets, mid-major 88,344 bets, low-major 59,475 bets). 1 shows a demonstrated deficit: mid-major 88,344 bets, **-4.3%**, corrected -8.2% to -0.4% — demonstrated deficit.

Measured on 191,053 graded bets over 26,591 games and 791 days of the 2021-2026 seasons, across 32 market-and-tier cells.

Every interval is corrected for 95 cumulative distinct hypotheses — the experiment ledger's count at render time, not the count when the backtest ran — which widens each one by x1.77. The correction can only ever get stricter as the search continues, which is the only direction it is allowed to move.

| Tier | Result |
|:---|:---|
| high-major | 43,228 bets, **-3.2%**, corrected -8.1% to +1.6% — no demonstrated edge |
| mid-major | 88,344 bets, **-4.3%**, corrected -8.2% to -0.4% — demonstrated deficit |
| low-major | 59,475 bets, **-4.0%**, corrected -8.1% to +0.0% — no demonstrated edge |
| unplaced | not enough evidence (6 bets, below the 200 declared in advance) |

Cut finer, by market **and** tier: **0 of 32 cells shows a demonstrated edge** and **3 shows a demonstrated deficit**, over the 23 that clear the floor declared in advance.

- `team_total / mid_major`: 13,478 bets, **-5.8%**, corrected -9.4% to -2.2% — demonstrated deficit
- `moneyline / low_major`: 7,561 bets, **-7.9%**, corrected -14.8% to -1.1% — demonstrated deficit
- `total_points / low_major`: 17,903 bets, **-5.2%**, corrected -9.4% to -0.9% — demonstrated deficit

### The tier this lab was built expecting to be the best

The reason for a fourth lab was market heterogeneity — 360 teams on a Tuesday night in January being priced with less attention than a 32-team league, so softness should appear at the low-major end. By point estimate the **worst** measured tier is **mid-major**: 88,344 bets, **-4.3%**, corrected -8.2% to -0.4% — demonstrated deficit. Whatever is different about that board, this model is not better there.

### The pooled figure, which is not the answer

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

Pooled across every market and tier: 191,053 bets, **-4.0%**, corrected -6.4% to -1.5% — demonstrated deficit.

### A claim this document has retracted, recorded 2026-09-04

Before this block was generated, this document said of **low-major** that it was *“the only tier whose interval excludes zero, and it excludes zero on the losing side”* — a demonstrated deficit. That was measured on the core team markets alone, before the alternate ladders and the halves entered the population.

**It no longer holds.** On today's record low-major reads 59,475 bets, **-4.0%**, corrected -8.1% to +0.0% — no demonstrated edge.

**The measurement did not move; the search did.** The uncorrected 95% interval is -6.3% to -1.7% and still excludes zero. What widens it across is the family-wise correction over 95 cumulative hypotheses — x1.7689 — every one of which this lab wrote down before it was tested. An interval is paid for by the whole search that produced it, including the parts of that search that have not run yet, and this is one interval paying. A claim that dissolves once the search is counted in full was never worth the width it was first printed at.

## The model is not worthless — it is beaten by the vig

The worst blind sides that clear the 200-bet floor declared in advance:

- `low_major / player_threes / always over`: 227 bets, **-40.0%**
- `high_major / player_rebounds / always over`: 15,706 bets, **-30.7%**
- `high_major / player_threes / always over`: 6,771 bets, **-28.3%**
- `mid_major / player_first_basket / always over`: 292 bets, **-27.2%**
- `high_major / alternate_total_points / always under`: 6,618 bets, **-25.3%**

Each is a rule that needs no model at all. All 3 measured tiers return more than every one of them. That is what *the model carries information* means here, and it is a different statement from *the model beats the price* — which is the one the next section tests.

## Three instruments, and none of them is the return

**Brier against the market, per tier, with the vig left in.**

| Tier | Rows | Model minus raw market | Reading |
|:---|---:|:---|:---|
| high-major | 62,163 | -0.01663, corrected -0.02197 to -0.01129 | demonstrated deficit |
| mid-major | 137,296 | -0.00962, corrected -0.01319 to -0.00604 | demonstrated deficit |
| low-major | 94,182 | -0.00776, corrected -0.01103 to -0.00449 | demonstrated deficit |

A **negative** advantage is the model scoring worse than the price it is betting into. The verdict column reads the sign the same way every other interval in this repository does; it is a Brier difference and not a return, and it is never added to one.

In high-major (0.25118 against 0.25000, 62,163 rows) the model's Brier is worse than the base rate: beaten by always predicting the league average.

**Calibration, over the whole population and over the bets the model selected.** These are counts of rows across Division I rather than a return, and they are reported together because only the second one is evidence about the bets this lab would place:

- overall: **0.4 pp underconfident** over 566,370 rows
- on the bets it **selected**: **10.4 pp overconfident** over 189,381 rows

The overall figure is not evidence about a betting policy. Nothing stakes money on the overall population.

## The held-out test

The held-out test is 2025, 2026 (held out), discovered on 2021-2024 and **not declared in advance** — the seasons held out were chosen after the discovery numbers had been seen, so this is a second look at the data rather than a pre-registered test. It graded 71,778 held-out bets over 9,776 games against 119,275 on the discovery seasons, across 32 cells:

- did not replicate: **0** of 32
- not enough evidence: **3** of 32
- nothing to replicate: **9** of 32
- replicated: **0** of 32
- reversed: **0** of 32
- untestable: **20** of 32

*Not enough evidence* and *nothing to replicate* are not failures to replicate. A cell with no discovery claim had nothing to carry forward, and a cell below the floor the criteria declared in advance prints a phrase and not a number. Neither is a pass, an avoid, or a no-value call.

## What this does not settle

- **One price window.** Every number above is measured at the `card` snapshot and says nothing about any other.
- **The half-point decomposition was refused, not computed.** The ticket-margin reconstruction agreed with the recorded outcome on 162,340 of 189,381 settled bets (85.7%), below the bar this repository set for using it, so how much of any spread or total figure is half a point at a key number is still open.
- **9 of 32 cells are below the 200-bet floor declared in advance** and carry a phrase rather than a number: `total_points_h1 / high_major` (184 bets), `moneyline_h1 / mid_major` (184 bets), `alternate_team_total / mid_major` (91 bets), `moneyline_h1 / low_major` (82 bets), `moneyline_h1 / high_major` (54 bets), `alternate_team_total / low_major` (11 bets), `spread / unplaced` (3 bets), `total_points / unplaced` (2 bets), `moneyline / unplaced` (1 bet). A market in that list is not a market judged to have no value; it is a market with no price-based evidence either way.
- **Nothing here is a forward result.** Every number above is a historical backtest, bet into prices somebody has already seen resolve. The forward ledger is untouched by all of it and is the only evidence that can still grow.
