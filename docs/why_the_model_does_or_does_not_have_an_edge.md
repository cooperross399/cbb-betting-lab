# Why the model does not have an edge

**Generated from `data/outputs/cbb_price_backtest.json`.** Every figure is read
from that record rather than typed, so this cannot drift from the measurement.
Re-render whenever the record changes.

Read `docs/what_we_can_and_cannot_claim.md` first. This says what the evidence
*is*; that says how to read it.

## The answer

**No demonstrated edge, on 118,050 graded bets across
32 market-and-tier cells.** 0 cell shows a demonstrated
edge. 1 shows a demonstrated deficit.

| Cut | Result |
|:---|:---|
| high-major | 24,691 bets, **-3.1%**, corrected -10.0% to +3.8% — no demonstrated edge |
| mid-major | 58,633 bets, **-4.1%**, corrected -9.0% to +0.9% — no demonstrated edge |
| low-major | 34,720 bets, **-4.3%**, corrected -10.0% to +1.4% — no demonstrated edge |
| **pooled** | 118,050 bets, **-3.9%**, corrected -7.2% to -0.7% — demonstrated deficit |

Pooled is listed last and is never the headline: the three tiers are three
distributions and the brief forbids a single Division I number standing alone.

## A correction, and it is the point of re-measuring

**An earlier version of this document said low-major was "the only tier whose
interval excludes zero, and it excludes zero on the losing side".** That was
true of the core team markets alone — low-major then read −3.9%, corrected
−7.4% to −0.3%, a demonstrated deficit.

It is **no longer true**. With the alternate ladders and the halves added, the
same tier reads -4.3%, corrected
-10.0% to +1.4%
— **no demonstrated edge**.

Nothing about the model changed. The population did: the new markets are one
season deep and thin, which widens every interval they enter. A deficit that
survives on four seasons of three markets and dissolves when a fifth is added
was **fragile to the population all along**, and the earlier wording did not
say so because at the time there was nothing to say it against.

The direction is unchanged and worth keeping: low-major is still the worst
tier by point estimate, and the lab was built expecting it to be the best.

## The thesis this lab was built on is still contradicted

The reason for a fourth lab was market heterogeneity — *"360 teams on a Tuesday
night in January"* being priced with less attention than a 32-team league, so
softness should appear at the low-major end. Low-major is the **worst** tier by
point estimate in both measurements. Whatever is different about that board,
this model is not better there.

## The model is not worthless — it is beaten by the vig

Blind betting is far worse than the model. The worst blind sides that clear the
200-bet floor:

- `high_major / alternate_total_points / always under`: 6,618 bets, **-25.3%**
- `mid_major / alternate_spread / always home`: 18,066 bets, **-21.7%**
- `mid_major / alternate_total_points / always the underdog`: 25,824 bets, **-18.1%**
- `low_major / spread_h1 / always home`: 654 bets, **-16.9%**
- `high_major / alternate_spread / always the favourite`: 2,285 bets, **-15.9%**

The pooled model figure of **-3.9%** beats every one of them. The
model carries information and not enough of it to cross the hold. A model
returning the blind figure would be worth deleting; this one is worth keeping
and still not worth betting.

## Three instruments agree, and none of them is the return

- **Forecast skill.** The model loses to the market on Brier in every tier
  **with the vig left in** — pooled advantage −0.01312 [−0.01468, −0.01156]. In
  high-major its Brier is worse than the base rate: beaten by always predicting
  the league average.
- **Anti-predictiveness.** By claimed edge, the shortfall widens **11.8 pp**
  from the smallest bucket to the largest. The biggest claimed edges do worst,
  so raising the edge threshold is the wrong response — the one move a
  disappointing backtest invites.
- **Calibration on selected bets.** Overall
  **0.5 pp underconfident**
  over 369,902 rows; on the bets it **selected**,
  **10.0 pp overconfident** over
  116,891. Every selected bin is over-predicted.
  The overall figure is not evidence.

## What this does not settle

- **The new markets are one season deep.** Ladders and halves were bought for
  2024 only before the credit cap bound, so every figure on them rests on a
  few hundred events and says so.
- **Props and futures are still unbought.** Nothing here speaks to them.
- **One price window**, card time T−60m.
- **The half-point decomposition was refused, not computed** — the ticket-margin
  reconstruction verified below the 99% bar, so how much of any spread or total
  figure is half a point at a key number is still open.
- **Reachability is unmeasured.** There is no in-season line-movement store to
  split on, and there will not be before November.
- **The forward ledger is untouched by all of this** and is the only evidence
  that can still grow.

