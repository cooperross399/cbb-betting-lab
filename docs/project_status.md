# Where this lab is, item by item, with the evidence

**Read `docs/what_we_can_and_cannot_claim.md` before any number here.** This
file says what was *built*; that one says what may be *claimed*, and the two are
not the same thing.

Every row is checkable from the repository without anyone's judgment. A row that
is not done says so, and says what it is waiting on.

Last updated **2026-09-01**.

## The headline

**Nothing has been measured against real prices yet, no market is allowlisted,
nothing is bet, and that is the correct state.** The season opens in 61 days.
The historical purchase is running as this is written; until it finishes and the
backtest scores it, this lab has machinery and no findings — which is exactly
what a lab looks like on the day before its first measurement.

## Definition of Done

### Infrastructure

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 1 | Repo private, CI green on `main`, full suite passes | **done** | `cooperross399/cbb-betting-lab`, private. `Tests` workflow green. 462 tests. |
| 2 | Every workflow on a cron, no laptop | **partly** | Data refresh, board fetch, card publish and post-slate settlement all live in `CBB Gameday Refresh` (4 crons). `Line Movement` has 4 crons. `Provider Quota` daily. **Weekly refit-and-measure is being built.** Probe and purchase are dispatch-only *by design* — a cron on a credit-spending discovery run is a standing order to spend money, and a test enforces their absence. |
| 3 | Delivery chain verified end to end with a real card | **partly, and the gap is one click** | Links 1 and 2 verified with a real dispatch on 2026-09-01: run 33548634161 published `latest_status.json`, `latest_card_comment.md`, `latest_forward_evidence.md`, `latest_what_we_can_claim.md` and `snapshots/2026-09-01.csv` to `card-feed`, and the card was read. **Link 3 is blocked on Cooper granting the Claude Code GitHub app access to this repository** — `docs/delivery_chain.md`. |
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
| 9 | Historical prices bought for every measurable market, store deduped on price identity | **running** | Wave 1 (`core_team`, six seasons) dispatched under a 1,300,000 cap. Dedupe on price identity is pinned by `test_prices_dedupe_on_identity_not_the_row.py`, which caught a real CSV round-trip defect. |
| 10 | Line-movement capture live, price survival recorded | **done** | `Line Movement`, 4 crons a day year-round, 6 credits a capture. Survival is three-valued — a quote the next capture never covered is `unknown`, not `gone`. |

### Models and measurement

| # | Item | State |
|--:|:---|:---|
| 11 | Walk-forward fits, per tier, November prior, connectivity refusing to price | **being built** |
| 12 | Price backtest over the full bought population, every market, clustered, corrected, replicated | **waiting on the purchase** |
| 13 | Market-vs-model regression printed for every candidate | **waiting** |
| 14 | Calibration measured on selected bets, not only overall | `reports/calibration_on_selected.py` exists; unrun |
| 15 | Reachability: edge split by whether the price survived | Instrument live and accumulating; no edge to split yet |
| 16 | Claims / when-this-ends / why-the-model docs, headline reads the sign | **2 of 3 done** — the third is written from the run record and there is no run record yet. `test_the_headline_reads_the_sign.py` already pins the predicate. |

### Self-operation

| # | Item | State | Evidence |
|--:|:---|:---|:---|
| 17 | Experiment ledger append-only, populated, its correction used by the reports | **done** | 30 pre-registered hypotheses, each with a falsifiable direction. Correction **×1.60**. `save()` raises rather than shrinking. The claims report reads it. |
| 18 | Promotion criteria pre-registered on disk; demotion one direction only | **done** | `data/manual/promotion_criteria.json`, declared 2026-09-01 before any challenger was measured. There is no `grant()` in `promotion.py` or `staging_provider_policy.py`, and a test sweeps for one. |
| 19 | The weekly loop runs unattended and re-renders the claims doc itself | **being built** | |
| 20 | `CLAUDE.md` has a "Current operating state" a future session can read, contract strings pinned | **done** | `test_contract_strings.py` pins all 14. |
| 21 | `docs/decision_log.md` and `docs/ported_defects.md` complete | **done** | 16 decisions, 7 defect classes with the regression test for each. |

## What is actually waiting on Cooper

**One thing, and it is not the acceptance receipt yet** — that comes when there
is evidence to sign against.

**Grant the Claude Code GitHub app access to `cbb-betting-lab`**:
`https://github.com/settings/installations` → Claude → Repository access → add
`cbb-betting-lab` → Save. That unblocks link 3 of the delivery chain. The
routine body is committed and creates unchanged afterwards.

## The three numbers worth knowing today

- **77,160 credits** bought the retention probe's answer: all 15 team, ladder
  and half markets are retained and measurable at 93-100% across up to 17 books.
  Five prop markets are measurable, nine are thin, five are not retained at all.
- **20.5% of provider team names did not resolve** until the probe measured it —
  and the misses ran high-major 13%, low-major **53%**, biased directly against
  the hypothesis this lab exists to test. Now 0 of 365.
- **35,173,680 credits** is the full catalogue against a **4,992,714** balance,
  which is why the purchase is prioritised rather than complete.
