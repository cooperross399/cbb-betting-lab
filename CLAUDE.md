# CLAUDE.md — College Basketball Betting Lab Operating Instructions

This repository is the source of truth for the College Basketball Betting Lab.
Claude operates it directly. Where anything else in the repo conflicts with this
file, this file wins.

**Active repo path: `/Users/cooperross/Projects/cbb-betting-lab`.**

**Scope: NCAA Division I men's basketball, and only that.** Cooper, 2026-08-31:
women's basketball and the lower divisions are **separate projects in their own
repositories** if they ever happen — the same call he made for NCAAF. Do not add
them here: not a registry entry, not an adapter, not a season calendar. He
confirmed it again mid-build on 2026-09-01 (*"dont worry about women's
basketball"*). If a session finds itself widening this lab, it has misread this
line.

The competition registry stays, and it is not wasted work. It keeps every
sport-specific fact — provider sport key, market list, season calendar,
timezone, day boundary, credit cap, policy key, output prefix — in one place
rather than scattered through the code, which is exactly what made this
machinery copyable out of the NHL lab and into this one. It is a **portability**
device rather than a multi-sport one, and
`tests/test_competition_registry_is_the_only_place.py` fails the build when a
sport literal appears anywhere else.

**This is the fourth lab, and the port is a known cost.** These four
repositories share no code, and the same defect classes appear independently in
each. `docs/ported_defects.md` lists every defect class inherited from a sibling,
where it came from, and the regression test here that pins it. Read it before
believing this lab is sound. **Do not refactor the sibling labs — that
prohibition is absolute and is not a question to bring Cooper.** They hold
measured numbers that cannot be rebought.

## Read these first

Every session, in this order. These replace chat history as project memory.

1. `CLAUDE.md` (this file) — hard rules, which override everything.
2. `docs/what_we_can_and_cannot_claim.md` — written before the first
   measurement. Read before making any claim about whether this works.
3. `docs/cbb_data_sources.md` — where every number comes from, what each source
   cannot tell us, its licence, its revision behaviour and its latency.
4. `docs/when_this_ends.md` — the decision date and the sample floor, both
   declared before the data existed.
5. `docs/credit_cost.md` — what this costs against a quota shared with three
   labs.
6. `docs/project_status.md` — where the lab is and what to do next.
7. `docs/decision_log.md` — every judgment call this build made instead of
   asking.
8. Latest `data/outputs/` reports, then PRs and Actions runs.

The ordering is deliberate: **claims before sources before cost before status.**
A session that reads status first will quote a number before it knows how to
read it.

## Current operating state

**As of 2026-09-01. Nothing has been measured yet, no market is allowlisted,
nothing is bet, and that is the correct state.** The season opens in two months
and the machinery is being built before it, which is the whole point of the
runway.

### The season, verified rather than assumed

- **The 2026-27 D-I season opens Sunday 2026-11-01** — a single game, Notre Dame
  against Villanova at the Palazzetto dello Sport in Rome, 09:30 ET. **Real
  volume starts Monday 2026-11-02.** That is 61 days from today.
- **The 2027 NCAA tournament is 76 teams and 75 games**, not 68 and 67. It is
  the first season under the expanded bracket: the First Four becomes a
  12-game Opening Round of 24 teams on 16-17 March 2027, then the familiar
  63-game 64-team bracket. **Cooper's brief says 67 games and is a season out of
  date**; verified against NCAA.org and NCAA.com.
- **365 D-I teams across 32 conferences.** Build the universe from ESPN's
  conference walk, **not** `/teams?groups=50`, which returns 362 and silently
  omits Queens, Lindenwood and Southern Indiana.
- **29 schools change conference for 2026-27**, the Pac-12 resumes with nine
  members, the WAC is renamed the UAC and the MAAC is renamed the Metro
  Conference. Nothing in this lab hardcodes a conference name or membership.
- **The regular-season game limit rose from 31 to 32**, so expect roughly 180
  more games league-wide than 2025-26's 6,318.

### What is measured and cached

- **Eight seasons: 94,194 team-games, 1,493,589 player-games, 45,391 game
  segments**, 2018-19 through 2025-26, from hoopR release assets. Every asset is
  sha256-hashed on ingest because **upstream rebuilds the whole current-season
  file nightly and overwrites in place**.
- **2025-26: 6,318 games, 5,752 D-I versus D-I, 551 with a non-D-I side — and
  541 of those 551 (98%) fall in November and December.** Exactly the buy-games
  Cooper predicted. Never fitted on, never carded, always counted.
- **Overtime happens in 5.2-5.8% of games**, stable across all eight seasons.
  Measured, not assumed. **Full games never end level** (0.000% over 94,194
  team-games) — there is no draw in this sport and no three-way is built.
- **First halves end level 3.54% of the time** over 90,766 halves. A half CAN
  push and a full game cannot, which is why segments carry `resolves_ties`.
- **Venue state has three values, not two.** Of 709 games flagged
  `neutral_site` in 2025-26, **39 (5.5%) are in a participant's own city and 7
  in their own arena** — Vanderbilt hosting the SEC tournament in Nashville,
  Houston in Houston for a Sweet 16. `quasi_neutral` is its own state and the
  model fits an effect for it.
- **Conference tiers are derived from measured non-conference margin**, never a
  name list: 6 high-major conferences / 79 teams, 10 mid-major / 122, 17
  low-major / 164. Cut points `HIGH_MAJOR_MARGIN = 8.0` and `MID_MAJOR_MARGIN =
  −3.0` were declared **before any market was measured per tier**.
- **The slate spans twelve hours** — 11:00 ET to 23:00 ET, 45% of games still to
  tip at 19:00 ET. That is why there are two card slots and why the tip guard
  runs per game rather than against one deadline.
- **Peak slate: 200 games in a single day** (opening Monday of 2022-23). The
  credit cap is set above it, because a cap below the worst slate starves it.

### The two calendar conventions, both measured

- **The slate day is the plain Eastern calendar date.** This was reasoned to a
  06:00 ET boundary — by analogy with hockey — and **measured to zero**: against
  ESPN's own filed `game_date` over 6,318 games, a 0-hour boundary disagrees on
  **0** and a 6-hour boundary on **1**. No D-I game tips between midnight and
  08:00 ET, so the late-night boundary a hockey lab needs protects nothing here.
  The single game that could tell them apart is East Texas A&M at Hawai'i,
  20:00 in Honolulu, which ESPN files under the **Eastern** date of the next
  morning. It has its own test.
- **A season is labelled by the year it ENDS**, matching hoopR:
  `mbb_schedule_2027.parquet` is the 2026-27 season. An earlier version of this
  lab labelled by the starting year, which would have made every season filter
  miss on one side of every join.

### What the retention probe measured, 2026-09-01

**77,160 credits, 144 events planned and 102 matched, run completed inside its
cap** — so a `NOT_RETAINED` verdict is a fact about the archive rather than
about the budget. `data/outputs/cbb_retention_probe.{json,md}`; the report
re-renders from the record for free.

- **All 15 team, ladder and half markets are RETAINED_AND_MEASURABLE**, at
  93-100% of probed events across up to **17 books**. `moneyline`, `spread`,
  `total_points`, `team_total`; every alternate ladder; both halves of spread,
  total, moneyline and team total. This is the population the lab's thesis
  rests on and the archive has all of it.
- **Props are thin and uneven, as expected.** Measurable: `player_points`
  (59.8%), `player_assists` and `player_rebounds` (58.8%), `player_threes`
  (54.9%), `player_points_rebounds` (51.0%). Thin: blocks, steals, turnovers,
  double-double, first basket, and three of the combinations. **Not retained at
  all (0 of 102):** `player_field_goals`, `player_first_team_basket`,
  `player_frees_attempts`, `player_frees_made`, `player_triple_double`.
- **The stratification is NOT balanced and says so.** 2 of 49 cells hold fewer
  than 3 games. An unbalanced probe reporting itself as balanced is worse than
  no probe.

### The defect the probe found, which is the most expensive one so far

**20.5% of provider team names did not resolve, and the misses were biased.**
`_EXPANSIONS` mapped `st -> saint` unconditionally, so `Michigan St` normalised
to `michigan saint` and matched nothing; 27 further schools are simply called
something else by the provider (`Fort Wayne Mastodons`, `Grand Canyon
Antelopes`, `UMKC Kangaroos`). Per-tier match rate over 144 sampled games:
**high-major 86.8%, mid-major 76.1%, low-major 46.7%.**

A join that fails uniformly is a smaller sample. **One that fails on half the
low-major board is a biased sample, and the bias runs directly against the
hypothesis this lab exists to test.** It would have produced a number, an
interval and a wrong answer, with nothing indicating a fifth of the vocabulary
was unreadable — and it was one dispatch away from buying those events.

Fixed with `variants()`: an ambiguous token expands into **every** reading and
`resolve()` refuses when the readings name different schools. **0 of 365
unresolved**, pinned by `test_every_provider_team_name_resolves.py`, which runs
all 365 observed spellings every time. The vocabulary is committed at
`data/manual/provider_team_names_observed.json` — read off 140 cached
historical slate listings, not guessed. *Off-season is a reason not to know
what a market costs, not a reason not to know what a school is called.*

### Prices

- **Quota: 4,992,714 credits remaining** (read from `x-requests-remaining`,
  2026-09-01, not from documentation). Cooper authorises up to 1,500,000 a
  month for this lab. The siblings' committed monthly spend is ~36,000.
- **`basketball_ncaab` is `active=False` today** — the off-season — so there is
  no live board, and market coverage must still be probed **in season**: a
  market unquoted in September establishes nothing.
  **The team alias map is no longer incomplete, and the reason is worth
  keeping.** This file used to say the map was seeded by hand and knowingly
  incomplete *because* there was no live board. That was the wrong inference
  from a true premise: the archive's historical slate listings are a board, and
  the probe's cache holds 140 of them carrying the complete 365-name D-I
  vocabulary. Off-season is a reason not to know what a market **costs**, not a
  reason not to know what a school is **called**.
- **Women's basketball is a separate sport key** (`basketball_wncaab`), so
  excluding it from the price side is total and free.
- **Historical NCAAB featured markets exist from 2020-11-16; everything else
  from 2023-05-03.** That date falls after the 2022-23 season ended, so **the
  full catalogue is buyable for exactly three seasons** (2023-24, 2024-25,
  2025-26) and featured markets for six.
- **The pessimistic full-catalogue buy is 17.6M credits against a 5M quota**, so
  the purchase runs in Cooper's stated priority order — core team markets across
  every season first, then ladders, then props, then futures — and the retention
  probe runs first to replace the pessimistic bound with a measured rate.

### Markets and gates

- **35 markets wired, 34 provider keys deferred with a reason each.** Every
  wired market names the quantity it settles against.
- **The whole quarter family is deferred** because men's college basketball
  plays two halves. Those markets cannot exist, and *a market nobody quotes and
  a market that cannot exist look identical in a coverage report* — so they are
  deferred with that reason rather than asked for and found empty.
- **Nothing reaches `Availability.CONFIRMED`, so no player prop can produce a
  selection.** Measured: ESPN's mens-college-basketball injuries endpoint is
  permanently empty (0 records, against 76 for the NBA *in the NBA's own
  off-season*); CBBD has no availability endpoint at all; the conference reports
  that exist cover ~115 of 365 teams, **conference games only**, so two thirds
  of D-I and the entire November-December window are uncovered. Props are
  priced, frozen and settled; they cannot be selected, and the card says so in
  those words. The exact analogue of goalie saves.
- **Referee assignments are not published pre-game anywhere verifiable**, so
  referee identity never enters a pre-game model. Post-game coverage is
  excellent (97.7% of games, stable ids, back to 2016) and is a *descriptive*
  instrument only.
- **No market is allowlisted.** `withdraw()` exists in
  `staging_provider_policy.py` and `grant()` does not — Claude may take a market
  away from the card and may never give it one.

### Defects found by disbelieving a number

- **A made free throw is not a basket, and the obvious filter does not know
  that.** ESPN's play type is `MadeFreeThrow` — one word — so a
  `str.contains("Free Throw")` screen matches **none** of the 253,589
  free-throw rows in a season. It inflated the possession count by 15 a game
  and, far worse, would have settled `player_first_basket` on whoever made the
  game's first **free throw**: a plausible name, a real player, a wrong bet,
  and nothing would have looked broken.
- **The football lab's forward-ledger interval is 10.3x too narrow.** Its
  standard error lands at `s/G` where a cluster standard error is `s/√G`.
  Reproduced here on 632 synthetic bets over 200 clusters against a cluster
  bootstrap, fixed in `stats.interval_by_cluster`, and recorded in
  `docs/ported_defects.md`. **The sibling lab is not touched.**
- **The possession estimator is stable across seasons and the play-by-play
  count is not.** Seven seasons agree to 1.7-2.7 possessions; 2026 jumps to
  6.5, coinciding exactly with ESPN quadrupling its substitution reporting. A
  model built on the PBP count would carry a discontinuity that is an artifact
  of the feed. The model uses the estimator.

## Contract strings — never change these

Cooper's scheduled routines hard-code these. Renaming any of them silently
breaks his automation, and the breakage looks like the lab going quiet.

| Thing | Exact value |
|:------|:------------|
| Workflow name | `CBB Gameday Refresh` |
| Workflow file | `.github/workflows/cbb-gameday-refresh.yml` |
| Card feed branch | `card-feed` |
| Card comment file on the feed | `latest_card_comment.md` |
| Status file on the feed | `latest_status.json` |
| Odds API secret | `CBB_ODDS_API_KEY` |
| CollegeBasketballData secret | `CBBD_API_KEY` |
| Drive file title pattern | `CBB Card <date> <slot>` |
| Accumulating note | `This card is **accumulating evidence, not making recommendations.**` |
| Claims output | `data/outputs/cbb_what_we_can_claim.md` |
| Forward evidence output | `data/outputs/cbb_forward_evidence.md` |
| Forward evidence ledger | `data/processed/cbb_forward_evidence.csv` |
| Experiment ledger | `data/outputs/experiment_ledger.json` |
| Changed-selections marker | `Selections changed` |

Every output file is competition-prefixed, so nothing else could ever overwrite
a CBB record. `tests/test_contract_strings.py` pins every one of these against
this table.

## Hard rules (never break these)

- **Never fabricate** a price, a line, an injury, a lineup, a venue or a
  player's status. A missing price stays missing.
- **Never place a bet** or automate one. Nothing here is ever wired to a
  sportsbook.
- **No market reaches the card without measurement against real prices and a
  reviewed human acceptance receipt.** Claude prepares the evidence and stops.
  **Claude may withdraw an allowlist and may never grant one.**
- **An excluded market is never a pass, an avoid, or a no-value call.** A
  blocked card yields no selections and says why.
- **State the sample size next to every measured number.** An interval that
  includes zero means **"no demonstrated edge"**, in those words.
- **Never report a pooled headline across the whole of Division I.** High-major,
  mid-major and low-major are different distributions. A policy that wins in
  low-major games and loses in high-major ships in low-major only, if it ships.
- **Calibration can rule a model out, never in.** Where a priced test exists, it
  decides.
- **Cluster every interval by game and by day.** One game supplies many
  correlated bets; a 200-game slate is not 800 independent observations.
- **Family-wise correction from the experiment ledger's cumulative count**, not
  the day's, reported beside the raw figure.
- **"Conditioned on what, known when?"** on every adjustment. Hindsight leaks
  look exactly like edges.
- **A soft number you cannot bet is not an edge.** Edge is measured against a
  price actually available at card time at a US book Cooper can open, regions
  `us,us2`, and reported separately for prices that survived to the next capture
  and prices that did not. An edge living entirely in vanishing prices is
  reported as **not reachable**, in those words.
- **Never fold a futures return into a headline ROI over game bets.** State the
  hold time beside every futures number.
- **Never stake correlated selections as independent, and never sum their
  edges.** Spread, moneyline, team total, game total and a player's points are
  one event seen five ways. Exposure is reported per game and per slate.
- **Report how much of any spread or total edge is half a point at a key
  number** rather than a differing view of the game.
- **Before concluding a market "isn't offered", check per-bookmaker and
  alternate-line coverage — and probe in season.** A market unquoted in
  September establishes nothing.
- **Never print, write, compare, or commit an API key.**
  `tests/test_no_secrets_committed.py` enforces it; the exemption for
  key-shaped strings is **by recorded value, never by directory**.
- **Never weaken a gate**, never sign a human acceptance receipt on Cooper's
  behalf, never merge with failing CI, never force-push.
- **Never edit protected manual files** except through the one permitted path:
  `data/manual/staging_provider_policy.json` (withdrawal only) and
  `data/manual/human_acceptance_receipts/*` (never).
- **Do not trust the nominal cron time.** GitHub has been firing these repos'
  crons 4.5-5.3 hours late since 2026-08-27. Every deadline is checked against
  `nominal + schedule_contract.OBSERVED_LATENESS_H`.

## What Claude decides, and what Cooper decides

Claude works autonomously on: data, models, measurement, reports, tests,
workflows, docs, and opening PRs with green CI. Every judgment call it made
instead of asking is in `docs/decision_log.md`.

**Cooper decides exactly one thing: signing the acceptance receipt that
allowlists a market.** Credits are not a constraint and are not brought to him.

## Main commands

```bash
# One-time local setup
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt && .venv/bin/python -m pip install -e .

# Data (free; spends no credits)
PYTHONPATH=src .venv/bin/python scripts/fetch_cbb_data.py --seasons 2024 2025 2026 2027
PYTHONPATH=src .venv/bin/python scripts/build_datasets.py --seasons 2024 2025 2026 --validate-possessions

# Cost arithmetic (spends nothing, touches no network)
PYTHONPATH=src .venv/bin/python scripts/estimate_credit_cost.py

# Quota (free endpoint)
PYTHONPATH=src .venv/bin/python scripts/check_provider_quota.py

# Tests
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m compileall -q src scripts
```
