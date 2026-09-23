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

**No market is allowlisted, nothing is bet, and that is the correct state.**
The history HAS been measured, and the measurement is the finding: this heading
said *"As of 2026-09-01. Nothing has been measured yet"* until 2026-09-18,
against this file's own generated headline a hundred lines below it and against
`docs/project_status.md`, which says in as many words that the honest word for
this lab's state is no longer *unmeasured*. A dated stamp on a section that is
edited weekly is a claim nobody regenerates, so there is no stamp here now and
no countdown either; the season's dates are in the next section and `git log`
has the rest.

### The season, verified rather than assumed

- **The 2026-27 D-I season opens Sunday 2026-11-01** — a single game, Notre Dame
  against Villanova at the Palazzetto dello Sport in Rome, 09:30 ET. **Real
  volume starts Monday 2026-11-02.**
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
- **2025-26 carries games against non-D-I opposition, they are concentrated in
  November and December, and they are never fitted on, never carded and always
  counted.** **This bullet used to present three figures as a partition and
  they do not add up.** The total was bound to the shot-zone record's coverage
  and the D-I-versus-D-I figure to a segment of the PURCHASE PLAN — two records
  counting two different populations — and the remainder was stated by no
  record at all, so the three were short of each other by fifteen games. Each
  figure passed the binding check, because a marker binds a value to a field
  and cannot know that the sentence around it is arithmetic. Nothing here
  renders that partition, so it is not asserted; the coverage figure is in
  `data/outputs/cbb_shot_zones_2026.json` and the plan's own segment counts are
  in `data/outputs/cbb_historical_purchase.json`.
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
  name list — so the count in each tier MOVES with the data and the lookback
  window, and is not a constant to be typed. `conferences.tier_table` computes
  it and `data/outputs/cbb_ratings_fit.json` records the shape each fit placed.
  (This sentence used to give "6 high-major conferences / 79 teams, 10
  mid-major / 122, 17 low-major / 164" — a name-list census, in the sentence
  saying tiers are never a name list, and contradicted by the table's own
  61 / 131 / 172.) Cut points `HIGH_MAJOR_MARGIN = 8.0` and `MID_MAJOR_MARGIN =
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

**The rebuilt full store, measured 2026-09-05 and re-run on 2026-09-09 against
the refused-by-name filter (PR #53).** The population it carries and the way
its market-and-tier cells fall across the verdicts are in the record census
below, which is generated from the record. They were typed here by hand until
2026-09-18 and every one of them was wrong — the wagers offered, the graded
bets, the games and the count of demonstrated deficits, four figures that a
regeneration moved and nobody re-derived. They are not restated here at their
old values, because a document that keeps a superseded population beside a
generated one gives a reader two answers and no way to choose.
The store is core team 2021–2026 complete, ladders and halves on 609 events;
the prop wave's event count is in no record here and is no longer stated. A
second ladders wave of 1,199,926 credits was lost before persistence
(defects S–W) and is not re-bought.

**Which correction these figures carry.** The ledger's cumulative count and
the factor derived from it are stated in the generated block, which is the only
place this file writes either. **Its composition is counted in the generated census below, one row per
registration search, and is not restated here.** It was restated here until
2026-09-18, as an exhaustive list that summed to barely three quarters of the
ledger — it omitted the residual-regression entries and the weekly-search ones,
and it undercounted the replication's appended looks. Understating the
family understates every correction derived from it, which is the flattering
direction, and nothing could catch it: a hand-written sum is not
interval-shaped, and each of its parts was a number some record really held.

What stays here is the part that is a judgement rather than a count: the **3
rebound-differential hypotheses registered 2026-09-10 over 2027-2030** sit in a
window whose four seasons were chosen by a POOLED power calculation while the
three tests registered are per-tier — so all three are underpowered, and
`scripts/record_experiments.py` states the arithmetic rather than the claim it
was registered under. Every interval is widened by the factor the block states. The
records on disk keep the correction each was scored under, and **which
correction that is, per record, is in the generated census below**. It is
generated for the reason this sentence used to demonstrate: it named four
records and four counts by hand, three were already wrong when it was written,
and the 2026-09-17 regeneration falsified the fourth the same day. The records
are **not** rewritten:
a record is the evidence of what was measured. Every generated report re-reads
the ledger when it renders and re-derives its verdicts at the cumulative count
it finds there, naming both counts on the page when they differ (decision 46).
That is the reading below, and the reading in
`docs/what_we_can_and_cannot_claim.md` and
`docs/why_the_model_does_or_does_not_have_an_edge.md`. The correction may only
ever get stricter, and it just did — so a re-render can retract a claim and can
never manufacture one.

**WHEN THE LEDGER GROWS, RE-RENDER. It is free, and the suite will not go green
until you have.** Registering a hypothesis widens every interval this lab has
ever published, so every report goes stale the moment it lands. Each generated
report is brought current by running its own script with
`--rebuild-report-only` — `run_price_backtest.py` (once per output directory:
the default, `core_team_only/`, `holdout/`), `run_replication.py`,
`run_forecast_skill.py`, `run_prop_grading.py`, `fit_ratings.py` — plus
`run_what_we_can_claim.py`,
`run_why_the_model.py --splice-into`, `run_forward_evidence.py` and
`run_reachability.py`. None of those reads a price table, touches the network
or spends a credit; they re-read the ledger and re-derive the verdicts from the
run's own estimates.

**`docs/project_status.md` and this file are part-generated now.** Two blocks
in each are spliced from the records by `scripts/splice_headline_table.py`, so
run that too: the per-tier headline, which is the figure a reader acts on, and
the record census — what each record was scored under, the population of each
cut, and how the market-and-tier cells fall across the verdicts. The prose
around them is still hand-written, and every interval in it either matches a
current reading, carries an explicit `[@N]` saying which correction it is
stated at, or is refused; every comma-formatted count in it names where it
comes from — a record FIELD, a file outside `data/outputs/`, or a date it
stopped being true — in *Where every count on this page comes from* at the foot
of this file. "Some record states this integer somewhere" is no longer an
answer; it accepted a test-suite tally vouched for by a basketball statistic.
`tests/test_no_report_states_a_stale_correction.py` fails until both halves are
done, and names the file and the number it is waiting for.

<!-- BEGIN GENERATED: record_census -->

**What each record on disk was scored under.** A record keeps the family correction that was in force when it ran -- that is the evidence of what was measured -- and every generated report re-derives its verdicts at the ledger's cumulative count when it renders (decision 46). Where a row below is narrower than the ledger's own count, the gap is the search registered since.

| Record | Scored at | Factor |
|:---|---:|---:|
| `cbb_forecast_skill.json` | 133 | x1.8145 |
| `cbb_price_backtest.json` | 133 | x1.8145 |
| `cbb_prop_grading.json` | 133 | x1.8145 |
| `cbb_ratings_fit.json` | 130 | x1.8115 |
| `cbb_reachability.json` | 133 | x1.8145 |
| `core_team_only/cbb_price_backtest.json` | 130 | x1.8115 |
| `holdout/cbb_price_backtest.json` | 130 | x1.8115 |
| `holdout/cbb_replication.json` | 133 | x1.8145 |

**The populations those verdicts are measured on.**

| Cut | Wagers offered | Graded bets | Games |
|:---|---:|---:|---:|
| full store, all six seasons | 663,961 | 175,690 | 26,622 |
| core team markets only | 505,287 | 145,739 | 26,615 |
| discovery seasons | 441,098 | 110,682 | 16,812 |
| genuinely held-out seasons | — | 65,008 (71,797 taken) | 9,810 |

**The full-store price backtest, cut by market and tier:** 32 cells — 0 demonstrated edge, 5 demonstrated deficit, 17 no demonstrated edge, 10 below the 200-bet floor.

**The blind null baseline — betting one side of one market blindly, every time.** 160 sides, of which 102 clear the 200-bet floor; the rest carry no verdict at all. Across the 102: 0 demonstrated edge, 31 demonstrated deficit, 71 no demonstrated edge. 52 of them return more than their own tier's model, and 11 of those 52 are themselves a demonstrated deficit — beating the model and still losing money is the ordinary case here. The baseline covers the 13 game markets (`alternate_spread`, `alternate_team_total`, `alternate_total_points`, `moneyline`, `moneyline_h1`, `moneyline_h2`, `spread`, `spread_h1`, `spread_h2`, `team_total`, `total_points`, `total_points_h1`, `total_points_h2`) and no prop market at all.

**How far the search would have to go before each tier's corrected interval reached zero.** The family correction widens with every hypothesis registered, so a demonstrated deficit survives only until the search is large enough to dissolve it. This is that size, searched at render time from the tier's own return and standard error. Per tier; there is no pooled row here on purpose.

| Cut | Verdict today | Hypotheses before the interval reaches zero |
|:---|:---|---:|
| high-major | no demonstrated edge | — (not a demonstrated deficit today) |
| mid-major | demonstrated deficit | 35,427 |
| low-major | demonstrated deficit | 372 |

**What the family of 133 is made of.** Counted from `experiment_ledger.json` at render time, every entry in exactly one row, so the parts sum to the whole by construction. A composition stated by hand cannot: the one this replaced summed to 101.

| Registered under | Entries |
|:---|---:|
| `replication` | 35 |
| `player_props_vs_devig` | 30 |
| `residual_regression_2026_09_15` | 27 |
| `ladders_and_halves` | 11 |
| `conference_tier` | 4 |
| `core_team_markets` | 4 |
| `model_structure` | 4 |
| `schedule_states` | 4 |
| `forward_2027` | 3 |
| `player_props_vs_role_prior` | 3 |
| `rebound_differential_vs_spread` | 3 |
| `november_prior` | 2 |
| `champion_challenger` | 1 |
| `forward_evidence` | 1 |
| `reachability` | 1 |
| **total** | **133** |

*Generated by `scripts/splice_headline_table.py` from the records in `data/outputs/`. Do not edit between the markers; re-run the script.*

<!-- END GENERATED -->

<!-- BEGIN GENERATED: headline_table -->

**Family correction: 133 cumulative hypotheses, x1.8145.** Every interval below is widened by it. The count is the experiment ledger's cumulative total, not the day's.

| Cut | Bets | ROI | Corrected | Verdict |
|:---|---:|---:|:---|:---|
| high-major | 37,939 | -4.2% | -9.7% to +1.4% | no demonstrated edge |
| mid-major | 81,404 | -5.5% | -9.5% to -1.4% | demonstrated deficit |
| low-major | 56,340 | -4.6% | -8.8% to -0.3% | demonstrated deficit |

| Measure | Cut | Estimate | Corrected | Verdict |
|:---|:---|---:|:---|:---|
| forecast skill | high_major Brier vs raw | -0.01783 | -0.02379 to -0.01186 | demonstrated deficit |
| forecast skill | high_major disagreement | +0.04629 | -0.10379 to +0.19636 | no demonstrated edge |
| forecast skill | low_major Brier vs raw | -0.00782 | -0.01120 to -0.00444 | demonstrated deficit |
| forecast skill | low_major disagreement | +0.01125 | -0.19909 to +0.22159 | no demonstrated edge |
| forecast skill | mid_major Brier vs raw | -0.01066 | -0.01429 to -0.00704 | demonstrated deficit |
| forecast skill | mid_major disagreement | +0.03201 | -0.13038 to +0.19439 | no demonstrated edge |
| forecast skill | selected-bets disagreement | +0.13048 | -0.12026 to +0.38122 | no demonstrated edge |
| prop grading | high_major de-vig headline | -0.00548 | -0.01406 to +0.00310 | no demonstrated edge |
| prop grading | high_major role-prior control | +0.11296 | +0.06465 to +0.16128 | demonstrated edge |
| prop grading | low_major de-vig headline | -0.00651 | -0.03939 to +0.02638 | no demonstrated edge |
| prop grading | low_major role-prior control | +0.04490 | -0.03845 to +0.12825 | no demonstrated edge |
| prop grading | mid_major de-vig headline | -0.00439 | -0.01024 to +0.00146 | no demonstrated edge |
| prop grading | mid_major role-prior control | +0.11537 | +0.09070 to +0.14004 | demonstrated edge |
| prop grading | player_pra high-major | -0.01674 | -0.03152 to -0.00196 | demonstrated deficit |
| replication | total_points mid-major held out | -0.06538 | -0.13107 to +0.00031 | no demonstrated edge |

*Generated by `scripts/splice_headline_table.py` from the records in `data/outputs/` at the ledger's 133 hypotheses. Do not edit between the markers; re-run the script.*

<!-- END GENERATED -->

**Two published verdicts moved when those 33 hypotheses were registered, and
both moved the same way.** At the 62 hypotheses in force before the
registration (x1.7095) **low-major** read a demonstrated deficit; it crossed
zero at the 85th hypothesis and read **no demonstrated edge** from then until
2026-09-17, when refusing the neutral-court side wagers this store cannot
orient made it a demonstrated deficit **again**. Its reading today is in the
generated table above, which is the only place this file states it. The old
figures are not restated here: they were measured over a population that
included the 15,207 bets the 2026-09-17 exclusion refused, so they no longer
reproduce from any record
and a file that quoted them would be quoting a measurement nothing can check. **A third verdict moved at
98 -> 101 and went unnarrated**: `mid_major / player_threes` on the
blind null-baseline side lost its demonstrated-deficit reading in both the
full-store and the held-out backtest, its corrected high bound crossing zero between those two counts;
`docs/retracted_readings.md` records the crossing point, and is the only
place it is written. The commit that caused it said it retracted nothing.
The replication's held-out
**`total_points` / mid-major** cell, -6.5% over 8,267 bets, read a demonstrated deficit at -12.7% to -0.3% [@62] at those same 62
hypotheses and reads **no demonstrated edge** today; it crossed at the
**125th**. It crossed at the 95th until 2026-09-17, when the replication was
re-scored against a model that had just been handed its roster evidence: the
cell moved to -6.5% over 8,267 bets and survived thirty more registrations
before dissolving. Its verdict today is the verdict it carried before, so that
is a moved fact about the history and not a moved reading. Its current interval is in the generated
block, which is the only place this file states one. Blind null-baseline sides lose
demonstrated-deficit readings too, and on the records in this tree the move is
smaller than this paragraph used to claim: over 62 -> 95 the blind deficits go
from 33 down to 32 of the 102 sides clearing the floor on the full store, from
26 down to 24 of 101 on the held-out backtest, and stay at 28 of 48 on the
core-team cut — one, two and none, not five apiece. (At today's count they are 31, 23 and
27 of the same three denominators. Every figure in this paragraph said
something else until 2026-09-18: it had been read from records PR #53 replaced,
which still held the two markets this lab refuses by name, and neither those
records nor the counts they gave are recoverable from anything in this tree.)

**Two blind sides lost a demonstrated reading without any document saying so,
and a widened cost check found them.** `mid_major / player_threes` on the full
store and the held-out backtest went at 98 -> 101, in the registration whose own
commit message said it retracted nothing. Two blind sides on the
**core-team cut** went much earlier — demonstrated deficits at 30 hypotheses and
not demonstrated at the 130 that record now stores:
`low_major / spread / always away` (-3.8% over 21,393 bets) and
`low_major / spread / always the favourite` (-7.4% over 1,220). This sentence
named FOUR until 2026-09-18, and two of the four have never been demonstrated
deficits at any count: it was written against the pre-#53 record, which still
held the two markets this lab refuses by name, and that record is not in the
tree to be re-read. None of the four was narrated where it happened. The check that now refuses this reads every scored block of every
published record rather than one block of one, because the version that missed
both read only `by_tier`. The held-out cut has no `spread / low-major / always the
favourite` deficit to lose — that side reads no demonstrated edge there at 62
and at 95, on 637 held-out bets against 1,220 — and it loses `total_points /
high-major / always the underdog` instead, which the full store keeps at both
counts. The registration commit's message said the held-out backtest *"loses
seven and gains"* that side, which reads as eight. Counted from the records in
this tree it is neither: over 62 -> 95 the held-out cut loses exactly two blind
deficits — `high_major / total_points / always the underdog` and
`mid_major / alternate_total_points / always over` — and gains none, while the
full store loses only the second of those. The `67 - 62` this sentence carried
until 2026-09-18, and the pre-#53 `70 - 63` before that, were both read from
records that are not in this tree to be re-read.
Nothing anywhere becomes an edge. Mid-major survives with room: how much
room is in the generated census above, which searches the family size for the
first count at which each tier's corrected interval reaches zero, per tier and
never pooled. This file said **411** until 2026-09-18 and the record has never
supported it — the figure was derived, so no reader could look it up, and it
was the stated margin of safety on a demonstrated deficit.
**This is the pre-registration working,
not a reason to have skipped it** — an interval is paid for by the whole search
that produced it, including the parts that have not run yet.

**Nine more went at 101 -> 128 on 2026-09-15, and this registration is what
spent them. That sentence is history, and everything after it in this paragraph
used to be written in the present tense against records that no longer say it.**
Putting the 27 residual-regression features on the ledger took the
family 101 -> 128 -- the factor is in the generated block above, which is the
only place this file states it -- and nine published readings stopped
clearing the bar inside that one step.

Those nine rows covered four readings, and three of the four were PLAYER PROP
sides. A prop appears in no price-backtest record in this tree: the backtest
declared its scope on 2026-09-17 and measures team markets only, under which
the blind baseline dropped from 280 sides to 160 and those readings left
`cbb_price_backtest.json` altogether. They are not retracted now; they are
**not in that record at all**, which is a different statement and has to be
made differently. The fourth, `high_major / spread / always away`, is a team
side that survived the scope change and was re-measured by it; what the
re-measurement did to it is in `docs/retracted_readings.md`, and it is not what
that file said until 2026-09-18. This file states no crossing point of its own.
A crossing point is a figure about a cell, and it is stated once, in the
retraction ledger, where a test compares every row against the records.

**The retraction table is empty today.** Read against the published readings
the cost check can walk, at the ledger's current count, no reading this lab has
published is retracted -- which is what the empty table at the top of
`docs/retracted_readings.md` means.
`tests/test_the_forward_window_is_pre_registered.py` checks that table in both
directions, so it can be neither pre-filled to buy silence nor emptied to buy
quiet. **"Every published record" is what this bullet said until 2026-09-18 and
it was not true**: the walker recognises a reading by a point estimate beside a
standard error, one published record keys its estimate under a name the walker
did not read, and the roster test could not report the gap because it derives
its expectation from the same walker. What the walker reaches and what it still
cannot is stated in `docs/retracted_readings.md` and pinned there by a test, so
it is said once.

**Nine retracted, nothing added.** Of the 27 registered, exactly one survived
its own correction -- `d_def_reb_pct`, t = +4.14 -- and that one is a
replication of `d_orb`, which the ledger already held from the rebounding
registration of 2026-09-10. So the search cost nine published deficits and
produced no claim this lab did not already have. That is not an argument against
running it. It is the arithmetic that has to be visible for the count to mean
anything: the 27 were registered before they were scored, the correction is
cumulative by construction, and a search that finds nothing still widens every
interval the lab holds.

**There is no pooled row here on purpose.** A pooled all-of-Division-I headline
is banned in this repository; the pooled figure is computed so
`docs/when_this_ends.md` can apply the stopping rule to it, and never so it can
be quoted on its own.

**A CLAIM IN THIS FILE WAS RETRACTED, RESTORED, AND WITHDRAWN AGAIN — AND THE
THIRD TIME NOTHING WAS MEASURED.** Measured on the core team markets alone,
before the alternate ladders and the halves entered the population, this file
called low-major, until 2026-09-04, *the only tier whose interval excludes
zero, and it excludes zero on the losing side*. On 2026-09-04's partial store the same tier read **no
demonstrated edge** and the claim was withdrawn. On the full store it was a
**demonstrated deficit** again. It then read **no demonstrated edge** for a
while on a record whose population, model and store did not change at all —
what changed was the family, 62 hypotheses becoming 95 — and on 2026-09-17 it
became a demonstrated deficit once more, this time because the POPULATION did
change: on that date 15,207 bets on neutral courts that this store cannot
orient were refused rather than graded, and a misgraded row is a sign flip that
biases a return toward zero. That figure is the size of THAT exclusion and not
the difference between the record and any later one — the roster seam moved the
population again the same day — which is why it is dated here and witnessed to
the commit that made it rather than stated as a standing difference. The bets, the return and the CORRECTED interval are in the
generated table above, which is the only place this file states them; the
uncorrected interval is -6.9% to -2.2%, stated here because nothing in the
generated block reaches it. Earlier bounds are not restated, because they were
measured over a population that no longer exists and nothing can check them. The
*exclusivity* the original wording claimed has not been true since the full
store either, and this sentence named the wrong tiers for a day while saying so:
which tiers exclude zero today is a row of the generated table above and is not
restated out here. **A tier's zero-crossing is rendered, never typed.** The
version of this sentence that typed it said of a tier that it had stopped
excluding zero, against a record whose corrected interval for that tier lies
entirely below zero -- a demonstrated deficit, which is the opposite statement
and the one that flatters.
`test_no_tier_is_paired_with_a_zero_crossing_the_record_contradicts` reads the
record and refuses the shape now.
No figure from the superseded run is
reprinted here; its record is not committed, and a number nobody can re-read is
a number this file may not carry. The retraction is generated:
`reports/why_the_model.py` chooses *still holds* or *no longer holds* from
`verdict_of(current)` and nothing else, and since 2026-09-05 it also derives
**which** of the two things moved from the uncorrected interval, because the
sentence it used to print — *"Nothing about the model changed. The population
did"* — would have been a false cause today.

- **The lab's own thesis is contradicted.** Softness was expected at the
  low-major end. By point estimate the worst measured tier is **mid-major**
  (the mid-major row of the generated table above).
- **The model does not beat blind betting on return, and it loses to the vig.**
  The claim that it beat every blind rule was checked and is FALSE. **Every
  count in this bullet is now in the generated census above and none of it is
  typed here**: how many blind sides there are, how many clear the declared
  bet floor, how they fall across the verdicts, how many return more than their
  own tier's model, how many of those are themselves a demonstrated deficit,
  and which markets the baseline covers. It is generated because this bullet
  gave one population two denominators — it said *the 102 blind sides clearing
  the floor* in one sentence and *0 of 188* sixteen lines later, and no
  price-backtest record holds 188 of anything. The count guard could see
  neither figure, because neither carries a comma; and had 188 carried one, the
  guard as it then stood would have passed it anyway, because
  `cbb_prop_grading.json` stores 188 as the scored rows of
  `player_points_assists / low_major`. That is the same coincidence that let a
  shot-zone record vouch for a test count, and it is why a record claim now has
  to name its field. A denominator that disagrees with itself is not fixed by
  retyping it.
  What this bullet states, and the census does not, is the two examples.
  Mid-major `always the favourite` on moneyline returns **-0.7%** over 12,334
  bets against the model's own mid-major return in the table above. (This named
  `always the underdog`, which carries the same market's other side and the
  OPPOSITE conclusion: it returns **-9.4%** over 12,284 and so loses to the
  model rather than beating it. The figures quoted were always the favourite's;
  only the label was wrong, which is the worst way for an example to be wrong.)
  The spread is wide in both directions: the worst blind side is
  `high_major / alternate_total_points / always under` at **-25.3%** over 6,618
  bets, the best is its own other side, `always over` at **+20.5%** over the
  same 6,618. The `player_threes` example this paragraph carried until
  2026-09-18 named a market no price-backtest record holds. No blind side
  demonstrates an edge — the census says so by counting — and every positive
  one has an interval spanning zero after the correction. The evidence that the
  model carries information is the Brier score against the base rate, not the
  return against blind rules.
- **The model loses to the market on Brier in every tier, with the vig left
  in**, per tier and never pooled. All three are
  demonstrated deficits; the estimates and intervals are in the generated
  block. All three are demonstrated deficits at today's correction and none of them moved when the family grew. In high-major its Brier is worse than
  the **base rate** (0.25160 against 0.25000 over 53,844 rows) — beaten by
  predicting the league mean.
- **The skill measure shows nothing, and the one exception has been
  withdrawn.** The disagreement coefficient over every opinion (270,504 wagers)
  is **no demonstrated edge** in all three tiers.
  Every interval spans zero; they are in the generated block. On the **selected**
  bets only (100,856) high-major read a *demonstrated edge* until 2026-09-17 and
  reads **no demonstrated edge** now — the figure is in the generated block with
  the rest. That was the winner's-curse comparison and never the skill measure,
  so nothing this lab called a finding was lost with it, but it was a published
  verdict and it is withdrawn. **The family did not withdraw it.** Held at the
  measurement it was published from, the coefficient still excluded zero
  across the family's whole 30 -> 133 growth and would have needed 156 to
  cross; held at the family of 30 it was fitted under, the new measurement
  already spans zero. The
  estimate fell by 46% while the population fell by 13%, which moved the
  standard error by 6%. Four more disagreement verdicts moved the same way in
  the same regeneration. `docs/retracted_readings.md` states all five, with the
  two causes separated cell by cell. This file previously carried a paragraph
  attributing that bound's movement to two registrations and then to three,
  which was the right arithmetic for a cause that turned out not to be the
  operative one.
- **Anti-predictiveness is a shape, and the return by shape is measured.**
  Return by claimed-edge bucket reads **8 usable buckets of 8 populated** on
  each of high-major, mid-major and low-major; the `unplaced` tier has 7
  populated and 0 usable, every one of them under the row floor this table
  prints no frequency below. It was published here as *not measurable*, 0 of 8,
  which was never a fact about the archive: the graded export's projection had
  dropped the realised-return column and the report could not write a return it
  had not been handed. One bucket is a **demonstrated deficit** — low-major's
  -5% to +0% band, -5.3% over 10,587 settled wagers across 4,181 games, and the
  family-corrected interval lies entirely below zero. That is a stronger
  statement than failing to demonstrate an edge and it is a statement about the
  money. Overconfidence
  by bucket is measured too: high-major runs **+13.3 pp** in the smallest claimed-edge
  bucket (21,290 rows) to **-18.5 pp** in the largest (9,559), so **raising the
  threshold makes it worse** — the move a disappointing backtest invites.
- **Replication: 0 replicated / 0 did not replicate / 0 reversed / 3 not enough
  evidence / 9 nothing to replicate / 20 untestable**, over 32 cells; the
  held-out and discovery populations are in the record census above, because
  the two figures this sentence used to state were the record's values before
  it was regenerated and neither of them survived it. **This is not the
  split declared on 2026-09-03** (discovery [2021, 2022, 2023], holdout [2024]),
  so it is a **second look at the data rather than a pre-registered test** and
  every state in that count reads as one. `mid_major / team_total` is flagged
  *"a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication"* — -6.9% over 4,429
  held-out bets in 2026 where discovery demonstrated nothing. That cell's holdout is
  burned.
- **Not measured, and the reports say so.** The half-point decomposition was
  **refused**: the ticket-margin reconstruction agreed with the recorded outcome
  on 153,347 of 174,136 scorable bets (**88.1%**), below the 99% bar.
  Reachability has no in-season store to split on. Futures cannot be bought at
  all — no historical bulk endpoint.

### The player-prop model, scored — 2026-09-08

**Design section 10 has run and the model loses to the market.**
`data/outputs/cbb_prop_grading.{json,md}`, re-renderable for free with
`scripts/run_prop_grading.py --rebuild-report-only`.

- **The identity closed before anything was scored.** The store offered
  **257,474** prop wagers under the declared casefold; the run accounted for
  257,474 with a residual of **exactly 0** and filed both of design section
  10's receipts in its own process. 484,790 book-quotes settled, **342,678**
  paired two-sided at their own book over 171,339 two-sided pairs, and
  **339,660 rows** scored. 0 pushes, 2,834 voids, 0 unsettleable, **no probability
  clipped**, and the control declined **0** of the wagers the model priced.
- **No tier shows a demonstrated edge, and the model's log loss is worse than
  the price's in all three.** high-major 0.68839 against 0.68265, mid-major
  0.68793 against 0.68339, low-major 0.67955 against 0.67379. The headline
  advantage — the least favourable of two de-vigs and two push conventions — shows **no demonstrated edge in any tier**; the three
estimates and their intervals are in the generated block. **Uncorrected, high-major and mid-major exclude zero on the losing
  side**; the family correction at the ledger's current count is what makes them *no
  demonstrated edge* rather than a deficit, which is the correction working and
  not the measurement moving.
- **One cell is a demonstrated deficit**: `player_pra` / high-major, over 4,308 wagers on 350 game
  clusters; the figure is in the generated block. Of
  the 30 registered market-and-tier cells, 20 are *no demonstrated edge*, that
  one is a deficit, and 9 sit below a declared floor and carry a phrase.
- **It beats its own control, and that is not the same claim.** The
  identity-blind role-prior control loses decisively in high-major and mid-major, and by nothing
  demonstrable in low-major; the three are in the generated block. That says the per-athlete evidence is
  worth something over a role table; it says nothing whatever about the market,
  and the report prints that sentence beside every one of them.
- **Against the VIGGED price it is also worse by point estimate in every
  tier** (-0.0025, -0.0013, -0.0032, all spanning zero). That comparison is a
  diagnostic and is never a headline: it hands the model the whole hold.
- **The calibration is the shape of the finding.** Monotonically overconfident
  on both sides: high-major says 84.0% and wins 74.3% over 701 rows, says 26.5%
  and wins 36.2% over 3,874. The de-vigged price is close to calibrated on the
  same rows.
- **Coverage reproduces the design's own claim**: two-sided coverage is
  **98.7% at the money**, 50.7% one rung out, 13.2% two, 4.7% three and **1.1%
  four**. The 184 scored rows past three rungs are reported apart as
  **UNBENCHMARKED** and are never an edge.
- **`player_first_basket` and `player_double_double` are refused BY NAME**, are
  filtered immediately after the census gate, and appear in no cell, no verdict
  and no hypothesis.

**The ledger's 33 player-prop entries stay `pending`, and so does every
other entry in it.** This lab's
convention is that the ledger records the registration and the record on disk
carries the result; decision 54 says why, and
`tests/test_the_player_props_are_pre_registered.py` no longer reads the field as
evidence that nothing was measured.

**What this does NOT unblock.** Nothing is allowlisted, no prop can reach
`Availability.CONFIRMED`, and `price_backtest.build_record` still scores player
markets with no census receipt — a receipt lives for one process and the grading
run is a different one. `test_the_grading_commit_still_owes_this_gate` and
clause 5 of `tests/test_player_census_reconciles.py` hold both halves open.

### The winner's curse, measured

**Overall calibration is not evidence, and this run is why.** Overall the model
is **0.4 pp underconfident** over 526,728 graded rows — essentially calibrated,
with gaps that cancel, and only five of ten bins over-predicted. On the bets it
**selected**, it is **10.4 pp overconfident** over 174,136, and **every one of
the ten bins is over-predicted**.

It worsens with confidence: in the 90-100% band the model says 93.9% and wins
**90.7%** over 11,547 rows overall, and says 94.1% and wins **79.9%** over 2,411
rows on what it picked.

A model is selected into its bets by its own disagreement with the price, so
its bets are the tail of its own error distribution. This is an independent
reproduction of the NHL lab's 9-12 pp in a different sport.

### Four defects the measurement path found, all fixed

1. **An absent experiment ledger was reported as a family of one.**
   `looks_from_ledger` returns `max(count, 1)`, so a missing file and a
   one-entry file are the same integer — and the report stated it as fact about
   a file it never opened. A correction of x1.00 — the factor at a family of 1 — widens nothing, so a missing
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
  month for this lab. Headroom for the sibling labs' committed spend is reserved out of that authorisation; what they have committed is recorded in their own repositories and not here, so no figure for it is published on this page.
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
- **The pessimistic full-catalogue buy does not fit inside a month's quota**, so
  the purchase runs in Cooper's stated priority order — core team markets across
  every season first, then ladders, then props, then futures — and the retention
  probe runs first to replace the pessimistic bound with a measured rate. **This
  bullet published a figure half the size of the one `docs/project_status.md`
  publishes for the same named quantity.** `docs/credit_cost.md` states the full
  catalogue's price twice and the two spellings differ by exactly the region
  count `data/outputs/cbb_credit_cost.json` stores. Which of them is the full
  catalogue is NOT established: no field of that record holds a catalogue total,
  so neither figure can be bound to one, and a figure that cannot be bound is
  not restated here. `scripts/estimate_credit_cost.py` is what would settle it
  by rendering the total into the record.

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
  the day's, reported beside the raw figure. **A hypothesis is registered before
  the thing it tests is built**, and what that costs the intervals already
  published is computed and published with it.
- **A quantity exempted from the correction can never become a finding.** The
  seven descriptive-only declarations pay nothing because none of them is a
  claim about edge; `record()`, `save()` and `Ledger Guard` all refuse to let
  one be promoted afterwards, which is the only reason the exemption is honest.
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
| The required check `Tests` | `tests/test_workflows.py`: parsed YAML — `if:`, `needs:` and `strategy:` all refused on the required job, and `if:` on any other job in the file, because GitHub reports a **conditionally-skipped required check as Success**; the suite line's arguments a WHITELIST (`-q`, `-rs`, one `--junit-xml=` under the runner temp) rather than a blocklist that let `--version` through; the gate line pinned as a whole command and then EXECUTED under stubs with the invoked command words read back | the seven operational workflows keep their deliberate `continue-on-error`, `\|\| true` and `if-no-files-found: warn`; a nested `bash -c`; `cd` before pytest; the pin is exact, so `python3` for `python` is refused too |
| Zero skips, every guard ran | `scripts/check_test_results.py` on the junit CI writes — per TEST, comparing each required guard's `def test_*` against the testcases recorded, and refusing evidence older than the marker the suite step writes; `tests/conftest.py` at collection, which stops the run on a collection-phase skip, on any narrowing pytest actually received (`--deselect`, `-k`, `--ignore`, `--ignore-glob`, the ini `addopts`, `PYTEST_ADDOPTS`), and on any tracked `tests/test_*.py` that collected nothing | a non-strict `xfail` marker; a waiver keyed on a token no sweep arm draws; **a test deleted outright** — the declaration goes with it, and `MINIMUM_TESTS = 5` is the only floor left |
| Ledger append-only | `save(floor=…)` at runtime; `Ledger Guard` diffing THE one tracked ledger, `data/outputs/experiment_ledger.json`, against the PR base, keyed on `(search, name, seasons, stage)`; `pending` may be filled in once, nothing else moves. The tracked render `cbb_experiment_ledger.md` is not compared key by key — it is rebuilt from the JSON in the same workflow and any diff is a failure. **Descriptive-only declarations are diffed too**, keyed on `(search, name)`: one may not be removed or rewritten, and no head hypothesis may carry a name either side declared — read off the BASE as well as the head, so deleting the declaration and adding the hypothesis in one commit is still caught. `record()` and `save()` refuse the same two edits in process | an appended hypothesis is taken on trust; the same span written in two orders is two keys; `Ledger Guard` is not a context main's protection requires, so its red does not block the merge |
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

## Where every count on this page comes from

**Every comma-formatted count outside the generated blocks is enumerated, and
refused unless it says where it comes from.**
`test_every_count_the_documents_state_is_accounted_for` finds each one by its
shape and `test_every_bound_count_is_the_value_at_the_field_it_names` then
READS the field each one names. There are four things a count may be, and the
first is the one to reach for.

1. **Generated.** A figure between `BEGIN GENERATED` and `END GENERATED` is
   rendered from the records by `scripts/splice_headline_table.py`, and the
   committed bytes are compared against a fresh render on every run. It cannot
   go stale and it needs no marker, so fenced counts are not swept at all.
2. **Bound to a record FIELD.** `[src: <figure> in
   data/outputs/<record>.json#/<pointer>]`. The guard walks that pointer in
   that record and checks the field holds the figure. **This replaced "some
   record under `data/outputs/` states this integer somewhere", and that is
   the whole point of it**: the store holds thousands of integers, so about
   one four-digit figure in eight passes such a test by coincidence, and one
   did — a test-suite tally was vouched for by a shot-zone record's field-goal
   attempts, while the true figure would have been refused. A record path with
   no field is refused here.
3. **Witnessed elsewhere.** `[src: <figure> in <path outside data/outputs/>]`,
   for a count this lab keeps in a module, a decision log or a test. The named
   file is read and the figure looked for in it.
4. **History.** `[superseded: <figure> on YYYY-MM-DD]`, written ON THE LINE
   that states the figure rather than in a list at the foot of the page, and
   refused if any record still holds it. A marker that excuses a present-tense
   sentence has to be where the sentence is; `[@N]` is anchored to its interval
   for the same reason.

Every marker below names a figure this page states outside the fences.

- [src: 1,220 in data/outputs/cbb_price_backtest.json#/null_baseline/124/bets] — `low_major / spread / always the favourite`, blind-baseline bets.
- [src: 2,411 in data/outputs/cbb_price_backtest.json#/calibration/selected/9/n] — selected-bet rows in the 90-100% confidence band.
- [src: 2,834 in data/outputs/cbb_prop_grading.json#/population_census/void] — prop wagers voided.
- [src: 3,874 in data/outputs/cbb_prop_grading.json#/by_tier/0/calibration/model__conditional/2/rows] — high-major prop rows in the 20-30% predicted band.
- [src: 4,181 in data/outputs/cbb_forecast_skill.json#/by_tier/2/buckets/2/games] — game clusters under low-major's -5% to +0% claimed-edge bucket.
- [src: 4,308 in data/outputs/cbb_prop_grading.json#/by_market_and_tier/6/rows] — `player_pra` / high-major wagers.
- [src: 4,429 in data/outputs/holdout/cbb_replication.json#/markets/16/seasons/1/bets] — `mid_major / team_total` bets in the held-out 2026 season.
- [src: 6,318 in data/outputs/cbb_shot_zones_2026.json#/coverage/games] — 2025-26 games in the shot-zone coverage.
- [src: 6,618 in data/outputs/cbb_price_backtest.json#/null_baseline/5/bets] — `high_major / alternate_total_points / always under`, the worst blind side.
- [src: 6,618 in data/outputs/cbb_price_backtest.json#/null_baseline/4/bets] — its other side, `always over` — the same bet count, which is why the sentence says *the same*.
- [src: 8,267 in data/outputs/holdout/cbb_replication.json#/markets/17/holdout/bets] — the replication's held-out `total_points` / mid-major bets.
- [src: 9,559 in data/outputs/cbb_forecast_skill.json#/by_tier/0/buckets/7/rows] — high-major rows in the largest claimed-edge bucket.
- [src: 10,587 in data/outputs/cbb_forecast_skill.json#/by_tier/2/buckets/2/rows] — settled wagers in low-major's -5% to +0% bucket.
- [src: 11,547 in data/outputs/cbb_price_backtest.json#/calibration/overall/9/n] — all graded rows in the 90-100% confidence band.
- [src: 12,284 in data/outputs/cbb_price_backtest.json#/null_baseline/61/bets] — `mid_major / moneyline / always the underdog`.
- [src: 12,334 in data/outputs/cbb_price_backtest.json#/null_baseline/60/bets] — `mid_major / moneyline / always the favourite`.
- [src: 21,290 in data/outputs/cbb_forecast_skill.json#/by_tier/0/buckets/0/rows] — high-major rows in the smallest claimed-edge bucket.
- [src: 21,393 in data/outputs/cbb_price_backtest.json#/null_baseline/123/bets] — `low_major / spread / always away`.
- [src: 53,844 in data/outputs/cbb_forecast_skill.json#/by_tier/0/rows] — high-major rows the Brier comparison is fitted on.
- [src: 77,160 in data/outputs/cbb_retention_probe.json#/credits_spent] — credits the retention probe spent.
- [src: 90,766 in data/outputs/cbb_historical_purchase.json#/waves/1/why] — college first halves behind the 3.54% level-finish rate; the record states it in its own text.
- [src: 94,194 in data/outputs/cbb_ratings_fit.json#/team_games_supplied] — team-games supplied to the ratings fit.
- [src: 100,856 in data/outputs/cbb_forecast_skill.json#/populations/selected/rows] — the threshold-selected bets.
- [src: 153,347 in data/outputs/cbb_price_backtest.json#/half_point/convention/agreed] — bets where the ticket-margin reconstruction agreed with the recorded outcome.
- [src: 171,339 in data/outputs/cbb_prop_grading.json#/overround/pairs] — two-sided prop pairs.
- [src: 174,136 in data/outputs/cbb_price_backtest.json#/half_point/convention/checked] — scorable bets the half-point convention was checked on.
- [src: 174,136 in data/outputs/cbb_price_backtest.json#/calibration/selected_overconfidence/n] — selected bets the 10.4 pp overconfidence is measured over — a different field of the same record that happens to hold the same integer, which is why both are named.
- [src: 257,474 in data/outputs/cbb_prop_accounting.json#/offered] — prop wagers the store offered under the declared casefold.
- [src: 270,504 in data/outputs/cbb_forecast_skill.json#/populations/all_opinions/rows] — every settled wager the model had an opinion on.
- [src: 339,660 in data/outputs/cbb_prop_grading.json#/population_census/scored] — prop rows scored.
- [src: 342,678 in data/outputs/cbb_prop_grading.json#/devig_census/devigged] — book-quotes paired two-sided at their own book.
- [src: 484,790 in data/outputs/cbb_prop_grading.json#/devig_census/supplied] — book-quotes settled and supplied to the de-vig.
- [src: 526,728 in data/outputs/cbb_price_backtest.json#/calibration/overall_overconfidence/n] — graded rows the overall calibration is measured over.
- [src: 1,493,589 in data/outputs/cbb_weekly_loop.json#/steps/1/lines/4] — player-games in the processed tables; the weekly loop's own log line states it.
- [src: 4,992,714 in data/outputs/cbb_credit_cost.json#/quota_remaining] — credits remaining on the account at the recorded read.
- [src: 45,391 in src/cbb_betting_lab/forward_evidence.py] — game segments in the processed table, eight seasons.
- [src: 1,199,926 in docs/decision_log.md] — the credits the lost ladders wave spent (decision 27).
- [src: 15,207 in tests/test_the_forward_window_is_pre_registered.py] — neutral-court bets refused on 2026-09-17.
- [src: 253,589 in src/cbb_betting_lab/settlement.py] — free-throw rows in a season.
- [src: 1,500,000 in docs/credit_cost.md] — Cooper's standing monthly authorisation.

**What this does NOT check, and a reader should know which.**

- **Integers without a comma.** `32 cells`, `5 demonstrated deficits`, `791
  days` — a `\d+` sweep over English prose is every decision number, ordinal,
  season and defect count on the page, so the guard is scoped to the shape that
  is a population or a tally by construction. This is the hole a blind-baseline
  denominator sat in for four rounds while contradicting another sentence eight
  lines away. The answer taken was not a wider sweep: that whole census is now
  generated, where nothing is typed and nothing needs finding.
- **Which SENTENCE a bound figure belongs to.** The marker binds a VALUE to a
  FIELD and the guard checks the field holds the value. It does not read the
  English around the figure, so a sentence that quotes a correctly bound number
  while describing the wrong cell still passes. What binding buys is a source a
  reader can follow and a red suite the day the record moves — not a proof that
  the prose is about that source.
- **Whether a superseded figure was ever true.** The marker asserts that no
  record holds it now and that the page says when it stopped holding. The
  record it came from is generally not in the tree any more, which is why the
  figure is narrated rather than quoted.
- **Percentages, decimals, and money to the cent.** A percentage carries no
  comma and is not seen — unless it is large enough to carry one, in which case
  it is, because the guard reads the comma and not the sign after it. A
  comma-formatted DECIMAL is not matched at all, rather than matched as its
  integer part, because truncating it would put a figure this page never states
  into a failure message. **That exemption covers a price with cents, and this
  section claimed the opposite until 2026-09-18**: a dollar amount in whole
  units is enumerated and refused like any other count, and the same amount
  written to the cent is not seen at all. Money in whole units is in scope;
  money to the cent is the decimal exemption wearing a dollar sign, and there is
  no live instance because every money figure in these documents is a whole
  number of credits. A limit stated falsely is worse than
  no limit, and this one has now been stated falsely in both directions. The
  corrected intervals among the percentages are refused by
  `test_every_interval_in_the_document_is_accounted_for` instead.
- **Correction factors are a separate rule, and it does not reach this far.**
  A factor is not comma-formatted, so nothing above sees one. In `CLAUDE.md`
  and `docs/project_status.md`,
  `test_a_correction_factor_in_the_prose_names_the_family_it_is_the_factor_of`
  requires every factor spelling outside the fences to name, in the same sentence,
  the family size whose `stats.bonferroni_factor` it equals, and
  `test_no_sentence_pairs_a_record_with_a_correction_factor_outside_the_fence`
  refuses any sentence that pairs a record with a factor — that pairing is a row
  of the record census and is rendered, never typed. **A RECORD IS RECOGNISED BY
  ITS ENGLISH NAME AS WELL AS ITS FILENAME SINCE 2026-09-18**, because the
  filename pattern was an escape: the same false sentence with
  `data/outputs/cbb_price_backtest.json` replaced by *the price backtest* was
  green at full-suite scope. The English names are derived from the records on
  the census, not listed. **And a factor is recognised written out**, `a factor
  of N` and `N-fold` as well as `xN`, and at one decimal place as well as four. What is NOT recognised is a factor in some further spelling
  nobody has thought of; the protection that does not depend on a spelling is
  the census block, which renders each record's own `looks` and
  `correction_factor` from the record.
- **A VERDICT, as opposed to a figure.** This is the widest hole on the page and
  it is named rather than implied. Nothing here reads a sentence that states a
  result in words — *"the search found nothing"*, *"the cut is clean"* — and for
  two days one such sentence published a demonstrated deficit as a reading that
  no longer excluded zero. One shape of it is now decidable and is checked:
  `test_no_tier_is_paired_with_a_zero_crossing_the_record_contradicts` reads the
  price backtest's own per-tier bounds and refuses any unanchored sentence in
  `CLAUDE.md` or `docs/project_status.md` that names a tier and contradicts them
  about zero. That is one vocabulary over one block of one record, and it SKIPS
  any sentence naming another cut — a market, the held-out replication, the
  core-team backtest, a claimed-edge bucket — because those have their own
  bounds and comparing them to the tier row would be a false red. The verdict
  WORDS are not in that vocabulary at all: they were tried and eight honest
  sentences went red, because a verdict word beside a tier name is usually about
  some other cut. Every other verdict-shaped sentence in these documents is
  unguarded, and the answer is the same one as for the counts: state the verdict
  where it is rendered and point at the block.
- **A SUITE SIZE, and a COUNTDOWN.** `test_no_document_publishes_a_test_count`
  and `test_no_document_publishes_a_countdown` refuse these outright rather than
  trying to check them. Neither is in a record, nothing renders either, and both
  are wrong within a day — a test is added, or the sun comes up. Both of the
  test counts these documents carried were wrong when they were found, and so
  were both of the countdowns.
- **Every other document in this repository.** Only `CLAUDE.md`,
  `docs/project_status.md` and `docs/retracted_readings.md` have their counts
  enumerated. The one thing checked across all of them is that a figure one of
  these three declares superseded is not stated as current somewhere else.
