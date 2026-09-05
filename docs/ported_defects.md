# Every defect inherited from a sibling lab, and the test here that pins it

**This is the fourth lab.** The football lab's `CLAUDE.md` states the cost
plainly: these repositories share no code, the same defect classes appeared
independently in each, and six NHL fixes were hand-ported into football on
2026-08-31. A fourth lab means a fourth hand-port.

**The sibling labs are not touched.** Not to refactor, not to extract shared
code, not to fix a defect noticed there. That prohibition is absolute. They hold
measured numbers that cannot be rebought, and one of the entries below is a live
defect in a sibling that is recorded here and deliberately left alone.

The list is kept so the port is **auditable** rather than assumed. If it grows
long enough that extraction into a shared package is obviously worth it, the
arithmetic goes in the final report as a recommendation and nothing is acted on.

---

## Inherited and closed before they could happen here

| # | Defect | Came from | What it cost there | Test here |
|---:|:---|:---|:---|:---|
| 1 | **Deduping a price store on the whole row, timestamps included** | NHL | Every quote written twice. ROI unchanged, every interval **√2 too narrow**. Its first "clean" run reported 144,060 bets and nothing looked wrong. | `test_prices_dedupe_on_identity_not_the_row.py` — and `PRICE_IDENTITY` carries no timestamp, asserted as a property |
| 2 | **Counting every book's quote as an independent bet** | NHL | 2.83 quotes per selection, so intervals √2.83 too narrow. Per quote, its full store said all three team markets were **demonstrated losses**; per wager, all three span zero. | same file — `best_price_per_wager` collapses to one bet at the best price |
| 3 | **A headline that never read the sign** | NHL | `what_we_can_claim` announced *"at least one result survived the correction and then replicated"* on a market returning **−6.6%**. | `test_the_headline_reads_the_sign.py` — `RoiInterval.verdict()` returns `demonstrated deficit`, never `edge` |
| 4 | **UTC dates meeting league game dates in a join** | NHL | **69% of every bought price silently discarded**, and the survivors were systematically the afternoon games. | `test_slate_day_and_season_match_the_source.py` — checked against ESPN's own filed date over 6,318 games |
| 5 | **Two hand-built copies of a join key** (five-member bug family: provider names vs abbreviations, `home -1.5` vs `home_minus`, outcomes staged in the provider's vocabulary, a CSV round-trip turning an empty player into the string `"nan"`) | NHL | Weeks. Each failure was silent. | one `selection.selection_key`, called by both sides of every join; `season.clean_text` is the only reader of CSV-borne text |
| 6 | **Yes/no markets staged under two spellings** (the anytime-scorer bug) | NHL | One wager staked twice, published as two independent best bets at two prices, frozen into the ledger twice. | `selection.yes_no_selection` maps Yes→`over`, No→`under`; `double_double`, `triple_double` and `first_basket` all go through it |
| 7 | **A credit cap estimated from markets *asked* rather than markets *returned*** | NHL | A run capped at 200,000 spent **289,984**, while the code and its test both asserted the cap "cannot be breached". | `test_the_credit_cap_holds_the_worst_slate.py`; the cap is enforced against the measured running total from `x-requests-last` |
| 8 | **A cache filename tagged with a chunk's *length*** | football | Four ten-market chunks collided and three were lost. The NHL lab's `_markets_fingerprint` existed for exactly this and was not ported. | `odds_api.markets_fingerprint`, and the probe's own collision test |
| 9 | **A secrets guard exempting a *directory* rather than a *value*** | football | 32-hex event ids are the same shape as an API key. Exempting `data/raw/` would carve a hole exactly where provider data lands. | `test_no_secrets_committed.py::test_the_event_id_exemption_is_by_value_and_not_by_directory` |
| 10 | **A `\s*` in a credential-assignment regex** | football | `\s` crosses a newline, so `NAME=` on one line and any word on the next read as an assignment — which is what `.env.example` looks like, and the guard failed on a file whose values are all empty. | `ASSIGNMENT` uses `[ \t]*`, with the reason in the source |
| 11 | **A verdict decided by whichever season ran last** | football | +2.3% on 2025 shipped a policy; −1.8% on 2023 did not. Same policy, same script, opposite verdicts, and the card read whichever ran most recently. | `verdicts.read` returns `ships=False` unless `seasons_cleared ⊇ seasons_tested` |
| 12 | **A pre-registered hypothesis with no predicted direction** | football | Three of twelve slots spent on cuts that could only ever be exploratory. | `experiment_ledger.Hypothesis` raises `DirectionRequired` |
| 13 | **A walk-forward leak from a distribution loaded once outside the loop** | football | The per-play yardage distribution used to price 2023 had seen 2025. **Only the compound markets consumed it, which is precisely why the compound group looked good.** | `test_fit_ratings.py::test_corrupting_every_game_after_a_cut_leaves_the_earlier_fits_identical` (this cell used to name `test_ratings_are_walk_forward.py`, which never existed) `.py` corrupts every later game and asserts the fit is byte-identical |
| 14 | **A segment that hardcoded the full-game tie rule** | football | A first half priced level at 0.4% when **7.4% of NFL first halves actually end level**. | segments carry `resolves_ties`; measured here at **3.54% of 90,766 college first halves**, with full games at **0.000%** |
| 15 | **A missing column read as a zero by `getattr(..., None)`** | football | A backtest reported zero bets, which read as "the model never disagrees enough". The price columns had never been built. | a missing settlement column raises; `stores.read_store(for_append=True)` raises rather than returning empty |
| 16 | **`git show X > file` creating a zero-byte file when the show fails** | football | pandas refuses a zero-byte CSV. It killed the first rehearsal on exactly the branch state the first real run would have had. | every restore is temp-then-move; every CSV read is defensive |
| 17 | **A publish step under `if: always()` clobbering a good card** | EPL | A late-firing trigger landed past the deadline and, firing last, replaced the day's card with a blocked one. | the publish-level clobber guard, verified against a **real git ref** across all six cases — string assertions about shell logic are near-worthless |
| 18 | **An unauthenticated fetch making a guard fail open** | football | On a private repo it read "no card-feed branch yet", the backup trigger never stood down, and every game day fetched the slate twice and posted the card twice. | the already-published guard authenticates, and a test asserts it can |
| 19 | **An `@mention` overriding an ignored repository subscription** | EPL | Emails continued after the subscription was set to ignored, because the card comment still mentioned him. Two changes are needed, not one. | the card comment mentions nobody, and a test asserts it |
| 20 | **A hardcoded fixture window** | EPL | Correct for one week. After that every provider price fell outside it, every market read `unavailable`, and **every card came back Blocked while the fetch, the mapping and the completeness checks all passed.** A green run with no card is the signature. | the slate is derived from the fixtures in hand, never written down |
| 21 | **Concluding a market "isn't offered" from one market key** | EPL | `total_2_5` was excluded for a season. The complete line was absent from the bulk `totals` market and present all along in `alternate_totals`. | every retention conclusion rolls up to the **market**, never the provider key |

---

## Found in a sibling during this build, recorded and deliberately not fixed there

### The football lab's forward-ledger interval is about ten times too narrow

`football-betting-lab/src/football_betting_lab/forward_evidence.py`,
`interval_by_game`. It computes

    variance = Σ(wᵢ² · s² / G) · G ;  standard_error = √(variance / G)

which is algebraically `s·√(Σwᵢ²)/√G`; with roughly equal clusters `Σwᵢ² ≈ 1/G`,
so it lands at **`s/G` where a cluster standard error is `s/√G`**.

**Reproduced independently before it was reported.** On 632 synthetic bets over
200 clusters: the ratio estimator gives 0.03694, a cluster bootstrap over whole
games gives 0.03683, and that formula gives **0.00356 — 10.3× too narrow.**

It is on the one report in that lab which grows all season, and whose own
docstring says *"a narrow interval is how 'no demonstrated edge' quietly becomes
a claim."* Its sibling function in the same repository — `props_backtest._interval`
— is the correct ratio estimator, so the two disagree by a factor of ten inside
one codebase.

**Not fixed there**, per Cooper's absolute instruction. Fixed here in
`stats.interval_by_cluster`, with the defective formula reproduced verbatim in
`tests/test_clustered_interval_is_not_too_narrow.py` so it cannot come back.

**Worth Cooper's attention**: the football lab's forward ledger begins
accumulating from 2026-09-09, and every interval it reports until this is fixed
will be about ten times too tight. It has not yet produced a published number,
so nothing measured is invalidated — but the first one it produces would be.

---

## Defects original to this lab, found by disbelieving a number

Not inherited, but recorded in the same place because the next lab will inherit
*them*.

| # | Defect | How it was found | Test |
|---:|:---|:---|:---|
| A | **A made free throw counted as a made field goal.** ESPN's play type is `MadeFreeThrow` — one word — so `str.contains("Free Throw")` matches **none** of 253,589 free-throw rows in a season. | The possession validation the brief demanded returned an obviously wrong number (estimator 138.9 against a count of 153.9). | `test_free_throws_are_not_baskets.py` |
| A′ | The same defect would have settled **`player_first_basket` on whoever made the game's first free throw** — a plausible name, a real player, a wrong bet, and nothing would have looked broken. | Only visible because the possession check failed loudly first. | same file |
| B | **A season labelled by its starting year.** hoopR labels a season by the year it **ends**; this lab briefly did the opposite, which would have made every `season == 2027` filter miss every `season == 2027` row. | Verified against the real parquet rather than assumed. | `test_slate_day_and_season_match_the_source.py` |
| C | **A six-hour "basketball day" boundary**, reasoned by analogy with hockey. Measured against ESPN's own filed date over 6,318 games: **0 disagreements at midnight, 1 at six hours.** No D-I game tips between midnight and 08:00 ET, so the boundary protected nothing and broke the one Hawai'i game. | Measured rather than argued. | same file, plus a test for the Hawai'i game specifically |
| D | **A gate test that banned a word instead of an assertion.** It failed on the note that says *"this is not a pass, an avoid or a no-value call"* — the required phrasing. | The test failed on correct code. | `test_gates_fail_closed.py` now strips negated clauses first |
| E | **`player_first_team_basket` settleable for only one side.** `cbb_game_segments.csv` stored the *game's* first basket and nothing about each team's, so the market graded for whichever side scored first — measured at **exactly 50.03% of played rows**. | The settlement agent measured the coverage and reported the denominator instead of quoting a record on half a market. | `test_settlement_settles_real_games.py::test_the_first_team_basket_settles_for_BOTH_teams` — now 100.00% |

**Defect E is the one worth reading twice.** A market that settles for half its
rows produces a *record*, and a record with no denominator beside it looks
exactly like a market with thin book coverage. Nothing errored, nothing was
wrong, and the number would have been half a market reported as a market. It was
caught only because the settlement work measured its own coverage and printed
the denominator — which is the house rule that "a number without a sample size
is not a result", applied to settlement rather than to returns.

| F | **A CSV round-trip broke a dedupe key, so every re-run wrote every quote twice.** `stores.append` deduped on a key including `player`; an empty player is written as `""` and read back as `NaN`, so the row already on disk and the identical row about to be written compared **unequal**. Any retried or re-dispatched capture doubled the store. | A line-movement test that appended the same capture twice and asserted the row count did not move. Not by review — the code reads correctly. | `test_prices_dedupe_on_identity_not_the_row.py::test_a_csv_round_trip_cannot_break_the_dedupe_key` |

**Defect F is the fifth member of the NHL lab's join-vocabulary family arriving
in a sixth place.** That lab listed it as *"a CSV round-trip turning empty
players into the string `nan` on one side of a hand-built key"*, and this
repository was built with `selection_key()` precisely so it could not recur —
which it did not, in the joins. It recurred in the **store**, where a key is
also built and where nobody had thought to look, and the symptom is the one the
NHL lab named exactly: **a duplicated store does not look wrong, it looks
significant.** ROI would have been unchanged and every interval root-two too
narrow.

The fix normalises the key on both sides before comparing — NaN, `None`, `""`
and the literal string `"nan"` are one absent value, and `3`, `3.0` and
`"3.00"` are one line — and normalises **only the key**, never the stored data.
The lesson for the next lab is that "one function builds every join key" has to
include the keys that are not called joins.

| G | **The provider's team names did not resolve for a fifth of Division I**, and the failures were concentrated exactly where this lab's thesis lives. `_EXPANSIONS` mapped `st -> saint` unconditionally, so `Michigan St` normalised to `michigan saint` and matched nothing; a further 27 schools are simply called something else (`Fort Wayne Mastodons`, `Grand Canyon Antelopes`, `UMKC Kangaroos`). **75 of 365 provider names (20.5%) resolved to nothing**, and the per-tier match rate over 144 sampled games was high-major 86.8%, mid-major 76.1%, **low-major 46.7%**. | The retention probe reported 42 of 144 sampled games unmatched and named them. The probe's own cached slate listings then answered whether the schools were absent or merely misspelt — 365 provider names against 365 D-I teams, so nothing was absent. | `test_every_provider_team_name_resolves.py` — all 365, on every run |

**Defect G is member one of the NHL lab's join-vocabulary family — "provider
team names vs league abbreviations" — and it is the most expensive one this lab
has found.** Not because it was hard to fix, but because of *which* rows it
dropped. A join that fails uniformly is a smaller sample. A join that fails on
53% of low-major games and 13% of high-major ones is a **biased** sample, and
the bias runs directly against the hypothesis the lab exists to test: Cooper's
case for a fourth lab is that *"the low-major end of the board is priced with
far less attention"*. Measuring that on a population that had silently lost half
its low-major games would have produced a number, an interval, and a wrong
answer — with nothing anywhere indicating that a fifth of the vocabulary was
unreadable.

It was also nearly bought. The purchase was one dispatch away, and it would have
paid for events whose prices no join could ever have found — the precise thing
the brief warns about: *"Fetching prices nothing can consume spends credits on
rows no join will ever find."*

The fix is `variants()`: an ambiguous token expands into **every** reading and
`resolve()` refuses when the readings name different schools. `Michigan St`
yields both `michigan state` and `michigan saint`, and only one is a school.
The alternative — a rule deciding by position, or a list of which schools are
"State" schools — is right most of the time, and the times it is wrong settle a
bet against the wrong game without erroring.

| H | **An unreadable snapshot is settled as a day with no opinions, and the day is then marked done.** `forward_evidence.read_snapshot` reads through `stores.read_store` *without* `for_append`, so a snapshot pandas cannot parse comes back as an **empty frame**. `settle_snapshots` then grades zero rows, writes the `.settled` sidecar and moves on: a night of frozen opinions is recorded as a night with nothing in it, and the prices they were frozen at are gone. **Closed on adversarial review.** `settle_snapshots` now reads through `read_snapshot_strictly` and an unparseable snapshot is counted, named and **skipped** — no grading, no sidecar, the day left open. | Reproduced by putting a zero-byte CSV beside a good snapshot and running `scripts/run_forward_evidence.py --settle`: the good day settled its rows against real 2026 box scores and the broken day was marked settled with a note reading `0 rows`. Re-run after the fix over the same real archive: the broken day is left unmarked, and when the file is restored its **32 real opinions settle in full**. | `test_run_forward_evidence.py::test_an_unreadable_snapshot_is_not_marked_settled_and_still_grades_once_repaired` — both halves: no sidecar for the broken day, and the night grading in full on the pass after the file comes back. |

**Defect H is defect 16 arriving one layer higher up.** The football lab's
zero-byte `git show` artifact is already on the inherited list, and the gameday
workflow's restore step already carries the temp-then-move guard that stops one
reaching the archive. This is the same file shape reaching the *settle* pass
instead, where the defensive read that is right for a renderer is wrong for a
recorder: the module cannot tell "this day held no opinions" from "this day's
file is broken", and only one of those may be marked done.

The fix is in `forward_evidence.py` rather than in the script, and it is the one
the original report proposed: `read_snapshot` stays lenient for renderers, and
the settle pass reads through a second entry point, `read_snapshot_strictly`,
which raises. A snapshot it cannot parse is counted into
`SettlementResult.snapshots_unreadable`, named in `unreadable_days`, and skipped
— never graded and never marked.

**The marker was the damage, not the empty frame.** A day left unmarked still
grades when the file is restored from `card-feed` or repaired by hand; a day
marked done never will be, and the prices it was frozen at are gone. So the run
still stays green — a permanent red would keep the gameday backup trigger from
ever standing down and spend a second slate's credits every day — but the night
is now recoverable rather than closed at zero.

| I | **A waiting day counted rows it threw away.** `settle_snapshots` grades a snapshot's rows in order and breaks at the first whose result is not published, then discards the day — but every row graded before the break had already incremented `rows_settled`. The ledger was always correct and the day always waited atomically; what was wrong was the **accounting identity the workflow prints**, and the same rows were counted again on the pass that finally settled the day. | The one reconciliation line that is not arithmetic over the counters themselves — rows graded against what the ledger file actually grew by. | `test_run_forward_evidence.py::test_a_waiting_day_counts_nothing_it_threw_away` |

**Defect I is what the accounting identity is for.** It is not a data defect —
nothing is lost, nothing is double-written, and the ledger is exactly right —
which is precisely why nothing else would ever have noticed it. It was visible
only because the reconciliation carries one line that is **not** arithmetic on
the counters themselves: what the pass says it graded, against what the file on
disk actually grew by. Every other line in that block can only catch a counter
that was never incremented.

The same signature belongs to a genuine catastrophe — a pass that grades a whole
night and writes none of it — so the gap is printed and explained rather than
subtracted out. The fix belongs in `forward_evidence.py`, most plausibly by
deciding whether the day waits before any of its rows are graded, or by grading
into a provisional result that is only merged when the day is appended.

| J | **An accounting identity whose two sides were computed from each other.** The settle pass printed `settled + void + unsettleable = rows seen` and failed the run when it did not hold — but `SettlementResult.rows_seen` is a **property** returning exactly that sum, so the line was a tautology. It held for every pass that could ever run, including one that graded four hundred opinions and counted none of them, which is the failure it was printed to catch. **Closed on adversarial review.** | Found by reading the identity rather than the output. Confirmed by constructing a `Reconciliation` from a result whose counters were all zero after a full night was graded: it reported **HOLDS**. | `test_run_forward_evidence.py::test_a_graded_row_that_reaches_no_counter_fails_the_rows_identity` — `_record_outcome` is replaced with one that grades the row and increments nothing, which is what a new branch added without its counter would do. The run exits 1. |
| K | **`read_store(for_append=True)` failed OPEN on a file that parsed into garbage.** The strict read exists so a caller about to append to, or judge on, a damaged file refuses rather than reading it as empty. It caught unparseable files and missed files that parse: `b"\x00\x01 not,a,csv\n\x00"` comes back from `pd.read_csv` as one row under a bogus header, and the reader then PADDED the absent columns with NA — handing back something shaped exactly like this lab's ledger. Downstream, the auto-demotion gate read a corrupt forward ledger, found no measurable bets, and reported that no allowlisted market had fallen through its floor. | NHL/football lab family: a lenient read standing in for a strict one. | `test_weekly_loop.py::test_an_unreadable_forward_ledger_never_withdraws_and_never_passes`, plus the schema check in `stores.read_store` |
| L | **The historical purchase persisted nothing, three ways at once.** The `actions/cache` path and the artifact path were both hand-spelled as `data/raw/cbb/historical_${window}` while `historical.cache_dir_for` returns `data/raw/cbb/historical_purchase/${window}`; and the live buy never writes the store at all, because the processed CSV is derived by `--rebuild`, which the workflow never ran. A run spent **1,299,945 credits**, bought **1.82M price rows**, reported them, and left a 22KB artifact holding only its own report. The responses survived by luck — a sibling cache happens to cover the whole of `data/raw/cbb`. | New here. The nearest sibling is the football lab's probe caching chunks under a filename tagged with the chunk's *length*. | `test_workflows.py::test_the_purchase_workflow_names_the_directory_the_module_actually_writes` (derives the path from the module rather than restating it) and `::test_the_purchase_workflow_builds_the_store_it_uploads` |
| M | **The ratings fit was singular on three seasons of four.** The four venue columns were the only unregularised columns in the design, so a season with no quasi-neutral game carrying a local team left two of them structurally zero. Compounding it, `matchups_for` supplied only the PRICED season's schedule, while the prior is fitted on strictly earlier seasons — which is what emptied the columns. Raised `LinAlgError` the first time it was ever asked to price a real multi-season history; every existing test fitted one season with that season's schedule in hand, the one arrangement in which it cannot appear. | New here. | `test_ratings_fit_is_well_posed.py` (7 tests) |
| N | **Three more word-ban tests, bringing the count to six.** `'grant('` matched a docstring saying there is no `grant()`; `'contents: write'` matched a comment naming the workflows allowed to hold it; and the claims-doc test banned a filename, which satisfied the pre-registration requirement and made the re-rendering requirement impossible. All three now ask the syntax tree, the parsed YAML, or the behaviour. | The house rule in `docs/build_order.md` predicted this and was written *before* three of the six. | `test_weekly_loop.py::test_nothing_in_the_loop_grants_an_allowlist`, `::test_the_weekly_workflow_holds_no_write_access_and_no_credential`, `::test_the_loop_re_renders_the_claims_doc_without_destroying_its_framing` |

**Defect J is the reason defect I was worth printing.** An identity is only
worth the independence of its two sides. `settle_snapshots` now counts
`rows_read` off the snapshot files before a single row is graded, and the rows
line is checked against **that** — a number no outcome counter can influence.
The inequality runs one way only: `rows_seen < rows_read` is the legitimate
signature of defect I, a day that waited part-way through, so it is explained;
`rows_seen > rows_read`, or any shortfall on a pass where nothing waited, is a
frozen opinion that reached no count, and the run exits non-zero.

The general rule, and the one the next lab will need: **a reconciliation line
whose right-hand side is derived from its left-hand side is decoration, and
decoration inside an accounting block is worse than no line at all — a reader
trusts it.** Every identity here now names where its other side came from: the
files on disk, or the length of the ledger.

**Defect I was first shipped as an explanation and is now a fix, and the
difference matters.** The agent that found it printed the gap on its own line
and pinned the wording with a test, on the reasoning that a pass which graded a
whole night and wrote none of it has the identical signature. That reasoning is
right about the *signature* and wrong about the *remedy*: **the accounting
identity is the instrument that catches rows going missing, and an identity
carrying a standing exemption cannot catch anything.** The counters are now
snapshotted before a day is graded and restored when it turns out to be
waiting, so the identity holds with no exemption — and the case the explanation
was protecting (a night graded and written nowhere) now shows up as the
anomaly it is.

| O | **An absent experiment ledger reported as a family of one.** `looks_from_ledger` returns `max(count, 1)`, so a missing file and a one-entry file are the same integer, and the renderer stated it as fact about a file it had never opened. A correction of x1.00 widens nothing, so a missing ledger makes every result look **more** significant than it is. | New here. Nearest sibling: the NHL lab's headline that announced a replicated loss as good news. | `test_the_headline_reads_the_sign.py::test_an_absent_ledger_is_never_reported_as_a_family_of_one` |
| P | **The weekly loop could never finish its own measurement.** Unbounded, the price backtest scores every season in the store — a measured **eight hours** against a 240-minute job timeout and GitHub's six-hour ceiling. It would have been killed every Monday and reported degraded for ever, which looks exactly like a lab that is running. | New here, and specific to a sport with 1.8M bought quotes. | `test_weekly_loop.py::test_the_weekly_backtest_is_bounded_to_a_season` |
| Q | **A pooled verdict no tier shared.** The pooled disagreement coefficient read `demonstrated edge` while every tier read `no demonstrated edge`: three intervals each spanning zero pooled into one that does not, because the sample triples while the estimate barely moves. Arithmetic, not a discovery — and it put this repository's strongest reserved phrase in the one cell the brief says is never the headline. | The brief's rule 9, arriving by a door nobody had watched. | `test_the_headline_reads_the_sign.py::test_a_pooled_verdict_no_tier_shares_is_flagged_where_it_happens` |
| R | **A card test that only failed at night.** The fixture built tips at `now + 3..8h`; run at 20:45 ET the later ones land after midnight, which `slate_date` correctly files under tomorrow. The card reported them off-slate and froze nothing — **the card was right** — but it read as a regression, and the suite passed all afternoon and failed after dark. | New here. The nearest sibling is the NHL lab's UTC-vs-league-date defect, which discarded 69% of bought prices. | `test_the_card_runs_end_to_end_offline.py` (simultaneous tips at `now+65min`, with the boundary window skipped and its reason stated) |

**Four refusals earned their keep on 2026-09-04**, and none of them was a
defect in the thing that refused:

1. `forecast_skill` **would not de-vig without a `book` column**, because
   pooling every row into one nameless book pairs quotes across books and
   understates the hold, sometimes to nothing.
2. It **would not de-vig a one-sided quote** — a fair price needs both sides of
   the wager, and the complement is the only pair with a hold in it.
3. `replication` **would not replicate on a season inside the discovery
   window**, because re-scoring a rule on the data it was chosen on reproduces
   the selection rather than the effect, with a tighter interval each time the
   sample grows.
4. The **relay declined to copy the card to Drive** on a prompt that told it to
   override a stated guard, not notify Cooper, and move private data to an
   external service. The payload was genuine; the prompt was shaped exactly
   like an injection, and a relay that complied with it would comply with a
   real one.

A lab whose instruments only ever say yes is a lab with no instruments.
| S | **1,199,926 credits of responses lost, because persistence sat after a step that could die.** Purchase run 33917619764 bought the ladders-and-halves wave, then the store rebuild was OOM-killed on the 7GB runner (`The operation was canceled`, two minutes in). Every step after it — the raw-response artifact upload and both `actions/cache` saves — was skipped, so nothing from the run was persisted anywhere. The responses were the purchase; the store is derived from them for free; the cheap thing was ordered before the expensive one. | Defect L again, by a different door: L was a wrong path, S is a wrong order. | `test_workflows.py::test_the_purchase_uploads_raw_responses_before_anything_can_die` |
| T | **A whole wave staged as Python dicts exhausts a runner.** `rebuild_from_cache` accumulated every row of the plan in one list — 4,811,004 dicts for the lost wave — then `append_prices` copied it into a DataFrame and concatenated the existing store. Peak memory is now one wave-season, streamed and appended before the next is read. | New here; the sibling labs' purchases were an order of magnitude smaller. | `test_historical_rebuild_streams_per_segment.py` |
| U | **The store rebuild was scoped to the run's own wave and appended onto a stale store.** Each run rebuilt only its wave and appended to whatever `data/processed` the cache restored — a snapshot that only re-saves when the code hash changes. So after buying props the store held the original 4-season core team plus props and **nothing from the two waves bought in between**: it "shrank" from 2,946,929 rows to 2,326,236 while the raw cache held everything. Rebuild now derives from every wave's cache, from scratch. | The NHL lab's "CI state artifact restores the previous run's samples forever." | `test_historical_rebuild_streams_per_segment.py::test_a_rebuild_starts_from_nothing` |
| V | **Two experiment ledgers.** A tracked copy under `data/outputs/holdout/` — made so a holdout replication could read a correction beside its own outputs — was where `run_replication` then *appended its holdout looks*, while `run_price_backtest` read its correction from the original. Identical only because the one replication so far recorded zero looks; the first real holdout look would have left the next backtest's correction short by exactly that look. Both scripts now default `--ledger` to the repository's one ledger regardless of `--output-dir`; the copy is gone; the guard and #6's test name one file. | The ledger's own docstring: *a ledger that can shrink reports a correction smaller than the truth.* A ledger that can fork does the same. | `tests/test_one_ledger.py` |
| W | **Defect J again, in the frame builder's own census, four commits after defect J was written up.** `build_skill_frame.build` set `paired = len(graded) - len(excluded)`, so `supplied = paired + unpairable` reconciled for any two frames whatever — the identity printed to catch a graded row reaching neither bucket could not have caught one. It also folded the rows with no pair key into `paired`, counting a row as having found a complement it never looked for. Both terms are now counted off the frame, the keyless rows are a third term, and `main` compares the census's `supplied` against the rows it read from the CSV — the one comparison here with two real sides. **Closed on adversarial review, before the census had ever run on real data.** | Defect J, this repository. The write-up says a reconciliation line whose right-hand side is derived from its left-hand side is decoration; this line was written the week after, by copying the *shape* of `OpinionAccounting`'s identity rather than its rule. | `test_build_skill_frame.py::test_every_census_term_is_counted_off_the_frame_and_none_is_a_residual`, `::test_a_row_that_reached_no_bucket_makes_the_identity_fail_rather_than_absorb`, `::test_main_refuses_a_census_that_does_not_reconcile_and_writes_nothing` — the refusal branch had survived the whole suite, because no pair of input files can make disjoint, exhaustive buckets fail to add up |
| X | **An unresolved name was graded as a void, and a void is a settled bet.** `run_price_backtest.grade` returned `Outcome.VOID` with the reason "does not appear in this game's box score" whenever a prop's player name found no candidate in the box score. Void is the book's treatment of a genuine did-not-play; a name the join could not resolve is *unknown*, and calling it a void counts it as a settled non-loss. Inherited shape: the football lab's "a lone candidate on the wrong team is a void, not a match". | UNSETTLEABLE for an unresolved name, with its own census field; VOID reserved for a name that resolves to a player recorded as did-not-play. The full-store run shows the size of it: **11,181 of 925,831 wagers**. | `tests/test_an_unresolved_name_is_not_a_void.py` |
| Y | **`GroupBy.first()` skips nulls, so the first basket could name the second scorer.** `made.groupby("game_id").first()` returns the first NON-NULL value per column, so a first made field goal with no athlete attribution was filled from the next basket: a real player, a wrong `player_first_basket` settlement, and nothing looking broken. Same family as the free-throw filter already recorded in this file — a plausible wrong answer rather than an error. | An order-preserving positional pick that keeps nulls, so an unattributed first basket makes the market unsettleable instead of naming somebody. | `tests/test_first_basket_keeps_an_unattributed_scorer_null.py` |
| Z | **A check that a condition can disable is not a check.** GitHub reports a conditionally-skipped required check as **Success**. A sibling session found this for the required `Tests` job; the same hole was then found in this lab's new policy gate, where `if: false` on the job, `if: ${{ false }}` on its step, `if: github.event_name == 'workflow_dispatch'`, or a `needs:` on a skipped neighbour each left the gate never running with the whole suite green. Three independent verifiers found it in one round. | The gate's own tests refuse `if:`, `needs:` and `strategy:` on the job that produces its verdict, with a test per spelling. | `tests/test_workflows.py` (the policy-gate section) |
| AA | **A mis-signed line at the source, and the model bet it at 99.95%.** Diagnosing two unpairable wagers turned up one that is not merely one-sided: on 2024-02-17 BetMGM filed `alternate_spread` **home 18.5 and away 18.5, both positive, both at -110**, on a game where another book's ladder ran to home -41.5 and priced home -18.5 at -117. Under the store's home-frame convention two same-signed sides are not two sides of one wager, so neither pairs — but the graded export carried the home row as a **selected bet with a model probability of 0.9995**. The model was not finding value; it was reading a sign error as a 19-point gift. Across the whole store 28 of 2,012,728 handicap-side rows (0.0014%) fail to pair at their own book, 24 of them one book. | The unpairable census names every excluded row with its book, market, line and price, so a mis-signed quote appears in the record instead of being averaged into a return. The deeper guard — refusing a quote whose two sides carry the same sign — is **not** built and is recorded here as open. | `tests/test_build_skill_frame.py` (the census); no guard yet for same-signed sides |
| AB | **A guard that asserted a property of a file it does not own.** A CI guard built a shortened copy of `tests/test_contract_strings.py` by cutting the text at the last `def test_`, and required the result to parse with one test fewer. Nothing anywhere said the last test in that file may not carry a decorator. Appending a parametrized test moved the cut behind its decorator, the copy stopped parsing, and the guard's helper returned nothing — so the check that exists to detect a lost test was itself defeated by an edit to a file it never mentions. Both sessions were green locally; only the full-suite CI run saw it. | The guard now parses the tree, takes the last top-level test, and cuts from the earliest of its own line and its decorators' lines — reading structure rather than text. Demonstrated in both directions: with a parametrized test appended, the old cut fails as CI did and the new one passes. | `tests/test_check_test_results.py` (owned by a sibling session; landed as their PR #29) |
