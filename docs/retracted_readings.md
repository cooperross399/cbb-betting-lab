# Readings this lab published and the family correction has since withdrawn

A registration widens every interval the lab holds, and a wider correction can
only ever **retract** — it can never turn a null into a finding. So every
registration has a cost, the cost is always computable, and this file is where
it is stated.

**Why a table and not prose.** The first version of this rule asked only that a
retracted cell be *named somewhere* in `CLAUDE.md` or `docs/project_status.md`.
That is satisfiable by accident: those documents name cells for reasons of their
own, and 25 readings that are still perfectly live were already "narrated" by
that test, with nothing written about them. A retraction was also invisible if
its cell carried no market (`by_tier` rows) or no tier (`pooled` rows), because
the check gave up before trying — so for 42 readings the instruction "name the
cell" could not be followed at all, and the only way out of a red suite would
have been to weaken the guard.

`tests/test_the_forward_window_is_pre_registered.py` now compares this table
against every scored reading in every published record, **in both directions**:
a retraction missing from this table fails, and a row here for a reading that is
*not* retracted fails too. The second half is what stops the table being
pre-filled to buy silence.

The prose account of what these cost — which verdict moved, and what it means —
lives in `CLAUDE.md`. This file is the ledger of the fact.

| record | block | leaf | season | tier | label | market | rule | ROI | demonstrated at | crossed at |
|:---|:---|:---|:---|:---|:---|:---|:---|---:|---:|---:|
| `cbb_price_backtest.json` | `null_baseline` | `—` | `—` | mid_major | `—` | player_threes | always the underdog | -7.30% | 95 | 99 |
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | mid_major | `—` | player_threes | always the underdog | -7.30% | 95 | 99 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always home | -3.41% | 30 | 62 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always away | -3.35% | 30 | 49 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always the favourite | -7.49% | 30 | 76 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | team_total | always over | -3.75% | 30 | 38 |
| `holdout/cbb_replication.json` | `markets` | `holdout` | `—` | mid_major | `—` | total_points | — | -6.36% | 62 | 95 |

**None of these
 is a claim that was wrong.** Each was a correctly measured
deficit at the family the lab held when it was scored, and each stopped clearing
the bar as the search grew. The measurement did not move; the number of looks
did. That is the cost of pre-registering honestly, and it is paid in public here
rather than absorbed by re-rendering a report and saying nothing.

**Six of the seven are blind null-baseline sides** — "always the underdog",
"always over" — which are the lab's own control rules, not model bets. The
seventh is the replication's held-out `total_points` / mid-major cell, which
`CLAUDE.md` discusses by name.

**Four crossed long before anyone noticed.** The core-team sides crossed at 38,
49, 62 and 76 hypotheses; the ledger reached 101 on 2026-09-10 and no document
had ever mentioned them. They were found by widening the check that is supposed
to enforce this rule, after that check was caught reading one block of one
record.
