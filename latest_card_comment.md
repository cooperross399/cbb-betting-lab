**NCAA Division I men's basketball — 2026-11-17, morning slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-17 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 32 market(s): alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| Bryant Bulldogs at Massachusetts Minutemen | moneyline (game) | away | +550 | +508 | 0.10u | Near tip | fanduel | 9.3% | +9.13% | 0.00% | 56% | mid_major |
| Illinois Fighting Illini at Duke Blue Devils | moneyline (game) | away | +316 | +300 | 0.15u | Near tip | betonlineag | 27.9% | +6.27% | 0.00% | 47% | high_major |
| Central Michigan Chippewas at Dayton Flyers | moneyline (game) | away | +520 | +501 | 0.10u | Near tip | fanduel | 20.8% | +5.39% | 0.00% | 59% | mid_major |
| Green Bay Phoenix at West Florida Argonauts | moneyline (game) | home | +210 | +201 | 0.15u | Near tip | ballybet | 38.4% | +5.12% | 0.00% | 65% | low_major |
| Hofstra Pride at Murray St Racers | moneyline (game) | away | +545 | +527 | 0.10u | Near tip | courtside | 22.2% | +5.07% | 0.00% | 69% | mid_major |
| Saint Peter's Peacocks at UMass Lowell River Hawks | moneyline (game) | away | +250 | +242 | 0.15u | Near tip | bovada | 20.3% | +4.68% | 0.00% | 57% | low_major |
| Sacred Heart Pioneers at Providence Friars | team_total_h1 (h1) | away_over +28.5 | +100 | -104 | 0.25u | Near tip | fanduel | 58.7% | +4.06% | 0.00% | 70% | high_major |
| Fordham Rams at Manhattan Jaspers | moneyline (game) | home | +550 | +539 | 0.10u | Near tip | fanduel | 15.0% | +3.88% | 0.00% | 49% | mid_major |
| Le Moyne Dolphins at Evansville Purple Aces | moneyline (game) | away | +250 | +244 | 0.15u | Near tip | bovada | 30.6% | +3.84% | 0.00% | 67% | mid_major |
| Tennessee St Tigers at South Florida Bulls | moneyline (game) | away | +560 | +552 | 0.10u | Near tip | circasports | 13.7% | +3.33% | 0.00% | 68% | mid_major |
| Sam Houston St Bearkats at Wyoming Cowboys | moneyline (game) | away | +599 | +592 | 0.10u | Near tip | courtside | 18.6% | +3.13% | 0.00% | 57% | mid_major |
| Marist Red Foxes at Army Knights | team_total_h1 (h1) | home_over +30.5 | -106 | -107 | 0.25u | Near tip | fanduel | 61.8% | +2.92% | 0.00% | 59% | low_major |
| Lamar Cardinals at Omaha Mavericks | total_points (game) | under +156.5 | -103 | -103 | 0.25u | Near tip | lowvig | 73.8% | +2.22% | 0.00% | 83% | low_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. A long price is sized by its price instead: +200 to +500 0.15u, +501 to +1500 0.1u, longer than +1500 0.05u (the NHL Due List ladder). The site's record counts every bet at 0.25u, or to win 0.25u on a minus price, up to +199, and at that ladder from +200, whatever trust says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

13 position(s) across 13 game(s); the cap is 1 per game and 20 per slate. 1 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

16,175 priced = 8,019 no opinion + 399 below threshold + 0 unparseable + 17 ambiguous + 7,727 gated + 13 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 16,175 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 7,726 | gated |
| the model has no opinion on this selection | 8,019 | no_opinion |
| no price on it clears the declared edge threshold | 399 | below_threshold |
| every clearing price is outside the declared band | 17 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 1 | gated |
| the slate's declared position cap is already full | 0 | gated |

108 staged row(s) belong to a slate day other than 2026-11-17 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 54 game(s) judged — upcoming=54. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=25, low_major=7, mid_major=23. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

54 game(s) priced on this slate day, out of 55 the read saw — the board carries every upcoming game, not tonight's. 32,786 staged quote(s) over 109 event block(s).

109 event(s), 1,381 bookmaker block(s), 32,786 outcome(s) = 32,786 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,480 credit(s) actually spent over 55 request(s); the pessimistic pre-flight bound was 5,190; 4960842 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 54 of 54 game(s).

Frozen: `2026-11-17.csv`, from 16,175 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-17_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**3 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Lamar Cardinals at Omaha Mavericks: bovada spread (game) away -2 at -125 is beaten by -1.5 at -120
- Indiana Hoosiers at Arkansas Razorbacks: bovada total_points (game) over +155 at -115 is beaten by +154.5 at -110
- Maryland-Eastern Shore Hawks at DePaul Blue Demons: bovada spread (game) home -34 at -105 is beaten by -33.5 at +100

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 55 event(s) on 2026-11-17: 55 resolved to a scheduled game, 0 named no game on the schedule that day, 0 name(s) did not resolve. It returned 55 matchup(s), 55 priceable. History: 39,436 team-game row(s) strictly before 2026-11-17, through 2026-11-16, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

14,398 of 16,175 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 1,719 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 27 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 19 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 12 |

13,664 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 10,522 |
| closed by the closing-line gate (models/closing_gate.py) | 3,128 |
| past the alternate-ladder cap (models/rung_cap.py) | 14 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 50,566 settled forward row(s), 31,706 closing-line row(s)); low-major 0.095 (seed 0.011, 12,078 settled forward row(s), 8,986 closing-line row(s)); mid-major 0.000 (seed 0.032, 45,274 settled forward row(s), 28,698 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Closing-line gate: high-major alternate_spread, high-major alternate_total_points, high-major team_total, low-major alternate_total_points, low-major team_total, mid-major alternate_spread, mid-major alternate_total_points, mid-major team_total closed tonight; the model's leans there have lost to the close (alarm of 2026-11-17).

Line movement: 737 event(s) carry a move since their first capture; 97 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/44085425947
