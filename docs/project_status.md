# Where this lab is, item by item, with the evidence

**Read `docs/what_we_can_and_cannot_claim.md` before any number here.** This
file says what was *built*; that one says what may be *claimed*, and the two are
not the same thing.

Every row is checkable from the repository without anyone's judgment. A row that
is not done says so, and says what it is waiting on.

Last updated **2026-09-04**.

## The headline

**No market is allowlisted, nothing is bet, and that is the correct state.**
The season opens in 59 days.

**The history is bought: 1,821,842 price rows over 19,974 games, four seasons,
33 books, all at card time (T-60m).** The price backtest is scoring it as this
is written. Until that finishes, this lab has machinery, a bought population and
no findings — and the honest word for that is *unmeasured*, not *null*.

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
| 1 | Repo private, CI green on `main`, full suite passes | **done** | `cooperross399/cbb-betting-lab`, private. `Tests` workflow green on every push. **721 tests.** |
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
| 9 | Historical prices bought for every measurable market, store deduped on price identity | **core team markets done; ladders, props and futures not bought** | **1,299,945 credits, 1,821,842 price rows, 19,974 events, 33 books**, seasons 2021-2024, window `card` (T-60m). `moneyline`, `spread`, `total_points`, `team_total`. The cap bound before seasons 2025-26 and before waves 2-4, which is the ordinary case for a purchase deliberately larger than one month's credits; the event order makes every prefix a proportional sample. **The first purchase persisted nothing** — two hand-spelled paths and a store the live buy never writes — and the responses survived by luck inside a sibling cache. `docs/ported_defects.md` L. Dedupe on price identity is pinned by `test_prices_dedupe_on_identity_not_the_row.py`. |
| 10 | Line-movement capture live, price survival recorded | **done** | `Line Movement`, 4 crons a day year-round, 6 credits a capture. Survival is three-valued — a quote the next capture never covered is `unknown`, not `gone`. |

### Models and measurement

| # | Item | State |
|--:|:---|:---|
| 11 | Walk-forward fits, per tier, November prior, connectivity refusing to price | **done** | `models/ratings.py` + `scripts/fit_ratings.py`. Fitted 146 days of 2025-26: **4,719 of 5,415 games priced**, league 108.38 per 100 at 68.39 possessions. Prior weight decays **0.867 (12 Nov) → 0.420 (20 Feb)**, monotone, and is carried on every matchup. Connectivity refuses two teams the schedule graph has not connected — on 5 Nov, 121 components and **0.4% priceable**. **Home advantage is heterogeneous and fitted, not assumed: high_major +12.36, mid_major +7.34, low_major +3.90 per 100 possessions**, 409 venues, shrunk toward the league mean. |
| 12 | Price backtest over the full bought population, every market, clustered, corrected, replicated | **done** | **86,351 bets** from 1,821,842 quotes, identity reconciling, correction x1.60 from 30 hypotheses. Pooled **-2.5%**, corrected -4.6% to -0.4%. Per tier: high -2.0%, mid -1.9% (both *no demonstrated edge*), low **-3.9%** (*demonstrated deficit*). Replication on held-out 2024: **0 replicated / 0 failed / 0 reversed / 5 nothing to replicate**, and it refused to call a -12.1% holdout cell a replication. |
| 13 | Market-vs-model regression printed for every candidate | **done** | `reports/forecast_skill.py`. **The model loses to the market on Brier in every tier with the vig left in** — pooled advantage **-0.01312 [-0.01468, -0.01156]**; in high-major its Brier is worse than the base rate. Anti-predictiveness is a table: the shortfall widens **11.8pp** from the smallest claimed-edge bucket to the largest, so raising the threshold makes it worse. |
| 14 | Calibration measured on selected bets, not only overall | **built, unrun** | `reports/calibration_on_selected.py`. |
| 15 | Reachability: edge split by whether the price survived | **built; no edge to split yet** | `reachability.py` + `scripts/run_reachability.py`, 41 tests. Three-valued survival, per book and per tier, and it emits **"not reachable"** in those words when an edge lives only in prices that vanished. The store is empty today because it is September, and it says so rather than printing an empty table. |
| 16 | Claims / when-this-ends / why-the-model docs, headline reads the sign | **done** | All three. `docs/why_the_model_does_or_does_not_have_an_edge.md` is **generated from the run record**, not typed, so it cannot drift. The claims doc carries a fenced block the weekly loop re-renders while its pre-measurement framing survives. A pooled verdict no tier shares is now flagged where it happens. |

### Self-operation

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 17 | Experiment ledger append-only, populated, its correction used by the reports | **done** | 30 pre-registered hypotheses, each with a falsifiable direction. Correction **×1.60**. `save()` raises rather than shrinking. The claims report reads it. |
| 18 | Promotion criteria pre-registered on disk; demotion one direction only | **done** | `data/manual/promotion_criteria.json`, declared 2026-09-01 before any challenger was measured. There is no `grant()` in `promotion.py` or `staging_provider_policy.py`, and a test sweeps for one. |
| 19 | The weekly loop runs unattended and re-renders the claims doc itself | **done** | `Weekly Refit and Measure`, Mondays 11:00 UTC, `contents: read` and no credential — it measures what is already bought and cannot spend. 43 tests. It re-renders the fenced block inside `docs/what_we_can_and_cannot_claim.md`; a missing fence is an error and never an append. |
| 20 | `CLAUDE.md` has a "Current operating state" a future session can read, contract strings pinned | **done** | `test_contract_strings.py` pins all 14. |
| 21 | `docs/decision_log.md` and `docs/ported_defects.md` complete | **done** | 20 decisions, **14 defect classes** (A-N) with the regression test for each. N is the word-ban test family reaching six members, three of them on 2026-09-03. |

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
