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

**2026-09-05, on the rebuilt full store: 925,831 wagers offered, 191,053 graded
bets over 26,591 games and 791 days of seasons 2021-2026, 32 market-and-tier
cells. 0 shows a demonstrated edge; 3 show a demonstrated deficit.**
The store is core team 2021–2026 complete, ladders and halves on 609 events,
props on 3,223 events; a second ladders wave of 1,199,926 credits was lost
before persistence (defects S–W) and is not re-bought.

Every interval below is quoted **as the record carries it**: the backtest ran
while the experiment ledger held 30 hypotheses, so its stored bounds are
widened by **x1.60**. The ledger now holds **62** — 30 discovery entries and
the 32 holdout looks the replication appended — and the generated reports
re-apply **x1.71** at render time, which is why the same tier reads wider in
`docs/what_we_can_and_cannot_claim.md` and
`docs/why_the_model_does_or_does_not_have_an_edge.md`. The correction may only
ever get stricter.

| Cut | Bets | ROI | Corrected (x1.60) | Verdict |
|:---|---:|---:|:---|:---|
| high-major | 43,228 | -3.2% | -7.6% to +1.2% | no demonstrated edge |
| mid-major | 88,344 | -4.3% | -7.8% to -0.8% | demonstrated deficit |
| low-major | 59,475 | -4.0% | -7.7% to -0.3% | demonstrated deficit |

**There is no pooled row here on purpose.** A pooled all-of-Division-I headline
is banned in this repository; the pooled figure is computed so
`docs/when_this_ends.md` can apply the stopping rule to it, and never so it can
be quoted on its own.

**A CLAIM IN THIS FILE WAS RETRACTED, AND THE FULL STORE RESTORED HALF OF IT.**
Measured on the core team markets alone, before the alternate ladders and the
halves entered the population, this file called low-major *the only tier whose
interval excludes zero, and it excludes zero on the losing side*. On
2026-09-04's partial store the same tier read **no demonstrated edge** and the
claim was withdrawn. On the full store low-major is a **demonstrated deficit**
again — 59,475 bets, -4.0%, corrected -7.7% to -0.3% — so the **sign** survives
and the **exclusivity does not**: mid-major excludes zero as well. No figure
from the superseded run is reprinted here; its record is not committed, and a
number nobody can re-read is a number this file may not carry. Nothing about the
model changed either time; the population did. The retraction itself is now
generated: `reports/why_the_model.py` chooses *still holds* or *no longer holds*
from `verdict_of(current)` and nothing else, so it cannot become a stale
paragraph again.

- **The lab's own thesis is contradicted.** Softness was expected at the
  low-major end. By point estimate the worst measured tier is **mid-major**
  (-4.3% over 88,344 bets).
- **The model does not beat blind betting on return, and it loses to the vig.**
  The claim that it beat every blind rule was checked and is FALSE: of the
  190 blind sides clearing the 200-bet floor, **61 return more than
  their own tier's model**, and 13 of those carry a demonstrated deficit — mid-major
  `always the underdog` on moneyline returns -2.0% over 14,091 bets against the
  model's -4.3%. The spread is wide in both directions: the worst blind side is
  `low_major / player_threes / always over` at **-40.0%** over 227 bets, the best
  is +20.7% over 345. **No blind side demonstrates an edge either (0 of
  190)** — every positive one has an interval spanning zero after the
  correction. The evidence that the model carries information is the Brier score
  against the base rate, not the return against blind rules.
- **The model loses to the market on Brier in every tier, with the vig left
  in**, per tier and never pooled: high-major **-0.01663**, corrected -0.02147
  to -0.01179 over 62,163 rows; mid-major **-0.00962**, corrected -0.01286 to
  -0.00638 over 137,296 rows; low-major **-0.00776**, corrected -0.01072 to
  -0.00479 over 94,182 rows. In high-major its Brier is worse than the **base
  rate** (0.25118 against 0.25000) — beaten by predicting the league mean.
- **The skill measure shows nothing.** The disagreement coefficient over every
  opinion (293,661 wagers) is **no demonstrated edge** in all three tiers:
  high +0.088 corrected -0.033 to +0.208; mid +0.122 corrected -0.015 to
  +0.259; low +0.046 corrected -0.130 to +0.223. On the **selected** bets only
  (110,316) high-major reads +0.239 corrected +0.030 to +0.449 — that is the
  winner's-curse comparison, never the skill measure.
- **Anti-predictiveness is a shape.** Return by claimed-edge bucket is **not
  measurable** on this record (0 usable buckets of 8 populated). Overconfidence
  by bucket is: high-major runs **+13.4 pp** in the smallest claimed-edge
  bucket (24,416 rows) to **-18.3 pp** in the largest (11,232), so **raising the
  threshold makes it worse** — the move a disappointing backtest invites.
- **Replication: 0 replicated / 0 did not replicate / 0 reversed / 3 not enough
  evidence / 9 nothing to replicate / 20 untestable**, over 32 cells; 71,778
  held-out bets on 2025 and 2026 against 119,275 on 2021-2024. **This is not the
  split declared on 2026-09-03** (discovery [2021, 2022, 2023], holdout [2024]),
  so it is a **second look at the data rather than a pre-registered test** and
  every state in that count reads as one. `mid_major / team_total` is flagged
  *"a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication"* — -6.6% over 4,968
  held-out bets where discovery demonstrated nothing. That cell's holdout is
  burned.
- **Not measured, and the reports say so.** The half-point decomposition was
  **refused**: the ticket-margin reconstruction agreed with the recorded outcome
  on 162,340 of 189,381 scorable bets (**85.7%**), below the 99% bar.
  Reachability has no in-season store to split on. Futures cannot be bought at
  all — no historical bulk endpoint.

### The winner's curse, measured

**Overall calibration is not evidence, and this run is why.** Overall the model
is **0.4 pp underconfident** over 566,370 graded rows — essentially calibrated,
with gaps that cancel, and only five of ten bins over-predicted. On the bets it
**selected**, it is **10.4 pp overconfident** over 189,381, and **every one of
the ten bins is over-predicted**.

It worsens with confidence: in the 90-100% band the model says 93.9% and wins
**90.4%** over 12,475 rows overall, and says 94.2% and wins **80.9%** over 3,103
rows on what it picked.

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
| Policy gate check name | `Policy Gate` |
| Policy gate workflow file | `.github/workflows/policy-gate.yml` |

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
