# Why the model does not have a demonstrated edge

Every figure below is read from a record on disk by `scripts/run_why_the_model.py`, never typed. The records, and the moment each stamped itself with:

- **price backtest** — `data/outputs/cbb_price_backtest.json`, generated 2026-09-04T19:59:28Z
- **forecast skill** — `data/outputs/cbb_forecast_skill.json`, generated 2026-09-04T17:27:08Z
- **held-out replication** — `data/outputs/holdout/cbb_replication.json`, generated 2026-09-04T07:21:08Z

Read `docs/what_we_can_and_cannot_claim.md` first. This says what the evidence *is*; that says how to read it.

## The answer

**No demonstrated edge in any of the 3 measured tiers** (high-major 24,691 bets, mid-major 58,633 bets, low-major 34,720 bets). None shows a demonstrated deficit.

Measured on 118,050 graded bets over 16,634 games and 513 days of the 2021-2024 seasons, across 32 market-and-tier cells.

Every interval is corrected for 30 cumulative distinct hypotheses — the experiment ledger's count at render time, not the count when the backtest ran — which widens each one by x1.60. The correction can only ever get stricter as the search continues, which is the only direction it is allowed to move.

| Tier | Result |
|:---|:---|
| high-major | 24,691 bets, **-3.1%**, corrected -10.0% to +3.8% — no demonstrated edge |
| mid-major | 58,633 bets, **-4.1%**, corrected -9.0% to +0.9% — no demonstrated edge |
| low-major | 34,720 bets, **-4.3%**, corrected -10.0% to +1.4% — no demonstrated edge |
| unplaced | not enough evidence (6 bets, below the 200 declared in advance) |

Cut finer, by market **and** tier: **0 of 32 cells shows a demonstrated edge** and **1 shows a demonstrated deficit**, over the 23 that clear the floor declared in advance.

- `total_points / low_major`: 10,532 bets, **-5.2%**, corrected -10.2% to -0.2% — demonstrated deficit

### The tier this lab was built expecting to be the best

The reason for a fourth lab was market heterogeneity — 360 teams on a Tuesday night in January being priced with less attention than a 32-team league, so softness should appear at the low-major end. By point estimate the **worst** measured tier is **low-major**: 34,720 bets, **-4.3%**, corrected -10.0% to +1.4% — no demonstrated edge. Whatever is different about that board, this model is not better there.

### The pooled figure, which is not the answer

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

Pooled across every market and tier: 118,050 bets, **-3.9%**, corrected -7.2% to -0.7% — demonstrated deficit.

### A claim this document has retracted, recorded 2026-09-04

Before this block was generated, this document said of **low-major** that it was *“the only tier whose interval excludes zero, and it excludes zero on the losing side”* — a demonstrated deficit. That was measured on the core team markets alone, before the alternate ladders and the halves entered the population.

**It no longer holds.** On today's record low-major reads 34,720 bets, **-4.3%**, corrected -10.0% to +1.4% — no demonstrated edge.

Nothing about the model changed. The population did: the markets added since are one season deep and thin, which widens every interval they enter. A finding that survives on the narrower population and dissolves when the wider one is measured was fragile to the population all along, and the earlier wording did not say so because at the time there was nothing to say it against.

## The model is not worthless — it is beaten by the vig

The worst blind sides that clear the 200-bet floor declared in advance:

- `high_major / alternate_total_points / always under`: 6,618 bets, **-25.3%**
- `mid_major / alternate_spread / always home`: 18,066 bets, **-21.7%**
- `mid_major / alternate_total_points / always the underdog`: 25,824 bets, **-18.1%**
- `low_major / spread_h1 / always home`: 654 bets, **-16.9%**
- `high_major / alternate_spread / always the favourite`: 2,285 bets, **-15.9%**

Each is a rule that needs no model at all. All 3 measured tiers return more than every one of them. That is what *the model carries information* means here, and it is a different statement from *the model beats the price* — which is the one the next section tests.

## Three instruments, and none of them is the return

**Brier against the market, per tier, with the vig left in.**

| Tier | Rows | Model minus raw market | Reading |
|:---|---:|:---|:---|
| high-major | 19,384 | -0.01883, corrected -0.02452 to -0.01314 | demonstrated deficit |
| mid-major | 39,810 | -0.01268, corrected -0.01588 to -0.00948 | demonstrated deficit |
| low-major | 26,356 | -0.00966, corrected -0.01286 to -0.00646 | demonstrated deficit |

A **negative** advantage is the model scoring worse than the price it is betting into. The verdict column reads the sign the same way every other interval in this repository does; it is a Brier difference and not a return, and it is never added to one.

In high-major (0.25698 against 0.24996, 19,384 rows), mid-major (0.25181 against 0.24986, 39,810 rows), low-major (0.24967 against 0.24916, 26,356 rows) the model's Brier is worse than the base rate: beaten by always predicting the league average.

**Anti-predictiveness, per tier.** By claimed edge, the shortfall against the model's own probability widens from the smallest bucket to the largest by:

- high-major: **13.0 pp** across 4 usable buckets (2,515 rows in the smallest, 8,143 in the largest)
- mid-major: **12.2 pp** across 4 usable buckets (6,156 rows in the smallest, 13,868 in the largest)
- low-major: **9.6 pp** across 4 usable buckets (4,508 rows in the smallest, 7,421 in the largest)

The biggest claimed edges do worst in every tier that can be measured, so raising the edge threshold is the wrong response — and it is the one move a disappointing backtest invites.

**Calibration, over the whole population and over the bets the model selected.** These are counts of rows across Division I rather than a return, and they are reported together because only the second one is evidence about the bets this lab would place:

- overall: **0.5 pp underconfident** over 369,902 rows
- on the bets it **selected**: **10.0 pp overconfident** over 116,891 rows

The overall figure is not evidence about a betting policy. Nothing stakes money on the overall population.

## The held-out test

The held-out test is 2024 (held out), discovered on 2021-2023 and declared in advance on 2026-09-03. It graded 31,468 held-out bets over 4,628 games against 54,883 on the discovery seasons, across 12 cells:

- did not replicate: **0** of 12
- not enough evidence: **4** of 12
- nothing to replicate: **5** of 12
- replicated: **0** of 12
- reversed: **0** of 12
- untestable: **3** of 12

*Not enough evidence* and *nothing to replicate* are not failures to replicate. A cell with no discovery claim had nothing to carry forward, and a cell below the floor the criteria declared in advance prints a phrase and not a number. Neither is a pass, an avoid, or a no-value call.

## What this does not settle

- **One price window.** Every number above is measured at the `card` snapshot and says nothing about any other.
- **The half-point decomposition was refused, not computed.** The ticket-margin reconstruction agreed with the recorded outcome on 98,660 of 116,891 settled bets (84.4%), below the bar this repository set for using it, so how much of any spread or total figure is half a point at a key number is still open.
- **9 of 32 cells are below the 200-bet floor declared in advance** and carry a phrase rather than a number: `total_points_h1 / high_major` (184 bets), `moneyline_h1 / mid_major` (184 bets), `alternate_team_total / mid_major` (91 bets), `moneyline_h1 / low_major` (82 bets), `moneyline_h1 / high_major` (54 bets), `alternate_team_total / low_major` (11 bets), `spread / unplaced` (3 bets), `total_points / unplaced` (2 bets), `moneyline / unplaced` (1 bet). A market in that list is not a market judged to have no value; it is a market with no price-based evidence either way.
- **Nothing here is a forward result.** Every number above is a historical backtest, bet into prices somebody has already seen resolve. The forward ledger is untouched by all of it and is the only evidence that can still grow.
