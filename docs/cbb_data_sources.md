# Where every number comes from, and what it cannot tell us

**Verified by fetching each source on 2026-08-31 and 2026-09-01, not assumed.**
Where a source was probed and found absent, that is recorded as an absence with
its date — because *"the source does not have this"* and *"we looked in the
wrong place"* have looked identical before, and the second one cost the NHL lab
a market for a season.

Every figure below is measured from the cached bytes. This lab holds **eight
seasons: 94,194 team-games, 1,493,589 player-games, 45,391 game segments**,
2018-19 through 2025-26.

---

## hoopR / SportsDataverse — the primary source

**What it is.** ESPN-derived men's college basketball, published as GitHub
release assets on `sportsdataverse/sportsdataverse-data`. Free, unauthenticated,
parquet. Fetched directly rather than through a wrapper: `hoopR` (R, v3.1.0,
2026-08-27) and `sportsdataverse-py` (last commit 2026-08-31) are both **alive
and maintained** — unlike the football lab's `nfl_data_py`, which is archived —
but the loaders are three lines of URL construction, and fetching directly is
what lets this lab pin, hash and snapshot.

**`sportsdataverse/hoopR-data` is ARCHIVED** (last push 2023-04-05, "hoopR data
2002-2021"). Nothing here points at it, and a test pins that.

| Feed | Seasons | Cadence | Latency | What it gives |
|:---|:---|:---|:---|:---|
| `schedules` | 2002-**2027** | 07:00 UTC daily, **18 Oct - 30 Apr only** | overnight | `game_date` (the Eastern date ESPN files the game under), venue, `neutral_site`, `status_period`, `notes_headline`, both conference ids |
| `team_box` | 2003-2026 | same | ~03:00 ET next morning | team totals, the four factors' inputs |
| `player_box` | 2003-2026 | same | ~03:00 ET next morning | every prop settlement quantity |
| `pbp` | 2003, 2006-2026 | same | ~03:00 ET next morning | clock, score, period, shot type, participants |

**Licence: Creative Commons Attribution 4.0 International**, verified from
`hoopR-mbb-data/LICENSE.md` — *"licensed under the Creative Commons Attribution
4.0 International License"*, free to share and adapt, commercially, with
attribution. Every report this lab publishes credits SportsDataverse.

**The chain of title is not clean, and that is stated rather than glossed.**
The CC BY grant is SportsDataverse's over their own compilation. The underlying
data is ESPN's, and ESPN runs on the Disney Terms of Use, which prohibit
automated extraction and commercial use of *their* products. Consuming an
already-published parquet from GitHub is not this lab scraping ESPN, but the
question is legal rather than settled. It is recorded here so nobody later
mistakes silence for clearance.

### Revision behaviour — the reason ingest hashes everything

**The daily job rebuilds and re-uploads the entire current-season file, every
run, overwriting in place under the same URL.** There is no per-game "final"
flag, no changelog, and no version history on a release asset. Every 2003-2021
play-by-play asset was rewritten on 2026-07-29 and 2022-2025 on 2026-08-03.

So every fetch records a **sha256 of the bytes** into `data/raw/cbb/manifest.json`,
and `hoopr.check_for_restatements()` reports any asset whose bytes moved. A
restatement that changes a row already settled against is how a walk-forward
test quietly stops being one. Restatements are reported, never applied silently.

**A green Actions badge upstream is not evidence the data moved.** The
pipeline's own workflow file documents its silent-failure mode — *"the git calls
are swallowed with no rc check, that lands as a GREEN job that published
nothing"* — and its `timestamp.json` disagrees with the assets' real write times
by three weeks. Freshness is judged from the asset's own bytes and nothing else.

**No cron between 1 May and 17 October.** Off-season data is frozen; a refresh
then is a manual dispatch. A 404 on a season not yet played is **not published
yet**, a distinct condition from a failure, because otherwise the nightly cron
is red every night until November and a monitor that cries wolf for two months
is not read on the night it matters.

### Coverage, and how non-Division-I is excluded

ESPN-derived and therefore **not televised-only**. 2025-26: 6,318 games, of
which 6,300 final, 14 postponed, 4 cancelled. Play-by-play on 6,275; team box on
6,299.

**728 distinct team ids appear and only 365 are D-I.** The membership marker is
a non-null conference id, which 365 ids carry across 31 conferences while 363
carry none — Morehouse, Blackburn, Maine Fort Kent, Penn State Behrend and the
rest of the D-II, D-III, NAIA and junior-college exhibition opponents.

**Measured: 551 of 6,318 games in 2025-26 have a non-D-I side, and 541 of those
551 (98%) fall in November and December.** These are the buy-games. They are
never fitted on, never carded, never in the ledger, and always counted.

**Do not use ESPN's `/teams?groups=50` endpoint as the D-I universe.** It
returns **362** and silently omits three genuine D-I programmes — Queens,
Lindenwood and Southern Indiana, all recent D-II reclassifications, each of
which reports `isActive: true` under group 50 when asked individually. The
conference walk returns 365 and agrees with the NCAA's own count.

**Women's basketball and the lower divisions are in separate release tags**
(`espn_womens_college_basketball_*`), so no sex filter is needed inside the
men's files.

### What it cannot tell us

- **Possessions.** Nothing in the ESPN feed is a possession. See below.
- **`home_linescores` cannot be parsed.** It is a string holding a *numpy repr*
  — `"[{'displayValue': '33', 'period': 1.0, ...}\n {...}]"` — with newlines
  instead of commas, so `ast.literal_eval` fails. Halftime scores are derived
  from play-by-play, which is the authoritative source anyway.
- **Schema is not stable across seasons.** The 2003 play-by-play has 59 columns
  named `qtr`/`game_half`; 2025 has 63; 2026 has 62. Never union seasons without
  an explicit column contract.
- **Substitution coverage jumped 4x in 2026** (829,632 events against 195,930 in
  2025), which is why the 2026 file has 2.92M rows against 2025's 2.19M. It is a
  change in ESPN's reporting depth, not in basketball. No lineup or on-off work
  is attempted from this feed.
- **2004 and 2005 have no play-by-play at all.**

---

## Possessions: derived, and validated rather than assumed

Cooper's instruction was to *"validate the standard estimator against
play-by-play rather than assuming the estimator."* Doing so **found a defect
rather than confirming an assumption.**

The estimator is `FGA − OREB + TOV + 0.475 × FTA`. The independent check counts
possession-ending events in the play stream: a made field goal, a defensive
rebound, a turnover, or the last made free throw of a trip.

| Season | Estimator | PBP count | Gap | r | Games |
|---:|---:|---:|---:|---:|---:|
| 2019 | 140.0 | 142.2 | −2.19 | 0.942 | 5,473 |
| 2020 | 140.0 | 141.9 | −1.88 | 0.889 | 5,384 |
| 2021 | 140.2 | 142.1 | −1.93 | 0.978 | 4,015 |
| 2022 | 138.3 | 140.1 | −1.74 | 0.962 | 5,830 |
| 2023 | 138.0 | 139.7 | −1.67 | 0.981 | 6,115 |
| 2024 | 139.2 | 141.0 | −1.82 | 0.984 | 6,149 |
| 2025 | 138.0 | 140.7 | −2.65 | 0.944 | 6,133 |
| **2026** | 138.9 | **145.4** | **−6.53** | 0.943 | 6,274 |

Two findings, and the second is the one that decides which number the model uses.

**The defect.** The obvious screen for "not a free throw" is
`str.contains("Free Throw")`. ESPN's play type is **`MadeFreeThrow` — one word,
no space** — so that screen matches **none** of the 253,589 free-throw rows in a
season, and every one of them counts as a made field goal. It inflated the
possession count by 15 a game, and far worse, it would have settled
`player_first_basket` on whoever made the game's first **free throw**: a
plausible name, a real player, a wrong bet, and nothing about it would have
looked broken. `tests/test_free_throws_are_not_baskets.py` pins it.

**The estimator is stable and the play-by-play count is not.** Seven seasons
agree to within 1.7-2.7 possessions; 2026 jumps to 6.5. That jump coincides
exactly with ESPN's fourfold increase in substitution reporting, so it is a
change in the feed rather than in the sport. A model built on the PBP count
would carry a discontinuity at 2026 that is an artifact.

**So the model uses the estimator**, and the ~1.5% residual gap is recorded
rather than tuned away. It also matters less than it looks: tempo enters the
model as a *fitted* quantity from the same definition used to predict, so a
constant offset in the possession convention cancels out of the predicted score.

---

## The Odds API — prices

**Sport keys, read from the provider's own `/v4/sports?all=true` listing on
2026-09-01 rather than from documentation:**

| Key | Title | Active today | Outrights |
|:---|:---|:---|:---|
| `basketball_ncaab` | NCAAB | **False** (off-season) | no |
| `basketball_ncaab_championship_winner` | NCAAB Championship Winner | True | **yes** |
| `basketball_wncaab` | WNCAAB | False | no |

**Women's basketball is a separate sport key**, so excluding it from the price
side is total and free: this repository never names `basketball_wncaab`, and a
test enforces that no fetch names any key the registry did not declare.

There is **no conference-winner key and no season-win-totals key** at the sport
level. If those markets exist they are market keys under `basketball_ncaab`, and
that is an in-season probe question rather than a September one.

**Historical availability, from the provider's "Earliest Historical Timestamps":**

- `basketball_ncaab` — **2020-11-16**, featured markets (moneyline, spreads,
  totals) only.
- Everything else — props, halves, every alternate ladder — **2023-05-03**,
  site-wide. That date falls **after** the 2022-23 season ended, so **the full
  catalogue is buyable for exactly three seasons**: 2023-24, 2024-25, 2025-26.
  Featured markets reach back six.

**Revision.** Snapshots are immutable and carry `timestamp` / `previous_timestamp`
/ `next_timestamp` — **genuinely point-in-time and safe for walk-forward.** The
provider's own caveat is recorded: *"they can still be present in historical odds
snapshots"* about data errors, and prices before 2022-09-18 are back-computed
from decimal with rounding error.

**Latency.** Featured markets 60s pre-match, additional markets 60s, scores
about 30s.

**Licence.** Terms updated 2026-08-31. Permitted verbatim: *"Storing our data and
retaining it indefinitely"*, *"Using our data in research papers and analytical
dashboards"*, *"Using our data to train statistical and machine learning
models"*. Prohibited: *"Do not resell, repackage, or redistribute our data as a
standalone data product."* Governing law New South Wales. About as permissive as
a commercial odds licence gets for a private research lab.

### What it cannot settle

`/scores` returns **final team totals only** — no halftime, no period array, no
overtime flag, no player lines, no play-by-play. So the odds provider can settle
full-game moneyline, spread and total and **nothing else**; every half market,
team total, player prop and first-basket bet settles from hoopR. `daysFrom` caps
at 3, so scores must be harvested within 72 hours or they are gone.

---

## Availability — investigated honestly, and there is nothing usable

Expected to find nothing reliable and structured, and that is what was found.
This is the CBB analogue of the NHL lab's confirmed-starting-goalie problem, and
it is worse.

| Source | State on 2026-09-01 |
|:---|:---|
| ESPN `/mens-college-basketball/injuries` | HTTP 200, **`"injuries":[]`** — zero records, against **76** for the NBA *in the NBA's own off-season*. The college-football sibling endpoint held three records during a live week, two dated 2022 and one 2020, two marked `Active`: abandoned residue, not a feed. |
| ESPN team `/injuries` | HTTP 200, `count: 0` for every D-I team. Structurally present, never populated. |
| ESPN rosters | 567 players across 40 D-I rosters: **567/567 `Active`, 567/567 empty `injuries[]`.** |
| espn.com/mens-college-basketball/injuries | **HTTP 404.** ESPN ships no college injuries page at all. |
| CollegeBasketballData | **No injuries, availability or status endpoint.** 38 paths, none of them availability; the roster schema has no status field. |
| hoopR `espn_mbb_injuries()` | A thin wrapper over the two dead endpoints. Its own documentation: *"returns an empty tibble (zero rows) when no injuries are reported."* |
| Conference / NCAA player-availability reports | **Real, and narrow.** Eight leagues (ACC, B10, B12, SEC, Big East, A-10, MVC, MW) publish through one third-party iframe vendor with no public API. T-15h initial, T-2h update. |
| RotoWire / Covers / SportsDataIO | No public API; RotoWire's own note: *"In CBB many lineups, if not most, are announced after tipoff"* and *"we don't have lineups for some smaller schools"*. |

**The coverage arithmetic is the whole finding.** Those eight leagues total
roughly **115-120 of 365 teams**, and — verified for the Big Ten and Mountain
West — the reports cover **conference games only**. So two thirds of Division I
is never covered, and the entire November-December non-conference slate is
uncovered even for covered teams. The NCAA's own mandatory policy applies *only*
to championship games.

A model fed that feed would see a high-major's injuries in January and nothing
at all for two hundred low-major teams, and nothing for anybody in the window
this lab most wants to price. **Ingesting it would create the asymmetric blind
spot rather than close it.**

**So availability is modelled as unobserved.** `gates.Availability` has five
states and **nothing reaches `CONFIRMED`**. `no_report` and `undesignated` are
kept strictly apart, because a gate that read a missing feed as "nobody is
injured" would clear an entire slate. Player props are priced, frozen and
settled; they **cannot produce a selection**, and the card says so in those
words.

---

## Officials — post-game only, so they are not modelled

Referee assignment affects foul rate and therefore totals, so this was worth
establishing rather than assuming.

**Post-game, ESPN is excellent.** `gameInfo.officials` and the core API's
`/officials` endpoint give three named officials with **stable ids**. Measured
over every D-I game on 2026-02-14 (132 events, 28 conferences): **127 of 131
returned a full three-man crew, 97.7% overall, and coverage does not degrade at
the low-major end** — VMI, The Citadel, Queens, Jackson State and Central
Arkansas all returned full crews. Spot checks back to 2016 return crews with
stable ids, so a decade-deep referee database is buildable.

**Pre-game, there is nothing.** For a scheduled game the officials endpoint
returns `count: 0` and `gameInfo` carries only the venue. NCAA.com carries no
officials data at all; CBBD has no officials field; regular-season crews are
assigned through ArbiterSports, a closed officials-facing system with no public
feed. RefMetrics claims daily pre-game assignments but its terms forbid
*"automated access, scraping, or extraction"* and its coverage is unverified —
**it is not used.**

**Therefore referee identity never enters a pre-game model**, and no report will
imply it does. A crew-tendency database is worth building as a *descriptive*
instrument, and it is explicitly not a pricing input. The exact in-season moment
assignments populate could not be established from the off-season and must be
measured in November rather than assumed.

---

## CollegeBasketballData — better than hoopR at settlement, gated by a key we do not have

Operator: Rad Sports Analytics LLC, the CollegeFootballData people. OpenAPI 3.0
spec at `https://api.collegebasketballdata.com/api-docs.json`, MIT-licensed
server source at `github.com/CFBD/cbb-api` (last push 2026-08-25).

**Richer than hoopR for settlement.** `GameBoxScoreTeamStats` carries
`possessions` directly, plus `pace`, `fourFactors`, `points.byPeriod`. Player
box scores carry `usage`, `offensiveRating`, `trueShootingPct`. Play-by-play
carries `shotInfo{shooter, made, range, assisted, location{x,y}}` and `onFloor`.

**Every endpoint is 401-gated.** Six were tried unauthenticated — `/teams`,
`/conferences`, `/games`, `/lines/providers`, `/plays/types`, `/scoreboard` —
and all six returned HTTP 401. **No response shape here was observed; all of it
is read from the spec and the source**, and that is stated rather than implied.

**Obtaining a key requires submitting an email address at
`collegebasketballdata.com/key`.** That is a form submission on Cooper's behalf,
which this lab does not do unasked — it is the one item in the final report. The
free tier is **1,000 calls a month**, shared with CFBD; Tier 2 at **$5/month**
raises it to 30,000. Only `/scoreboard` and `/stats/team/leaderboard` are
Patreon-gated; everything else is on the free key.

**Its lines endpoint is not usable for this lab.** `GameLineInfo` is seven
fields — `provider, spread, overUnder, homeMoneyline, awayMoneyline, spreadOpen,
overUnderOpen`. One row per provider per game: **no timestamps, no line-movement
history, no closing series, no halves, no team totals, no props, no alternates.**

**First-basket attribution is reconstructed, not authoritative.** The server
parses shooter and assist out of free-text `playText` with string matching, and
its changelog carries repeated fixes there. Recorded so it is never treated as
ground truth.

**Recommendation:** worth a key and worth $5/month for `possessions` and
`pace` as an independent check on this lab's derived numbers. It is **not** on
the critical path — hoopR settles everything already wired.

---

## Deliberately not used

- **Barttorvik.** Two independent reasons. First, `robots.txt` contains
  `User-agent: ClaudeBot / Disallow: /` and `User-agent: anthropic-ai /
  Disallow: /` — **the site is closed to this agent** and is not fetched.
  Second, and decisive even without that: T-Rank is **recomputed over the full
  season retrospectively**. `2024_team_results.csv` carried `Last-Modified: 07
  Oct 2025` and `2025_team_results.csv` `08 Nov 2025` — seasons rewritten months
  and years after they ended. A retrospective rating **cannot be used as a
  walk-forward feature or benchmark**, and its point-in-time archive is
  `Disallow`ed too. If Cooper wants it, the route is email, not a scraper.
- **stats.ncaa.org** — `robots.txt` is `User-Agent: * / Disallow: /`. Fully
  closed. Not fetched.
- **Massey** — HTTP 403 Cloudflare interstitial to every automated request. What
  it serves could not be established, and that is recorded as unknown rather
  than guessed.
- **Sagarin** — **dead.** `Last-Modified: 20 Apr 2023`, header reads "FINAL
  College Basketball 2022-2023". No new ratings for three seasons.
- **KenPom, EvanMiya, Haslametrics** — paid and ToS-restricted. Not scraped, not
  depended on. KenPom ~$24.95/year with a paid API at an unpublished price;
  EvanMiya ~$29.99/month. The subscription case is in the final report.
- **NET rankings** — 365 D-I teams with an official `Non-Div I` column, which is
  a free authoritative marker for the exclusion. **No archive and no date
  selector**: it must be snapshotted daily or it cannot be reconstructed. Worth
  starting a daily snapshot; not depended on for anything yet.

**A public rating is a benchmark to be beaten, never a model input.** A lab
whose ratings are someone else's ratings is a wrapper, its history is revised
under it, and it cannot answer why it is right.

---

## Settlement: which source settles what

| Quantity | Source | Confidence |
|:---|:---|:---|
| Final score, margin, total, team total | `team_games` | exact |
| Halftime score, first-half markets | `game_segments` from play-by-play | exact |
| Second-half markets | `team_score − team_score_h1` | **exact arithmetic, ambiguous rule** — see below |
| Overtime | `periods > 2` | exact; measured at **5.2-5.8% of games** across eight seasons |
| Every player counting stat | `player_games` | exact |
| Double-double / triple-double | derived from five categories at 10+ | exact |
| First basket scorer | `game_segments.first_basket_athlete_id` | exact **after** the free-throw fix |
| Method of first basket | — | **not settleable**; deferred with a reason |
| Fantasy points | — | **not settleable**; the formula differs by operator |
| Possessions | estimator, validated | ~1.5% against a play-by-play count |

### The one settlement ambiguity, stated rather than buried

**Most US books settle a second-half wager including overtime; a minority do
not.** This lab wires the majority rule (`markets.SECOND_HALF_INCLUDES_OVERTIME
= True`) and **cannot verify it** — it is a line in a book's rulebook, not a
fact about basketball.

That is the exact shape of the football lab's single largest false finding: a
market that returned +11.7% over 3,109 held-out bets on a **constant settlement
offset**, which survived split-half, fragility and a Bonferroni correction
across twenty markets, *because a constant offset replicates by construction*.
So: every second-half number this lab produces carries this caveat, second-half
markets are screened for settlement disagreement before any of them is believed,
and **a second-half result that looks strong is treated as a settlement suspect
first and a finding second.**
