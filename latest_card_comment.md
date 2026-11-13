**NCAA Division I men's basketball — 2026-11-13, evening slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-13 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 32 market(s): alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| Harvard Crimson at GW Revolutionaries | moneyline_h1 (h1) | away | +335 | +304 | 0.15u | Near tip | betrivers | 22.0% | +9.85% | 4.07% | 100% | mid_major |
| UL Monroe Warhawks at Arizona St Sun Devils | spread_h1 (h1) | home -18.5 | +140 | +131 | 0.25u | Near tip | bovada | 21.3% | +6.19% | 0.00% | 67% | high_major |
| South Dakota Coyotes at Drake Bulldogs | moneyline_h1 (h1) | away | +390 | +375 | 0.15u | Near tip | fanduel | 20.1% | +5.42% | 3.66% | 84% | mid_major |
| Wright St Raiders at Samford Bulldogs | spread_h1 (h1) | away -1.5 | +120 | +114 | 0.25u | Near tip | bovada | 53.5% | +5.35% | 0.00% | 80% | low_major |
| Milwaukee Panthers at TCU Horned Frogs | spread_h1 (h1) | home -14.5 | +125 | +120 | 0.25u | Near tip | bovada | 35.7% | +4.53% | 0.00% | 68% | high_major |
| Southern Miss Golden Eagles at Texas State Bobcats | moneyline (game) | away | +525 | +511 | 0.10u | Near tip | betparx | 11.2% | +4.46% | 0.00% | 81% | mid_major |
| UC San Diego Tritons at Utah State Aggies | spread_h1 (h1) | home -8.5 | +125 | +122 | 0.25u | Near tip | bovada | 36.9% | +3.46% | 0.00% | 77% | mid_major |
| UIC Flames at Saint Mary's Gaels | total_points_h1 (h1) | under +69.5 | +148 | +145 | 0.25u | Near tip | fanduel | 43.9% | +3.29% | 0.00% | 82% | mid_major |
| Arizona Wildcats at Auburn Tigers | total_points_h1 (h1) | over +77.5 | +142 | +141 | 0.25u | Near tip | fanduel | 41.0% | +2.81% | 0.00% | 65% | high_major |
| Pittsburgh Panthers at Butler Bulldogs | total_points_h1 (h1) | over +77.5 | +142 | +141 | 0.25u | Near tip | fanduel | 38.0% | +2.81% | 0.00% | 55% | high_major |
| Stanford Cardinal at UNLV Rebels | total_points_h1 (h1) | over +73.5 | +142 | +141 | 0.25u | Near tip | fanduel | 45.7% | +2.81% | 0.00% | 63% | high_major |
| Troy Trojans at NC State Wolfpack | spread_h1 (h1) | away +12 | +110 | +109 | 0.25u | Near tip | bovada | 62.5% | +2.72% | 4.77% | 67% | high_major |
| Lindenwood Lions at Omaha Mavericks | total_points_h1 (h1) | over +73 | +105 | +105 | 0.25u | Near tip | bovada | 46.1% | +2.04% | 4.02% | 68% | low_major |
| Ohio Bobcats at Purdue Boilermakers | moneyline_h1 (h1) | away | +600 | +600 | 0.10u | Near tip | williamhill_us | 11.8% | +2.00% | 2.73% | 66% | high_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. A long price is sized by its price instead: +200 to +500 0.15u, +501 to +1500 0.1u, longer than +1500 0.05u (the NHL Due List ladder). The site's record counts every bet at 0.25u, or to win 0.25u on a minus price, up to +199, and at that ladder from +200, whatever trust says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

14 position(s) across 14 game(s); the cap is 1 per game and 20 per slate. 2 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

26,113 priced = 17,263 no opinion + 789 below threshold + 0 unparseable + 36 ambiguous + 8,011 gated + 14 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 26,113 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 8,002 | gated |
| the model has no opinion on this selection | 17,263 | no_opinion |
| no price on it clears the declared edge threshold | 789 | below_threshold |
| every clearing price is outside the declared band | 36 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 7 | gated |
| a position is already taken on this game | 2 | gated |
| the slate's declared position cap is already full | 0 | gated |

0 staged row(s) belong to a slate day other than 2026-11-13 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 55 game(s) judged — started=1, upcoming=54. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=29, low_major=7, mid_major=19. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

55 game(s) priced on this slate day, out of 55 the read saw — the board carries every upcoming game, not tonight's. 54,708 staged quote(s) over 110 event block(s).

110 event(s), 1,415 bookmaker block(s), 54,708 outcome(s) = 54,708 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,878 credit(s) actually spent over 56 request(s); the pessimistic pre-flight bound was 5,286; 4982938 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 55 of 55 game(s).

Frozen: `2026-11-13.csv`, from 25,726 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-13_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**7 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- West Florida Argonauts at Cleveland St Vikings: bovada total_points (game) over +150.5 at -130 is beaten by +150 at -110
- West Florida Argonauts at Cleveland St Vikings: rebet total_points (game) over +150.5 at -133 is beaten by +149.5 at -118
- West Florida Argonauts at Cleveland St Vikings: bovada total_points (game) under +150 at -110 is beaten by +150.5 at +100
- West Florida Argonauts at Cleveland St Vikings: rebet total_points (game) under +149.5 at -111 is beaten by +150.5 at +100
- Stanford Cardinal at UNLV Rebels: hardrockbet total_points (game) over +153.5 at -115 is beaten by +152.5 at -110
- Stanford Cardinal at UNLV Rebels: hardrockbet total_points (game) under +152.5 at -110 is beaten by +153.5 at -105
- Xavier Musketeers at Mississippi St Bulldogs: bovada total_points (game) under +162 at -110 is beaten by +162.5 at -105

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 55 event(s) on 2026-11-13: 55 resolved to a scheduled game, 0 named no game on the schedule that day, 0 name(s) did not resolve. It returned 55 matchup(s), 55 priceable. History: 39,026 team-game row(s) strictly before 2026-11-13, through 2026-11-12, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

19,898 of 26,113 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 5,142 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.845e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 35 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 34 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.066e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.125e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.211e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.231e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.527e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.213e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.232e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.338e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.352e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.038e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.110e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.140e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.360e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.538e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.734e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.761e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.987e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.027e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.078e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.237e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.249e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.372e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.531e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.599e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.720e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.762e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.804e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.880e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 5.022e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 9.418e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 28 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 16 |

18,794 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 14,278 |
| closed by the closing-line gate (models/closing_gate.py) | 4,498 |
| past the alternate-ladder cap (models/rung_cap.py) | 18 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 41,328 settled forward row(s), 27,162 closing-line row(s)); low-major 0.058 (seed 0.011, 9,642 settled forward row(s), 7,288 closing-line row(s)); mid-major 0.000 (seed 0.032, 39,660 settled forward row(s), 24,878 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Closing-line gate: high-major alternate_spread, high-major alternate_total_points, high-major spread, high-major team_total, high-major total_points, low-major alternate_total_points, low-major team_total, mid-major alternate_spread, mid-major alternate_total_points, mid-major team_total closed tonight; the model's leans there have lost to the close (alarm of 2026-11-13).

Line movement: 561 event(s) carry a move since their first capture; 99 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/43488881873
