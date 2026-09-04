# Why the model does not have an edge

**Generated from `data/outputs/cbb_price_backtest.json`, the run record of the
price backtest over the full bought population.** Every figure below is read
from that file rather than typed, so this document cannot drift from the
measurement that produced it. Re-render it whenever the record changes.

Read `docs/what_we_can_and_cannot_claim.md` first. This file says what the
evidence *is*; that one says how to read it.

## The answer

**No demonstrated edge, on 86,351 graded bets.** Where an
interval excludes zero it does so on the losing side, and this document calls
that a **demonstrated deficit** rather than an edge, because the sign is read
rather than assumed.

| Cut | Result |
|:---|:---|
| high-major | 19,565 bets, **-2.0%**, corrected -6.3% to +2.3% — no demonstrated edge |
| mid-major | 40,179 bets, **-1.9%**, corrected -5.0% to +1.3% — no demonstrated edge |
| low-major | 26,601 bets, **-3.9%**, corrected -7.4% to -0.3% — demonstrated deficit |
| **pooled** | 86,351 bets, **-2.5%**, corrected -4.6% to -0.4% — demonstrated deficit |

Pooled is listed last and is never the headline. High-major, mid-major and
low-major are three different distributions and the brief forbids a single
Division I number standing alone.

## The thesis this lab was built on is contradicted

The reason for a fourth lab was market heterogeneity: *"A 32-team league priced
by every book is the hardest possible case. 360 teams on a Tuesday night in
January is the opposite."* The expectation was that softness would show up at
the low-major end.

**It is the low-major tier that carries the only interval excluding zero, and
it excludes zero on the losing side.** High-major and mid-major both span zero;
low-major does not. Whatever is different about the low-major board, this model
is worse there, not better.

That is a real finding and it is the opposite of the one the lab was built to
look for. It is recorded here in the direction it came out.

## The model is not worthless — it is beaten by the vig

Betting blind returns far worse than the model does. From the same run record,
every blind side that clears the 200-bet floor is negative,
and the worst are heavily so:


- `high_major / team_total / always under`: 1,995 bets, **-13.9%**
- `high_major / moneyline / always away`: 4,837 bets, **-10.8%**
- `mid_major / team_total / always under`: 7,161 bets, **-8.2%**
- `mid_major / moneyline / always away`: 9,170 bets, **-7.6%**
- `mid_major / team_total / always the underdog`: 5,533 bets, **-7.4%**

The pooled model figure of **-2.5%** is better than every one of them.
So the model carries information — it simply does not carry enough to cross the
hold. That distinction matters: a model that returned the blind figure would be
worth deleting, and this one is worth keeping and improving.

**It is not worth betting.** A number that is better than blind and still
negative is a smaller loss, not a profit.

## What this does not settle

- **Four seasons of core team markets only.** `moneyline`, `spread`,
  `total_points` and `team_total`. Ladders, halves, player props and futures
  were not bought — the purchase cap bound first — so nothing here says
  anything about them.
- **One price window.** Every quote is card time, T-60m. A different lead is a
  different measurement.
- **The half-point decomposition was refused, not computed.** The ticket-margin
  reconstruction agreed with the recorded outcome on 83.8% of scorable bets,
  below the 99% the module requires, so it declined rather than compute on an
  unverified spread convention. How much of any spread or total figure is half
  a point at a key number is therefore **still open**.
- **Reachability is unmeasured.** The line-movement store holds no in-season
  captures yet, so nothing here is split by whether the price survived. An edge
  that lived only in vanishing prices would look identical to one that did not,
  and `reachability.py` exists to tell them apart once there is a season to
  measure.
- **The forward ledger is untouched by all of this.** It starts on
  2026-11-01 and is the only evidence that can still grow.

## What would change the answer

Nothing in `docs/when_this_ends.md` is loosened by this result. The stopping
rule was declared before the data existed and this measurement does not meet
the bar for continuing on the strength of a finding, because there is no
finding. The lab keeps running because forward evidence cannot be back-dated,
not because anything here is promising.

