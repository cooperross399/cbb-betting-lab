**NCAA Division I men's basketball — 2026-11-11, evening slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-11 (evening)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 32 market(s): alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| Oakland Golden Grizzlies at Boise State Broncos | moneyline_h1 (h1) | away | +570 | +509 | 0.10u | Near tip | fanduel | 11.1% | +12.27% | 2.58% | 82% | mid_major |
| UTSA Roadrunners at Seattle Redhawks | moneyline_h1 (h1) | away | +570 | +529 | 0.10u | Near tip | fanduel | 13.7% | +8.81% | 3.00% | 64% | mid_major |
| Campbell Fighting Camels at East Tennessee St Buccaneers | total_points_h1 (h1) | over +71.5 | +150 | +136 | 0.25u | Near tip | bovada | 45.7% | +8.06% | 0.00% | 67% | mid_major |
| Chicago St Cougars at Cal Baptist Lancers | spread_h1 (h1) | away +4.5 | +120 | +109 | 0.25u | Near tip | bovada | 51.4% | +7.77% | 0.00% | 67% | low_major |
| Marquette Golden Eagles at Michigan Wolverines | total_points_h1 (h1) | over +76.5 | +148 | +141 | 0.25u | Near tip | fanduel | 31.2% | +5.36% | 0.00% | 69% | high_major |
| North Carolina Central Eagles at VMI Keydets | moneyline (game) | away | +335 | +327 | 0.15u | Near tip | ballybet | 32.0% | +4.03% | 0.00% | 82% | low_major |
| USC Trojans at California Golden Bears | moneyline (game) | home | +315 | +309 | 0.15u | Near tip | fanduel | 36.8% | +3.58% | 0.00% | 65% | high_major |
| Valparaiso Beacons at South Dakota St Jackrabbits | spread_h1 (h1) | home -0.5 | +110 | +109 | 0.25u | Near tip | bovada | 48.1% | +2.87% | 0.00% | 82% | mid_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. A long price is sized by its price instead: +200 to +500 0.15u, +501 to +1500 0.1u, longer than +1500 0.05u (the NHL Due List ladder). The site's record counts every bet at 0.25u, or to win 0.25u on a minus price, up to +199, and at that ladder from +200, whatever trust says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

8 position(s) across 8 game(s); the cap is 1 per game and 20 per slate. 4 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

17,988 priced = 10,742 no opinion + 664 below threshold + 0 unparseable + 22 ambiguous + 6,552 gated + 8 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 17,988 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 6,536 | gated |
| the model has no opinion on this selection | 10,742 | no_opinion |
| no price on it clears the declared edge threshold | 664 | below_threshold |
| every clearing price is outside the declared band | 22 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 12 | gated |
| a position is already taken on this game | 4 | gated |
| the slate's declared position cap is already full | 0 | gated |

130 staged row(s) belong to a slate day other than 2026-11-11 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 46 game(s) judged — imminent=1, started=4, upcoming=41. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=14, low_major=8, mid_major=37, unplaced=1. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

**1 provider team name(s) did not resolve**, over 1 lookup(s). Each one is a game this lab cannot place, and a silent loss looks exactly like a quiet market. The alias map is knowingly incomplete: the provider's college basketball key was inactive when it was seeded, so there was no live board to read real spellings off.

## The board this card was made from

Source: the provider.

46 game(s) priced on this slate day, out of 60 the read saw — the board carries every upcoming game, not tonight's. 39,999 staged quote(s) over 106 event block(s).

106 event(s), 1,330 bookmaker block(s), 39,999 outcome(s) = 39,999 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,292 credit(s) actually spent over 47 request(s); the pessimistic pre-flight bound was 4,422; 4994972 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 46 of 46 game(s).

Frozen: `2026-11-11.csv`, from 16,120 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-11_evening.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**24 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Incarnate Word Cardinals at UC Davis Aggies: draftkings spread_h1 (h1) away +8.5 at -145 is beaten by +9.5 at +100
- Incarnate Word Cardinals at UC Davis Aggies: fanduel spread_h1 (h1) away +12.5 at -380 is beaten by +13.5 at -136
- Incarnate Word Cardinals at UC Davis Aggies: draftkings spread_h1 (h1) home -9.5 at -135 is beaten by -8.5 at +110
- Incarnate Word Cardinals at UC Davis Aggies: fanduel spread_h1 (h1) home -13.5 at +102 is beaten by -12.5 at +260
- Incarnate Word Cardinals at UC Davis Aggies: draftkings team_total_h1 (h1) home_over +44.5 at -250 is beaten by +43.5 at -130
- Incarnate Word Cardinals at UC Davis Aggies: draftkings team_total_h1 (h1) home_under +43.5 at +100 is beaten by +44.5 at +180
- Incarnate Word Cardinals at UC Davis Aggies: betmgm total_points (game) under +155.5 at -115 is beaten by +156.5 at -110
- Incarnate Word Cardinals at UC Davis Aggies: draftkings total_points_h1 (h1) over +80.5 at -170 is beaten by +77.5 at -115
- Incarnate Word Cardinals at UC Davis Aggies: draftkings total_points_h1 (h1) under +77.5 at -120 is beaten by +80.5 at +125
- Dartmouth Big Green at Albany Great Danes: betrivers spread (game) away -7.5 at -139 is beaten by -6.5 at -134
- and 14 more.

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 60 event(s) on 2026-11-11: 45 resolved to a scheduled game, 14 named no game on the schedule that day, 3 name(s) did not resolve. It returned 45 matchup(s), 45 priceable. History: 38,834 team-game row(s) strictly before 2026-11-11, through 2026-11-10, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

15,456 of 17,988 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 1,204 |
| no rating exists for this game: the board event did not join to a game the model was asked about, so the model was never asked about THIS one — the two school names resolved to no hoopR team, or resolved and named no game on this day's schedule, and `reports/card_matchups.py`'s join census says which. A join failure is not the model declining, and it is not a pass, an avoid or a no-value call. The model answered about 45 other game(s) on this slate | 382 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.675e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 160 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.498e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 94 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.457e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 48 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.330e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.412e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.650e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.906e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.204e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.340e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.504e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.635e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.824e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.184e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.256e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.324e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.649e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.813e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.942e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.945e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.993e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 5.242e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 9.218e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 21 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 15 |

14,388 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 10,856 |
| closed by the closing-line gate (models/closing_gate.py) | 3,496 |
| past the alternate-ladder cap (models/rung_cap.py) | 36 |

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 36,268 settled forward row(s), 22,040 closing-line row(s)); low-major 0.000 (seed 0.011, 5,418 settled forward row(s), 5,648 closing-line row(s)); mid-major 0.000 (seed 0.032, 26,216 settled forward row(s), 17,304 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.

Closing-line gate: high-major alternate_spread, high-major alternate_total_points, high-major spread, high-major team_total, high-major total_points, low-major alternate_total_points, mid-major alternate_spread, mid-major alternate_total_points, mid-major team_total closed tonight; the model's leans there have lost to the close (alarm of 2026-11-11).

Line movement: 482 event(s) carry a move since their first capture; 0 lean(s) the market moved against were halved before the edge bar (a move of at least 2% on a moneyline or 1 point(s) on a spread or total).

**This is a November-regime slate.** Roster turnover in this sport is enormous and the win/loss graph is nearly disconnected between conferences this early, so a rating now is identified almost entirely by the preseason prior. Every price on this card carries the prior's weight beside it, and a price whose rating records no prior weight is refused rather than shown — a November number must never be presentable as a February one.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* Every market above was allowlisted by a reviewed policy with a human acceptance receipt behind it — verified when the policy was loaded, not asserted: a receipt file naming the market, citing an evidence record whose sha256 still matches the file on disk, signed by a person who is not Claude, and dated. A policy with one allowlisted market lacking any of that loads manual-only in its entirety. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/43084586774
