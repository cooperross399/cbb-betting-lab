# Proposed: allowlist every wired market

**This file is a proposal. It allowlists nothing, and it cannot.** It is the
evidence Claude prepares so that Cooper can decide. `grant()` does not exist in
`src/cbb_betting_lab/staging_provider_policy.py`, `data/manual/README.md` names
Cooper as the only writer of the policy file, and `CLAUDE.md` says in as many
words that this lab may withdraw an allowlist and may never give one. Nothing
here was signed, and no receipt was written or drafted.

## What was asked for

Cooper, 2026-09-25: *"i want every market allowlisted. If it never produces a
pick then so be it but i want it to try."*

That is a decision about what to run forward and accumulate a live record on,
not a claim that an edge exists. This page is written on that basis. It does
not argue the markets are good. It says, per market, what is known, what has
never been measured, and — the part that matters most for the instruction —
**which of them a receipt would not actually make try.**

## What is allowlisted today

Ten markets, each behind a receipt signed on 2026-09-23 and verified by the
`Policy Gate` check: `alternate_spread`, `alternate_team_total`,
`alternate_total_points`, `moneyline`, `moneyline_h1`, `spread`, `spread_h1`,
`team_total`, `total_points`, `total_points_h1`.

The registry wires thirty-five markets in total, so twenty-five are not
allowlisted. Enumerated from `markets.MARKETS_BY_KEY`, not from prose.

## Why this page is not the policy edit

The policy file is not a switch. `load()` verifies a receipt for **every**
allowlisted market and, on the first market that lacks one, forces the whole
policy to manual-only — fail closed, whole, not market by market.

Measured on a sandbox copy of `data/manual/`, with the twenty-five added and no
new receipts written:

- before: mode `allowlisted`, `allows("moneyline")` is **True**, no receipt failures;
- after: mode `manual_only`, `allows("moneyline")` is **False**, twenty-five receipt failures;
- the ten markets that work today — every one of them — **stop being usable.**

So writing the twenty-five in without receipts does not give the card
twenty-five more markets to try. It gives it none, and takes away ten. It also
turns `Policy Gate` red. The instruction and the mechanism point the same way:
the twenty-five need twenty-five signatures, and a partial grant is worse than
no grant.

## The evidence bundle's own recommendation, verbatim

`scripts/run_what_we_can_claim.py --competition cbb --rerender`, re-run against
the records on disk (the report it rendered was byte-identical to the committed
one, so nothing here has drifted):

> **The only result that survives is a loss.** 32 market-and-tier cell(s) across 10 market(s) are measured against real prices. None excludes zero on the winning side; 5 exclude(s) it on the **losing** side after correcting for everything this lab has ever tested, which is a **demonstrated deficit** […]

> This run read records, rendered markdown, and touched no network. It allowlisted no market, signed no receipt and spent no credit.

and one of the standing notes the same document carries:

> **No market reaches the card without a reviewed human acceptance receipt**, whatever the numbers above say. This lab may withdraw an allowlist and may never grant one.

**The bundle recommends enabling nothing.** This proposal is made against that
recommendation, deliberately and on Cooper's instruction, because the
instruction is about running a card forward rather than about what the
back-measurement found.

## Known limitations, per market

**None of the twenty-five has ever been measured against a real price.** The
price backtest covers ten markets and every one of them is already allowlisted.
There is no ROI and no sample size to state for any market on this list, and
none is stated. A market with no price-based evidence is not a market judged to
have no value — it is a market with no evidence either way.

| Market | Tier | Settles on | Archive | Would a receipt make it try? |
|:---|---:|:---|:---|:---|
| `moneyline_h2` | 2 | `half_margin` | archive has it — 95 of 102 probed events, 3 books | yes, once a price is bought |
| `spread_h2` | 2 | `half_margin` | archive has it — 101 of 102 probed events, 3 books | yes, once a price is bought |
| `team_total_h1` | 2 | `half_team_score` | archive has it — 101 of 102 probed events, 6 books | yes, once a price is bought |
| `team_total_h2` | 2 | `half_team_score` | archive has it — 100 of 102 probed events, 2 books | yes, once a price is bought |
| `total_points_h2` | 2 | `half_total` | archive has it — 100 of 102 probed events, 3 books | yes, once a price is bought |
| `player_assists` | 3 | `player_assists` | archive has it — 60 of 102 probed events, 11 books | no — availability gate |
| `player_blocks` | 3 | `player_blocks` | archive has it — 44 of 102 probed events, 2 books | no — availability gate |
| `player_blocks_steals` | 3 | `player_blocks_steals` | archive has it — 27 of 102 probed events, 2 books | no — availability gate |
| `player_double_double` | 3 | `player_double_double` | archive has it — 30 of 102 probed events, 4 books | no — refused by the model by name |
| `player_field_goals` | 3 | `player_field_goals_made` | **never fetched** — 0 of 102 probed events returned a price | no — availability gate |
| `player_first_basket` | 3 | `player_first_basket` | archive has it — 28 of 102 probed events, 6 books | no — refused by the model by name |
| `player_first_team_basket` | 3 | `player_first_team_basket` | **never fetched** — 0 of 102 probed events returned a price | no — availability gate |
| `player_frees_attempts` | 3 | `player_free_throws_attempted` | **never fetched** — 0 of 102 probed events returned a price | no — availability gate |
| `player_frees_made` | 3 | `player_free_throws_made` | **never fetched** — 0 of 102 probed events returned a price | no — availability gate |
| `player_points` | 3 | `player_points` | archive has it — 61 of 102 probed events, 11 books | no — availability gate |
| `player_points_assists` | 3 | `player_points_assists` | archive has it — 49 of 102 probed events, 2 books | no — availability gate |
| `player_points_rebounds` | 3 | `player_points_rebounds` | archive has it — 52 of 102 probed events, 4 books | no — availability gate |
| `player_pra` | 3 | `player_pra` | archive has it — 49 of 102 probed events, 6 books | no — availability gate |
| `player_rebounds` | 3 | `player_rebounds` | archive has it — 60 of 102 probed events, 11 books | no — availability gate |
| `player_rebounds_assists` | 3 | `player_rebounds_assists` | archive has it — 49 of 102 probed events, 1 book | no — availability gate |
| `player_steals` | 3 | `player_steals` | archive has it — 47 of 102 probed events, 2 books | no — availability gate |
| `player_threes` | 3 | `player_threes_made` | archive has it — 56 of 102 probed events, 11 books | no — availability gate |
| `player_triple_double` | 3 | `player_triple_double` | **never fetched** — 0 of 102 probed events returned a price | no — availability gate |
| `player_turnovers` | 3 | `player_turnovers` | archive has it — 46 of 102 probed events, 1 book | no — availability gate |
| `championship_winner` | 4 | `tournament_champion` | **never probed** — futures, served under a separate provider sport key | not established |

The archive column is the 2026-09-01 retention probe, read from
`data/outputs/cbb_retention_probe.json`. "Never fetched" means the probe asked
and no book returned a price on any probed event — it is a fact about the
archive, not about the budget: the probe completed inside its cap.
`championship_winner` was never probed at all, so there is no reading for it in
either direction.

## Which of these a signature would actually move

- **Five markets — the four second halves and the first-half team total.** A
  receipt removes the policy block; it does not by itself produce a selection,
  and nothing has been bought for them yet, so they try only after a purchase.
  These are the only markets on the list where the policy file is the thing
  standing in the way.
- **Seventeen player props.** They cannot produce a selection whatever the
  policy says. Nothing in this sport reaches `Availability.CONFIRMED`: ESPN's
  men's-college-basketball injuries endpoint is empty, CollegeBasketballData has
  no availability endpoint, and the conference reports that exist cover roughly
  a third of the division, conference games only. **Allowlisting them changes
  nothing observable.** What would make them try is an availability source, and
  that is a data problem, not a policy one.
- **Two markets refused by the model by name** — `player_double_double` and
  `player_first_basket`. These are never priced at all, for reasons recorded in
  the model's own words in `data/outputs/cbb_what_we_can_claim.md`. A receipt
  does not reach them either; a model decision would.
- **One futures market.** Nothing has been bought and nothing has settled. It
  also settles on a clock measured in months, and this lab never folds a futures
  return into a headline over game bets, so it would need a hold-time convention
  before a number from it could be read.

So of the twenty-five, **five would begin trying on a signature plus a purchase,
one is untested, and nineteen would not begin trying at all.** That is the part
of the instruction the policy file cannot deliver, and it is better said here
than discovered in March from a card that never carried a prop.

## No market on this page is recorded as probed or retained

Nothing here sets a retention verdict for any market. The five marked **never
fetched** are recorded as never fetched. `championship_winner` is recorded as
never probed. Neither is a judgement that the market is unavailable, and neither
may be turned into one without a probe that ran in season.

## What Cooper does next, if he wants this

One receipt per market under `data/manual/human_acceptance_receipts/`, then the
matching entries in `data/manual/staging_provider_policy.json`, in a pull
request whose `Policy Gate` is green. The required fields, and what the gate
checks about each, are in `data/manual/README.md`. Claude wrote no receipt and
no template for one.

A receipt cites an evidence record and its sha256. For a market with no
price-based evidence, the honest citation is the document that says so:

```
shasum -a 256 data/outputs/cbb_what_we_can_claim.md
```

That hash moves every time the experiment ledger grows and the report
re-renders, which will take the receipts stale and turn `Policy Gate` red. That
is the designed behaviour — it is how the NHL lab caught its own stale
approval — and not a fault to work around.
