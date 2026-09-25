# Where this lab is, item by item, with the evidence

**Read `docs/what_we_can_and_cannot_claim.md` before any number here.** This
file says what was *built*; that one says what may be *claimed*, and the two are
not the same thing.

Every row is checkable from the repository without anyone's judgment. A row that
is not done says so, and says what it is waiting on.

**This document carries no "last updated" stamp.** It said 2026-09-05 while
holding six sentences dated 2026-09-18, because a stamp is a figure nobody
regenerates and the only reader who can keep one honest is the one who
remembers to. `git log -1 -- docs/project_status.md` is the authority and
cannot go stale.

## The headline

**No market is allowlisted, nothing is bet, and that is the correct state.**
The season opens on 2026-11-01 and real volume starts on 2026-11-02. **No
countdown is published here**: the one that stood in this line was wrong under
its own stamp and wrong again under today's date, which is what a figure
measured from *today* does in a committed file.

**The history is bought and it has been measured.** The full store's
population — wagers offered, graded bets, games — and the way its
market-and-tier cells fall across the verdicts are in the record census below,
generated from the record. Across those cells **there is no demonstrated edge
anywhere**; the cells that carry a phrase rather than a number are the ones
below the 200-bet floor declared in advance. Every one of those counts was
typed here by hand until 2026-09-18 and every one of them was wrong. The
honest word for this lab's state is no longer *unmeasured*. It is *measured*,
and the finding is a loss.

**The player-prop model has been scored, and it loses to the market.**
`data/outputs/cbb_prop_grading.{json,md}`, 2026-09-08, design section 10. The
store offered **257,474 prop wagers** under the declared casefold and the run
accounted for every one of them with a residual of **exactly 0**; 484,790
book-quotes settled, **342,678** paired two-sided at their own book, and
**339,660 rows** over 171,339 two-sided pairs were scored against a de-vigged
fair price. **No tier shows a demonstrated edge.** The model's mean log loss is
ABOVE the de-vigged price's in all three — high-major 0.68839 against 0.68265,
mid-major 0.68793 against 0.68339, low-major 0.67955 against 0.67379 — and the headline advantage, which is the least favourable of the two de-vigs and the two push conventions, shows no demonstrated edge in any tier; the three estimates and their intervals are in the generated block above. Uncorrected, the
first two exclude zero on the LOSING side; the family correction is what makes
them *no demonstrated edge* rather than a deficit, and that is the correction
working rather than the measurement moving. Of the 30 registered
market-and-tier cells, **20 are no demonstrated edge, 1 is a demonstrated deficit — `player_pra` / high-major, over 4,308 wagers on 350 game clusters, in the generated block above — and 9 sit below a declared floor and
carry a phrase rather than a number.** The model does beat its own
identity-blind role-prior control decisively in high-major and mid-major — both in the generated block above — which says its
per-athlete evidence is worth something over a role table and says nothing
whatever about the market. Against the VIGGED price — the handicapped
comparison, printed as a diagnostic and never a headline — the model is worse by
point estimate in every tier.

**Which correction the figures below carry.** Every interval in this file is the family-corrected one at the experiment ledger's cumulative count, which the generated block below states along with the factor derived from it — the same correction every generated report in
`data/outputs/` now states its verdicts at, because since decision 46 a report
re-reads the ledger when it renders instead of replaying the count its run was
scored at. This file is hand-written, so it is re-derived by hand and pinned by
`tests/test_no_report_states_a_stale_correction.py`, which fails the day a
hypothesis is registered and these rows are not re-derived.

**The per-tier headline is generated, not typed.** It is spliced from
`data/outputs/cbb_price_backtest.json` by
`scripts/splice_headline_table.py`, so it cannot be left behind by a
registration the way every figure in this file used to be:

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

**Some records on disk carry something narrower, and that is correct.** Which
records, and what each was scored under, is the first table of the record
census above — generated, because this paragraph named four records and four
corrections by hand, three of them were already wrong when it was written, and
the 2026-09-17 regeneration falsified the fourth the same day. None of the
records is rewritten: a record is the evidence of what was measured, and the
correction it was measured under is part of that evidence. So a record may
read narrower than every document quoting it, and the gap is exactly the search
registered since. The correction may only ever get stricter — a re-render can
retract a claim and can never manufacture one.

**And on 2026-09-05 it got stricter, which changed a verdict this file carries.**
Registering the player-prop model's 33 hypotheses before that model existed took
the family from 62 to 95 and the factor from ×1.7095 to ×1.7689. (The ledger has since grown twice more — the generated block above carries
where it stands — with the forward window and the rebound
differential both registered on 2026-09-10; 62 and 95 here are what it held on
that date, not today.) At the wider factor **low-major tier ROI stopped being a
demonstrated deficit**, having crossed zero at the 85th hypothesis — and on
2026-09-17 it became one again, when the neutral-court exclusion removed 15,207
misgraded bets whose sign flips had been biasing the tier toward zero. Its
reading is in the generated block above. The intervals it carried before that
exclusion are not restated here: they were measured over a population that no
longer exists, so nothing can check them. So is the replication's held-out `total_points` / mid-major cell,
-6.5% over 8,267 bets, which reads **no demonstrated edge** today, in the generated block
above; it crossed at the **125th**. It crossed at the 95th — the last entry of
that registration — until 2026-09-17, when the replication was re-scored against
a model that had just been handed its roster evidence. At 95 hypotheses the
re-scored cell still reads a demonstrated deficit, -12.9% to -0.1% [@95]. The
verdict today is the one it already carried, so what moved is the crossing point
and not the reading. **Mid-major survives** as a demonstrated deficit — its return and
interval are in the generated block above, and how much more searching it would
survive is in the record census above, searched from the tier's own return and
standard error rather than typed. This line said **411** until 2026-09-18 and no
record has ever supported it. Nothing became an edge.
Decision 43 records the call and the arithmetic.

**Two defects were found and fixed on 2026-09-03 that would have made the first
measurement meaningless**, both in the seam between the ratings and the
backtest, and both found by a report describing its own output rather than by a
test. The prior's weight was **0.0% on 3 November and 0.0% on 20 February** —
the November regime deleted — and the tier table was built over the season it
was pricing, moving 9.3% of teams across a boundary that selects which
home-court effect applies. A backtest was killed mid-run because its numbers
would have been about a model that will never ship. `docs/ported_defects.md`
M and the commit of 2026-09-03.

## Definition of Done

### Infrastructure

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 1 | Repo private, CI green on `main`, full suite passes | **done** | `cooperross399/cbb-betting-lab`, private. `Tests` workflow green on every push, zero skipped — `scripts/check_test_results.py` compares each required guard's `def test_*` against the junit CI writes, per test. **No test count is published here.** This cell published a test count until 2026-09-18 that was low by roughly a thousand, and the count guard accepted it because a shot-zone record happens to store the same integer as a team's field-goal attempts — the figure is not repeated here, because a record does hold that integer and so it cannot honestly be marked superseded either. A suite size is not a record figure, nothing regenerates it, and it is stale the moment a test is added; the authority is `pytest tests/ --collect-only -q`, run by the reader. |
| 2 | Every workflow on a cron, no laptop | **done** | Data refresh, board fetch, card publish and post-slate settlement all live in `CBB Gameday Refresh` (4 crons). `Line Movement` has 4 crons. `Provider Quota` daily. `Weekly Refit and Measure` runs Mondays 11:00 UTC and is green. Probe and purchase are dispatch-only *by design* — a cron on a credit-spending discovery run is a standing order to spend money, and a test enforces their absence. |
| 3 | Delivery chain verified end to end with a real card | **done** | All four links. The workflow published to `card-feed` (run 33551726107); `CBB CARD RELAY` (`trig_013PaobEWhpXv7vwN3wVxEXS`) copied it into Drive; the file **`CBB Card CHAIN VERIFICATION 2026-09-03 (safe to delete)`, 8,013 bytes**, was **read back in full** and holds the card verbatim. Not a green run — the bytes were read. The relay refused the first verification attempt as a suspected injection and was right to; `docs/delivery_chain.md`. |
| 4 | `tests/test_no_secrets_committed.py` passes, no key ever printed | **done** | It fired for real on the committed probe record (102 provider event ids, 32-hex, the same shape as a key) and was fixed by naming the recorded key, never by exempting the directory. |

### Data and settlement

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 5 | `docs/cbb_data_sources.md`, with licence, revision behaviour and latency | **done** | Every source recorded, including the ones that cannot be used and why. |
| 6 | Processed tables for every season the sources reach, row counts asserted | **done** | 94,194 team-games, 1,493,589 player-games, 45,391 game segments over 2018-19 to 2025-26. Asserted in `test_settlement_settles_real_games.py`. |
| 7 | Every wired market names the quantity it settles against, proven on real games | **done** | 35 wired, 34 deferred with a reason each. `tests/test_settlement_settles_real_games.py` settles every wired market over real historical games. |

### Prices

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 8 | Retention probe run, report re-renderable from the record | **done** | 2026-09-01, 144 events planned / 102 matched, **77,160 credits** against a 147,020 bound. `data/outputs/cbb_retention_probe.{json,md}`; `scripts/rerender_retention_probe.py` rebuilds the report for free. |
| 9 | Historical prices bought for every measurable market, store deduped on price identity | **core team complete (6 seasons); ladders 609 events; props bought over three seasons, event count in no record; futures unbuyable; CI cache lineage healed by run 33937872800, whose rebuild census matches the local one at 3,863,325 rows (the cached-response count and size in that run's step summary are on GitHub, not in a record here, so they are not quoted)**| Store: the wagers offered are in the record census near the top of this file — this cell said **920,712** until 2026-09-18 [superseded: 920,712 on 2026-09-18] against a record reading otherwise (core team 2021–2026 complete at 2,946,929 rows; ladders and halves 609 events; the prop wave's event count is stated in no record here; futures need a historical endpoint the provider does not expose). **1,199,926 credits of a second ladders wave were lost** to a rebuild that died before persistence — defects S/T/U/W in `docs/ported_defects.md` — and are not re-bought: that is Cooper's decision, with the number attached. |
| 10 | Line-movement capture live, price survival recorded | **done** | `Line Movement`, 4 crons a day year-round, 6 credits a capture. Survival is three-valued — a quote the next capture never covered is `unknown`, not `gone`. |

### Models and measurement

| # | Item | State |
|--:|:---|:---|
| 11 | Walk-forward fits, per tier, November prior, connectivity refusing to price | **done** | `models/ratings.py` + `scripts/fit_ratings.py`. Fitted 146 days of 2025-26: **4,719 of 5,415 games priced**, league 108.38 per 100 at 68.39 possessions. Prior weight decays monotonically and is carried on every matchup — read from the record's own timeline, the median weight runs **0.8292 → 0.2239 on offence, 0.8722 → 0.4186 on defence and 0.5764 → 0.1000 on tempo between 10 November and 20 February**. This cell said **0.867 (12 Nov) → 0.420 (20 Feb)** until 2026-09-18: the timeline holds no 12 November day at all and neither endpoint is anywhere in the record. Connectivity refuses two teams the schedule graph has not connected — on 5 Nov, 121 components and **0.4% priceable**. **Home advantage is heterogeneous and fitted, not assumed: high_major +12.36, mid_major +7.34, low_major +3.90 per 100 possessions**, 409 venues, shrunk toward the league mean. |
| 12 | Price backtest over the full bought population, every market, clustered, corrected, replicated | **done** | `data/outputs/cbb_price_backtest.json`. The graded-bet population, the wagers offered and the games are in the record census near the top of this file, and so is the market-and-tier tally, because all five figures were typed into this row by hand and all five were wrong; the snapshot is `card`. Per tier, never pooled into one Division I headline: high-major **no demonstrated edge**, mid-major **demonstrated deficit**, low-major **demonstrated deficit** — the bets, the returns and the corrected intervals are in the generated block near the top of this file, and are not restated here. **Those bounds are stated at the ledger's current cumulative count, which the generated block above gives; what this record itself was scored at is in the census block, and since the 2026-09-17 re-score the two agree.** Low-major is the verdict that has moved most: a demonstrated deficit when the run was first scored, crossing zero at the 85th hypothesis as the family grew, and a demonstrated deficit **again** since 2026-09-17 — that last move being the population rather than the search, as 15,207 neutral-court bets this store cannot orient are now refused instead of graded. Its corrected reading is in the generated block above; its uncorrected interval is -6.9% to -2.2%, stated here because nothing in the generated block reaches it. The bounds it carried before that exclusion are not restated, because the population they were measured over no longer exists. Replication (`data/outputs/holdout/cbb_replication.json`): held out 2025 and 2026, discovered on 2021-2024 — the held-out and discovery populations are in the census block near the top of this file, over 32 cells: **0 replicated / 0 did not replicate / 0 reversed / 3 not enough evidence / 9 nothing to replicate / 20 untestable**. **This is not the split declared on 2026-09-03**, which declared discovery [2021, 2022, 2023] and holdout [2024]; a holdout chosen after the discovery numbers were seen is a **second look at the data rather than a pre-registered test**, and every state in that count has to be read as one. `mid_major / team_total` is flagged a **new discovery made on the holdout** and not a replication: the discovery window demonstrated nothing there, while the held-out 2026 season's own **-6.9% over 4,429 bets** excludes zero — so the only clean season this lab had is spent on it and it has no held-out test of its own. |
| 13 | Market-vs-model regression printed for every candidate | **done** | `reports/forecast_skill.py`, fitted on **every settled wager the model had an opinion on (270,504)** rather than on the bets it selected — decision 28. **Every corrected interval in this row is stated at the ledger's current cumulative count, in the generated block above, and the record was re-scored at that same count on 2026-09-17.** The record and the block therefore no longer disagree; the sentence that used to stand here said the fit was scored at 30 (×1.6041) and that no reading changed between the two counts, and the second half of that is now false in a way worth naming rather than deleting — **five published `demonstrated edge` verdicts were withdrawn by that re-score**, and `docs/retracted_readings.md` states each of them with the two causes separated. **The model loses to the market on Brier in every measured tier with the vig left in**, model minus raw market, family-corrected and per tier rather than pooled — three demonstrated deficits, in the generated block above. In high-major the model's Brier is worse than the **base rate** (0.25160 against 0.25000 over 53,844 rows): beaten by predicting the league average. **The disagreement coefficient is the skill measure, and it shows no demonstrated edge in any tier** — every interval spans zero, and all three are in the generated block above. On the **threshold-selected bets only** (100,856) high-major read a *demonstrated edge* until that re-score and reads **no demonstrated edge** now — the figure is in the generated block above: that was the **winner's-curse comparison and never the skill measure**, because the bets were selected by the same disagreement the coefficient is fitted on, so no finding was lost with it. The family did not withdraw it: at the published measurement it still excluded zero across the family's whole 30 -> 133 growth and would have needed 156 to cross, and at the family of 30 the new measurement already spans zero. Return by claimed-edge bucket **is** measurable on this record — **8 usable buckets of 8 populated** on each real tier, with one demonstrated deficit among them, low-major's -5% to +0% band over 10,587 settled wagers; it was published here as *not measurable, 0 of 8*, which was an artefact of a dropped export column and never a fact about the archive. Overconfidence by bucket worsens as the claimed edge grows — high-major runs **+13.3 pp** in the smallest bucket (21,290 rows) to **-18.5 pp** in the largest (9,559 rows), so raising the threshold makes it worse. This row previously carried the DE-VIGGED pooled advantage with its UNCORRECTED bounds, described as the comparison *with the vig left in* — the wrong instrument, the un-widened interval and a pooled Division I headline; the retired figure is not reprinted here because no document in this repository may carry it. It then briefly carried a pooled disagreement coefficient called a demonstrated edge, which is the same mistake in the other instrument. `tests/test_why_the_model.py` reads these figures out of `data/outputs/cbb_forecast_skill.json` and compares them against this row. |
| 14 | Calibration measured on selected bets, not only overall | **done** | **The winner's curse, measured.** Overall **0.4 pp underconfident** over 526,728 graded rows; on the bets the model **selected**, **10.4 pp overconfident** over 174,136. All ten selected bins are over-predicted, against five of ten overall, and it worsens with confidence — in the 90-100% band the model says 93.9% and wins 90.7% over 11,547 rows overall, and says 94.1% and wins **79.9%** over 2,411 rows on what it picked. Independent reproduction of the NHL lab's 9-12 pp. Rendered in `cbb_price_backtest.md` beside the sentence *the overall figure is not evidence*. |
| 15 | Reachability: edge split by whether the price survived | **built; no edge to split yet** | `reachability.py` + `scripts/run_reachability.py`. Three-valued survival, per book and per tier, and it emits **"not reachable"** in those words when an edge lives only in prices that vanished. The store is empty today because it is September, and it says so rather than printing an empty table. |
| 16 | Claims / when-this-ends / why-the-model docs, headline reads the sign | **done** | All three. `docs/why_the_model_does_or_does_not_have_an_edge.md` said it was **generated from the run record** and no generator existed — every figure in it had been typed, and it had already drifted. `scripts/run_why_the_model.py` is that generator; the weekly loop splices its fenced block, and `tests/test_why_the_model.py` compares the committed document against a fresh render of the record beside it. The claims doc carries a fenced block the weekly loop re-renders while its pre-measurement framing survives. A pooled verdict no tier shares is now flagged where it happens. |

### Self-operation

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 17 | Experiment ledger append-only, populated, its correction used by the reports | **done** | The total is in the generated block above. Its composition: **30 pre-registered discovery entries**, each with a falsifiable direction; **32 holdout looks** the replication of 2026-09-05 appended, because putting a discovery finding to the holdout **is** a second look and is counted as one; **33 player-prop hypotheses** registered the same day *before that model existed* — ten priceable markets × three tiers against the de-vigged two-sided fair price, plus one per tier against an identity-blind role-prior control; **3 forward-window hypotheses** registered 2026-09-10, eight weeks before the 2026-11-02 opener and with zero rows of forward evidence in existence, one per tier over 2027-2029; **3 rebound-differential hypotheses** registered the same day over 2027-2030, one per tier; and **27 residual-regression hypotheses** registered 2026-09-15, every feature of `team_features.py`, `shot_zones.py`, `player_features.py` and `derived_ratings.py` against the model's own residual over 2021-2026, each with an a priori direction; and **2 weekly-search hypotheses** the refit-and-measure loop drained from `data/manual/weekly_search_queue.json` in week 2026-W38, its first real spend — the weekly refit's ROI against the standing champion, and whether frozen opinions beat the closing price. That composition is 30 + 32 + 33 + 3 + 3 + 27 + 2 + 3, the last three being the held-out looks the replication of 2026-09-17 appended, one per cell it put to the holdout, because putting a discovery finding to the holdout IS a second look and is counted as one — and the total it comes to is the one in the generated block above. The loop reads that queue and never writes it, which is what makes the budget a rate limit rather than a suggestion. **The rebound window is underpowered and the file that registers it now says so**: the four seasons were chosen from a POOLED power calculation, while what was registered is three per-tier tests, and at 80% power the per-tier minimum detectable slope over four seasons is 12.02 against observed slopes of +8.5, +8.6 and +4.5. The entries stand because the ledger is append-only — a registered hypothesis is not withdrawn to make its own arithmetic look better. The correction is in the generated block above, up from ×1.7732 at 98, ×1.7095 at 62 and ×1.60 at 30, and decision 43 records which two published verdicts that move cost. The 98 → 101 step cost a third that went unnarrated until a review found it: **`mid_major / player_threes` on the blind null-baseline side lost its demonstrated-deficit reading** in both the full-store and held-out backtests. The 101 → 128 step, which registered the 27 residual-regression hypotheses on 2026-09-15 — the features of `team_features.py`, `shot_zones.py`, `player_features.py` and `derived_ratings.py` run against the model's own residual, each with an a priori direction, over 2021-2026 — cost **nine** published readings on 2026-09-15, all of them blind null-baseline sides at the time, and they were narrated in the commit that caused them. That sentence is history: three of the four readings those nine rows covered are player-prop sides, and the backtest declared its scope on 2026-09-17 and measures team markets only, so those readings are not retracted now — they are not in any price-backtest record at all. `docs/retracted_readings.md` carries both statements and the dates. One of the 27 survived its correction, `d_def_reb_pct` at t = +4.14, and it replicates the `d_orb` entry the ledger already held: the step added no claim. `save(floor=…)` raises rather than shrinking, and `Ledger Guard` diffs the tracked file against the PR base — the recorder cannot heal a cut ledger past its own pre-registered constant, which `test_check_ledger_append_only.py` measures rather than assumes. Seven quantities are declared **descriptive-only**: they are excluded from the count on the grounds that none can be a finding, and `record()`, `save()` and `Ledger Guard` all refuse to promote one afterwards, which is what makes the exclusion honest. The claims report reads the ledger and re-applies the factor at render time. |
| 18 | Promotion criteria pre-registered on disk; demotion one direction only | **done** | `data/manual/promotion_criteria.json`, declared 2026-09-01 before any challenger was measured. There is no `grant()` in `promotion.py` or `staging_provider_policy.py`, and a test sweeps for one. |
| 19 | The weekly loop runs unattended and re-renders the claims doc itself | **done** | `Weekly Refit and Measure`, Mondays 10:00 UTC, `contents: read` and no credential — it measures what is already bought and cannot spend. `tests/test_weekly_loop.py` covers it. It re-renders the fenced block inside `docs/what_we_can_and_cannot_claim.md`; a missing fence is an error and never an append. |
| 20 | `CLAUDE.md` has a "Current operating state" a future session can read, contract strings pinned | **done** | `test_contract_strings.py` pins every string in its own `CONTRACTS` table, and the count is not restated here: this cell said **14** against a table of 16, which is the shape of stale-by-retyping that a roster count always has. |
| 21 | `docs/decision_log.md` and `docs/ported_defects.md` complete | **done** | 59 decisions, **31 defect classes** (A-AE) with the regression test for each. S-W are the ladders-and-halves rebuild that died before persistence and cost 1,199,926 credits; decision 27 is Cooper's call not to re-buy it, with the number attached. AC-AE are the paid-data purchase path: a zero-billed response charged the pessimistic bound, an exhausted account published as a fact about the provider's archive, and the fix for U disarming the anti-shrink guard that stood over it. |
| 22 | Player props scored against a de-vigged fair price, per tier, the 33 pre-registered hypotheses answered | **done** | `reports/prop_grading.py` + `scripts/run_prop_grading.py`, `data/outputs/cbb_prop_grading.{json,md}`, `tests/test_prop_grading.py`. **No test count here either**, for the reason row 1 gives: this cell published one until 2026-09-18 and it was wrong by twelve, in the same table as the figure that round was raised to remove and invisible to the count guard for the same reason — it carries no comma. `pytest tests/test_prop_grading.py --collect-only -q` is the authority. Both de-vigs (proportional and power) from one pairing pass joined on event, market, athlete, line **and book**, with the headline the least favourable to the model; both push conventions scored for the same reason (measured push mass **0.0000** — the store carries 6 quotes on 3 integer lines, so the choice was worth nothing here); the de-vigged fair price and the identity-blind role-prior control printed BEFORE the model in every section; mean log loss, Brier and calibration by decile; intervals clustered by game, day **and athlete** with the widest winning. **The calibration is the shape of the finding**: the model is monotonically overconfident on both sides — in high-major it says 84.0% and wins 74.3% over 701 rows, and says 26.5% and wins 36.2% over 3,874. Coverage is reported beside every verdict and measured **98.7% at the money, 50.7% one rung out, 13.2% two, 4.7% three and 1.1% four**, which is design section 10's own claim reproduced; the **184 rows past three rungs are reported apart as UNBENCHMARKED** and are never an edge. Median overround removed **1.0758**, median power exponent 1.1208; **no probability was clipped** and the control declined **0** of the wagers the model priced. `player_first_basket` and `player_double_double` are filtered immediately after the census gate and are never scored, never given a verdict, and are not a pass, an avoid or a no-value call. |

## What is actually waiting on Cooper

**Nothing, until there is evidence to sign an acceptance receipt against.**

The GitHub App grant was the one outstanding item and Cooper made it on
2026-09-03. The delivery chain is verified end to end and the lab needs no
further input to run.

## The three numbers worth knowing today

- **77,160 credits** bought the retention probe's answer: all 15 team, ladder
  and half markets are retained and measurable at 93-100% across up to 17 books.
  Five prop markets are measurable, nine are thin, five are not retained at all.
- **20.5% of provider team names did not resolve** until the probe measured it —
  and the misses ran high-major 13%, low-major **53%**, biased directly against
  the hypothesis this lab exists to test. Now 0 of 365.
- **35,173,680 credits** is the full catalogue against a **4,992,714** balance,
  which is why the purchase is prioritised rather than complete. `CLAUDE.md`
  carried a figure half this size for the same named quantity until 2026-09-18,
  because `docs/credit_cost.md` states the price twice and the two differ by the
  region count the cost record stores. Neither can be bound to a field — that
  record holds no catalogue total — so which is the catalogue is not settled
  here either.

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

- [src: 2,411 in data/outputs/cbb_price_backtest.json#/calibration/selected/9/n] — selected-bet rows in the 90-100% confidence band.
- [src: 3,874 in data/outputs/cbb_prop_grading.json#/by_tier/0/calibration/model__conditional/2/rows] — high-major prop rows in the 20-30% predicted band.
- [src: 4,308 in data/outputs/cbb_prop_grading.json#/by_market_and_tier/6/rows] — `player_pra` / high-major wagers.
- [src: 4,429 in data/outputs/holdout/cbb_replication.json#/markets/16/seasons/1/bets] — `mid_major / team_total` bets in the held-out 2026 season.
- [src: 4,719 in data/outputs/cbb_ratings_fit.json#/seasons_detail/0/games_priced] — 2025-26 games the ratings fit priced.
- [src: 5,415 in data/outputs/cbb_ratings_fit.json#/seasons_detail/0/games_offered] — 2025-26 games it was offered.
- [src: 8,267 in data/outputs/holdout/cbb_replication.json#/markets/17/holdout/bets] — the replication's held-out `total_points` / mid-major bets.
- [src: 9,559 in data/outputs/cbb_forecast_skill.json#/by_tier/0/buckets/7/rows] — high-major rows in the largest claimed-edge bucket.
- [src: 10,587 in data/outputs/cbb_forecast_skill.json#/by_tier/2/buckets/2/rows] — settled wagers in low-major's -5% to +0% bucket.
- [src: 11,547 in data/outputs/cbb_price_backtest.json#/calibration/overall/9/n] — all graded rows in the 90-100% confidence band.
- [src: 21,290 in data/outputs/cbb_forecast_skill.json#/by_tier/0/buckets/0/rows] — high-major rows in the smallest claimed-edge bucket.
- [src: 53,844 in data/outputs/cbb_forecast_skill.json#/by_tier/0/rows] — high-major rows the Brier comparison is fitted on.
- [src: 77,160 in data/outputs/cbb_retention_probe.json#/credits_spent] — credits the retention probe spent.
- [src: 94,194 in data/outputs/cbb_ratings_fit.json#/team_games_supplied] — team-games supplied to the ratings fit.
- [src: 100,856 in data/outputs/cbb_forecast_skill.json#/populations/selected/rows] — the threshold-selected bets.
- [src: 147,020 in data/outputs/cbb_retention_probe.json#/pessimistic_bound] — the probe's pessimistic credit bound.
- [src: 171,339 in data/outputs/cbb_prop_grading.json#/overround/pairs] — two-sided prop pairs.
- [src: 174,136 in data/outputs/cbb_price_backtest.json#/calibration/selected_overconfidence/n] — selected bets the 10.4 pp overconfidence is measured over.
- [src: 257,474 in data/outputs/cbb_prop_accounting.json#/offered] — prop wagers the store offered under the declared casefold.
- [src: 270,504 in data/outputs/cbb_forecast_skill.json#/populations/all_opinions/rows] — every settled wager the model had an opinion on.
- [src: 339,660 in data/outputs/cbb_prop_grading.json#/population_census/scored] — prop rows scored.
- [src: 342,678 in data/outputs/cbb_prop_grading.json#/devig_census/devigged] — book-quotes paired two-sided at their own book.
- [src: 484,790 in data/outputs/cbb_prop_grading.json#/devig_census/supplied] — book-quotes settled and supplied to the de-vig.
- [src: 526,728 in data/outputs/cbb_price_backtest.json#/calibration/overall_overconfidence/n] — graded rows the overall calibration is measured over.
- [src: 1,493,589 in data/outputs/cbb_weekly_loop.json#/steps/1/lines/4] — player-games in the processed tables.
- [src: 3,863,325 in data/outputs/cbb_prop_accounting.json#/store/rows_scanned] — rows in the price store the prop accounting scanned.
- [src: 4,992,714 in data/outputs/cbb_credit_cost.json#/quota_remaining] — credits remaining on the account at the recorded read.
- [src: 45,391 in src/cbb_betting_lab/forward_evidence.py] — game segments in the processed table, eight seasons.
- [src: 1,199,926 in docs/decision_log.md] — the credits the lost ladders wave spent (decision 27).
- [src: 15,207 in tests/test_the_forward_window_is_pre_registered.py] — neutral-court bets refused on 2026-09-17.
- [src: 2,946,929 in src/cbb_betting_lab/models/player_rates.py] — rows of the rebuilt core-team price store.
- [src: 8,013 in docs/delivery_chain.md] — the workflow run the delivery chain was verified on.
- [src: 35,173,680 in docs/credit_cost.md] — the full historical catalogue's price.

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
