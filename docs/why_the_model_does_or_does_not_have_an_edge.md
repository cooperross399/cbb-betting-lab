# Why the model does or does not have an edge

**The block between the markers below is generated**, by
`scripts/run_why_the_model.py`, from `data/outputs/cbb_price_backtest.json`,
`data/outputs/cbb_forecast_skill.json` and the held-out replication record.
Every figure in it is read from a record rather than typed, and
`scripts/run_weekly_loop.py` re-splices it every week, so it cannot drift from
the measurement. The generator refuses to render at all when one of the three
records is absent — a page that weighs two instruments and reads like an answer
is worse than no page.

**This heading is deliberately neutral**, and the generated answer below carries
its own. The file used to be titled *"Why the model does not have an edge"* over
figures that were typed by hand under a line claiming they were not; a title
that states the conclusion is a title that outlives the measurement.

Read `docs/what_we_can_and_cannot_claim.md` first. This says what the evidence
*is*; that says how to read it.

<!-- BEGIN GENERATED: why_the_model -->

Every figure below is read from a record on disk by `scripts/run_why_the_model.py`, never typed. The records, and the moment each stamped itself with:

- **price backtest** — `data/outputs/cbb_price_backtest.json`, generated 2026-09-18T03:02:12Z
- **forecast skill** — `data/outputs/cbb_forecast_skill.json`, generated 2026-09-18T03:04:50Z
- **held-out replication** — `data/outputs/holdout/cbb_replication.json`, generated 2026-09-18T00:22:10Z

Read `docs/what_we_can_and_cannot_claim.md` first. This says what the evidence *is*; that says how to read it.

## The answer

**No demonstrated edge in any of the 3 measured tiers** (high-major 37,939 bets, mid-major 81,404 bets, low-major 56,340 bets). 2 shows a demonstrated deficit: mid-major 81,404 bets, **-5.5%**, corrected -9.5% to -1.4% — demonstrated deficit; low-major 56,340 bets, **-4.6%**, corrected -8.8% to -0.3% — demonstrated deficit.

Measured on 175,690 graded bets over 26,622 games and 791 days of the 2021-2026 seasons, across 32 market-and-tier cells.

Every interval is corrected for 133 cumulative distinct hypotheses — the experiment ledger's count at render time, not the count when the backtest ran — which widens each one by x1.81. The correction can only ever get stricter as the search continues, which is the only direction it is allowed to move.

| Tier | Result |
|:---|:---|
| high-major | 37,939 bets, **-4.2%**, corrected -9.7% to +1.4% — no demonstrated edge |
| mid-major | 81,404 bets, **-5.5%**, corrected -9.5% to -1.4% — demonstrated deficit |
| low-major | 56,340 bets, **-4.6%**, corrected -8.8% to -0.3% — demonstrated deficit |
| unplaced | not enough evidence (7 bets, below the 200 declared in advance) |

Cut finer, by market **and** tier: **0 of 32 cells shows a demonstrated edge** and **5 shows a demonstrated deficit**, over the 22 that clear the floor declared in advance.

- `moneyline / high_major`: 4,393 bets, **-11.1%**, corrected -21.4% to -0.7% — demonstrated deficit
- `moneyline / mid_major`: 8,873 bets, **-8.0%**, corrected -14.7% to -1.4% — demonstrated deficit
- `team_total / mid_major`: 11,618 bets, **-6.3%**, corrected -10.1% to -2.5% — demonstrated deficit
- `moneyline / low_major`: 6,967 bets, **-9.8%**, corrected -16.7% to -2.8% — demonstrated deficit
- `total_points / low_major`: 17,978 bets, **-5.2%**, corrected -9.5% to -0.9% — demonstrated deficit

### The tier this lab was built expecting to be the best

The reason for a fourth lab was market heterogeneity — 360 teams on a Tuesday night in January being priced with less attention than a 32-team league, so softness should appear at the low-major end. By point estimate the **worst** measured tier is **mid-major**: 81,404 bets, **-5.5%**, corrected -9.5% to -1.4% — demonstrated deficit. Whatever is different about that board, this model is not better there.

### The pooled figure, which is not the answer

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

Pooled across every market and tier: 175,690 bets, **-4.9%**, corrected -7.5% to -2.3% — demonstrated deficit.

### A claim this document has retracted, recorded 2026-09-04

Before this block was generated, this document said of **low-major** that it was *“the only tier whose interval excludes zero, and it excludes zero on the losing side”* — a demonstrated deficit. That was measured on the core team markets alone, before the alternate ladders and the halves entered the population.

**It still holds.** On today's record low-major reads 56,340 bets, **-4.6%**, corrected -8.8% to -0.3% — demonstrated deficit.

## The model is not worthless — it is beaten by the vig

The worst blind sides that clear the 200-bet floor declared in advance:

- `high_major / alternate_total_points / always under`: 6,618 bets, **-25.3%**
- `mid_major / alternate_spread / always home`: 15,628 bets, **-20.8%**
- `high_major / moneyline / always the underdog`: 6,207 bets, **-19.8%**
- `high_major / moneyline / always away`: 6,213 bets, **-19.5%**
- `low_major / spread_h1 / always home`: 593 bets, **-19.3%**

Each is a rule that needs no model at all. All 3 measured tiers return more than every one of them. That is what *the model carries information* means here, and it is a different statement from *the model beats the price* — which is the one the next section tests.

## Three instruments, and none of them is the return

**Brier against the market, per tier, with the vig left in.**

| Tier | Rows | Model minus raw market | Reading |
|:---|---:|:---|:---|
| high-major | 53,844 | -0.01783, corrected -0.02379 to -0.01186 | demonstrated deficit |
| mid-major | 127,094 | -0.01066, corrected -0.01429 to -0.00704 | demonstrated deficit |
| low-major | 89,546 | -0.00782, corrected -0.01120 to -0.00444 | demonstrated deficit |

A **negative** advantage is the model scoring worse than the price it is betting into. The verdict column reads the sign the same way every other interval in this repository does; it is a Brier difference and not a return, and it is never added to one.

In high-major (0.25160 against 0.25000, 53,844 rows) the model's Brier is worse than the base rate: beaten by always predicting the league average.

**Anti-predictiveness, per tier — the realised RETURN by claimed edge.** Not the shortfall against the model's own probability: that is overconfidence, which the model's own selection produces almost mechanically, and it is a different quantity reported elsewhere. This is what the wagers paid.

- high-major: the return falls by **-0.6 pp** from the smallest claimed-edge bucket to the largest across 8 usable buckets (21,290 rows in the smallest, 9,559 in the largest), and the two family-corrected intervals **overlap, so the fall is not demonstrated**.
  - claimed-edge bucket (below -10%): 21,290 bets, **-3.5%**, corrected -9.0% to +2.1% — no demonstrated edge
  - claimed-edge bucket (-10% to -5%): 4,642 bets, **-0.8%**, corrected -8.4% to +6.8% — no demonstrated edge
  - claimed-edge bucket (-5% to +0%): 4,847 bets, **-5.2%**, corrected -11.9% to +1.6% — no demonstrated edge
  - claimed-edge bucket (+0% to +2%): 1,769 bets, **-6.4%**, corrected -19.6% to +6.7% — no demonstrated edge
  - worst-returning bucket (+2% to +5%): 2,474 bets, **-9.5%**, corrected -19.1% to +0.1% — no demonstrated edge
  - claimed-edge bucket (+5% to +10%): 3,654 bets, **-4.7%**, corrected -15.4% to +6.0% — no demonstrated edge
  - claimed-edge bucket (+10% to +20%): 5,609 bets, **-3.8%**, corrected -12.4% to +4.8% — no demonstrated edge
  - claimed-edge bucket (+20% and above): 9,559 bets, **-2.9%**, corrected -10.9% to +5.2% — no demonstrated edge
- mid-major: the return falls by **1.4 pp** from the smallest claimed-edge bucket to the largest across 8 usable buckets (46,974 rows in the smallest, 16,132 in the largest), and the two family-corrected intervals **overlap, so the fall is not demonstrated**.
  - claimed-edge bucket (below -10%): 46,974 bets, **-4.3%**, corrected -8.8% to +0.1% — no demonstrated edge
  - claimed-edge bucket (-10% to -5%): 13,774 bets, **-1.4%**, corrected -5.5% to +2.8% — no demonstrated edge
  - claimed-edge bucket (-5% to +0%): 14,264 bets, **-4.0%**, corrected -8.6% to +0.5% — no demonstrated edge
  - claimed-edge bucket (+0% to +2%): 5,177 bets, **-4.8%**, corrected -12.4% to +2.7% — no demonstrated edge
  - claimed-edge bucket (+2% to +5%): 7,278 bets, **-5.1%**, corrected -12.0% to +1.9% — no demonstrated edge
  - worst-returning bucket (+5% to +10%): 10,038 bets, **-6.2%**, corrected -12.8% to +0.5% — no demonstrated edge
  - claimed-edge bucket (+10% to +20%): 13,457 bets, **-2.7%**, corrected -9.2% to +3.8% — no demonstrated edge
  - claimed-edge bucket (+20% and above): 16,132 bets, **-5.7%**, corrected -12.8% to +1.4% — no demonstrated edge
- low-major: the return falls by **2.7 pp** from the smallest claimed-edge bucket to the largest across 8 usable buckets (31,462 rows in the smallest, 9,225 in the largest), and the two family-corrected intervals **overlap, so the fall is not demonstrated**.
  - claimed-edge bucket (below -10%): 31,462 bets, **-3.1%**, corrected -7.7% to +1.6% — no demonstrated edge
  - claimed-edge bucket (-10% to -5%): 10,863 bets, **-0.6%**, corrected -4.8% to +3.6% — no demonstrated edge
  - claimed-edge bucket (-5% to +0%): 10,587 bets, **-5.3%**, corrected -9.7% to -0.8% — demonstrated deficit
  - claimed-edge bucket (+0% to +2%): 3,985 bets, **-1.4%**, corrected -9.2% to +6.5% — no demonstrated edge
  - claimed-edge bucket (+2% to +5%): 5,418 bets, **-4.1%**, corrected -11.5% to +3.3% — no demonstrated edge
  - claimed-edge bucket (+5% to +10%): 7,820 bets, **-3.9%**, corrected -10.2% to +2.5% — no demonstrated edge
  - claimed-edge bucket (+10% to +20%): 10,186 bets, **-5.5%**, corrected -12.6% to +1.6% — no demonstrated edge
  - worst-returning bucket (+20% and above): 9,225 bets, **-5.8%**, corrected -14.0% to +2.3% — no demonstrated edge

A bucket whose family-corrected interval lies entirely below zero is worse than no edge, not the same as it: in low-major -5% to +0% the model's own claimed edge selected wagers that lost money on the evidence of this run. Each is printed above with the corrected interval this sentence is read off.

**Calibration, over the whole population and over the bets the model selected.** These are counts of rows across Division I rather than a return, and they are reported together because only the second one is evidence about the bets this lab would place:

- overall: **0.4 pp underconfident** over 526,728 rows
- on the bets it **selected**: **10.4 pp overconfident** over 174,136 rows

The overall figure is not evidence about a betting policy. Nothing stakes money on the overall population.

## The held-out test

The held-out test is 2025, 2026 (held out), discovered on 2021-2024 and **not declared in advance** — the seasons held out were chosen after the discovery numbers had been seen, so this is a second look at the data rather than a pre-registered test. It graded 65,008 held-out bets over 9,810 games against 110,682 on the discovery seasons, across 32 cells:

- did not replicate: **0** of 32
- not enough evidence: **3** of 32
- nothing to replicate: **9** of 32
- replicated: **0** of 32
- reversed: **0** of 32
- untestable: **20** of 32

*Not enough evidence* and *nothing to replicate* are not failures to replicate. A cell with no discovery claim had nothing to carry forward, and a cell below the floor the criteria declared in advance prints a phrase and not a number. Neither is a pass, an avoid, or a no-value call.

## What this does not settle

- **One price window.** Every number above is measured at the `card` snapshot and says nothing about any other.
- **The half-point decomposition was refused, not computed.** The ticket-margin reconstruction agreed with the recorded outcome on 153,347 of 174,136 settled bets (88.1%), below the bar this repository set for using it, so how much of any spread or total figure is half a point at a key number is still open.
- **10 of 32 cells are below the 200-bet floor declared in advance** and carry a phrase rather than a number: `spread_h1 / high_major` (189 bets), `total_points_h1 / high_major` (181 bets), `moneyline_h1 / mid_major` (168 bets), `moneyline_h1 / low_major` (79 bets), `moneyline_h1 / high_major` (47 bets), `alternate_team_total / mid_major` (13 bets), `alternate_team_total / low_major` (10 bets), `spread / unplaced` (3 bets), `total_points / unplaced` (3 bets), `moneyline / unplaced` (1 bet). A market in that list is not a market judged to have no value; it is a market with no price-based evidence either way.
- **Nothing here is a forward result.** Every number above is a historical backtest, bet into prices somebody has already seen resolve. The forward ledger is untouched by all of it and is the only evidence that can still grow.

<!-- END GENERATED -->

## Why there is nothing below this line

Every figure about this model lives inside the generated block above, including
the retraction of a claim an earlier version of this document made. There used
to be a hand-written note here headed *the figures in this section are
historical* which then hand-typed the tier's **current** return and corrected
interval underneath it, so a re-measurement moved the table above and left the
paragraph below saying what the tier used to read. That note is now rendered
from the record like everything else, and
`tests/test_why_the_model.py::test_no_figure_is_typed_outside_the_generated_fence`
keeps this page free of typed figures.
