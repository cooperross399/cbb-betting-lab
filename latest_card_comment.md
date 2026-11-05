**NCAA Division I men's basketball — 2026-11-05, morning slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-05 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|:---|---:|---:|---:|---:|:---|
| UMass Lowell River Hawks at Merrimack Warriors | moneyline (game) | away | +320 | +282 | bovada | 34.9% | +12.36% | 0.00% | 100% | low_major |
| Binghamton Bearcats at Saint Peter's Peacocks | moneyline (game) | away | +320 | +292 | bovada | 28.4% | +9.55% | 0.00% | 92% | low_major |
| New Hampshire Wildcats at Rider Broncs | alternate_spread (game) | home -7.5 | +275 | +252 | bovada | 21.2% | +8.70% | 0.00% | 92% | low_major |
| Georgia St Panthers at Charlotte 49ers | moneyline (game) | away | +600 | +567 | draftkings | 22.7% | +7.11% | 0.00% | 92% | mid_major |
| South Florida Bulls at DePaul Blue Demons | alternate_total_points (game) | over +158.5 | +225 | +221 | bovada | 37.0% | +3.33% | 0.00% | 92% | high_major |
| Chattanooga Mocs at Penn State Nittany Lions | alternate_total_points (game) | over +158.5 | -110 | -112 | hardrockbet | 43.8% | +3.24% | 0.00% | 92% | high_major |
| Delaware St Hornets at Navy Midshipmen | moneyline (game) | away | +375 | +370 | bovada | 21.3% | +3.13% | 0.00% | 100% | low_major |
| Mercyhurst Lakers at Notre Dame Fighting Irish | spread (game) | away +19.5 | +106 | +104 | ballybet | 57.4% | +3.00% | 0.00% | 92% | high_major |
| Howard Bison at Alcorn St Braves | alternate_spread (game) | home -2.5 | +323 | +320 | draftkings | 21.0% | +2.96% | 0.00% | 92% | low_major |
| McNeese Cowboys at North Texas Mean Green | alternate_spread (game) | away -10.5 | +375 | +372 | bovada | 10.6% | +2.75% | 0.00% | 100% | mid_major |
| Vermont Catamounts at Fairfield Stags | alternate_spread (game) | home -9.5 | +320 | +318 | bovada | 25.3% | +2.54% | 0.00% | 100% | low_major |
| Jacksonville Dolphins at Florida Gators | alternate_spread (game) | away +31.5 | +130 | +130 | hardrockbet | 58.5% | +2.29% | 0.00% | 100% | high_major |
| Cornell Big Red at Lehigh Mountain Hawks | alternate_spread (game) | away -10.5 | +340 | +339 | bovada | 18.9% | +2.26% | 0.00% | 92% | mid_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

13 position(s) across 13 game(s); the cap is 1 per game and 20 per slate. 13 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

7,527 priced = 453 no opinion + 7,029 below threshold + 0 unparseable + 19 ambiguous + 13 gated + 13 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 7,527 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 453 | no_opinion |
| no price on it clears the declared edge threshold | 7,029 | below_threshold |
| every clearing price is outside the declared band | 19 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 13 | gated |
| the slate's declared position cap is already full | 0 | gated |

66 staged row(s) belong to a slate day other than 2026-11-05 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 43 game(s) judged — upcoming=43. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=22, low_major=12, mid_major=10. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

43 game(s) priced on this slate day, out of 44 the read saw — the board carries every upcoming game, not tonight's. 18,144 staged quote(s) over 87 event block(s).

87 event(s), 1,000 bookmaker block(s), 18,144 outcome(s) = 18,144 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

488 credit(s) actually spent over 44 request(s); the pessimistic pre-flight bound was 4,134; 77067 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 43 of 43 game(s).

Frozen: `2026-11-05.csv`, from 7,527 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-05_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

No book's ladder contradicted itself: every better line cost more on the same book.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 44 event(s) on 2026-11-05: 43 resolved to a scheduled game, 1 named no game on the schedule that day, 0 name(s) did not resolve. It returned 43 matchup(s), 43 priceable. History: 38,126 team-game row(s) strictly before 2026-11-05, through 2026-11-04, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

7,074 of 7,527 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 416 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 20 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 9 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 8 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 8,008 settled forward row(s)); low-major 0.064 (seed 0.011, 1,168 settled forward row(s)); mid-major 0.000 (seed 0.032, 6,464 settled forward row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 206 event(s) carry a move since their first capture; 80 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/42021507117
