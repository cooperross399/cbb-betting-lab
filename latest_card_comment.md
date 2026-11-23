**NCAA Division I men's basketball — 2026-11-23, evening slot.** Decision: `no-selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-23 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

**None.** No wager on this slate cleared every bar.

These are the bars they met, in the order the bars are applied. A wager is counted under the **first** bar it meets and is asked nothing after it, so a market stopped by the allowlist was never put to the model at all:

* the model has no opinion on this selection — 7,250 wager(s)
* no price on it clears the declared edge threshold — 2,456 wager(s)
* every clearing price is outside the declared band — 2 wager(s)
* the game has tipped, is imminent, or has no readable tip time — 64 wager(s)

None of the above is a pass, an avoid, or a no-value call. Where a gate stopped a market the card names the gate, and where the edge threshold stopped one that is a statement about the prices this run could actually reach at card time and not a view about the bet. **Claude may withdraw an allowlist and may never grant one.** No selection, no lean, no pass and no stake.

## Exposure

0 position(s) across 0 game(s); the cap is 1 per game and 20 per slate. 0 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

9,772 priced = 7,250 no opinion + 2,456 below threshold + 0 unparseable + 2 ambiguous + 64 gated + 0 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 9,772 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 7,250 | no_opinion |
| no price on it clears the declared edge threshold | 2,456 | below_threshold |
| every clearing price is outside the declared band | 2 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 64 | gated |
| a position is already taken on this game | 0 | gated |
| the slate's declared position cap is already full | 0 | gated |

2,022 staged row(s) belong to a slate day other than 2026-11-23 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 22 game(s) judged — imminent=6, started=4, upcoming=12. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=24, low_major=13, mid_major=27. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

22 game(s) priced on this slate day, out of 64 the read saw — the board carries every upcoming game, not tonight's. 25,499 staged quote(s) over 86 event block(s).

86 event(s), 966 bookmaker block(s), 25,499 outcome(s) = 25,499 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

696 credit(s) actually spent over 23 request(s); the pessimistic pre-flight bound was 2,118; 4914079 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 22 of 22 game(s).

Frozen: `2026-11-23.csv`, from 6,129 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-23_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**32 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Monmouth Hawks at North Carolina Tar Heels: bovada spread_h1 (h1) home -10 at -120 is beaten by -9.5 at -115
- UNC Greensboro Spartans at Pepperdine Waves: courtside total_points (game) under +152.5 at -113 is beaten by +153.5 at -106
- UNC Greensboro Spartans at Pepperdine Waves: courtside total_points (game) under +152.5 at -113 is beaten by +153.5 at -106
- UNC Greensboro Spartans at Pepperdine Waves: draftkings total_points (game) under +152.5 at -115 is beaten by +153.5 at -108
- Nevada Wolf Pack at San Francisco Dons: bovada spread (game) away -15.5 at -130 is beaten by -14.5 at -125
- Nevada Wolf Pack at San Francisco Dons: betrivers spread (game) home +15.5 at -132 is beaten by +16.5 at -130
- Nevada Wolf Pack at San Francisco Dons: bovada spread (game) home +14.5 at -105 is beaten by +15.5 at +100
- Nevada Wolf Pack at San Francisco Dons: rebet spread (game) home +12.5 at -125 is beaten by +15.5 at -118
- Nevada Wolf Pack at San Francisco Dons: draftkings spread_h2 (h2) away -23.5 at -115 is beaten by -22.5 at +105
- Nevada Wolf Pack at San Francisco Dons: draftkings spread_h2 (h2) home +22.5 at -145 is beaten by +23.5 at -120
- and 22 more.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 64 event(s) on 2026-11-23: 22 resolved to a scheduled game, 42 named no game on the schedule that day, 0 name(s) did not resolve. It returned 22 matchup(s), 22 priceable. History: 39,774 team-game row(s) strictly before 2026-11-23, through 2026-11-22, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

8,837 of 9,772 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 907 |
| refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call. | 16 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 8 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 4 |

6,315 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 6,315 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 76,230 settled forward row(s), 44,504 closing-line row(s)); low-major 0.089 (seed 0.011, 26,216 settled forward row(s), 15,626 closing-line row(s)); mid-major 0.000 (seed 0.032, 73,656 settled forward row(s), 41,996 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 1,045 event(s) carry a move since their first capture; 94 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/45287225248
