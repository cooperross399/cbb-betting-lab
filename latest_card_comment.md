**NCAA Division I men's basketball — 2026-11-04, evening slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-04 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 35 market(s): alternate_spread, alternate_team_total, alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|:---|---:|---:|---:|---:|:---|
| Maryland-Eastern Shore Hawks at High Point Panthers | alternate_spread (game) | away +26.5 | +280 | +243 | fanduel | 71.6% | +13.25% | 0.00% | 92% | low_major |
| SE Louisiana Lions at Auburn Tigers | alternate_spread (game) | away +22.5 | +250 | +231 | hardrockbet | 47.6% | +8.07% | 0.00% | 100% | high_major |
| CSU Northridge Matadors at Wichita St Shockers | alternate_spread (game) | away +9.5 | +250 | +232 | hardrockbet | 42.8% | +7.77% | 0.00% | 100% | mid_major |
| Radford Highlanders at California Golden Bears | alternate_team_total (game) | away_under +61.5 | +440 | +425 | fanduel | 16.5% | +5.03% | 0.00% | 100% | high_major |
| Queens University Royals at Loyola Marymount Lions | alternate_spread (game) | home -14.5 | +245 | +238 | fanduel | 19.8% | +4.38% | 0.00% | 100% | mid_major |
| Longwood Lancers at Saint Joseph's Hawks | alternate_team_total (game) | home_under +72.5 | +440 | +428 | fanduel | 26.6% | +4.35% | 0.00% | 100% | mid_major |
| North Dakota St Bison at Saint Mary's Gaels | alternate_spread (game) | home -18.5 | +225 | +218 | betrivers | 32.0% | +4.35% | 0.00% | 100% | mid_major |
| Northern Kentucky Norse at South Dakota Coyotes | alternate_team_total (game) | home_under +71.5 | +420 | +414 | fanduel | 24.5% | +3.39% | 0.00% | 100% | low_major |
| Fairleigh Dickinson Knights at Butler Bulldogs | alternate_spread (game) | away +18.5 | +300 | +295 | fanduel | 46.4% | +3.38% | 0.00% | 92% | high_major |
| Milwaukee Panthers at Santa Clara Broncos | moneyline_h1 (h1) | away | +520 | +512 | fanduel | 16.1% | +3.33% | 3.26% | 92% | mid_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

10 position(s) across 10 game(s); the cap is 1 per game and 20 per slate. 30 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

4,195 priced = 321 no opinion + 3,824 below threshold + 0 unparseable + 10 ambiguous + 30 gated + 10 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 4,195 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 321 | no_opinion |
| no price on it clears the declared edge threshold | 3,824 | below_threshold |
| every clearing price is outside the declared band | 10 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 30 | gated |
| the slate's declared position cap is already full | 0 | gated |

578 staged row(s) belong to a slate day other than 2026-11-04 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 10 game(s) judged — upcoming=10. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=16, low_major=2, mid_major=10. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

10 game(s) priced on this slate day, out of 28 the read saw — the board carries every upcoming game, not tonight's. 10,206 staged quote(s) over 38 event block(s).

38 event(s), 384 bookmaker block(s), 10,206 outcome(s) = 10,206 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

326 credit(s) actually spent over 11 request(s); the pessimistic pre-flight bound was 966; 78381 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 10 of 10 game(s).

Frozen: `2026-11-04.csv`, from 4,195 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-04_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**2 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Radford Highlanders at California Golden Bears: bovada total_points (game) over +167.5 at +215 is beaten by +166.5 at +230
- Radford Highlanders at California Golden Bears: bovada total_points (game) under +166.5 at -320 is beaten by +167.5 at -295

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 28 event(s) on 2026-11-04: 10 resolved to a scheduled game, 18 named no game on the schedule that day, 0 name(s) did not resolve. It returned 10 matchup(s), 10 priceable. History: 38,074 team-game row(s) strictly before 2026-11-04, through 2026-11-03, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

3,875 of 4,195 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the distribution could not be built (This segment claims to resolve ties and holds 1.539e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.045e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.177e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.913e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.371e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.638e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.673e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.275e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.619e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.841e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 7,234 settled forward row(s)); low-major 0.000 (seed 0.011, 722 settled forward row(s)); mid-major 0.000 (seed 0.032, 5,370 settled forward row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Line movement: 185 event(s) carry a move since their first capture; 0 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/41895045575
