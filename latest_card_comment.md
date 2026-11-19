**NCAA Division I men's basketball — 2026-11-19, evening slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-19 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| Arkansas-Little Rock Trojans at Jacksonville Dolphins | alternate_spread (game) | away -6.5 | +340 | +311 | 0.15u | Now | draftkings | 19.3% | +9.39% | 0.00% | 61% | low_major |
| Tarleton State Texans at USC Trojans | alternate_spread (game) | home -33.5 | +230 | +209 | 0.15u | Now | hardrockbet | 30.8% | +9.13% | 0.00% | 69% | high_major |
| Maine Black Bears at Quinnipiac Bobcats | spread_h1 (h1) | away +5.5 | -105 | -114 | 0.25u | Near tip | bovada | 62.4% | +6.13% | 0.00% | 42% | low_major |
| Montana St Bobcats at High Point Panthers | alternate_spread (game) | away +9.5 | +165 | +156 | 0.25u | Now | betmgm | 69.1% | +5.72% | 0.00% | 42% | low_major |
| Charleston Cougars at Drake Bulldogs | alternate_spread (game) | away +5.5 | -175 | -188 | 0.25u | Near tip | betmgm | 75.5% | +4.67% | 0.00% | 68% | mid_major |
| NC State Wolfpack at Murray St Racers | alternate_spread (game) | home -5.5 | +351 | +340 | 0.15u | Near tip | draftkings | 16.0% | +4.56% | 0.00% | 49% | high_major |
| Tulane Green Wave at Louisiana Tech Bulldogs | alternate_spread (game) | away +6.5 | -190 | -196 | 0.25u | Near tip | betmgm | 75.3% | +3.13% | 0.00% | 57% | mid_major |
| Texas A&M Aggies at TCU Horned Frogs | alternate_spread (game) | home -1.5 | +116 | +114 | 0.25u | Near tip | courtside | 57.8% | +3.07% | 0.00% | 58% | high_major |
| Stetson Hatters at Louisville Cardinals | alternate_spread (game) | away +42.5 | -200 | -204 | 0.25u | Near tip | hardrockbet | 90.4% | +2.83% | 0.00% | 57% | high_major |
| Buffalo Bulls at St. Bonaventure Bonnies | alternate_spread (game) | home -5.5 | -280 | -284 | 0.25u | Now | williamhill_us | 67.2% | +2.38% | 0.00% | 59% | mid_major |
| UC Santa Barbara Gauchos at Pepperdine Waves | team_total_h1 (h1) | away_over +35.5 | -102 | -102 | 0.25u | Near tip | fanduel | 56.8% | +2.35% | 0.00% | 72% | mid_major |
| Utah Tech Trailblazers at Washington Huskies | alternate_spread (game) | away +12.5 | +210 | +210 | 0.15u | Now | betrivers | 33.5% | +2.14% | 0.00% | 69% | high_major |
| UTEP Miners at New Mexico St Aggies | alternate_spread (game) | away +5.5 | -190 | -190 | 0.25u | Near tip | betmgm | 62.2% | +2.09% | 0.00% | 58% | mid_major |
| Houston Cougars at Kansas Jayhawks | alternate_spread (game) | home +6.5 | -155 | -155 | 0.25u | Near tip | betmgm | 51.6% | +2.02% | 0.00% | 44% | high_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. A long price is sized by its price instead: +200 to +500 0.15u, +501 to +1500 0.1u, longer than +1500 0.05u (the NHL Due List ladder). The site's record counts every bet at 0.25u, or to win 0.25u on a minus price, up to +199, and at that ladder from +200, whatever trust says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

14 position(s) across 14 game(s); the cap is 1 per game and 20 per slate. 21 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

15,228 priced = 11,358 no opinion + 3,821 below threshold + 0 unparseable + 3 ambiguous + 32 gated + 14 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 15,228 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 11,358 | no_opinion |
| no price on it clears the declared edge threshold | 3,821 | below_threshold |
| every clearing price is outside the declared band | 3 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 11 | gated |
| a position is already taken on this game | 21 | gated |
| the slate's declared position cap is already full | 0 | gated |

224 staged row(s) belong to a slate day other than 2026-11-19 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 29 game(s) judged — started=1, upcoming=28. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=30, low_major=6, mid_major=21. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

29 game(s) priced on this slate day, out of 57 the read saw — the board carries every upcoming game, not tonight's. 36,334 staged quote(s) over 86 event block(s).

86 event(s), 877 bookmaker block(s), 36,334 outcome(s) = 36,334 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,030 credit(s) actually spent over 30 request(s); the pessimistic pre-flight bound was 2,790; 4942872 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 29 of 29 game(s).

Frozen: `2026-11-19.csv`, from 14,874 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-19_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**12 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- West Virginia Mountaineers at Florida Gators: betmgm spread (game) away +11.5 at -115 is beaten by +12.5 at +110
- West Virginia Mountaineers at Florida Gators: betmgm spread (game) home -12.5 at -145 is beaten by -11.5 at -110
- West Virginia Mountaineers at Florida Gators: betmgm spread (game) home -13.5 at -115 is beaten by -11.5 at -110
- West Virginia Mountaineers at Florida Gators: hardrockbet spread (game) home -13.5 at -125 is beaten by -12.5 at -120
- West Virginia Mountaineers at Florida Gators: betmgm total_points (game) over +146.5 at -125 is beaten by +145.5 at -115
- West Virginia Mountaineers at Florida Gators: bovada total_points (game) over +145.5 at -120 is beaten by +144.5 at -110
- West Virginia Mountaineers at Florida Gators: hardrockbet total_points (game) over +146.5 at -110 is beaten by +145.5 at +100
- West Virginia Mountaineers at Florida Gators: williamhill_us total_points (game) over +147.5 at -110 is beaten by +146.5 at -105
- West Virginia Mountaineers at Florida Gators: betmgm total_points (game) under +145.5 at -115 is beaten by +146.5 at -102
- West Virginia Mountaineers at Florida Gators: bovada total_points (game) under +144.5 at -120 is beaten by +145.5 at -110
- and 2 more.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 57 event(s) on 2026-11-19: 29 resolved to a scheduled game, 28 named no game on the schedule that day, 0 name(s) did not resolve. It returned 29 matchup(s), 29 priceable. History: 39,714 team-game row(s) strictly before 2026-11-19, through 2026-11-18, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

12,298 of 15,228 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 2,900 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 12 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 11 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 7 |

8,428 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 8,428 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 57,612 settled forward row(s), 36,192 closing-line row(s)); low-major 0.058 (seed 0.011, 13,788 settled forward row(s), 10,116 closing-line row(s)); mid-major 0.000 (seed 0.032, 51,046 settled forward row(s), 32,320 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 828 event(s) carry a move since their first capture; 74 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/44602793114
