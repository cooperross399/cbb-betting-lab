# What this costs, and the decisions the arithmetic forced

The **arithmetic** is generated, not written: `data/outputs/cbb_credit_cost.md`,
rebuilt by `scripts/estimate_credit_cost.py` from the real cached schedule. It
spends nothing and touches no network. Read it for the numbers.

This file holds the **reasoning**, and it lives separately for a reason the NHL
lab learned by losing one: a finding appended to a regenerated file lasts
exactly one re-run.

## The one number that decides the whole purchase programme

**The full catalogue costs 35,173,680 credits. The account holds 4,992,714.**

That is not a near miss to be optimised away. Buying every market, every
alternate rung and every prop across the three seasons the provider retains
them for costs **seven times the entire remaining balance**. No ordering, cap
or scheduling trick changes that, and a plan that pretends otherwise would
spend four million credits discovering it.

So the purchase is **prioritised, not complete**, and the brief already named
the order: core team markets across every season first, then ladders, then
props, then futures. That order is also, and not coincidentally, the order of
decreasing confidence that a market is quoted at all on a Tuesday night in
January in the Ohio Valley Conference.

## Two dates decide what is buyable at all

Both are the provider's, both were read from its documentation and confirmed
against its responses rather than assumed:

- **Featured markets** — `h2h`, `spreads`, `totals` — exist for
  `basketball_ncaab` from **2020-11-16**.
- **Everything else** — every prop, every half, every alternate ladder — exists
  from **2023-05-03**, site-wide.

The second date falls *after* the 2022-23 season ended. So the full catalogue
is buyable for **three seasons and no more** (2023-24, 2024-25, 2025-26), while
the featured markets reach back **six**.

This is the single most important structural fact about this lab's evidence,
and it cuts in a direction worth stating plainly: **the deepest population this
lab can ever have is the shallowest catalogue.** 32,379 games of moneyline,
spread and total is the largest priced population any of these four labs has
ever assembled — an order of magnitude more than the NHL lab's 2,710 events and
forty times the football lab's 816. And it holds three markets.

That is the trade the brief's own thesis rests on. Cooper's case for a fourth
lab was sample size: *"If there is an edge here, this lab can prove it inside
one season."* The arithmetic says he is right about the team markets and wrong
about the props, and the purchase order follows the arithmetic.

## Why the peak day is opening Monday, and why that sets every cap

The largest slate of a college basketball season is its **first**, not a
February Saturday: **200 games on the opening Monday of 2023**. February
Saturdays run 120-155.

Every cap in this repository is set against 200 rather than against the median
of 32, because **a cap below the worst slate is a cap that starves it**, and a
starved fetch and an unquoted market look identical in the reports. The NHL
lab's probe once reported its own starvation as market absence. Every report
here states the cap it ran under and the credits it actually spent, so the two
can be told apart by reading rather than by remembering.

## What the live season costs, and why it is a rounding error

Featured markets come from the **bulk** endpoint: 3 keys x 2 regions = **6
credits for the entire slate**, whatever its size. On a 200-game day that is
200 games for 6 credits. This is why the featured markets are never asked per
event, and it is the reason the live season is affordable at any cadence.

Everything else is per-event, at a pessimistic 96 credits a game. Two snapshots
a day across a full season bounds at 1,106,148 — inside the monthly
authorisation, but only just, and only because the bound assumes every market
returns at every book, which no low-major game will.

The live fetch is protected from the purchase structurally rather than by
arithmetic: the purchase runs under its own cap in its own workflow, and the
card's fetch reads `x-requests-remaining` and refuses to start if it cannot
cover its own cap. **A run that starts on a thin quota gets partway through the
slate and stops, freezing a biased subset into the ledger as though it were the
day.** That is worse than not running, because the ledger cannot tell afterwards
that it happened.

## The ceiling, and where it actually binds

Cooper's standing authorisation is **1,500,000 credits per calendar month**,
with the instruction to scale it down if the real quota will not carry it
alongside the siblings' committed spend. The siblings commit **36,175 a month**
(NHL 26,091, football 10,084) — under 1% of the balance, and not a constraint.

The binding constraint is the **balance**, not the ceiling: 4,992,714 total
against a 1,500,000 monthly permission means the account holds about three and
a third months of fully-authorised spending, once, with no reset that refills
it. Every credit spent here is spent permanently.

That reframes the purchase from "which markets fit in a month" to **"which
markets are worth a third of everything we will ever have"**, and it is why the
retention probe runs first. Buying a market the archive does not retain, or
retains too thinly to measure against, spends real credits on rows no join will
ever find.

## The arithmetic that is deliberately absent

**What a season of forward evidence costs is not estimated here**, because it
is not a purchase. It is the live fetch, already counted, and it is the only
evidence that cannot be bought at any price. Historical prices can be bought;
forward evidence cannot be back-dated, and in this sport a missed night is up
to two hundred games.
