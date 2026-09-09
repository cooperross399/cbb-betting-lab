# Prop accounting — what became of every prop wager the store offers

**This is a census and not a grading.** Every number below is a count of wagers. Nothing here compares a probability against a price, and no result of any kind is stated or implied.

- Store: `/private/tmp/wt-grading/data/processed/cbb_historical_prices__card.csv`, 977,613,435 bytes, sha256 `143d7d307d9bc3b21989d7857aac6a52f8abd010da2c1e0ea2df8c0f0b82b78b`
- 3,863,325 rows scanned, 504,394 of them prop quotes, over 1,180 event(s) and 140 slate day(s)
- Subject: the declared fold is `casefold`, and the offered count below is under that one and no other
- Model: `cbb_betting_lab.models.slate:slate_model`, walk-forward over 140 slate day(s)

**257,474 wager(s) offered, 257,474 accounted for, residual 0.**

| Bucket | Wagers |
|:---|---:|
| priced | 246,218 |
| refused by name | 723 |
| no opinion (the four below, never summed into a finding) | 10,531 |
| &nbsp;&nbsp;unregistered_market | 0 |
| &nbsp;&nbsp;name_unresolved | 6,154 |
| &nbsp;&nbsp;athlete_refused | 4,377 |
| &nbsp;&nbsp;never_asked | 0 |
| unreadable | 2 |

## Per market

| Market | Offered | Accounted | Residual | Buckets |
|:---|---:|---:|---:|:---|
| player_assists | 33,630 | 33,630 | 0 | name_unresolved=1,112, athlete_refused=754, priced=31,764 |
| player_double_double | 2 | 2 | 0 | refused_by_name=2 |
| player_first_basket | 721 | 721 | 0 | refused_by_name=721 |
| player_points | 78,213 | 78,213 | 0 | name_unresolved=1,772, athlete_refused=1,324, priced=75,115, unreadable=2 |
| player_points_assists | 6,903 | 6,903 | 0 | name_unresolved=64, priced=6,839 |
| player_points_rebounds | 7,943 | 7,943 | 0 | name_unresolved=114, priced=7,829 |
| player_pra | 23,613 | 23,613 | 0 | name_unresolved=350, athlete_refused=610, priced=22,653 |
| player_rebounds | 52,710 | 52,710 | 0 | name_unresolved=1,387, athlete_refused=974, priced=50,349 |
| player_rebounds_assists | 6,436 | 6,436 | 0 | name_unresolved=76, priced=6,360 |
| player_steals | 11,310 | 11,310 | 0 | name_unresolved=176, athlete_refused=10, priced=11,124 |
| player_threes | 25,179 | 25,179 | 0 | name_unresolved=921, athlete_refused=691, priced=23,567 |
| player_turnovers | 10,814 | 10,814 | 0 | name_unresolved=182, athlete_refused=14, priced=10,618 |

## Per tier

Printed side by side and never pooled into one Division I line: a fold that refuses one tier's spellings more often than another's reads as a single number in a total and as a biased population three steps downstream.

| Tier | Wagers | Buckets |
|:---|---:|:---|
| high_major | 97,042 | refused_by_name=411, name_unresolved=2,170, athlete_refused=2,460, priced=92,001 |
| low_major | 3,722 | refused_by_name=10, name_unresolved=126, priced=3,586 |
| mid_major | 156,710 | refused_by_name=302, name_unresolved=3,858, athlete_refused=1,917, priced=150,631, unreadable=2 |

## Why the model said nothing

The model's own sentences, grouped. Not one of them is a pass, an avoid or a no-value call, and an absent opinion is never a probability of zero.

**athlete_refused** — 4,377 wager(s) in 2 distinct sentence(s)

- 3,861 x refused: fewer than four prior appearances / fewer than sixty prior minutes; this would be a role-table price wearing a player's name.
- 516 x refused: this athlete carries no minutes projection, or one below eight minutes. Below eight the distribution is dominated by whether he plays at all, which this lab cannot know at sixty minutes to tip -- the projection would be a statement about the coach and would be published as one about the player. Not a pass, not an avoid, not a no-value call.

**name_unresolved** — 6,154 wager(s) in 2 distinct sentence(s)

- 6,144 x refused: this name resolves only in tonight's box score, which is a player this lab has not seen, not a name it cannot read. The clause after the comma is the design's and this module cannot check it: the roster searched is a PRIOR roster, so a spelling that reaches no prior athlete is a debutant and an unreadable spelling at once, and separating the two would need the box score of the game being priced. `providers/player_names.py` measured 372 unreachable spellings on 2026-09-05, against 9,584 (game, player) pairs, on a settlement-time join this module may not make.
- 10 x refused: this lab could not read the book's spelling of this player as exactly one athlete on either roster.

**refused_by_name** — 723 wager(s) in 2 distinct sentence(s)

- 721 x refused: this market settles on the scorer of the game's first field goal, which is decided by the starting five and the opening tip. Neither is knowable at T-60 in this sport, no tip-winner data exists in any table here, and a per-minute rate says nothing about minute zero. It is also a mutually exclusive family -- the probabilities across a game's players must sum to at most one, and the store quotes 422 names over 1,180 games, a partial field, so no normalisation exists and independently priced names would over-sum with nothing looking wrong. This is a model refusal, not a data absence: `first_basket_athlete_id` is present on 100% of game-segment rows and the market is perfectly settleable. Not a pass, not an avoid, not a no-value call.
- 2 x refused: the store holds two quotes on one player-game. There is nothing to measure, and pricing it would add a pre-registered hypothesis -- widening every other interval in the lab -- in exchange for a sample of one.

**unreadable** — 2 wager(s) in 1 distinct sentence(s)

- 2 x refused: R4, line above the count lattice ceiling. This lattice runs to 83 and the line is 89.5. Returning (0, 0, 1) there would report a confident zero that is an artefact of where the lattice was truncated.

