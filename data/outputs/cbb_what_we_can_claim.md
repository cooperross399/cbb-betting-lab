# What the evidence actually supports — NCAA Division I men's basketball

Generated from the measurement records on disk, so it cannot drift from them. The hand-written rules — written before the first measurement, which is the whole point of them — live in `docs/what_we_can_and_cannot_claim.md`. **This file is re-rendered from its own run record and is never edited by hand.**

- Generated: 2026-09-05T16:56:49+00:00
- Sample floor: **200 bets**, declared in advance. Below it this document prints a phrase and not a number.

**The only result that survives is a loss.** 32 market-and-tier cell(s) across 10 market(s) are measured against real prices. None excludes zero on the winning side; 3 exclude(s) it on the **losing** side after correcting for everything this lab has ever tested, which is a **demonstrated deficit**: `team_total` / mid_major (historical price backtest, bets) at -5.8% over 13,478 bets across 384 days; `moneyline` / low_major (historical price backtest, bets) at -7.9% over 7,561 bets across 632 days; `total_points` / low_major (historical price backtest, bets) at -5.2% over 17,903 bets across 7,131 games. A demonstrated deficit is a finding, not a null result, and it is the finding this lab has.

## The correction this document applies

**62 distinct hypotheses have ever been tested here**, and every interval below is widened by **x1.71** before it means what it says. That is the ledger's **cumulative** count and never the day's: *a search that runs every week is not twelve tests, it is twelve tests a week, forever.*

- Alpha budget: **6 new hypotheses a week**, declared 2026-09-01. When it is spent the search waits; it never lowers the bar.
- 30 discovery, 32 holdout. Putting a discovery finding to the holdout is a second look and is counted as one.

The correction is re-applied here at render time rather than copied out of the record it came from. A backtest run in December carries December's family size; by March the ledger has grown and the same number means less. This can only ever make an interval wider.

## Measured against real prices

**Never pooled across Division I.** High-major, mid-major and low-major are different distributions, so every row below is one market in one tier. A policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all.

### Historical price backtest

Prices bought after the games resolved. **A backtest that beats the opening number is not a bet**, and no figure here is evidence that a price was reachable at card time.

| Market | Tier | Cut | Bets | Clusters | ROI | 95% interval | Family-corrected | Replication | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|
| `alternate_spread` | high_major | bets | 2,551 | 70 games | -10.4% | -33.0% to +12.2% | -49.1% to +28.2% | no held-out test has been run | no demonstrated edge |
| `alternate_total_points` | high_major | bets | 2,114 | 64 games | -1.1% | -31.0% to +28.7% | -52.1% to +49.8% | no held-out test has been run | no demonstrated edge |
| `moneyline` | high_major | bets | 5,510 | 712 days | -3.5% | -9.3% to +2.4% | -13.5% to +6.6% | not enough evidence on the 2025, 2026 (held out) window | no demonstrated edge |
| `moneyline_h1` | high_major | bets | 54 | 44 days | — | — | — | no held-out test has been run | not enough evidence (54 bets, below the 200 declared in advance) |
| `spread` | high_major | bets | 13,242 | 712 days | -1.7% | -4.4% to +0.9% | -6.2% to +2.8% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `spread_h1` | high_major | bets | 223 | 72 games | -24.7% | -47.9% to -1.5% | -64.4% to +15.0% | no held-out test has been run | no demonstrated edge |
| `team_total` | high_major | bets | 7,109 | 2,933 games | -2.8% | -5.5% to -0.2% | -7.4% to +1.7% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `total_points` | high_major | bets | 12,241 | 688 days | -3.3% | -6.4% to -0.3% | -8.5% to +1.8% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `total_points_h1` | high_major | bets | 184 | 57 games | — | — | — | no held-out test has been run | not enough evidence (184 bets, below the 200 declared in advance) |
| `alternate_spread` | mid_major | bets | 9,319 | 93 days | -3.4% | -13.9% to +7.1% | -21.4% to +14.6% | no held-out test has been run | no demonstrated edge |
| `alternate_team_total` | mid_major | bets | 91 | 6 days | — | — | — | no held-out test has been run | not enough evidence (91 bets, below the 200 declared in advance) |
| `alternate_total_points` | mid_major | bets | 7,467 | 230 games | -17.0% | -29.7% to -4.2% | -38.8% to +4.9% | no held-out test has been run | no demonstrated edge |
| `moneyline` | mid_major | bets | 10,194 | 736 days | -4.5% | -7.9% to -1.1% | -10.4% to +1.4% | not enough evidence on the 2025, 2026 (held out) window | no demonstrated edge |
| `moneyline_h1` | mid_major | bets | 184 | 79 days | — | — | — | no held-out test has been run | not enough evidence (184 bets, below the 200 declared in advance) |
| `spread` | mid_major | bets | 22,891 | 732 days | -1.5% | -3.6% to +0.6% | -5.1% to +2.1% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `spread_h1` | mid_major | bets | 799 | 238 games | -7.4% | -21.2% to +6.5% | -31.0% to +16.3% | no held-out test has been run | no demonstrated edge |
| `team_total` | mid_major | bets | 13,478 | 384 days | -5.8% | -7.9% to -3.8% | -9.3% to -2.4% | nothing to replicate on the 2025, 2026 (held out) window | demonstrated deficit |
| `total_points` | mid_major | bets | 23,327 | 728 days | -2.3% | -4.5% to -0.2% | -6.1% to +1.4% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `total_points_h1` | mid_major | bets | 594 | 202 games | -2.4% | -17.4% to +12.6% | -28.1% to +23.3% | no held-out test has been run | no demonstrated edge |
| `alternate_spread` | low_major | bets | 3,510 | 127 games | -2.1% | -19.2% to +15.0% | -31.3% to +27.2% | no held-out test has been run | no demonstrated edge |
| `alternate_team_total` | low_major | bets | 11 | 1 games | — | — | — | no held-out test has been run | not enough evidence (11 bets, below the 200 declared in advance) |
| `alternate_total_points` | low_major | bets | 3,785 | 121 games | -10.5% | -30.3% to +9.4% | -44.4% to +23.4% | no held-out test has been run | no demonstrated edge |
| `moneyline` | low_major | bets | 7,561 | 632 days | -7.9% | -11.8% to -4.1% | -14.6% to -1.3% | not enough evidence on the 2025, 2026 (held out) window | demonstrated deficit |
| `moneyline_h1` | low_major | bets | 82 | 82 games | — | — | — | no held-out test has been run | not enough evidence (82 bets, below the 200 declared in advance) |
| `spread` | low_major | bets | 16,090 | 634 days | -0.1% | -2.4% to +2.3% | -4.1% to +3.9% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `spread_h1` | low_major | bets | 405 | 121 games | +5.0% | -14.9% to +25.0% | -29.0% to +39.1% | no held-out test has been run | no demonstrated edge |
| `team_total` | low_major | bets | 9,802 | 334 days | -4.1% | -6.7% to -1.5% | -8.6% to +0.4% | nothing to replicate on the 2025, 2026 (held out) window | no demonstrated edge |
| `total_points` | low_major | bets | 17,903 | 7,131 games | -5.2% | -7.5% to -2.8% | -9.2% to -1.1% | nothing to replicate on the 2025, 2026 (held out) window | demonstrated deficit |
| `total_points_h1` | low_major | bets | 326 | 106 games | -11.4% | -32.3% to +9.5% | -47.1% to +24.4% | no held-out test has been run | no demonstrated edge |
| `moneyline` | unplaced | bets | 1 | 1 games | — | — | — | no held-out test has been run | not enough evidence (1 bets, below the 200 declared in advance) |
| `spread` | unplaced | bets | 3 | 2 games | — | — | — | no held-out test has been run | not enough evidence (3 bets, below the 200 declared in advance) |
| `total_points` | unplaced | bets | 2 | 1 games | — | — | — | no held-out test has been run | not enough evidence (2 bets, below the 200 declared in advance) |

## Pooled across Division I, and never the headline

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Cell | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| alternate_spread | 15,380 | 464 games | -4.3% | -12.3% to +3.8% | -18.0% to +9.5% | no demonstrated edge |
| alternate_team_total | 102 | 10 games | — | — | — | not enough evidence (102 bets, below the 200 declared in advance) |
| alternate_total_points | 13,366 | 415 games | -12.6% | -22.9% to -2.4% | -30.1% to +4.9% | no demonstrated edge |
| moneyline | 23,266 | 789 days | -5.4% | -7.9% to -2.8% | -9.8% to -1.0% | demonstrated deficit |
| moneyline_h1 | 320 | 320 games | +7.6% | -10.9% to +26.1% | -24.1% to +39.3% | no demonstrated edge |
| spread | 52,226 | 789 days | -1.1% | -2.4% to +0.2% | -3.4% to +1.1% | no demonstrated edge |
| spread_h1 | 1,427 | 431 games | -6.6% | -16.9% to +3.8% | -24.2% to +11.1% | no demonstrated edge |
| team_total | 30,389 | 412 days | -4.6% | -6.0% to -3.1% | -7.0% to -2.1% | demonstrated deficit |
| total_points | 53,473 | 21,076 games | -3.5% | -4.9% to -2.1% | -5.9% to -1.1% | demonstrated deficit |
| total_points_h1 | 1,104 | 365 games | -5.5% | -16.7% to +5.6% | -24.6% to +13.6% | no demonstrated edge |
| every market | 191,053 | 26,591 games | -4.0% | -5.3% to -2.6% | -6.3% to -1.6% | demonstrated deficit |

## What is in force, and what the card may actually use

- `the_odds_api:cbb` is **manual-only**. No market is allowlisted, the card produces no selection, and that is the correct state for a lab with no signed receipt.
- **No market is allowlisted, and that is the correct state.** `withdraw()` exists in `staging_provider_policy.py` and `grant()` does not: this lab may take a market away from the card and may never give it one. Adding a market is a receipt Cooper signs, in a pull request whose `Policy Gate` check is green — `.github/workflows/policy-gate.yml`, which runs on every pull request, verifies every allowlisted market against a receipt on disk, and is red while any market lacks one.

Every modelling policy is a **recorded verdict read from disk**, never an assertion in code, so what ships is auditable against the experiment that decided it. A missing verdict file ships nothing — the conservative reading of *no recorded decision* is *no policy in force*.

- `calibration_correction` is **not in force**. No verdict is recorded.
- `champion_model` is **not in force**. No verdict is recorded.
- `conference_tier_fits` is **not in force**. No verdict is recorded.
- `endgame_segment_model` is **not in force**. No verdict is recorded.
- `november_prior_schedule` is **not in force**. No verdict is recorded.
- `overtime_segment_model` is **not in force**. No verdict is recorded.
- `props_selectable_when_unconfirmed` is **not in force**. No verdict is recorded.
- `schedule_state_adjustment` is **not in force**. No verdict is recorded.
- `venue_home_effect` is **not in force**. No verdict is recorded.

## Not measured against real prices

- **19 market(s)** — no historical price has been bought for it and no forward opinion on it has settled. It is also gated: nothing in this sport reaches `Availability.CONFIRMED`, so it is priced, frozen and settled and cannot produce a selection.
  - `player_points` (settles on `player_points`), `player_rebounds` (settles on `player_rebounds`), `player_assists` (settles on `player_assists`), `player_threes` (settles on `player_threes_made`), `player_blocks` (settles on `player_blocks`), `player_steals` (settles on `player_steals`), `player_turnovers` (settles on `player_turnovers`), `player_field_goals` (settles on `player_field_goals_made`), `player_frees_made` (settles on `player_free_throws_made`), `player_frees_attempts` (settles on `player_free_throws_attempted`), `player_pra` (settles on `player_pra`), `player_points_rebounds` (settles on `player_points_rebounds`), `player_points_assists` (settles on `player_points_assists`), `player_rebounds_assists` (settles on `player_rebounds_assists`), `player_blocks_steals` (settles on `player_blocks_steals`), `player_double_double` (settles on `player_double_double`), `player_triple_double` (settles on `player_triple_double`), `player_first_basket` (settles on `player_first_basket`), `player_first_team_basket` (settles on `player_first_team_basket`)
- **3 market(s)** — historical prices for it **have** been bought and no measurement has scored them yet. That is a step this lab has not run, not a market the provider does not serve.
  - `moneyline_h2` (settles on `half_margin`), `spread_h2` (settles on `half_margin`), `total_points_h2` (settles on `half_total`)
- **2 market(s)** — no historical price has been bought for it and no forward opinion on it has settled.
  - `team_total_h1` (settles on `half_team_score`), `team_total_h2` (settles on `half_team_score`)
- **1 market(s)** — a futures market, served under a separate provider sport key, settling on a clock measured in months. Nothing has been bought for it and nothing has settled.
  - `championship_winner` (settles on `tournament_champion`)

**A market in this list is not a market judged to have no value.** It is a market with no price-based evidence either way, and nothing in this repository will present the two as the same thing. It is not a pass, it is not an avoid, and it is not a no-value call.

## Priced, frozen and settled — and unable to produce a selection

Division I men's basketball has **no mandated injury report**. Measured on 2026-09-01: ESPN's men's-college-basketball injuries endpoint is permanently empty, CollegeBasketballData has no availability endpoint at all, and the conference reports that exist cover roughly 115 of 365 teams, conference games only, which leaves two thirds of the division and the whole of November and December uncovered. A gate that read a missing feed as *nobody is injured* would clear an entire slate.

So nothing reaches `Availability.CONFIRMED`, and these 19 market(s) are priced, frozen and settled but **cannot produce a selection**: `player_points`, `player_rebounds`, `player_assists`, `player_threes`, `player_blocks`, `player_steals`, `player_turnovers`, `player_field_goals`, `player_frees_made`, `player_frees_attempts`, `player_pra`, `player_points_rebounds`, `player_points_assists`, `player_rebounds_assists`, `player_blocks_steals`, `player_double_double`, `player_triple_double`, `player_first_basket`, `player_first_team_basket`.

**A market in this list is not a market judged to have no value.** It is a market with no price-based evidence either way, and nothing in this repository will present the two as the same thing. It is not a pass, it is not an avoid, and it is not a no-value call.

## Provider keys this lab does not wire, and why

Nothing is silently dropped. A market nobody quotes and a market that **cannot exist** look identical in a coverage report and mean completely different things, so every unwired provider key carries its reason.

- **31 key(s)** — Men's college basketball plays two twenty-minute halves. There is no first quarter, so there is nothing to settle against. The provider documents this key because its basketball catalogue is shared with the NBA and WNBA. Asking for it would cost nothing and return nothing, which is exactly why it must be deferred with a reason rather than asked for and quietly found empty — a market nobody quotes and a market that cannot exist look identical in a coverage report and mean completely different things.
  - `alternate_spreads_q1`, `alternate_spreads_q2`, `alternate_spreads_q3`, `alternate_spreads_q4`, `alternate_team_totals_q1`, `alternate_team_totals_q2`, `alternate_team_totals_q3`, `alternate_team_totals_q4`, `alternate_totals_q1`, `alternate_totals_q2`, `alternate_totals_q3`, `alternate_totals_q4`, `h2h_q1`, `h2h_q2`, `h2h_q3`, `h2h_q4`, `player_assists_q1`, `player_points_q1`, `player_rebounds_q1`, `spreads_q1`, `spreads_q2`, `spreads_q3`, `spreads_q4`, `team_totals_q1`, `team_totals_q2`, `team_totals_q3`, `team_totals_q4`, `totals_q1`, `totals_q2`, `totals_q3`, `totals_q4`
- **1 key(s)** — Settles on how the first basket was scored — a dunk, a layup, a three, a tip-in. Play-by-play carries a text description of the shot, but the vocabulary is not standardised across the feed's own history and a book's categories are its own. Settling this would mean inventing a mapping from free text to a book's rulebook, and an invented settlement rule is how a lab manufactures a constant offset that replicates by construction. Revisit only with a source that states shot type as a code.
  - `player_method_of_first_basket`
- **1 key(s)** — Fantasy points are a scoring formula, and the formula differs by operator. Two books quoting `player_fantasy_points` are not quoting the same quantity, so there is no single named quantity for this market to settle against. DFS-only per the provider's own note.
  - `player_fantasy_points`
- **1 key(s)** — Same reason as `player_fantasy_points`: no single settlement quantity exists across operators.
  - `player_fantasy_points_alternate`

**A market in this list is not a market judged to have no value.** It is a market with no price-based evidence either way, and nothing in this repository will present the two as the same thing. It is not a pass, it is not an avoid, and it is not a no-value call.

## Reachability

**A soft number you cannot bet is not an edge.** Edge is measured against a price actually available at the moment the card is produced, at a US book Cooper can open, regions `us,us2` — and it is reported separately for prices that survived to the next capture and prices that did not. If a measured edge lives entirely in prices that vanish within minutes, it is reported as **not reachable**, in those words, regardless of its size or its significance.

The survival split is computed in `data/outputs/cbb_forward_evidence.md`. Nothing above has cleared the bars that would make reachability the deciding question.

## How much data would settle it

| If the true edge were | Bets needed to separate it from zero |
|---:|---:|
| +5% | ~1,537 |
| +8% | ~601 |
| +10% | ~385 |
| +15% | ~171 |

`docs/when_this_ends.md` set the decision date at **2027-04-19** and the sample floor at **10,000 settled opinions across at least 2,000 distinct games**, both declared on 2026-09-01 before any data existed. The forward ledger currently holds **0 settled opinions**. Below the floor the correct action is to diagnose the pipeline and **not to read the number**.

## Where every number above came from

- Experiment ledger: `data/outputs/experiment_ledger.json` — read
- Price backtest: `data/outputs/cbb_price_backtest.json` — read
- Forward-evidence ledger: `data/processed/cbb_forward_evidence.csv` — **not found**, so this document says nothing about it
- Replication record: `data/outputs/holdout/cbb_replication.json` — read

A file that is missing and a file that is unreadable are reported differently and deliberately. An unreadable measurement is a broken instrument, and reporting a broken instrument as *nothing measured* turns a fault into a null result.

## Standing notes

- An interval that includes zero means **no demonstrated edge**. Not 'promising', not 'trending positive', not 'small but positive'.
- An interval that excludes zero **on the losing side** is a **demonstrated deficit** and is named as one. It is never reported as an **edge** that survived and replicated, which is exactly what a sibling lab's version of this document once did on a market returning −6.6%. When a deficit replicates, this report says the loss is more credible — replication is evidence that a result is real, never evidence that it is good.
- Calibration can rule a model out. It can never rule one in. A market with only a calibration number has no price-based evidence, and this document will not present one as though it did.
- A result clears three things before it counts: enough bets, an interval that survives correcting for everything this lab has ever tested, and then holding on a window it was not found on. Clearing the first two and failing the third is the ordinary outcome, not a surprise.
- Every interval is clustered by game **and** by day, and the wider of the two is reported. One game supplies many correlated bets; a hundred-game Tuesday is not a thousand independent observations.
- **No market reaches the card without a reviewed human acceptance receipt**, whatever the numbers above say. This lab may withdraw an allowlist and may never grant one.
- The card produced by this repository is **accumulating evidence, not making recommendations**, and it says so on its face.
- Two sibling labs have finished and both measured no edge. That is the honest prior this document was written under, and a full-build instruction is an instruction about effort, never about the result.
