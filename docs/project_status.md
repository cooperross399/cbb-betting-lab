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

**Which correction the figures below carry.** Every interval in this file is the
family-corrected one **as the record that holds it carries it** — the price
backtest and the forecast-skill regression both ran while the experiment ledger
held 30 hypotheses, so their stored bounds are widened by **×1.60**. The ledger
now holds **62**, and `docs/what_we_can_and_cannot_claim.md` and
`docs/why_the_model_does_or_does_not_have_an_edge.md` re-apply **×1.71** at
render time, so the same tier reads **wider** there. That is the intended
direction: the correction may only ever get stricter, and neither document is
copying the other.

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
| 12 | Price backtest over the full bought population, every market, clustered, corrected, replicated | **done** | `data/outputs/cbb_price_backtest.json`. **191,053 graded bets** from **925,831 wagers offered**, over 26,591 games and 791 days of seasons 2021-2026, at the `card` snapshot. **32 market-and-tier cells: 0 demonstrated edge, 3 demonstrated deficit, 20 no demonstrated edge, 9 below the 200-bet floor.** Per tier, never pooled into one Division I headline: high-major **-3.2%** over 43,228 bets (6,203 game clusters), corrected -7.6% to +1.2% — **no demonstrated edge**; mid-major **-4.3%** over 88,344 bets (740 day clusters), corrected -7.8% to -0.8% — **demonstrated deficit**; low-major **-4.0%** over 59,475 bets (8,870 game clusters), corrected -7.7% to -0.3% — **demonstrated deficit**. Replication (`data/outputs/holdout/cbb_replication.json`): held out 2025 and 2026, discovered on 2021-2024 — **71,778 held-out bets over 9,776 games** against 119,275 on the discovery seasons, over 32 cells: **0 replicated / 0 did not replicate / 0 reversed / 3 not enough evidence / 9 nothing to replicate / 20 untestable**. **This is not the split declared on 2026-09-03**, which declared discovery [2021, 2022, 2023] and holdout [2024]; a holdout chosen after the discovery numbers were seen is a **second look at the data rather than a pre-registered test**, and every state in that count has to be read as one. `mid_major / team_total` is flagged a **new discovery made on the holdout** and not a replication: the discovery window demonstrated nothing there, while the held-out 2026 season's own **-6.6% over 4,968 bets** excludes zero — so the only clean season this lab had is spent on it and it has no held-out test of its own. |
| 13 | Market-vs-model regression printed for every candidate | **done** | `reports/forecast_skill.py`, fitted on **every settled wager the model had an opinion on (293,661)** rather than on the bets it selected — decision 28. **The model loses to the market on Brier in every measured tier with the vig left in**, model minus raw market, family-corrected and per tier rather than pooled: high-major **-0.01663, corrected -0.02147 to -0.01179** over 62,163 rows; mid-major **-0.00962, corrected -0.01286 to -0.00638** over 137,296 rows; low-major **-0.00776, corrected -0.01072 to -0.00479** over 94,182 rows — three demonstrated deficits. In high-major the model's Brier is worse than the **base rate** (0.25118 against 0.25000 over 62,163 rows): beaten by predicting the league average. **The disagreement coefficient is the skill measure, and it shows no demonstrated edge in any tier**: high-major **+0.088**, corrected -0.033 to +0.208 over 62,163 rows; mid-major **+0.122**, corrected -0.015 to +0.259 over 137,296 rows; low-major **+0.046**, corrected -0.130 to +0.223 over 94,182 rows — every interval spans zero. On the **threshold-selected bets only** (110,316) high-major reads +0.239, corrected +0.030 to +0.449, which the record labels a *demonstrated edge*: that is the **winner's-curse comparison and never the skill measure**, because the bets were selected by the same disagreement the coefficient is fitted on. Return by claimed-edge bucket is **not measurable** on this record (0 usable buckets of 8 populated); overconfidence by bucket is, and it worsens as the claimed edge grows — high-major runs **+13.4 pp** in the smallest bucket (24,416 rows) to **-18.3 pp** in the largest (11,232 rows), so raising the threshold makes it worse. This row previously carried the DE-VIGGED pooled advantage with its UNCORRECTED bounds, described as the comparison *with the vig left in* — the wrong instrument, the un-widened interval and a pooled Division I headline; the retired figure is not reprinted here because no document in this repository may carry it. It then briefly carried a pooled disagreement coefficient called a demonstrated edge, which is the same mistake in the other instrument. `tests/test_why_the_model.py` reads these figures out of `data/outputs/cbb_forecast_skill.json` and compares them against this row. |
| 14 | Calibration measured on selected bets, not only overall | **done** | **The winner's curse, measured.** Overall **0.4 pp underconfident** over 566,370 graded rows; on the bets the model **selected**, **10.4 pp overconfident** over 189,381. All ten selected bins are over-predicted, against five of ten overall, and it worsens with confidence — in the 90-100% band the model says 93.9% and wins 90.4% over 12,475 rows overall, and says 94.2% and wins **80.9%** over 3,103 rows on what it picked. Independent reproduction of the NHL lab's 9-12 pp. Rendered in `cbb_price_backtest.md` beside the sentence *the overall figure is not evidence*. |
| 15 | Reachability: edge split by whether the price survived | **built; no edge to split yet** | `reachability.py` + `scripts/run_reachability.py`, 41 tests. Three-valued survival, per book and per tier, and it emits **"not reachable"** in those words when an edge lives only in prices that vanished. The store is empty today because it is September, and it says so rather than printing an empty table. |
| 16 | Claims / when-this-ends / why-the-model docs, headline reads the sign | **done** | All three. `docs/why_the_model_does_or_does_not_have_an_edge.md` said it was **generated from the run record** and no generator existed — every figure in it had been typed, and it had already drifted. `scripts/run_why_the_model.py` is that generator; the weekly loop splices its fenced block, and `tests/test_why_the_model.py` compares the committed document against a fresh render of the record beside it. The claims doc carries a fenced block the weekly loop re-renders while its pre-measurement framing survives. A pooled verdict no tier shares is now flagged where it happens. |

### Self-operation

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 17 | Experiment ledger append-only, populated, its correction used by the reports | **done** | **62 distinct hypotheses**: 30 pre-registered discovery entries, each with a falsifiable direction, plus **32 holdout looks** the replication of 2026-09-05 appended, because putting a discovery finding to the holdout **is** a second look and is counted as one. Correction **×1.71**, up from ×1.60 at 30. `save(floor=…)` raises rather than shrinking, and `Ledger Guard` diffs the tracked file against the PR base — the recorder cannot heal a cut ledger past its own 30-entry constant, which `test_check_ledger_append_only.py` measures rather than assumes. The claims report reads the ledger and re-applies the factor at render time. |
| 18 | Promotion criteria pre-registered on disk; demotion one direction only | **done** | `data/manual/promotion_criteria.json`, declared 2026-09-01 before any challenger was measured. There is no `grant()` in `promotion.py` or `staging_provider_policy.py`, and a test sweeps for one. |
| 19 | The weekly loop runs unattended and re-renders the claims doc itself | **done** | `Weekly Refit and Measure`, Mondays 11:00 UTC, `contents: read` and no credential — it measures what is already bought and cannot spend. 43 tests. It re-renders the fenced block inside `docs/what_we_can_and_cannot_claim.md`; a missing fence is an error and never an append. |
| 20 | `CLAUDE.md` has a "Current operating state" a future session can read, contract strings pinned | **done** | `test_contract_strings.py` pins all 14. |
| 21 | `docs/decision_log.md` and `docs/ported_defects.md` complete | **done** | 44 decisions, **28 defect classes** (A-AB) with the regression test for each. S-W are the ladders-and-halves rebuild that died before persistence and cost 1,199,926 credits; decision 27 is Cooper's call not to re-buy it, with the number attached. |

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
