# What the site reads

Every page under `web/` is static and reads JSON that Publish Board writes
into `dist/data/`. Nothing on the site fetches a price, and no page names the
source of any input; the lab's documentation does that.

| File | Written by | Read by |
|:-----|:-----------|:--------|
| `board.json` | `build_board_json.py` | Board (shared), Game, Graphic (shared), Results (shared) |
| `history/<day>[_<slot>].json`, `history/index.json` | `site_history.py` | Archive (shared), Game (`?date=`) |
| `history/settled/<day>.json`, `results.json` | `settle_results.py` | Results (shared), Game (final), `site_pages.py` |
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
  pass.
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
- `spread.coverProb`, `spread.fairHomePrice`, `total.overProb`,
  `total.fairOverPrice`: the model's chances and fair prices on the posted
  lines.

## record.json

Accuracy only, never a return.

```
{generatedAt, through, nights, games,
 buckets: [{low, high, games, predicted, actual, interval: [lo, hi]}],
 byTier: {"<High major|Mid major|Low major|Unplaced>": {games, buckets}},
 brier: {games, model, market, modelAll},
 markets: {spread: {games, buckets}, total: {games, buckets}},
 movement: {toward, against, flat, picks},
 notes: [..]}
```

Each game is counted once under the side the board favoured; `predicted` is
the mean published chance in the band and `actual` the share that won.
`interval` is a Wilson 95% interval on the share. Market bands are merged
until each holds at least 10 games.

## tracker.json

```
{generatedAt, nights, firstDate, lastDate, teamPickDefaultUnits: 1,
 overall, byMarket, byTeam, byTier, byPrice, byMonth,
 opinions: {overall, byMarket, byKind},
 rows: [{date, id, kind, group, market, label, price, book, tier, team,
         teams: [away, home], line, result, staked, units, final}],
 notes: [..]}
```

A tally is `{w, l, p, bets, staked, units, returnPct}`; a grouped list is
`[{key, ...tally}]`. A best bet is staked one flat unit at the board's price;
a lean or pass is graded and staked nothing (`units: null`). `byTier` keys are
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
          defence, net, tempo, games, form, logo, rank, tonight?: {id, label, vs}}],
 note}
```
