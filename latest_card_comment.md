**NCAA Division I men's basketball — 2026-11-27, morning slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-27 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| Niagara Purple Eagles at Lafayette Leopards | alternate_spread (game) | home +3.5 | -280 | -297 | 1.20u | Now | bovada | 80.9% | +6.69% | 0.00% | 55% | low_major |
| Colgate Raiders at Hofstra Pride | alternate_spread (game) | home +3.5 | -245 | -252 | 1.00u | Near tip | bovada | 77.1% | +5.91% | 0.00% | 62% | mid_major |
| Drake Bulldogs at Boise State Broncos | alternate_spread (game) | home +4.5 | -400 | -400 | 1.00u | Now | bovada | 82.4% | +5.51% | 0.00% | 48% | mid_major |
| Southern Jaguars at Vanderbilt Commodores | alternate_spread (game) | home -41.5 | +190 | +190 | 1.00u | Now | hardrockbet | 16.0% | +5.00% | 0.00% | 40% | high_major |
| Memphis Tigers at Wake Forest Demon Deacons | moneyline (game) | home | +125 | +123 | 1.00u | Near tip | hardrockbet | 30.4% | +2.99% | 0.00% | 39% | high_major |
| Pacific Tigers at UC Davis Aggies | moneyline (game) | away | -200 | -201 | 1.00u | Near tip | fanduel | 80.6% | +2.33% | 0.00% | 41% | mid_major |
| Bellarmine Knights at Butler Bulldogs | spread_h1 (h1) | away +9.5 | +110 | +109 | 1.00u | Near tip | bovada | 55.9% | +2.65% | 0.00% | 33% | high_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 1u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 2u. A tier trusted at zero is the base size. A long price is sized by its price instead: +200 to +500 0.6u, +501 to +1500 0.4u, longer than +1500 0.2u (the NHL Due List ladder on a 1u base). The site's record counts every bet at 1u, or to win 1u on a minus price, up to +199, and at that ladder from +200, whatever trust says. On the evening card a pick on a game the morning card did not pick is bet at half that size.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

7 position(s) across 7 game(s); the cap is 1 per game and 20 per slate. 5 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

14,955 priced = 9,751 no opinion + 5,192 below threshold + 0 unparseable + 0 ambiguous + 5 gated + 7 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 14,955 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 9,751 | no_opinion |
| no price on it clears the declared edge threshold | 5,192 | below_threshold |
| every clearing price is outside the declared band | 0 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 5 | gated |
| the slate's declared position cap is already full | 0 | gated |

0 staged row(s) belong to a slate day other than 2026-11-27 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 49 game(s) judged — upcoming=49. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=27, low_major=7, mid_major=15. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

49 game(s) priced on this slate day, out of 49 the read saw — the board carries every upcoming game, not tonight's. 36,417 staged quote(s) over 98 event block(s).

98 event(s), 1,232 bookmaker block(s), 36,417 outcome(s) = 36,417 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,231 credit(s) actually spent over 51 request(s); the pessimistic pre-flight bound was 4,713; 4892801 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 49 of 49 game(s).

Reference prices: 142 quote(s) from `pinnacle`, read for the fair price only.

Frozen: `2026-11-27.csv`, from 14,955 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-27_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**16 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Radford Highlanders at American Eagles: courtside total_points (game) over +144.5 at -108 is beaten by +143.5 at -106
- Radford Highlanders at American Eagles: draftkings total_points (game) over +144.5 at -110 is beaten by +143.5 at -108
- Le Moyne Dolphins at Maine Black Bears: betrivers spread (game) away -0.5 at +100 is beaten by +0.5 at +104
- Navy Midshipmen at Fairfield Stags: bovada spread_h1 (h1) home -3 at -115 is beaten by -2.5 at -110
- Navy Midshipmen at Fairfield Stags: bovada total_points_h1 (h1) under +63 at -115 is beaten by +63.5 at -110
- TCU Horned Frogs at Baylor Bears: bovada spread (game) away +4.5 at -120 is beaten by +5 at -105
- TCU Horned Frogs at Baylor Bears: bovada spread (game) home -5 at -125 is beaten by -4.5 at +100
- TCU Horned Frogs at Baylor Bears: bovada spread (game) home -6 at -105 is beaten by -4.5 at +100
- TCU Horned Frogs at Baylor Bears: bovada total_points (game) under +154 at -120 is beaten by +154.5 at -115
- Fresno St Bulldogs at South Alabama Jaguars: betrivers spread (game) away -0.5 at -107 is beaten by +0.5 at -105
- and 6 more.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 49 event(s) on 2026-11-27: 49 resolved to a scheduled game, 0 named no game on the schedule that day, 0 name(s) did not resolve. It returned 49 matchup(s), 49 priceable. History: 40,548 team-game row(s) strictly before 2026-11-27, through 2026-11-26, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

13,552 of 14,955 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 1,366 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 23 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 14 |

8,348 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 8,348 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 86,304 settled forward row(s), 48,252 closing-line row(s)); low-major 0.123 (seed 0.011, 27,628 settled forward row(s), 16,408 closing-line row(s)); mid-major 0.000 (seed 0.032, 83,648 settled forward row(s), 46,608 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 1,200 event(s) carry a move since their first capture; 110 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/46006643280
