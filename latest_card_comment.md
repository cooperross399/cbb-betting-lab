**NCAA Division I men's basketball — 2026-09-01, morning slot.** Decision: `no-slate`. The card itself rendered without a problem; `latest_status.json` carries the run's health, which this process cannot see.
# CBB card — 2026-09-01 (morning)

This card is **accumulating evidence, not making recommendations.**

`the_odds_api:cbb` is **manual-only**. No market is allowlisted, the card produces no selection, and that is the correct state for a lab with no signed receipt.

## Selections

**None.** No wager on this slate cleared every bar.

No bar was reached, because there was no priced wager on this slate day to reach one. That is an absence of board coverage and it is reported as one.

That is not a pass, an avoid, or a no-value call, and it is not the model declining to find value. It is the state this lab is designed to be in until Cooper signs an acceptance receipt for a market: **Claude may withdraw an allowlist and may never grant one.** No selection, no lean, no pass and no stake.

## Exposure

0 position(s) across 0 game(s); the cap is 1 per game and 20 per slate. 0 wager(s) cleared every bar and were held back by a cap. Spread, moneyline, team total, game total and a player's points are one event seen five ways: these are counted per game and per slate, and their edges are never summed.

## The accounting identity

0 priced = 0 no opinion + 0 below threshold + 0 unparseable + 0 ambiguous + 0 gated + 0 bets (reconciles).

The unit is a **wager**, plus the price rows on this slate day that could not be made into one: 0 wager(s) and 0 unreadable row(s). A wager is one bet however many books hang it — twenty-one books quoting one game is not twenty-one bets, and counting quotes as bets is what made every interval in the NHL lab's first store √2.83 too narrow.

**This is the second of two identities and they are deliberately not merged.** The board section below carries the first, over the provider's *outcomes*: `outcomes = staged + unwired market + unknown selection + unreadable price + unplaceable event`. It reconciles on its own. Folding it into this one would put two populations on either side of a single equals sign — the outcomes are counted across every day the read saw, and these wagers are this slate day only — and an identity whose two sides describe different populations reconciles over whichever population survived. The count that joins them is the off-slate figure below.

| Bar | Wagers | Bucket |
|:---|---:|:---|
| the market is not allowlisted by a reviewed policy | 0 | gated |
| the model has no opinion on this selection | 0 | no_opinion |
| no price on it clears the declared edge threshold | 0 | below_threshold |
| every clearing price is outside the declared band | 0 | ambiguous |
| availability cannot be confirmed | 0 | gated |
| the game has tipped, is imminent, or has no readable tip time | 0 | gated |
| a position is already taken on this game | 0 | gated |
| the slate's declared position cap is already full | 0 | gated |

0 staged row(s) belong to a slate day other than 2026-09-01 and were not considered here. The bulk endpoint returns every upcoming game, not tonight's; a row for tomorrow frozen under today's date would look unfrozen tomorrow and be priced twice.

## The gates, each of which fails closed

**Availability.** **cannot produce a selection** — no availability report exists for this game. Division I men's basketball has no mandated injury report, and roughly two thirds of the division is never covered by the conference reports that do exist. This is not a pass, an avoid or a no-value call: it is a market the lab prices, freezes and settles but may not bet.

Measured, not assumed: ESPN's men's-college-basketball injuries endpoint returns zero records permanently (against 76 for the NBA in the NBA's own off-season), CollegeBasketballData has no availability endpoint at all, and the conference reports that do exist cover roughly 115 of 365 teams, conference games only. Nothing can reach `confirmed`, so no player prop can produce a selection.

**Tip time.** Tip guard, run against each game's own tip: 0 game(s) judged — none. Only `upcoming` may carry a stake; `unconfirmed` is a tip time this lab could not read and it quarantines exactly like a game that has already started.

It is judged twice — once when the bars are applied and once again on a freshly read clock immediately before this card was written — because this sport tips games every fifteen minutes for twelve hours and a slate takes minutes to fetch.

**Venue.** A game whose venue state is unknown or contradictory is quarantined rather than defaulted to neutral. Venue has three values in this sport and not two: of 709 games flagged neutral in 2025-26, 39 were in a participant's own city and 7 in their own arena.

**Tier.** Tiers from season(s) [2024, 2025, 2026], strictly before this one: none. A game takes the higher of its two sides' tiers, because the board's attention follows the stronger programme.

No pooled headline across the whole of Division I is ever reported. High-major, mid-major and low-major are different distributions, and `unplaced` is a state reported separately rather than folded into a tier's number.

## The board this card was made from

Source: the provider.

0 game(s) priced on this slate day, out of 0 the read saw — the board carries every upcoming game, not tonight's. 0 staged quote(s) over 0 event block(s).

0 event(s), 0 bookmaker block(s), 0 outcome(s) = 0 staged + 0 unwired market + 0 unknown selection + 0 unreadable price + 0 unplaceable event (reconciles).

Every outcome in this response was staged.

6 credit(s) actually spent over 1 request(s); the pessimistic pre-flight bound was 6; 4705916 remaining.

The cap is enforced inside the provider adapter before every request, against the **measured** running total from the response headers, never against the pre-flight estimate.

No per-event market was asked for: the slate is empty.

Nothing new was frozen from 0 wager(s) offered: every one of them was already frozen for this slate day, or none could be. A snapshot that already stands is not rewritten.

The whole board, every book, was written to `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/staging/cbb/2026-09-01_morning.csv` — which the card cannot read. Line shopping and price survival are measured from there; the freeze keeps one row per wager at the best price, which is the price this card would have taken.

## What the model said

0 of 0 priced wager(s) carry a modelled opinion. An absent opinion is **not** a probability of zero: it is the model declining, or never being asked.

The model had an opinion on every priced wager.

Recorded verdicts in force: calibration_correction=off, champion_model=off, conference_tier_fits=off, endgame_segment_model=off, november_prior_schedule=off, overtime_segment_model=off, props_selectable_when_unconfirmed=off, schedule_state_adjustment=off, venue_home_effect=off.

No earlier card for this slate day was available to this run, so nothing is claimed about whether the selections changed.

## What this card is not

* It is not a recommendation. This card is **accumulating evidence, not making recommendations.**
* An excluded market is **never** reported as a pass, an avoid, or a no-value call. Where a market produced nothing, the card says which gate stopped it.
* No number here is a measured edge. Every number above is a count of what this run did, and each one is stated with what it is out of.
* Nothing here is wired to a sportsbook, and no bet was placed.
* No market is allowlisted. Claude may withdraw an allowlist and may never grant one.

---
Run: https://github.com/cooperross399/cbb-betting-lab/actions/runs/33551726107
