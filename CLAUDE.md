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
sport literal appears anywhere else. That file was cited here for the whole of
the build and did not exist until 2026-09-04; written and run, it found four
literals (the `"cbb"` data-directory segment in `data/hoopr.py` and
`scripts/estimate_credit_cost.py`, the sport key in two report strings) and
they now read the registry. It does NOT enforce the `cbb_` output-prefix
convention on filenames — the lab writes those as literals in twenty places
and the guard says so in its docstring.

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

### The measurement, and it is decisive

**2026-09-04, on the expanded store: 2,233,844 quotes, 13 markets, 118,050
graded bets, 32 market-and-tier cells. Not one shows a demonstrated edge.**
The accounting identity reconciles at 436,920 of 436,920 offered; the family
correction is x1.60 from 30 pre-registered hypotheses.

| Cut | Bets | ROI | Corrected | Verdict |
|:---|---:|---:|:---|:---|
| high-major | 24,691 | -3.1% | -10.0% to +3.8% | no demonstrated edge |
| mid-major | 58,633 | -4.1% | -9.0% to +0.9% | no demonstrated edge |
| low-major | 34,720 | -4.3% | -10.0% to +1.4% | no demonstrated edge |
| pooled | 118,050 | -3.9% | -7.2% to -0.7% | demonstrated deficit |

**A CLAIM IN THIS FILE WAS RETRACTED BY THE RE-MEASUREMENT.** The core-team-only
run had low-major at -3.9% corrected -7.4% to -0.3%, and this file called it
*the only tier whose interval excludes zero*. Adding the alternate ladders and
the halves — one season deep and thin, which widens every interval they enter —
takes the same tier to **no demonstrated edge**. Nothing about the model
changed; the population did. **A deficit that dissolves when a fifth market is
added was fragile to the population all along.** The direction survives:
low-major is the worst tier by point estimate in both runs, and the lab was
built expecting it to be the best.

- **The lab's own thesis is contradicted.** Softness was expected at the
  low-major end. It is the worst tier in both measurements.
- **The model beats blind betting and loses to the vig.** Blind sides run to
  -13.9%; the model's -3.9% beats every one. Information, and not enough of it.
- **The model loses to the market on Brier in every tier, with the vig left
  in.** Pooled advantage **-0.01312 [-0.01468, -0.01156]**. In high-major its
  Brier is worse than the **base rate** — beaten by predicting the league mean.
- **Anti-predictiveness is a shape.** The shortfall widens **11.8pp** from the
  smallest claimed-edge bucket to the largest, so **raising the threshold makes
  it worse** — the move a disappointing backtest invites.
- **Replication: 0 replicated / 0 failed / 0 reversed / 5 nothing to
  replicate.** When a holdout cell returned -12.1% with an interval excluding
  zero, the module refused to call it a replication: *"a NEW DISCOVERY made on
  the only clean season this lab had"*. That cell's holdout is burned.
- **Not measured, and the reports say so.** The half-point decomposition was
  **refused** (ticket-margin verified at 83.8% against a 99% bar).
  Reachability has no in-season store to split on. Props and futures are
  unbought; futures cannot be bought at all — no historical bulk endpoint.

### The winner's curse, measured

**Overall calibration is not evidence, and this run is why.** Overall the model
is **0.5 pp underconfident** over 235,859 graded rows — essentially calibrated,
with gaps that cancel. On the bets it **selected**, it is **9.9 pp
overconfident** over 85,556, and every one of the ten bins is over-predicted.

It worsens with confidence: at 90-100% predicted the model wins **86.6%
overall** and **68.8% on what it picked**. It says 93% and wins 69%.

A model is selected into its bets by its own disagreement with the price, so
its bets are the tail of its own error distribution. This is an independent
reproduction of the NHL lab's 9-12 pp in a different sport.

### Four defects the measurement path found, all fixed

1. **An absent experiment ledger was reported as a family of one.**
   `looks_from_ledger` returns `max(count, 1)`, so a missing file and a
   one-entry file are the same integer — and the report stated it as fact about
   a file it never opened. A correction of x1.00 widens nothing, so a missing
   ledger makes every result look **more** significant.
2. **The weekly loop could never finish its own measurement.** Unbounded, the
   backtest scores the whole store: a measured **eight hours** against a
   240-minute timeout and GitHub's six-hour ceiling. It would have been killed
   every Monday and looked exactly like a lab that was running.
3. **The seam deleted the November prior regime.** `matchups_for` passed
   multi-season history straight to `fit`, whose contract is one season, so the
   prior's weight was **0.0% on 3 November and 0.0% on 20 February**. Also the
   tier table saw the season it was pricing, moving 9.3% of teams across a
   boundary that selects the home-court effect.
4. **A pooled verdict no tier shared.** The pooled disagreement coefficient read
   `demonstrated edge` while every tier read `no demonstrated edge` — three
   intervals each spanning zero pooling into one that does not. Arithmetic, not
   a discovery, and it put the reserved phrase in the one cell the brief says is
   never the headline. Now flagged where it happens.

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
  key-shaped strings is **by recorded value, vouched by hand, never by
  directory** — and the guard's known gaps are asserted in its own
  `test_the_gaps_this_guard_still_has_are_the_ones_written_down` rather than
  claimed away.
- **Never weaken a gate**, never sign a human acceptance receipt on Cooper's
  behalf, never merge with failing CI, never force-push. **CBB is PUBLIC and
  main is protected.** Measured 2026-09-05 with `gh api
  repos/cooperross399/cbb-betting-lab/branches/main/protection`: the required
  context is `Tests`, `enforce_admins` is on, and force-pushes and deletions
  are refused. Until this edit this file said the opposite, and said it with
  no way to check; the command is written down now so the next session
  re-measures instead of trusting the sentence.
  Protection asks for `Tests` and nothing else, so a red `Ledger Guard` still
  merges, and `required_status_checks.strict` is false, so a green tick may
  have been earned against a base main has moved past. Both gaps are written
  into `tests/test_workflows.py::test_the_disclosed_holes_are_real`.
- **Never edit protected manual files** except through the one permitted path:
  `data/manual/staging_provider_policy.json` (withdrawal only) and
  `data/manual/human_acceptance_receipts/*` (never).
- **Do not trust the nominal cron time.** GitHub has been firing these repos'
  crons 4.5-5.3 hours late since 2026-08-27. Every deadline is checked against
  `nominal + schedule_contract.OBSERVED_LATENESS_H`.

## How the hard rules are enforced, and where they are not

Every guard below is listed in three places that are held against each
other — `tests/test_the_guards_exist.py`, `tests/conftest.py` and
`scripts/check_test_results.py` — so that `git rm` of a guard, a `-k` that
deselects it, a `PYTEST_ADDOPTS` nobody reads, or a rename is a red build
rather than a smaller green one. Until 2026-09-04 deleting the two hard-rule
guards made the suite greener and nothing said so.

| Rule | Enforced by | What it does not reach |
|:---|:---|:---|
| No committed key | `tests/test_no_secrets_committed.py`: every tracked path, symlink target and text body; assignment in every suffix and every spelling; 102 probe event ids vouched by hand against their file | a key split across a concatenation, an encoded body, a homoglyph inside a `:`-separated value, a body behind a binary suffix — each asserted open in the guard |
| No sibling import | `tests/test_no_sibling_lab_import.py`: source and environment; an unparseable module is a failure | — |
| No sport literal outside the registry | `tests/test_competition_registry_is_the_only_place.py` | the `cbb_` output prefix on filenames; a key assembled at run time |
| Contract strings | `tests/test_contract_strings.py` | — |
| The required check `Tests` | `tests/test_workflows.py`: parsed YAML — `if:`, `needs:` and `strategy:` all refused on the required job, and `if:` on any other job in the file, because GitHub reports a **conditionally-skipped required check as Success**; the suite line's arguments a WHITELIST (`-q`, `-rs`, one `--junit-xml=` under the runner temp) rather than a blocklist that let `--version` through; the gate line pinned as a whole command and then EXECUTED under stubs with the invoked command words read back | the six operational workflows keep their deliberate `continue-on-error`, `\|\| true` and `if-no-files-found: warn`; a nested `bash -c`; `cd` before pytest; the pin is exact, so `python3` for `python` is refused too |
| Zero skips, every guard ran | `scripts/check_test_results.py` on the junit CI writes — per TEST, comparing each required guard's `def test_*` against the testcases recorded, and refusing evidence older than the marker the suite step writes; `tests/conftest.py` at collection, which stops the run on a collection-phase skip, on any narrowing pytest actually received (`--deselect`, `-k`, `--ignore`, `--ignore-glob`, the ini `addopts`, `PYTEST_ADDOPTS`), and on any tracked `tests/test_*.py` that collected nothing | a non-strict `xfail` marker; a waiver keyed on a token no sweep arm draws; **a test deleted outright** — the declaration goes with it, and `MINIMUM_TESTS = 5` is the only floor left |
| Ledger append-only | `save(floor=…)` at runtime; `Ledger Guard` diffing THE one tracked ledger, `data/outputs/experiment_ledger.json`, against the PR base, keyed on `(search, name, seasons, stage)`; `pending` may be filled in once, nothing else moves. The tracked render `cbb_experiment_ledger.md` is not compared key by key — it is rebuilt from the JSON in the same workflow and any diff is a failure | an appended hypothesis is taken on trust; the same span written in two orders is two keys; `Ledger Guard` is not a context main's protection requires, so its red does not block the merge |
| Real-data tests run in CI | `tests/fixtures/real_data/` — 400 games of 2025-26 and every row of three schedules, cut by `scripts/build_test_fixtures.py`; the full tables when built | the CI numbers are over the sample, and every printed number says so |

**A population guard for a scraped page does not exist because no scraper
does.** `tests/test_population_purity.py` says so and fails the day one
appears. Do not cite a test that is not on disk; nine such citations were
found and corrected on 2026-09-04, and this table is the place to add the
tenth when a rule gains a guard.

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

# Tests — the whole suite, or the collection hook stops the run. A `-k`, a
# `--deselect` or an `--ignore` now exits 1: run ONE FILE by naming it
# instead, which the hook allows.
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m pytest -q tests/test_workflows.py
PYTHONPATH=src .venv/bin/python -m compileall -q -f src scripts

# Re-cut the tracked real-data sample the suite reads where the tables are absent
PYTHONPATH=src .venv/bin/python scripts/build_test_fixtures.py
```
