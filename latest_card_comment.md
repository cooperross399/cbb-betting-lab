**NCAA Division I men's basketball — 2026-11-09, morning slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-09 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| UMKC Kangaroos at Jacksonville Dolphins | alternate_total_points (game) | over +154.5 | +236 | +218 | 0.35u | Near tip | courtside | 38.4% | +8.02% | 0.00% | 80% | low_major |
| South Carolina Upstate Spartans at Coastal Carolina Chanticleers | moneyline (game) | away | +400 | +389 | 0.25u | Near tip | bovada | 22.6% | +4.48% | 0.00% | 64% | mid_major |
| LIU Sharks at Towson Tigers | alternate_spread (game) | away -1.5 | +219 | +214 | 0.25u | Near tip | draftkings | 20.8% | +3.69% | 0.00% | 66% | mid_major |
| Minnesota Golden Gophers at Cincinnati Bearcats | moneyline (game) | away | +267 | +263 | 0.25u | Near tip | courtside | 19.2% | +3.38% | 0.00% | 64% | high_major |
| Stonehill Skyhawks at Columbia Lions | moneyline (game) | away | +471 | +464 | 0.25u | Near tip | courtside | 11.3% | +3.36% | 0.00% | 80% | mid_major |
| South Carolina St Bulldogs at Chicago St Cougars | moneyline (game) | away | +194 | +193 | 0.35u | Near tip | courtside | 36.0% | +2.51% | 0.00% | 80% | low_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. The site's record counts every bet at 0.25u whatever this column says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

6 position(s) across 6 game(s); the cap is 1 per game and 20 per slate. 12 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

7,791 priced = 7,071 no opinion + 683 below threshold + 0 unparseable + 19 ambiguous + 12 gated + 6 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 7,791 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 7,071 | no_opinion |
| no price on it clears the declared edge threshold | 683 | below_threshold |
| every clearing price is outside the declared band | 19 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 12 | gated |
| the slate's declared position cap is already full | 0 | gated |

66 staged row(s) belong to a slate day other than 2026-11-09 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 34 game(s) judged — upcoming=34. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=26, low_major=2, mid_major=9. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

34 game(s) priced on this slate day, out of 37 the read saw — the board carries every upcoming game, not tonight's. 15,945 staged quote(s) over 71 event block(s).

71 event(s), 805 bookmaker block(s), 15,945 outcome(s) = 15,945 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

386 credit(s) actually spent over 35 request(s); the pessimistic pre-flight bound was 3,270; 52033 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 34 of 34 game(s).

Frozen: `2026-11-09.csv`, from 7,791 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-09_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**6 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Florida Gulf Coast Eagles at Georgia Bulldogs: courtside total_points (game) under +161.5 at -113 is beaten by +162.5 at -110
- Florida Gulf Coast Eagles at Georgia Bulldogs: courtside total_points (game) under +161.5 at -113 is beaten by +162.5 at -110
- Florida Gulf Coast Eagles at Georgia Bulldogs: draftkings total_points (game) under +161.5 at -115 is beaten by +162.5 at -112
- South Carolina Upstate Spartans at Coastal Carolina Chanticleers: courtside total_points (game) over +149.5 at -118 is beaten by +148.5 at -113
- South Carolina Upstate Spartans at Coastal Carolina Chanticleers: courtside total_points (game) over +149.5 at -118 is beaten by +148.5 at -113
- South Carolina Upstate Spartans at Coastal Carolina Chanticleers: draftkings total_points (game) over +149.5 at -120 is beaten by +148.5 at -115

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 37 event(s) on 2026-11-09: 34 resolved to a scheduled game, 3 named no game on the schedule that day, 0 name(s) did not resolve. It returned 34 matchup(s), 34 priceable. History: 38,596 team-game row(s) strictly before 2026-11-09, through 2026-11-08, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

7,304 of 7,791 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 487 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 19,286 settled forward row(s)); low-major 0.366 (seed 0.011, 4,548 settled forward row(s)); mid-major 0.000 (seed 0.032, 15,434 settled forward row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Closing-line gate: high-major spread, high-major total_points closed tonight; the model's leans there have lost to the close (alarm of 2026-11-09).

Line movement: 366 event(s) carry a move since their first capture; 0 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/42616833583
