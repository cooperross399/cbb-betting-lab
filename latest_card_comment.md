**NCAA Division I men's basketball — 2026-11-11, morning slot.** Decision: `selections`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-11-11 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` allowlists 32 market(s): alternate_total_points, championship_winner, moneyline, moneyline_h1, moneyline_h2, player_assists, player_blocks, player_blocks_steals, player_double_double, player_field_goals, player_first_basket, player_first_team_basket, player_frees_attempts, player_frees_made, player_points, player_points_assists, player_points_rebounds, player_pra, player_rebounds, player_rebounds_assists, player_steals, player_threes, player_triple_double, player_turnovers, spread_h1, spread_h2, team_total, team_total_h1, team_total_h2, total_points, total_points_h1, total_points_h2, each behind a verified human acceptance receipt.

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| James Madison Dukes at Delaware Blue Hens | total_points_h1 (h1) | over +72.5 | +148 | +126 | 0.25u | Near tip | fanduel | 40.2% | +12.12% | 0.00% | 82% | mid_major |
| Chicago St Cougars at Cal Baptist Lancers | spread_h1 (h1) | away +4.5 | +125 | +111 | 0.25u | Near tip | bovada | 51.4% | +8.95% | 0.00% | 67% | low_major |
| UMKC Kangaroos at Florida A&M Rattlers | moneyline_h1 (h1) | home | +220 | +204 | 0.25u | Near tip | hardrockbet | 33.4% | +7.51% | 4.71% | 67% | low_major |
| Oakland Golden Grizzlies at Boise State Broncos | moneyline_h1 (h1) | away | +510 | +481 | 0.25u | Near tip | betrivers | 11.1% | +7.14% | 2.58% | 82% | mid_major |
| Jackson St Tigers at Southern Miss Golden Eagles | spread_h1 (h1) | home -7.5 | +130 | +120 | 0.25u | Near tip | bovada | 34.7% | +6.67% | 0.00% | 81% | mid_major |
| Lindenwood Lions at Nebraska Cornhuskers | team_total_h1 (h1) | away_over +26.5 | +105 | -103 | 0.25u | Near tip | draftkings | 58.4% | +6.55% | 0.00% | 79% | high_major |
| Loyola (Chi) Ramblers at Air Force Falcons | moneyline_h1 (h1) | home | +285 | +271 | 0.25u | Near tip | fanduel | 31.3% | +5.92% | 4.68% | 67% | mid_major |
| Fairleigh Dickinson Knights at East Texas A&M Lions | moneyline (game) | away | +599 | +586 | 0.25u | Near tip | courtside | 10.1% | +4.08% | 0.00% | 68% | low_major |
| Southern Indiana Screaming Eagles at IUPUI Jaguars | moneyline (game) | away | +315 | +309 | 0.25u | Near tip | fanduel | 35.3% | +3.64% | 0.00% | 80% | low_major |
| Furman Paladins at Holy Cross Crusaders | moneyline (game) | home | +545 | +538 | 0.25u | Near tip | courtside | 9.5% | +3.20% | 0.00% | 67% | low_major |
| Valparaiso Beacons at South Dakota St Jackrabbits | spread_h1 (h1) | home -0.5 | +110 | +109 | 0.25u | Near tip | bovada | 48.1% | +2.87% | 0.00% | 82% | mid_major |
| UMass Lowell River Hawks at Massachusetts Minutemen | total_points (game) | under +149.5 | +106 | +105 | 0.25u | Near tip | lowvig | 57.2% | +2.80% | 0.00% | 68% | mid_major |
| Oral Roberts Golden Eagles at Tulsa Golden Hurricane | moneyline_h1 (h1) | away | +600 | +600 | 0.25u | Near tip | williamhill_us | 12.0% | +2.00% | 2.71% | 80% | mid_major |

**Bet down to** is the worst price at which the wager still clears the card's 2% edge bar on the probability the bar read, floored at the price band's -400. Below it the same wager would not be a selection.

**Size** is 0.25u, scaled up by the trust the model has earned in the game's tier (the trust line above), at most 0.5u. A tier trusted at zero is the base size. The site's record counts every bet at 0.25u whatever this column says.

**When** is *Now* where the market has already moved toward the selection since its first capture today (at least 2% on a moneyline or 1 point(s) on a spread or total), so the price is leaving; otherwise *Near tip*, because over the archive the model's prices improved toward tip on average. Advice only: it moves no probability, no pick and no size.

Each edge is stated **per wager** and none of them is added to another. A game's spread, its moneyline, both team totals, the game total and a starter's points are one event seen six ways; their edges are not additive and their outcomes are not independent.

The push mass is the probability the joint distribution puts on the line landing exactly. The edge above **understates** the true expectation by that amount, because the one definition of edge in this repository has no push term and counting the push against the bet is the conservative direction. It is also the answer to how much of the number is half a point at a key number rather than a differing view of the game.

## Exposure

13 position(s) across 13 game(s); the cap is 1 per game and 20 per slate. 4 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

18,116 priced = 10,530 no opinion + 677 below threshold + 0 unparseable + 16 ambiguous + 6,880 gated + 13 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 18,116 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 6,876 | gated |
| the model has no opinion on this selection | 10,530 | no_opinion |
| no price on it clears the declared edge threshold | 677 | below_threshold |
| every clearing price is outside the declared band | 16 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 4 | gated |
| the slate's declared position cap is already full | 0 | gated |

0 staged row(s) belong to a slate day other than 2026-11-11 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 48 game(s) judged — upcoming=48. Only `upcoming` may carry a stake. `imminent` is a game tipping inside 60 minutes of the run — the T-60 lead the historical store was bought at and the lead every measured number rests on — and it carries no stake, exactly like a game that has already started. `unconfirmed` is a tip time this lab could not read and it quarantines the same way.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: high_major=10, low_major=9, mid_major=28, unplaced=1. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

**1 provider team name(s) did not resolve**, over 1 lookup(s). Each one is a game this lab cannot place, and a silent loss looks exactly like a quiet market. The alias map is knowingly incomplete: the provider's college basketball key was inactive when it was seeded, so there was no live board to read real spellings off.

## The board this card was made from

Source: the provider.

48 game(s) priced on this slate day, out of 48 the read saw — the board carries every upcoming game, not tonight's. 37,994 staged quote(s) over 96 event block(s).

96 event(s), 1,334 bookmaker block(s), 37,994 outcome(s) = 37,994 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

1,256 credit(s) actually spent over 49 request(s); the pessimistic pre-flight bound was 4,614; 4997018 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

Ladders, halves and props were asked for on 48 of 48 game(s).

Frozen: `2026-11-11.csv`, from 18,116 wager(s) offered. **The first opinion of the day for a game is never retroactively replaced** — this run may add a game the earlier slot could not reach and may never re-price one it did.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-11-11_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## Each book's ladder against itself

**10 quote(s) are dominated on their own book's ladder**: another rung on the same side offers a better line at a better price. This is a fact about the book's prices and is never an edge or a selection.
- Dartmouth Big Green at Albany Great Danes: courtside total_points (game) over +140.5 at -108 is beaten by +139.5 at -106
- Dartmouth Big Green at Albany Great Danes: draftkings total_points (game) over +140.5 at -110 is beaten by +139.5 at -108
- Charleston Cougars at Temple Owls: courtside total_points (game) over +155.5 at -142 is beaten by +154.5 at -137
- Charleston Cougars at Temple Owls: draftkings total_points (game) over +155.5 at -145 is beaten by +154.5 at -140
- Charleston Cougars at Temple Owls: courtside total_points (game) under +154.5 at +112 is beaten by +155.5 at +116
- Charleston Cougars at Temple Owls: draftkings total_points (game) under +154.5 at +110 is beaten by +155.5 at +114
- UMKC Kangaroos at Florida A&M Rattlers: courtside total_points (game) over +146.5 at -118 is beaten by +145.5 at -113
- UMKC Kangaroos at Florida A&M Rattlers: courtside total_points (game) over +146.5 at -118 is beaten by +145.5 at -113
- UMKC Kangaroos at Florida A&M Rattlers: draftkings total_points (game) over +146.5 at -120 is beaten by +145.5 at -115
- South Carolina St Bulldogs at Notre Dame Fighting Irish: bovada spread (game) home -27 at -115 is beaten by -26.5 at -110

## What the model said

Model `cbb_betting_lab.models.ratings:matchups_for` asked about 48 event(s) on 2026-11-11: 47 resolved to a scheduled game, 0 named no game on the schedule that day, 3 name(s) did not resolve. It returned 47 matchup(s), 47 priceable. History: 38,834 team-game row(s) strictly before 2026-11-11, through 2026-11-10, from `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv`.

16,316 of 18,116 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

Design 4's structural check was not asked: this card built no player distribution.

Design 13's per-tier resolution rate was not asked: this card holds no player projection to tier.

No scoring-event dispersion was chosen on this card: it built no player distribution.

| Why the model has no opinion | Wagers |
|:---|---:|
| the model was never asked about this event's athletes, so this prop carries no opinion: the model returned matchups only, so it was never asked about any athlete and no projection exists for this day. An absent projection is not a probability of zero | 753 |
| no rating exists for this game: the board event did not join to a game the model was asked about, so the model was never asked about THIS one — the two school names resolved to no hoopR team, or resolved and named no game on this day's schedule, and `reports/card_matchups.py`'s join census says which. A join failure is not the model declining, and it is not a pass, an avoid or a no-value call. The model answered about 47 other game(s) on this slate | 404 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.498e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 64 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.330e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.412e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.650e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 1.906e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.340e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 2.504e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.268e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 3.675e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.457e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.512e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.649e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.813e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.945e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.975e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 4.993e-02 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 5.242e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the distribution could not be built (This segment claims to resolve ties and holds 9.218e-03 of probability on the diagonal. A full game cannot end level; either the overtime cascade did not run or it did not converge.) | 32 |
| the player model is registered against ten markets and this is not one of them, so it was never asked about this line: player_points, player_rebounds, player_assists, player_threes, player_steals, player_turnovers, player_pra, player_points_rebounds, player_points_assists, player_rebounds_assists. An unregistered market is not a refusal and it is not a pass, an avoid or a no-value call | 20 |
| refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one. | 15 |

15,280 wager(s) the model priced were taken out of the edge bar's reach before it read them, so the identity above counts them under `no_opinion` with the wagers the model declined:

| Withdrawn before the edge bar | Wagers |
|:---|---:|
| no fair price: fewer than the trust table's minimum of books quote both sides | 12,278 |
| closed by the closing-line gate (models/closing_gate.py) | 2,984 |
| past the alternate-ladder cap (models/rung_cap.py) | 18 |

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
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/43042824833
