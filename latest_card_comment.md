**NCAA Division I men's basketball — 2026-11-08, evening slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-08 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|:---|---:|---:|---:|---:|:---|
| North Dakota St Bison at CSU Bakersfield Roadrunners | alternate_spread (game) | home -3.5 | +195 | +178 | hardrockbet | 42.6% | +8.59% | 0.00% | 100% | low_major |
| Houston Cougars at California Golden Bears | alternate_spread (game) | away -25.5 | +230 | +216 | hardrockbet | 10.6% | +6.64% | 0.00% | 93% | high_major |
| Richmond Spiders at Temple Owls | alternate_total_points (game) | over +157.5 | +220 | +210 | fanduel | 36.8% | +5.35% | 0.00% | 93% | mid_major |
| Pittsburgh Panthers at Penn State Nittany Lions | alternate_team_total (game) | home_under +73.5 | +148 | +142 | fanduel | 33.6% | +4.72% | 0.00% | 86% | high_major |
| UT-Arlington Mavericks at Hawai'i Rainbow Warriors | total_points_h1 (h1) | over +71.5 | +144 | +139 | fanduel | 44.7% | +4.45% | 0.00% | 93% | low_major |
| Wichita St Shockers at USC Trojans | alternate_spread (game) | home -15.5 | +390 | +380 | fanduel | 18.6% | +4.32% | 0.00% | 93% | high_major |
| Norfolk St Spartans at William & Mary Tribe | alternate_spread (game) | away +2.5 | +330 | +321 | bovada | 31.3% | +4.24% | 0.00% | 100% | mid_major |
| Incarnate Word Cardinals at UTEP Miners | alternate_spread (game) | away +2.5 | +460 | +455 | bovada | 26.2% | +3.04% | 0.00% | 93% | mid_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

8 position(s) across 8 game(s); the cap is 1 per game and 20 per slate. 51 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

9,473 priced = 2,751 no opinion + 6,192 below threshold + 0 unparseable + 35 ambiguous + 487 gated + 8 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 9,473 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 2,751 | no_opinion |
| no price on it clears the declared edge threshold | 6,192 | below_threshold |
| every clearing price is outside the declared band | 35 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 436 | gated |
| a position is already taken on this game | 51 | gated |
| the slate's declared position cap is already full | 0 | gated |

246 staged row(s) belong to a slate day other than 2026-11-08 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 28 game(s) judged — imminent=2, started=17, upcoming=9. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=23, low_major=11, mid_major=15. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

28 game(s) priced on this slate day, out of 49 the read saw — the board carries every upcoming game, not tonight's. 19,620 staged quote(s) over 77 event block(s).

77 event(s), 732 bookmaker block(s), 19,620 outcome(s) = 19,620 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

800 credit(s) actually spent over 29 request(s); the pessimistic pre-flight bound was 2,694; 53206 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 28 of 28 game(s).

Frozen: `2026-11-08.csv`, from 4,415 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-08_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**53 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Quinnipiac Bobcats at Vermont Catamounts: betrivers total_points (game) over +146.5 at -121 is beaten by +145.5 at -118
- Quinnipiac Bobcats at Vermont Catamounts: draftkings total_points (game) over +148.5 at -110 is beaten by +147.5 at +105
- Quinnipiac Bobcats at Vermont Catamounts: fliff total_points (game) over +148.5 at -125 is beaten by +147.5 at -120
- Quinnipiac Bobcats at Vermont Catamounts: betrivers total_points (game) under +145.5 at -124 is beaten by +146.5 at -121
- Quinnipiac Bobcats at Vermont Catamounts: draftkings total_points (game) under +147.5 at -145 is beaten by +148.5 at -120
- Quinnipiac Bobcats at Vermont Catamounts: fliff total_points (game) under +147.5 at -125 is beaten by +148.5 at -120
- SE Missouri St Redhawks at South Carolina Gamecocks: betmgm spread (game) away +10.5 at -125 is beaten by +11.5 at -105
- SE Missouri St Redhawks at South Carolina Gamecocks: betmgm spread (game) home -11.5 at -125 is beaten by -10.5 at -102
- SE Missouri St Redhawks at South Carolina Gamecocks: betrivers total_points (game) over +146.5 at -205 is beaten by +145.5 at -122
- SE Missouri St Redhawks at South Carolina Gamecocks: betrivers total_points (game) over +147.5 at -143 is beaten by +145.5 at -122
- and 43 more.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 49 event(s) on 2026-11-08: 28 resolved to a scheduled game, 21 named no game on the schedule that day, 0 name(s) did not resolve. It returned 28 matchup(s), 28 priceable. History: 38,524 team-game row(s) strictly before 2026-11-08, through 2026-11-07, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

6,726 of 9,473 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 947 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.529e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 176 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.407e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 166 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.882e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 160 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.502e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 158 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.329e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 136 |
| the distribution could not be built (This segment claims to resolve ties and holds 5.046e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 136 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.951e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 132 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.795e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 94 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.760e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 88 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.912e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 80 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.473e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 54 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.911e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 44 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.695e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 42 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.271e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 40 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.706e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.288e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.292e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.582e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.674e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.848e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.886e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 5.024e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 18 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 10 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 10 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 18,390 settled forward row(s)); low-major 0.373 (seed 0.011, 4,160 settled forward row(s)); mid-major 0.000 (seed 0.032, 14,268 settled forward row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 349 event(s) carry a move since their first capture; 96 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/42505254973
