# What the site reads

Every page under `web/` is static and reads JSON that Publish Board writes
into `dist/data/`. Nothing on the site fetches a price, and no page names the
source of any input; the lab's documentation does that.

| File | Written by | Read by |
|:-----|:-----------|:--------|
| `board.json` | `build_board_json.py` | Board (shared), Game, Graphic (shared), Results (shared) |
| `history/<day>[_<slot>].json`, `history/index.json` | `site_history.py` | Archive (shared), Game (`?date=`) |
| `history/settled/<day>.json`, `results.json` | `settle_results.py` | Results (shared), Game (final), `site_pages.py` |

In `results.json` and `history/settled/<day>.json` (2026-11-12) a graded CBB bet or lean carries `units` and `staked` at the tracked stake and `baseLabel`, its label as the board published it; `label` is `baseLabel · ±N.NNu`, so the shared Results page shows the units. `summary.picks` / `summary.leans`, `seasonRecord.picks` / `.leans` and `board.json` `record.picks` / `.leans` carry `units` and `staked` beside `w`, `l`, `p`. From 2026-11-13 `straightUp` and `totals` (night, season and board record) carry them too, priced at the board's moneyline for the projected winner and its `overPrice` / `underPrice` for the model's side; a call with no price on the board is counted in `unpriced` and staked nothing. A game's `total` carries `underPrice` beside `overPrice`.
| `history/finals/<day>.json` | `site_pages.py` | `site_pages.py` (a finals cache for days the settle did not keep) |
| `record.json` | `build_site_pages.py` | Record |
| `tracker.json` | `build_site_pages.py` | All results (Tracker) |
| `season.json` | `build_board_json.py` (through `site_pages.write_model_pages`) | Season |
| `ratings.json` | `build_board_json.py` (through `site_pages.write_model_pages`) | Season (ratings view) |
| `../site.json` | the workflow | `lib/sports.js` (`pages` lists the tabs this lab publishes) |

Samples for the previews live in `web/data/sample/` under the same names.

## board.json additions (2026-10-26)

Each game may carry, beside the keys the shared Board reads:

- `pick`: the card's own selection for the game when the card state recorded
  one (`kind: "bet"`, `units: 1.0`), else the best frozen opinion as
  `kind: "pass"` with `units: null`. A pass is a priced opinion the card did
  not select; a game the model refused has no `pick` at all and is never a
  pass. Since decision 74 an opinion the card did not select is
  `kind: "lean"` when its edge is at least
  `LEAN_EDGE` (the card's 2% bar), its market is allowlisted under a verified
  receipt and its price is inside the card's band; it stakes nothing and is
  graded into `record.leans`. `basis` is `"frozen"` for an opinion read off the
  forward freeze and `"model"` for one read off the board's own projection on a
  game the freeze holds no opinion on, which is published before tip only.
  Since decision 79 that edge is read on the trust-weighted probability the
  card's edge bar reads -- `market + w_tier x (model - market)`, the market
  the de-vigged two-sided price -- not the model's own; a side with no
  two-sided price is a pass. `modelProb` stays the model's own number and
  `trustedProb` carries the one the edge was read on.
- `factors`: the home win chance repriced step by step in the card's order,
  `[{key, label, homeWin, delta, homePts, awayPts, possessions, note}]`, keys
  `strength`, `home_court`, `form`, `rest`, `lineup`, `second_opinion`. The last
  `homeWin` equals `home.winProb`. Absent on a game the model refused.
- `ratings`: `{home, away}`, each `{offence, defence, net, tempo, tier, form,
  formGames, restDays, restBucket, restEffect, missing, lineupFactor,
  secondOpinion}` in points per 100 possessions against the average
  (`secondOpinion` is `{offence, defence, tempo}` or `null`).
- `tiers`: `{home, away}` as `high_major` / `mid_major` / `low_major` / `null`.
- `homeCourt`: `{tierMargin, departure, appliedBy}`.
- `moneyline.current`, `spread.current`, `total.current` and their opens come
  from the card's latest capture of the provider's board where it holds the
  market, and otherwise from the main line ESPN's scoreboard posts beside the
  game (`posted_lines`, decision 76). A game no book quotes carries none.
- `spread.coverProb`, `spread.fairHomePrice`, `total.overProb`,
  `total.fairOverPrice`: the model's chances and fair prices on the posted
  lines.

- `shops` (decision 93): the newest hourly capture's price shops on the game,
  before tip only, best first: `[{label, market, side, line, book, price,
  fair, edgePct, books, asOf}]`, a book whose price beats the median of
  every book's own no-vig price by at least 2% (`reports/price_shop.py`).
  Read from `line-movement`'s `latest_price_shop.json`; absent when that
  capture is more than three hours old. A slow book, never a model pick. The
  Tonight board is a shared page and does not show it; the game page does.

At the top level, `league: {efficiency, tempo}` is the Division I average
the ratings are measured against (points per 100 possessions, possessions
per game), so the game page can show each team as "+N% vs average". Absent
when the board was built without a fit.

The game page reads `factors` only to rank the three biggest reasons behind
the number; it draws no waterfall and prints no step.

## record.json

Accuracy only, never a return.

```
{generatedAt, through, nights, games,
 buckets: [{low, high, games, predicted, actual, interval: [lo, hi]}],
 byTier: {"<High major|Mid major|Low major|Unplaced>": {games, buckets}},
 brier: {games, model, market, modelAll},
 markets: {spread: {games, buckets}, total: {games, buckets}},
 movement: {toward, against, flat, picks},
 clv: {picks, meanPoints, beatClosePct, bets: {picks, meanPoints, beatClosePct}},
 notes: [..]}
```

`clv` is closing-line value on spread and total picks: the picked line against
the last line `history/lines/<day>.json` recorded before tip, in points from
the bettor's side, so positive is the better number. A tie does not beat the
close. Moneyline picks are left out because the series keeps only the home
price. `build_site_pages.py` also writes `meanPoints`, `beatClosePct` and
`picks` onto `board.json` as `record.clvPoints`, `record.beatClosePct` and
`record.clvPicks`.

Each game is counted once under the side the board favoured; `predicted` is
the mean published chance in the band and `actual` the share that won.
`interval` is a Wilson 95% interval on the share. Market bands are merged
until each holds at least 10 games.

## tracker.json

```
{generatedAt, nights, firstDate, lastDate, teamPickDefaultUnits: 0.25,
 stake: 0.25, stakeRule,
 overall, byMarket, byTeam, byTier, byPrice, byMonth,
 leans: {overall, byMarket, byPrice, byMonth},
 opinions: {overall, byMarket, byKind},
 rows: [{date, id, kind, group, market, label, price, betDownTo, book, tier, team,
         teams: [away, home], line, result, staked, units, final,
         closeLine, clvPoints}],
 notes: [..]}
```

A tally is `{w, l, p, bets, staked, units, returnPct}`; a grouped list is
`[{key, ...tally}]`. A best bet is counted at 0.25u on a plus price, or
enough to win 0.25u on a minus price, at the board's price, whatever the card
staked it (2026-11-04), up to +199; from +200 the NHL Due List's ladder applies, +200 to +500 at 0.15u, +501 to +1500 at 0.1u and longer than +1500 at 0.05u (2026-11-11, `stakeLadder`); `staked` is the amount risked, and a push returns 0. A
bet with no usable price is graded with `units: null`. A lean is tracked at the same stakes (2026-11-04), tallied under `opinions` and never in `overall`, and on its own under `leans` (2026-11-12), so every lean record the Record page shows carries its units; a pass is graded and staked nothing (`units: null`). `byTier` keys are
the card's tier letters (A high major, B mid major, C low major).

## season.json

```
{generatedAt, season, asOf, phase: "preseason"|"regular", played, remaining, projected,
 conferences: [{id, name, teams: [{id, abbr, name, short, tier, net, logo,
   record: {w, l}, confRecord: {w, l}, projConf: {w, l}, projOverall: {w, l},
   remaining, confRemaining, projRank}]}],
 method: [..]}
```

Projected records are expected wins over the games still to play on the
cached schedule, priced on the ratings and venue alone.

## ratings.json

```
{generatedAt, season, asOf, through, league: {efficiency, tempo, marginSd},
 tierCounts, rated,
 teams: [{id, abbr, name, short, conferenceId, conference, tier, offence,
          defence, net, tempo, games, form, logo, rank, wab, netRank?, bpiRank?,
          tonight?: {id, label, vs}}],
 note}
```

`wab` is wins above bubble from the day's ratings (`models/four_factors.resume`).
`netRank` and `bpiRank` (decision 93) are the NCAA's NET and ESPN's power
index, each ranked by its own net rating from the table the card's second
opinion read, shown only when that table is dated within a week of the page.
A subscription table the card reads is not shown.

## Bet down to (2026-11-01)

Every `pick` of kind `bet` or `lean` carries `betDownTo`: the worst American
price at which it still clears the card's 2% edge bar, floored at the price
band's −400 (null when no price in the band clears). A card selection carries
the number `reports.card_pricing.bet_down_to` computed on the probability the
bar read; a frozen opinion recovers that probability from its own edge and
price; a model-basis lean reads it off the push-aware win and loss chances.
The same pick carries `sub` and `extra`, the two lines the shared Board prints
under its label, with the bet-down-to number in `sub`. `tracker.json` rows
carry `betDownTo` too.
