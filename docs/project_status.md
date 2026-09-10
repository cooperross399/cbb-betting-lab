# Where this lab is, item by item, with the evidence

**Read `docs/what_we_can_and_cannot_claim.md` before any number here.** This
file says what was *built*; that one says what may be *claimed*, and the two are
not the same thing.

Every row is checkable from the repository without anyone's judgment. A row that
is not done says so, and says what it is waiting on.

Last updated **2026-09-05**.

## The headline

**No market is allowlisted, nothing is bet, and that is the correct state.**
The season opens in 59 days.

**The history is bought and it has been measured.** The full store offered
**925,831 wagers** over **26,591 games and 791 days** of seasons 2021-2026, all
at card time (T-60m), and **191,053** of them graded. Across **32
market-and-tier cells there is no demonstrated edge anywhere**; **3 are a
demonstrated deficit**, 20 are *no demonstrated edge*, and 9 sit below the
200-bet floor declared in advance and carry a phrase rather than a number. The
honest word for this lab's state is no longer *unmeasured*. It is *measured*,
and the finding is a loss.

**The player-prop model has been scored, and it loses to the market.**
`data/outputs/cbb_prop_grading.{json,md}`, 2026-09-08, design section 10. The
store offered **257,474 prop wagers** under the declared casefold and the run
accounted for every one of them with a residual of **exactly 0**; 484,790
book-quotes settled, **342,678** paired two-sided at their own book, and
**339,660 rows over 122,604 distinct wagers** were scored against a de-vigged
fair price. **No tier shows a demonstrated edge.** The model's mean log loss is
ABOVE the de-vigged price's in all three — high-major 0.68839 against 0.68265,
mid-major 0.68793 against 0.68339, low-major 0.67955 against 0.67379 — and the
headline advantage, which is the least favourable of the two de-vigs and the two
push conventions, is **-0.0057** (corrected -0.0139 to +0.0024), **-0.0045**
(-0.0102 to +0.0011) and **-0.0065** (-0.0386 to +0.0256). Uncorrected, the
first two exclude zero on the LOSING side; the family correction is what makes
them *no demonstrated edge* rather than a deficit, and that is the correction
working rather than the measurement moving. Of the 30 registered
market-and-tier cells, **20 are no demonstrated edge, 1 is a demonstrated
deficit — `player_pra` / high-major at -0.0167, corrected -0.0311 to -0.0023
over 4,308 wagers on 350 game clusters — and 9 sit below a declared floor and
carry a phrase rather than a number.** The model does beat its own
identity-blind role-prior control decisively in high-major (+0.1130, corrected
+0.0659 to +0.1601) and mid-major (+0.1154, +0.0913 to +0.1394), which says its
per-athlete evidence is worth something over a role table and says nothing
whatever about the market. Against the VIGGED price — the handicapped
comparison, printed as a diagnostic and never a headline — the model is worse by
point estimate in every tier.

**Which correction the figures below carry.** Every interval in this file is the
family-corrected one at the experiment ledger's **cumulative count of 98
distinct hypotheses, ×1.7732** — the same correction every generated report in
`data/outputs/` now states its verdicts at, because since decision 46 a report
re-reads the ledger when it renders instead of replaying the count its run was
scored at. This file is hand-written, so it is re-derived by hand and pinned by
`tests/test_no_report_states_a_stale_correction.py`, which fails the day a
hypothesis is registered and these rows are not re-derived.

**The records on disk carry something narrower, and that is correct.** The price
backtest and the forecast-skill regression were scored while the ledger held 30
(×1.6041) and `holdout/cbb_replication.json` while it held 62 (×1.7095), and
none of them is rewritten: a record is the evidence of what was measured, and
the correction it was measured under is part of that evidence. So a record may
read narrower than every document quoting it, and the gap is exactly the search
registered since. The correction may only ever get stricter — a re-render can
retract a claim and can never manufacture one.

**And on 2026-09-05 it got stricter, which changed a verdict this file carries.**
Registering the player-prop model's 33 hypotheses before that model existed took
the family from 62 to 95 and the factor from ×1.7095 to ×1.7689. (The ledger has
since reached **98**, ×1.7732, when the forward window was registered on
2026-09-10; 62 and 95 here are what it held on that date, not today.) At the wider
factor **low-major tier ROI is no longer a demonstrated deficit**: -4.0% over
59,475 bets, corrected -8.1% to +0.0%, crossing zero at the 85th hypothesis. So
is the replication's held-out `total_points` / mid-major cell, -6.4% over 8,214
bets, corrected -12.7% to +0.0%, which crosses at the **95th** — the last entry
of that registration. **Mid-major survives** at -4.3%, corrected -8.2% to
-0.4%, and would need 411 hypotheses to widen across. Nothing became an edge.
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
| 1 | Repo private, CI green on `main`, full suite passes | **done** | `cooperross399/cbb-betting-lab`, private. `Tests` workflow green on every push. **1,574 tests**, zero skipped — `scripts/check_test_results.py` compares each required guard's `def test_*` against the junit CI writes, per test. |
| 2 | Every workflow on a cron, no laptop | **done** | Data refresh, board fetch, card publish and post-slate settlement all live in `CBB Gameday Refresh` (4 crons). `Line Movement` has 4 crons. `Provider Quota` daily. `Weekly Refit and Measure` runs Mondays 11:00 UTC and is green. Probe and purchase are dispatch-only *by design* — a cron on a credit-spending discovery run is a standing order to spend money, and a test enforces their absence. |
| 3 | Delivery chain verified end to end with a real card | **done** | All four links. The workflow published to `card-feed` (run 33551726107); `CBB CARD RELAY` (`trig_013PaobEWhpXv7vwN3wVxEXS`) copied it into Drive; the file **`CBB Card CHAIN VERIFICATION 2026-09-03 (safe to delete)`, 8,013 bytes**, was **read back in full** and holds the card verbatim. Not a green run — the bytes were read. The relay refused the first verification attempt as a suspected injection and was right to; `docs/delivery_chain.md`. |
| 4 | `tests/test_no_secrets_committed.py` passes, no key ever printed | **done** | 16 tests. It fired for real on the committed probe record (102 provider event ids, 32-hex, the same shape as a key) and was fixed by naming the recorded key, never by exempting the directory. |

### Data and settlement

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 5 | `docs/cbb_data_sources.md`, with licence, revision behaviour and latency | **done** | Every source recorded, including the ones that cannot be used and why. |
| 6 | Processed tables for every season the sources reach, row counts asserted | **done** | 94,194 team-games, 1,493,589 player-games, 45,391 game segments over 2018-19 to 2025-26. Asserted in `test_settlement_settles_real_games.py`. |
| 7 | Every wired market names the quantity it settles against, proven on real games | **done** | 35 wired, 34 deferred with a reason each. 93 settlement tests over real historical games. |

### Prices

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 8 | Retention probe run, report re-renderable from the record | **done** | 2026-09-01, 144 events planned / 102 matched, **77,160 credits** against a 147,020 bound. `data/outputs/cbb_retention_probe.{json,md}`; `scripts/rerender_retention_probe.py` rebuilds the report for free. |
| 9 | Historical prices bought for every measurable market, store deduped on price identity | **core team complete (6 seasons); ladders 609 events; props 3,223 events; futures unbuyable; CI cache lineage healed by run 33937872800, whose rebuild census matches the local one at 3,863,325 rows (the cached-response count and size in that run's step summary are on GitHub, not in a record here, so they are not quoted)**| Store: **925,831 wagers offered** from the rebuilt cache (core team 2021–2026 complete at 2,946,929 rows; ladders and halves 609 events; props 3,223 events; futures need a historical endpoint the provider does not expose). **1,199,926 credits of a second ladders wave were lost** to a rebuild that died before persistence — defects S/T/U/W in `docs/ported_defects.md` — and are not re-bought: that is Cooper's decision, with the number attached. |
| 10 | Line-movement capture live, price survival recorded | **done** | `Line Movement`, 4 crons a day year-round, 6 credits a capture. Survival is three-valued — a quote the next capture never covered is `unknown`, not `gone`. |

### Models and measurement

| # | Item | State |
|--:|:---|:---|
| 11 | Walk-forward fits, per tier, November prior, connectivity refusing to price | **done** | `models/ratings.py` + `scripts/fit_ratings.py`. Fitted 146 days of 2025-26: **4,719 of 5,415 games priced**, league 108.38 per 100 at 68.39 possessions. Prior weight decays **0.867 (12 Nov) → 0.420 (20 Feb)**, monotone, and is carried on every matchup. Connectivity refuses two teams the schedule graph has not connected — on 5 Nov, 121 components and **0.4% priceable**. **Home advantage is heterogeneous and fitted, not assumed: high_major +12.36, mid_major +7.34, low_major +3.90 per 100 possessions**, 409 venues, shrunk toward the league mean. |
| 12 | Price backtest over the full bought population, every market, clustered, corrected, replicated | **done** | `data/outputs/cbb_price_backtest.json`. **191,053 graded bets** from **925,831 wagers offered**, over 26,591 games and 791 days of seasons 2021-2026, at the `card` snapshot. **32 market-and-tier cells: 0 demonstrated edge, 3 demonstrated deficit, 20 no demonstrated edge, 9 below the 200-bet floor.** Per tier, never pooled into one Division I headline: high-major **-3.2%** over 43,228 bets (6,203 game clusters), corrected -8.1% to +1.6% — **no demonstrated edge**; mid-major **-4.3%** over 88,344 bets (740 day clusters), corrected -8.2% to -0.4% — **demonstrated deficit**; low-major **-4.0%** over 59,475 bets (8,870 game clusters), corrected -8.1% to +0.0% — **no demonstrated edge**. **Those bounds are stated at the ledger's 98 cumulative hypotheses (×1.7732), not at the ×1.6041 over 30 the record itself was scored at and still records.** Low-major is the verdict that moved: it read a demonstrated deficit at -7.7% to -0.3% under the 30 hypotheses the run was scored at and at -8.0% to -0.1% while the ledger held 62, and it crosses zero at the 85th hypothesis. Its uncorrected interval still excludes zero at -6.3% to -1.7%, so what moved is the search and not the measurement. Replication (`data/outputs/holdout/cbb_replication.json`): held out 2025 and 2026, discovered on 2021-2024 — **71,778 held-out bets over 9,776 games** against 119,275 on the discovery seasons, over 32 cells: **0 replicated / 0 did not replicate / 0 reversed / 3 not enough evidence / 9 nothing to replicate / 20 untestable**. **This is not the split declared on 2026-09-03**, which declared discovery [2021, 2022, 2023] and holdout [2024]; a holdout chosen after the discovery numbers were seen is a **second look at the data rather than a pre-registered test**, and every state in that count has to be read as one. `mid_major / team_total` is flagged a **new discovery made on the holdout** and not a replication: the discovery window demonstrated nothing there, while the held-out 2026 season's own **-6.6% over 4,968 bets** excludes zero — so the only clean season this lab had is spent on it and it has no held-out test of its own. |
| 13 | Market-vs-model regression printed for every candidate | **done** | `reports/forecast_skill.py`, fitted on **every settled wager the model had an opinion on (293,661)** rather than on the bets it selected — decision 28. **Every corrected interval in this row is stated at the ledger's 98 cumulative hypotheses (×1.7732); the fit itself was scored at 30 (×1.6041) and `data/outputs/cbb_forecast_skill.json` still records that.** No reading in the row changes between the two — the three Brier deficits and the three spanning coefficients read the same at both — and the widening is visible only in the bounds. **The model loses to the market on Brier in every measured tier with the vig left in**, model minus raw market, family-corrected and per tier rather than pooled: high-major **-0.01663, corrected -0.02198 to -0.01128** over 62,163 rows; mid-major **-0.00962, corrected -0.01320 to -0.00603** over 137,296 rows; low-major **-0.00776, corrected -0.01104 to -0.00448** over 94,182 rows — three demonstrated deficits. In high-major the model's Brier is worse than the **base rate** (0.25118 against 0.25000 over 62,163 rows): beaten by predicting the league average. **The disagreement coefficient is the skill measure, and it shows no demonstrated edge in any tier**: high-major **+0.088**, corrected -0.04527 to +0.22045 over 62,163 rows; mid-major **+0.122**, corrected -0.02978 to +0.27357 over 137,296 rows; low-major **+0.046**, corrected -0.14853 to +0.24113 over 94,182 rows — every interval spans zero. On the **threshold-selected bets only** (110,316) high-major reads +0.239, corrected +0.00811 to +0.47075, which the record labels a *demonstrated edge*: that is the **winner's-curse comparison and never the skill measure**, because the bets were selected by the same disagreement the coefficient is fitted on. Return by claimed-edge bucket is **not measurable** on this record (0 usable buckets of 8 populated); overconfidence by bucket is, and it worsens as the claimed edge grows — high-major runs **+13.4 pp** in the smallest bucket (24,416 rows) to **-18.3 pp** in the largest (11,232 rows), so raising the threshold makes it worse. This row previously carried the DE-VIGGED pooled advantage with its UNCORRECTED bounds, described as the comparison *with the vig left in* — the wrong instrument, the un-widened interval and a pooled Division I headline; the retired figure is not reprinted here because no document in this repository may carry it. It then briefly carried a pooled disagreement coefficient called a demonstrated edge, which is the same mistake in the other instrument. `tests/test_why_the_model.py` reads these figures out of `data/outputs/cbb_forecast_skill.json` and compares them against this row. |
| 14 | Calibration measured on selected bets, not only overall | **done** | **The winner's curse, measured.** Overall **0.4 pp underconfident** over 566,370 graded rows; on the bets the model **selected**, **10.4 pp overconfident** over 189,381. All ten selected bins are over-predicted, against five of ten overall, and it worsens with confidence — in the 90-100% band the model says 93.9% and wins 90.4% over 12,475 rows overall, and says 94.2% and wins **80.9%** over 3,103 rows on what it picked. Independent reproduction of the NHL lab's 9-12 pp. Rendered in `cbb_price_backtest.md` beside the sentence *the overall figure is not evidence*. |
| 15 | Reachability: edge split by whether the price survived | **built; no edge to split yet** | `reachability.py` + `scripts/run_reachability.py`, 41 tests. Three-valued survival, per book and per tier, and it emits **"not reachable"** in those words when an edge lives only in prices that vanished. The store is empty today because it is September, and it says so rather than printing an empty table. |
| 16 | Claims / when-this-ends / why-the-model docs, headline reads the sign | **done** | All three. `docs/why_the_model_does_or_does_not_have_an_edge.md` said it was **generated from the run record** and no generator existed — every figure in it had been typed, and it had already drifted. `scripts/run_why_the_model.py` is that generator; the weekly loop splices its fenced block, and `tests/test_why_the_model.py` compares the committed document against a fresh render of the record beside it. The claims doc carries a fenced block the weekly loop re-renders while its pre-measurement framing survives. A pooled verdict no tier shares is now flagged where it happens. |

### Self-operation

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 17 | Experiment ledger append-only, populated, its correction used by the reports | **done** | **98 distinct hypotheses**: 30 pre-registered discovery entries, each with a falsifiable direction; **32 holdout looks** the replication of 2026-09-05 appended, because putting a discovery finding to the holdout **is** a second look and is counted as one; **33 player-prop hypotheses** registered the same day *before that model existed* — ten priceable markets × three tiers against the de-vigged two-sided fair price, plus one per tier against an identity-blind role-prior control; and **3 forward-window hypotheses** registered 2026-09-10, eight weeks before the 2026-11-02 opener and with zero rows of forward evidence in existence, one per tier over 2027-2029. Correction **×1.7732**, up from ×1.7095 at 62 and ×1.60 at 30, and decision 43 records which two published verdicts that move cost. `save(floor=…)` raises rather than shrinking, and `Ledger Guard` diffs the tracked file against the PR base — the recorder cannot heal a cut ledger past its own pre-registered constant, which `test_check_ledger_append_only.py` measures rather than assumes. Seven quantities are declared **descriptive-only**: they are excluded from the count on the grounds that none can be a finding, and `record()`, `save()` and `Ledger Guard` all refuse to promote one afterwards, which is what makes the exclusion honest. The claims report reads the ledger and re-applies the factor at render time. |
| 18 | Promotion criteria pre-registered on disk; demotion one direction only | **done** | `data/manual/promotion_criteria.json`, declared 2026-09-01 before any challenger was measured. There is no `grant()` in `promotion.py` or `staging_provider_policy.py`, and a test sweeps for one. |
| 19 | The weekly loop runs unattended and re-renders the claims doc itself | **done** | `Weekly Refit and Measure`, Mondays 11:00 UTC, `contents: read` and no credential — it measures what is already bought and cannot spend. 43 tests. It re-renders the fenced block inside `docs/what_we_can_and_cannot_claim.md`; a missing fence is an error and never an append. |
| 20 | `CLAUDE.md` has a "Current operating state" a future session can read, contract strings pinned | **done** | `test_contract_strings.py` pins all 14. |
| 21 | `docs/decision_log.md` and `docs/ported_defects.md` complete | **done** | 56 decisions, **28 defect classes** (A-AB) with the regression test for each. S-W are the ladders-and-halves rebuild that died before persistence and cost 1,199,926 credits; decision 27 is Cooper's call not to re-buy it, with the number attached. |
| 22 | Player props scored against a de-vigged fair price, per tier, the 33 pre-registered hypotheses answered | **done** | `reports/prop_grading.py` + `scripts/run_prop_grading.py`, `data/outputs/cbb_prop_grading.{json,md}`, 44 tests. Both de-vigs (proportional and power) from one pairing pass joined on event, market, athlete, line **and book**, with the headline the least favourable to the model; both push conventions scored for the same reason (measured push mass **0.0000** — the store carries 6 quotes on 3 integer lines, so the choice was worth nothing here); the de-vigged fair price and the identity-blind role-prior control printed BEFORE the model in every section; mean log loss, Brier and calibration by decile; intervals clustered by game, day **and athlete** with the widest winning. **The calibration is the shape of the finding**: the model is monotonically overconfident on both sides — in high-major it says 84.0% and wins 74.3% over 701 rows, and says 26.5% and wins 36.2% over 3,874. Coverage is reported beside every verdict and measured **98.7% at the money, 50.7% one rung out, 13.2% two, 4.7% three and 1.1% four**, which is design section 10's own claim reproduced; the **184 rows past three rungs are reported apart as UNBENCHMARKED** and are never an edge. Median overround removed **1.0758**, median power exponent 1.1208; **no probability was clipped** and the control declined **0** of the wagers the model priced. `player_first_basket` and `player_double_double` are filtered immediately after the census gate and are never scored, never given a verdict, and are not a pass, an avoid or a no-value call. |

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
  which is why the purchase is prioritised rather than complete.
