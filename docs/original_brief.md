You are building a **College Basketball Betting Lab** for me, start to finish,
in one continuous effort. This message is the complete brief and the complete
authorization. Everything you need is in it. Nothing in it waits on me except
the one signature named in "The single stop".

Do not reply with a plan and wait. Start working.

**Where and what**

- Build at `/Users/cooperross/Projects/cbb-betting-lab`, GitHub
  `cooperross399/cbb-betting-lab`, private. Create the repo yourself.
- Python 3.12 at `/opt/homebrew/opt/python@3.12/bin/python3.12`.
- `gh` is already authenticated on this machine (`gh auth status`).
- **The Odds API key**: same account and same monthly quota as my NHL and
  football labs. Store it as a GitHub secret (`CBB_ODDS_API_KEY`), never in a
  file that gets committed. If the secret is not set, take the value already in
  use by the sibling labs rather than asking me for it.
- **Credits are not a constraint** and I do not want to be asked about them.
  See "Cost" for the standing authorization.
- Save this brief into the repo as `docs/original_brief.md` as your first
  commit, so future sessions can read it.

Expect this to run long. It is not a plan-then-approve build. It ends with a
working, bought, measured, self-running lab.

---

Build it modelled on my existing NHL and football labs.

**Scope: NCAA Division I men's basketball, and only that.** Women's basketball
and the lower divisions are separate projects in their own repositories if they
ever happen — the same call I made for NCAAF on 2026-08-31. Do not add them
here, not as a registry entry, not as an adapter. Keep the competition registry
anyway: it is what stops sport-specific facts scattering through the code, and
it is why this machinery is copyable at all.

## This is a full build. Do not stop.

Everything in this brief gets built, bought, measured and wired **now**, before
opening night, in one continuous effort. The season is roughly nine to ten
weeks away and I want the whole thing out of the way before it starts.

**Do not hand work back to me.** Specifically, do not stop to:

- present a plan and wait for approval — write the plan into `docs/` and
  execute it;
- ask which of two designs I prefer — pick the one you can defend, record the
  choice and the reasoning in `docs/decision_log.md`, and move;
- ask whether to spend credits — the authorization is below;
- ask whether to buy history — buy it;
- ask whether to wire a market, a source, a workflow or a test — wire it;
- report a milestone and pause for a reaction;
- ask me to run a command, check a page, or paste a value you can obtain
  yourself. Read the environment rather than the error text; if something
  appears to need me, prove it does before saying so.

**Keep `docs/decision_log.md` as you go** — every question you wanted to ask
me and answered yourself, with the answer and the reasoning, in one line each.
That is how I audit the autonomy afterwards without being interrupted during
it. A build that made two hundred judgment calls and recorded them is one I can
review; one that made them silently is one I have to re-derive.

**Velocity never buys a relaxed gate.** A never-stop instruction is not
permission to lower a bar, skip a replication, weaken a guard, merge red CI, or
call something measured that is not. If honouring a gate means the build takes
longer, it takes longer. Two of my labs have already measured no edge; both are
correct outcomes, and an instruction to keep going is not an instruction to
find a different answer.

**If you get stuck, work around it and record it.** A source that will not
yield, a market that cannot settle, a package that is abandoned — document it
in the relevant `docs/` file with what you tried, wire whatever is reachable
instead, and continue. An unresolved obstacle is a documented limitation, not
a reason to stop building.

### The single stop

There is exactly one: **I sign the acceptance receipt that allowlists a
market.** Claude may withdraw an allowlist, never grant one. That is the NHL
lab's precedent and it holds — I merged PR #47 myself because Claude refused
to, and the merge is the human approval of record.

This is not a build step and it does not block the Definition of Done. Assemble
the complete evidence, draft the receipt with truthful provenance, open the PR
with the policy gate red, and tell me at the end that it is waiting. The lab
runs fully — fetching, pricing, freezing, settling, tracking, publishing a card
that says it is accumulating evidence — while it waits. Nothing else in this
document requires me.

Do not touch the sibling labs. Not to refactor, not to extract shared code, not
to fix a defect you notice there. They hold measured numbers I cannot rebuy.
Note anything you find in `docs/ported_defects.md` and leave their files alone.

## Definition of Done

The build is finished when every one of these is objectively true, verifiable
from the repo without my judgment. Check them off in `docs/project_status.md`
with the evidence for each.

**Infrastructure**
1. Repo exists, private, CI green on `main`, and the full test suite passes.
2. Every workflow runs on a cron in GitHub Actions and requires no laptop:
   data refresh, board fetch, line-movement capture, card publish, post-slate
   settlement, weekly refit-and-measure.
3. The delivery chain is verified **end to end with a real card**, not
   asserted: `card-feed` branch → cloud relay → Drive file → a paste-ready
   chat-task prompt handed to me. Zero email.
4. `tests/test_no_secrets_committed.py` passes and no key has ever been
   printed, written, compared or committed.

**Data and settlement**
5. `docs/cbb_data_sources.md` written, every source's licence, revision
   behaviour and in-season latency recorded.
6. The processed tables exist for every season the sources reach, with row
   counts asserted by test, and every settlement column present and pinned.
7. Every wired market has a named quantity it settles against, proven by
   settling real historical games. Markets that cannot settle are in a
   `DEFERRED_MARKETS` list with a reason each.

**Prices**
8. Retention probe run, and its report re-renderable from the run record.
9. **Historical prices bought** for every market the probe showed measurable,
   across every season retained, and the store deduped on price identity.
10. Line-movement capture live and writing to its own branch, with price
    survival recorded.

**Models and measurement**
11. Models fitted walk-forward, per conference tier, with the November prior
    regime handled explicitly and the connectivity diagnostic refusing to price
    disconnected matchups.
12. The price backtest has run over the full bought population, on every
    market, with sample size, clustered intervals, family-wise correction
    against the experiment ledger's cumulative count, and replication on a
    held-out season.
13. The market-vs-model regression is computed and printed for every candidate
    model.
14. Calibration measured **on selected bets**, not only overall.
15. Reachability measured: edge reported separately for prices that survived to
    the next capture and prices that did not.
16. `docs/what_we_can_and_cannot_claim.md`, `docs/when_this_ends.md` and
    `docs/why_the_model_does_or_does_not_have_an_edge.md` written from the run
    record, and the headline reads the sign.

**Self-operation**
17. The experiment ledger is append-only, populated with every hypothesis this
    build tested, and its correction factor is what the reports use.
18. Champion/challenger promotion criteria pre-registered on disk; automatic
    demotion wired one direction only.
19. The weekly loop runs unattended and re-renders the claims doc itself.
20. `CLAUDE.md` has a "Current operating state" section a future session can
    read as project memory, with contract strings pinned by tests.
21. `docs/decision_log.md` and `docs/ported_defects.md` complete.

Then, and only then, report to me: what was built, what the measurement says,
and what is waiting on my signature.

## Read this first, before writing a line of code

Three sibling labs exist and each one earned its machinery expensively:

- `/Users/cooperross/Projects/nhl-betting-lab` — the reference implementation,
  the most complete, and the one that reached a final measured answer.
- `/Users/cooperross/Projects/football-betting-lab` — the most recent port, and
  the best record of *what breaks when you port*.
- `/Users/cooperross/Projects/epl-betting-lab` — the delivery chain that
  actually lands a card in my hand.

Read all three `CLAUDE.md` files (especially "Current operating state"), their
`docs/`, `src/`, `tests/`, and their gameday/matchday workflows before designing
anything. Port this machinery rather than reinventing it:

- the **verdicts door** (`verdicts.ships()`) — recorded, versioned decisions
  read from disk, so what ships is auditable against the experiment that
  decided it, never asserted in code;
- the **experiment ledger** (`experiment_ledger.py` in the football lab) —
  append-only, every hypothesis ever put to the data, with a correction factor
  that grows with the count. Read its module docstring before you write a
  single search. It is the single most important file in any of these labs and
  the one this project needs most;
- the **forward-evidence ledger** — freeze the card's opinions before tip,
  settle them against the box score afterwards, never reprice, day-as-unit;
- the **allowlist receipt + PR gate** — no market reaches the card without
  measurement against real prices and a human acceptance receipt I sign;
- the **start-time guard** (their puck-drop / kickoff guard) — a started game,
  or one whose start cannot be confirmed, is quarantined and its stake removed;
- **`selection_key()`** — one function builds every join key on both sides.
  That bug family reached five members in the NHL lab and cost weeks: provider
  team names vs abbreviations, UTC dates vs league dates (69% of prices
  silently discarded), `home -1.5` vs `home_minus`, outcomes staged in the
  wrong vocabulary, and a CSV round-trip turning empty players into the string
  `"nan"`. Assume I will hit all five again if you hand-build keys twice;
- the **accounting identity** — priced = no_opinion + below_threshold +
  unparseable + ambiguous + bets, reconciled and printed every run;
- **cache staleness checks**, **shrink guards**, `tests/test_no_secrets_committed.py`.

Port the discipline exactly. Change the sport, not the standards.

### This is the fourth lab, and the port is a known cost

The football lab's `CLAUDE.md` says it directly: these labs share no code, the
same defect classes appeared independently in each, and six NHL fixes were
hand-ported into football on 2026-08-31. A fourth lab means a fourth hand-port.

Hand-port again, and **do not refactor the working labs** — that prohibition is
absolute and is not a question you bring me. Make the port auditable instead:
keep `docs/ported_defects.md` listing every defect class inherited from a
sibling, where it came from, and the regression test in this repo that pins it.
If that list ends up long enough that extraction into a shared package is
obviously worth it, put the list and the arithmetic in the final report as a
recommendation. Do not act on it.

## Why this sport is worth a fourth lab — and the honest frame

Both finished labs measured no edge. This one starts from the assumption that
it will too, and its job is to answer the question *decisively* rather than
optimistically. Two things make college basketball the best shot I have:

1. **Sample size.** The NHL answer was decisive because 73,918 bets have a
   tight interval. The NFL answer is thin because a season is 272 games. D-I
   men's basketball plays roughly 5,600 games a season across ~360 teams —
   verify the exact figures rather than trusting me. On team markets alone, a
   single season is a larger population than two NHL seasons of props. **If
   there is an edge here, this lab can prove it inside one season. If there
   isn't, it can prove that too.** That is the whole reason to build it.
2. **Market heterogeneity.** The NHL finding was that books are tightly
   aligned: 1,557 of 161,891 quotes beat a de-vigged consensus. A 32-team
   league priced by every book is the hardest possible case. 360 teams on a
   Tuesday night in January is the opposite: the low-major end of the board is
   priced with far less attention. If the market's efficiency is not uniform
   across the board, this is where that shows up.

And the counterweight, built in from day one rather than discovered in March —
see "Reachability". **A soft number you cannot bet is not an edge.** The
low-major games with the loosest lines have the smallest limits and move
fastest. Any measured edge that lives entirely in prices that vanish before a
human could act is reported as *not reachable*, in those words.

## Build order — everything before opening night

The 2026-27 D-I season opens in early November 2026 — verify the exact date
from the schedule rather than trusting me. Roughly nine to ten weeks from today
(2026-08-31). Unlike the football lab, which had nine *days*, this runway is
long enough to do the whole thing up front, and that is the instruction.

> Historical prices can be bought. **Forward evidence cannot be back-dated.**
> Every night the pipeline is not freezing opinions and settling them is a
> night of clean out-of-sample data that is gone permanently — and in this
> sport a night is up to a hundred games.

Order, run straight through:

1. **Experiment ledger and verdicts door first**, before any model exists, so
   the first hypothesis this lab ever tests is already counted.
2. **Data layer, settlement, and the exclusion guards.** Exhibitions, closed
   scrimmages, and games against non-D-I opponents — the analogue of the
   football lab's preseason guard, and much bigger here, because several
   hundred November games are buy-games against D-II and NAIA schools with no
   comparable data. Never fitted on, never in the ledger, counted and stated.
   Abstain rather than nuke a real slate.
3. **Odds staging + the forward-evidence organ**, wired and dry-run, ready to
   freeze from the first exhibition-free game of the season.
4. **Retention probe, then buy the full history**, then run the price backtest
   over the whole bought population. This is the step neither sibling lab
   managed before its season, and the runway exists precisely to do it.
5. **Models, walk-forward calibration, per-tier fits, the November prior
   regime.**
6. **Measurement, replication, family-wise correction, reachability.**
7. **The weekly self-running loop, the delivery chain, the evidence pack.**

Nothing is bet at any point, and the card says plainly that it is accumulating
evidence rather than making recommendations.

## Sources, verified before anything is built

There is no free official API here of the quality the NHL had. Investigate and
write `docs/cbb_data_sources.md` recording what each source can and cannot tell
us, its licence and terms, its revision behaviour, and its in-season latency:

- **CollegeBasketballData (collegebasketballdata.com)** — the basketball
  sibling of the CFBD API the football brief pointed at. Likely the best
  structured free-with-key option: teams, venues, schedules, box scores,
  play-by-play, lines, ratings. Verify what it actually serves and at what
  tier. If it needs a key, obtain one and store it as a GitHub secret
  (`CBBD_API_KEY`) under the same rules as the odds key; if obtaining it needs
  me, that is the one kind of thing worth a single line in the final report,
  not a stop.
- **hoopR / sportsdataverse** — ESPN-derived men's college basketball
  play-by-play, team box, player box and schedules published as release assets.
  The football lab learned that `nfl_data_py` is archived and now fetches the
  nflverse release assets directly; check the equivalent maintenance status
  here before depending on a wrapper package.
- **`cbbpy`** — ESPN scraper for PBP, box scores and game info.
- **NCAA official feeds** (stats.ncaa.org, data.ncaa.com) — unofficial,
  brittle, but the authority on D-I membership and on which games count.
- **Barttorvik / other public ratings** — free and useful as an *external
  benchmark to be beaten*, never as a model input. A lab whose ratings are
  someone else's ratings is a wrapper, its history is revised under you, and it
  cannot answer why it is right. Build tempo-free ratings in-house from
  play-by-play.
- **KenPom, EvanMiya, Haslametrics and any other paid or ToS-restricted site**
  — do not scrape them, and do not build a dependency on a number we have
  neither licensed nor reproduced. If one is worth subscribing to, put the case
  in the final report.
- **Availability / lineups** — investigate honestly and expect to find nothing
  reliable and structured. College basketball has no mandated injury report.
  Whatever you find, record its latency and its coverage, because a feed that
  covers the top 50 teams is a feed that makes every low-major player look
  healthy.
- **Officials** — referee assignment affects foul rate and therefore totals.
  Find out whether assignments are published pre-game and at what coverage. If
  they are not, say so and do not model them.
- **Odds**: The Odds API (`basketball_ncaab` and the futures keys), with the
  same shadow-staging discipline the siblings use — staging invisible to the
  card, policy JSON allowlist, PR gate, human receipt.

If a source cannot supply what a market needs to **settle**, that market is not
wired. Fetching prices nothing can consume spends credits on rows no join will
ever find; pricing without honest settlement manufactures evidence.

## Markets — all of them

**Team markets**: moneyline, spread and the full alternate ladder, total and
the full alternate ladder, team totals, first-half spread/total/moneyline,
second-half lines, and any race-to-N, margin-band, winning-margin or
double-result market the provider serves. There is no draw in college
basketball, so there is no three-way to price — do not build one.

**Player props, wherever quoted**: points, rebounds, assists, three-pointers
made, steals, blocks, turnovers, free throws made, the combination markets
(points+rebounds, points+assists, rebounds+assists, PRA), double-double,
triple-double, first basket scorer, and every alternate ladder. Expect coverage
to be thin and concentrated on televised high-major games — probe the provider
for what it actually serves rather than guessing, and **probe in season**,
because a market unquoted in September establishes nothing. Wire everything the
probe finds; leave a dated re-probe on a cron for markets that appear later.

**Futures**: conference regular-season and tournament winners, season win
totals, Final Four, national championship, and the tournament's
round-advancement family. Futures get their own treatment and their own section
of the report: they tie up stake for months, they settle on a different clock,
and their return is not comparable to a single-game bet. Never fold a futures
return into a headline ROI computed over game bets. State the hold time beside
every futures number.

**The tournament is its own market family.** Sixty-seven games in three weeks,
the deepest liquidity and the most public money of the year. It is the most
plausible place for a public-bias edge and it is also 67 games — an n that
cannot establish anything on its own. Both facts go in the report, together.

**Live/in-play is out of scope for v1** — capture and settlement latency make
it a different engineering problem — but the line-movement capture below is
what makes it testable later, so do not build anything that forecloses it.

Store **distributions, not point estimates**, so any offered line prices exactly
and every alternate rung settles identically.

## Modelling requirements — where college basketball differs

State and justify every distribution choice, then measure it.

1. **Possessions, not points.** Fit adjusted offensive and defensive efficiency
   per 100 possessions plus tempo, and simulate the game from those. Derive
   possessions from play-by-play where available and validate the standard
   estimator against it rather than assuming the estimator.
2. **The last two minutes break the model.** Intentional fouling and garbage
   time mean the final possessions have nothing like the game's average pace or
   efficiency — and that is exactly where totals land and where spreads cover
   or push. A model that extrapolates full-game efficiency to the last two
   minutes will misprice totals in a direction that looks systematic and is
   really a modelling artifact. Model end-game explicitly (clock, score margin,
   foul state) or simulate it, and show the fitted end-game distribution
   against the empirical one.
3. **Overtime.** Full-game spreads, totals and moneylines settle including OT;
   half markets do not. Model OT as its own segment rather than scaling the
   regulation distribution. Measure and state the OT rate rather than assuming
   it.
4. **November is a prior, not a fit.** Roster turnover in this sport is
   enormous — transfer portal, graduation, early entries — and measure the
   current rate rather than quoting mine. A rating built only on this season's
   games is uninformative until roughly December. Build an explicit preseason
   prior from returning minutes and production, incoming transfers' production
   at their prior school adjusted for level, and recruiting; then update it
   Bayesianly as games arrive, and **report the prior's weight in every price**
   so the card can never present a November number as if it were a February
   one. The first three weeks are simultaneously the most plausible place for
   an edge and the most likely place for catastrophic overconfidence. Measure
   November separately, always.
5. **Graph connectivity is an identifiability problem, not a nuisance.** In
   November the win/loss graph is nearly disconnected between conferences, so
   any adjusted rating is identified almost entirely by the prior. Compute and
   report a connectivity diagnostic, and **refuse to price** a matchup whose
   two teams' components are effectively unconnected beyond the prior. An
   unpriced game is an honest output; a confidently priced one built on no
   connecting evidence is not.
6. **Home advantage is heterogeneous and must be fitted, not assumed.** Fit a
   venue-level home effect with shrinkage toward a league mean. Flag neutral
   sites explicitly, and treat "neutral" sites that are not — a team playing 40
   miles from campus in a multi-team event or a conference tournament in its
   own city — as a distinct third state. A game mislabelled neutral is a
   multi-point error applied to every market on it.
7. **Key numbers and the half-point.** Model pushes on whole numbers exactly.
   Report how much of any claimed edge is really half a point of line value
   rather than a differing view of the game — the football brief's rule, and it
   applies to totals here more than to spreads.
8. **Correlation is a first-order accounting problem, worse than in football.**
   Spread, moneyline, team total, game total and a player's points are the same
   event seen five ways. A naive selector on a 100-game Tuesday will take
   several hundred correlated positions in one night. Never stake correlated
   selections as independent, never sum their edges, and report
   correlation-aware exposure per game and per slate, with a stated cap.
9. **Conference tiers are different distributions.** Fit and measure per tier
   at minimum (high-major / mid-major / low-major, defined explicitly and
   recorded). Never report a single pooled headline across the whole of D-I —
   the same rule that keeps NFL and FBS numbers apart. A policy that wins in
   low-major games and loses in high-major ships in low-major only, if it ships.
10. **Schedule states.** Rest days, travel distance, altitude (a real,
    measurable effect at a handful of venues), and conference-tournament
    fatigue — four games in four days is a state with no analogue in the
    regular season. Test them the way the NHL lab tested back-to-backs: a
    measured adjustment ships **because it wins the price backtest**, and a
    better-calibrated one that loses the backtest is refused.

## The gates that fail closed

Each is the analogue of the NHL lab's "goalie saves needs a confirmed starter":
a market that is modelled, measured, and still cannot produce a selection,
because the lab lacks the feed that would make the bet real.

1. **Availability.** Expect to find no reliable structured lineup or injury
   feed for D-I basketball. Build a confirmed-available gate with explicit
   states, and — critically, following the football lab — keep "a report exists
   and this player is not on it" apart from "no report exists at all". A gate
   that reads a missing feed as "nobody is injured" clears an entire slate.
   Where availability cannot reach `confirmed`, the market is priced, frozen
   and settled but **cannot produce a selection**, and the card says so in
   those words.
2. **Non-D-I and exhibition opponents.** Excluded from fitting and from the
   card, counted and stated, never silently dropped.
3. **Neutral-site classification.** Unknown or contradictory venue status
   quarantines the game rather than defaulting to neutral.
4. **Tip-time guard.** A started game, or one whose start cannot be confirmed,
   is quarantined and its stake removed. Note the difference from the siblings:
   this sport tips games every fifteen minutes for twelve hours, so this guard
   runs continuously through the slate, not once against a single kickoff.
5. **Postponement, venue change and cancellation** — more common here than in
   the NHL or NFL. Detect and quarantine.
6. **Population purity.** Women's basketball, D-II and D-III must never leak
   into the men's D-I population through a provider key, an ESPN id or a
   scraped page. Pin it with a test.
7. **Roster and role staleness.** Take a player's team and role from a current
   roster, never from his last logged game. The NHL lab measured 20.4% of
   priced players changing clubs over one summer and the football lab measured
   9.8% over two games; in this sport, with the portal, expect worse. Measure
   it in this lab rather than quoting either figure.

## Reachability — the CBB-specific rule

The NHL lab's line-shopping test is the template: only 1,557 of 161,891 quotes
beat a de-vigged leave-one-out consensus, and those realised −3.4%. Do the
equivalent here, and go further, because the plausible edge in this sport lives
in exactly the games where a price is hardest to actually get:

- Measure against a price **actually available at the moment the card is
  produced**, at a US book I can open. Regions stay `us,us2`. A price at a book
  I cannot open is not reachable and manufactures untakeable edges.
- Record book, timestamp and **survival**: did that price still exist at the
  next capture? Report the edge separately for prices that survived and prices
  that did not.
- A backtest that beats the *opening* number is not a bet. Say so wherever such
  a figure appears.
- If a measured edge lives entirely in prices that vanish within minutes, or at
  books whose limits on low-major games are trivial, the report states that the
  edge is **not reachable**, in those words, regardless of its size or
  significance.

Build the **line-movement capture** in the first week of the build, not late —
the NHL lab's version captures the board several times daily into its own
branch, which is what made ladder staleness and price survival testable at all.
Here it is not an afterthought; it is the instrument that decides whether any
finding is real money, and it needs to be running before the season so it has
history of its own.

## Self-sustaining and self-improving — what those words have to mean

**Self-sustaining** means the laptop is never required:

- Everything runs in GitHub Actions on a cron. Schedules, rosters, ratings and
  the board refetch every run; a failed fetch **degrades rather than empties**,
  and a degraded run is marked, never silently published as a thin slate.
- Nightly: fetch board → freeze opinions → publish card. Post-slate: settle →
  append to the forward ledger.
- Weekly: refit walk-forward, re-run measurement and replication, append to the
  experiment ledger, re-render `docs/what_we_can_and_cannot_claim.md` from the
  run record rather than by hand.
- Shrink guards and cache-staleness checks on every input, because in this
  sport a partial fetch looks exactly like a light slate.
- Every recurring failure mode gets a monitor, not a habit of me noticing.

**Self-improving** must not mean "search until something looks good." An
automated edge-hunter without a cumulative tally does not find edges; it
manufactures them on a schedule, with clean intervals and good prose. Read
`experiment_ledger.py`'s docstring in the football lab and port it first, then:

- **A declared alpha budget.** N new hypotheses per week, written down in
  advance with a predicted *direction* for each. The ledger is append-only and
  its correction factor grows with the cumulative count — the fiftieth test
  does not get the first test's benefit of the doubt. When the budget is spent,
  the search waits. It never lowers the bar.
- **Discovery and holdout are separated in advance**, and the holdout is not
  looked at until discovery is closed.
- **Champion/challenger with pre-registered promotion.** A challenger may
  replace the champion only by beating it on the price backtest, out of sample,
  by a margin declared before the comparison, with the ledger's correction
  applied. Every promotion is recorded as a verdict on disk with the experiment
  that justified it — never asserted in code.
- **Automatic demotion, one direction only.** An allowlisted market whose
  forward ROI interval falls below the floor declared at approval is
  **auto-withdrawn**. Granting an allowlist always requires a receipt I sign.
  The machine may take a market away from itself, never give itself one.
- **The loop must be able to conclude "no edge" and stop.** A search that can
  only terminate in a finding is a random number generator with good prose.
  Write `docs/when_this_ends.md` — the NHL lab has one — before the first
  measurement, declaring what result would end this project. Then honour it.

## Measurement discipline — the part I care most about

Port everything from the siblings, and treat these five as mandatory from the
first commit, because each one is a defect already paid for:

1. **Dedupe prices on price identity, never on the whole row.** The NHL store
   deduped on rows including timestamps, so every price was written twice;
   ROI was unchanged but every interval was √2 too narrow. **A duplicated store
   does not look wrong — it looks significant.** Regression test on day one.
2. **The headline must read the sign.** The NHL lab's summary triggered "at
   least one result survived and replicated" on a market that had replicated a
   *loss*. Regression test on day one.
3. **Regress outcome on market-implied vs model-implied probability, every
   week, and print it.** The NHL lab's coefficients were market 0.97, model
   0.03 [−0.037, +0.102] — the model added nothing and its claimed edge was
   anti-predictive, bigger claimed edge being worse. This single test is the
   fastest honest read on whether anything here is real.
4. **Calibrate on the bets you selected, not just overall.** The NHL model was
   calibrated across the board and overconfident by 9–12pp on precisely what it
   picked — the winner's curse. Overall calibration is not evidence.
5. **Cluster intervals by game and by day.** One game supplies many correlated
   bets; a 100-game slate is not 400 independent observations.

Plus the standing rules:

- **Walk-forward only.** A model is priced only on games strictly earlier than
  the one being scored.
- **The price backtest decides.** Calibration can rule a model out, never in.
- **Family-wise correction** across every market and segment tested, reported
  beside the raw figure, using the ledger's cumulative count and not the day's.
- **Replication on a held-out season** before any claim survives.
- **Minimum sample thresholds per market, declared in advance**, below which
  the verdict is "not enough evidence" — not a number.
- **"Conditioned on what, known when?"** on every adjustment. The NHL lab found
  a correction worth +162.8u on *actual* ice time that lost −37.6u on
  *expected* ice time — the only version a card can use. Hindsight leaks look
  exactly like edges.
- **CLV is a fast instrument, ROI is the verdict.** Track the closing price for
  every frozen opinion and report CLV per market beside ROI. My priority is
  profit and ROI, not CLV — a winning record with negative CLV is variance and
  the report must say that in those words, and a positive-CLV record that loses
  money is still losing money.
- **Sample size beside every number.** An interval including zero is reported as
  **"no demonstrated edge"**, in those words.

## Cost — standing authorization, no stop

The Odds API bills per market per event, and the quota is shared with the NHL
and football labs — same account, same key pool. **Credits are not a
constraint and I do not want to be asked about them.**

**You are authorized, without asking, to spend up to 1,500,000 credits per
calendar month** across probing, historical purchase and live fetching for this
lab — provided you first confirm the actual monthly allowance and remaining
balance from the response headers, and scale that ceiling down if the real
quota will not carry it alongside the NHL and football labs' committed spend.
Leave enough headroom that no live in-season fetch can ever be starved. If the
full catalogue needs more than the ceiling, buy in priority order — core team
markets across every season first, then ladders, then props, then futures — and
continue next month rather than stopping.

Before building the fetch, compute the real season cost from the actual
schedule and put the arithmetic in `docs/credit_cost.md`: games per day across
the season's shape, markets asked per tier, credits per peak day, credits per
season at one/two/N snapshots per day, plus the sibling labs' committed spend,
against the quota. Then:

- Set caps that **cannot starve a slate**, and read the real rate from the
  response headers as it is spent rather than trusting the documentation.
- **A starved fetch and an unquoted market look identical.** Never let the
  reports confuse them — the NHL lab's probe once reported its own starvation
  as market absence.
- **Tier the fetch**: core team markets on every D-I game; ladders, props and
  futures only where they are actually quoted, established by an in-season
  probe rather than assumed.
- **Probe retention before buying history.** The football lab's probe cost
  7,280 credits and answered which markets have historical prices *and enough
  of them to measure against* — those are different questions. Follow its two
  hard-won rules: roll every retention conclusion up to the market rather than
  the provider key, and make the probe's report re-renderable from the run
  record so improving its wording never costs credits twice.
- Then **buy the history and run the backtest**. This is the point of the
  runway. Do not defer it, do not sample it, and do not stop to tell me the
  number first — put the number in `docs/credit_cost.md` and keep going.

## Delivery — how the card reaches me

I want the card pulled from the model in Claude Code and delivered to me in a
scheduled task in **regular Claude**. That chain exists and works for the EPL
lab; port it, including its scars:

1. **`card-feed` branch.** Every refresh run publishes `latest_card_comment.md`
   and `latest_status.json` (`date`, `degraded`, `trigger`, `run_url`) to
   `refs/heads/card-feed` via plumbing commits. Discipline tests pin every
   `git push` in the workflow to that ref and pin `contents: write` to that one
   workflow. It is an orphan branch, so reaching it needs
   `git fetch origin card-feed` + `git show FETCH_HEAD:<file>`.
2. **A bad run must not clobber a good card.** The publish step is
   `if: always()` and last-write-wins, so port the EPL guard: skip publishing
   when all three hold — same `date` at the tip, tip `degraded` is `"false"`,
   and this run's degraded is not `"false"` (`"unknown"` counts as degraded).
   Keep the "no commit for today means the run did not finish" case working.
   Verify this against a real git ref across every case; string assertions
   about shell logic in a workflow file are near-worthless.
3. **A Claude Code cloud routine relays the feed into Google Drive**, writing
   one dated file per run (`CBB Card <date>`) whose content is the status line
   plus the card verbatim. It summarises nothing and sends nothing. Note the
   connector's `update_file` changes title and parent only, **not content** —
   so create a new dated file each run rather than trying to update one.
   Create and verify this routine yourself with the `schedule` skill and
   `RemoteTrigger`; run `RemoteTrigger list` first whenever a routine
   misbehaves.
4. **My chat-side scheduled task reads the newest Drive file and presents the
   card.** Chat-side tasks cannot be created from Claude Code and cannot clone
   a private repo — establish what the reader can actually access before
   designing anything, then hand me one paste-ready prompt and the exact time
   to set, in the final report. That is the one setup step I will do, and it is
   one paste.
5. **Zero email.** Remove the `@cooperross399` mention from the card comment
   *and* set the repo subscription ignored — a mention overrides an ignored
   subscription, so one without the other does nothing.
6. **Do not trust the nominal cron time.** GitHub has been firing my repos'
   crons 4.5–5.3 hours late since 2026-08-27. Check every deadline against
   `nominal + OBSERVED_LATENESS_H`, add early trigger pairs where one trigger
   cannot hold both the relay deadline and a freshness requirement, and test
   the observed lateness rather than only the schedule.
7. **This sport needs more than one card a day.** A noon tip and an 11pm tip
   cannot share one freeze. Design the card cadence around the slate's actual
   shape — a morning full-slate card and at least one afternoon refresh for the
   evening games — with each opinion frozen against the games it can still
   precede, and the first opinion of the day for any given game never
   retroactively replaced.
8. **Verify the whole chain end to end with a real card before calling the
   build done.** A green workflow run is not a delivered card; the EPL lab
   spent five days green and empty. Read the card that lands in Drive.

## Honesty rules — these are absolute

- Never fabricate a price, a line, an injury, a lineup, a venue or a player's
  status. A missing price stays missing.
- Never place a bet. Nothing here is ever wired to a sportsbook.
- No market reaches the card without measurement against real prices **and** a
  reviewed human acceptance receipt. Prepare the evidence and stop there — that
  is the single stop.
- An excluded market is never reported as a pass, an avoid, or a no-value call.
  A blocked card yields no selections and says why.
- Sample sizes beside every number; intervals including zero are "no
  demonstrated edge".
- Check per-bookmaker and alternate-line coverage before concluding a market
  "isn't offered".
- **Never print, write, compare, or commit an API key.** Secrets are GitHub
  secrets; `.env` is local-only and gitignored; port the secrets test — and
  port the football lab's refinement, that an exemption for key-shaped strings
  is by recorded value, never by directory.
- **Never merge with failing CI, never force-push, never weaken a gate, and
  never sign an acceptance receipt on my behalf.** If a policy gate goes red
  because evidence moved, leave it red and say so in the final report.
- Report the answer you got, not the answer you wanted. Two of these labs have
  measured no edge and both of those are correct outcomes. A full-build
  instruction is an instruction about effort, never about the result.

## How you work

Autonomously and continuously: data, models, measurement, reports, tests,
workflows, docs, and PRs with green CI, until the Definition of Done is met.
Adversarially review your own work before calling any part of it done —
reproduce every defect before fixing it, and add a regression test for each.
Prefer a defensible decision recorded in `docs/decision_log.md` over a question
to me, in every case except the single stop.

Python 3.12 (`/opt/homebrew/opt/python@3.12/bin/python3.12`). Keep a
`CLAUDE.md` with a "Current operating state" section that a future session can
read as project memory, and pin its contract strings with tests. Commit
frequently and push, so the work survives a session ending.

## Start here

1. Read the three sibling labs end to end. Then write
   `docs/what_we_can_and_cannot_claim.md` and `docs/when_this_ends.md`
   **before** the first measurement, so every number lands in a place that
   already knows how to read it and the project knows in advance what would
   end it.
2. Port the experiment ledger and the verdicts door, before any model exists,
   so the first hypothesis this lab ever tests is already counted.
3. Investigate and document the D-I men's basketball data sources, including
   licence terms, revision behaviour and in-season latency. Establish which
   markets can actually **settle** from what you find.
4. Compute the season credit cost from the real schedule into
   `docs/credit_cost.md`, probe retention, then buy the history.
5. Build the rest, straight through, to the Definition of Done. Then report:
   what was built, what the measurement says, what is waiting on my signature,
   and the one prompt for me to paste into a chat-side task.
