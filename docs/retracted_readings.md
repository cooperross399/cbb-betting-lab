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
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | mid_major | `—` | player_threes | always the underdog | -7.30% | 95 | 99 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always home | -3.41% | 30 | 62 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always away | -3.35% | 30 | 49 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | spread | always the favourite | -7.49% | 30 | 76 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | low_major | `—` | team_total | always over | -3.75% | 30 | 38 |
| `holdout/cbb_replication.json` | `markets` | `holdout` | `—` | mid_major | `—` | total_points | — | -6.36% | 62 | 95 |
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | high_major | `—` | spread | always away | -5.14% | 95 | 125 |
| `core_team_only/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | high_major | `—` | spread | always away | -4.02% | 30 | 125 |
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | high_major | `—` | player_assists | always the underdog | -8.00% | 95 | 111 |
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | high_major | `—` | player_rebounds | always the favourite | -4.56% | 95 | 123 |
| `holdout/cbb_price_backtest.json` | `null_baseline` | `—` | `—` | mid_major | `—` | player_rebounds_assists | always the favourite | -6.68% | 95 | 128 |

**None of these
 is a claim that was wrong.** Each was a correctly measured
deficit at the family the lab held when it was scored, and each stopped clearing
the bar as the search grew. The measurement did not move; the number of looks
did. That is the cost of pre-registering honestly, and it is paid in public here
rather than absorbed by re-rendering a report and saying nothing.

**Fifteen of the sixteen are blind null-baseline sides** — "always the
underdog", "always over", "always away" — which are the lab's own control rules,
not model bets. The sixteenth is the replication's held-out `total_points` /
mid-major cell, which `CLAUDE.md` discusses by name.

**Four crossed long before anyone noticed.** The core-team sides crossed at 38,
49, 62 and 76 hypotheses; the ledger reached 101 on 2026-09-10 and no document
had ever mentioned them. They were found by widening the check that is supposed
to enforce this rule, after that check was caught reading one block of one
record.

**Nine were retracted on 2026-09-15 by the residual search.** Registering the 27
residual-regression features took the family from 101 to 128, and the bottom
nine rows are what that cost. Every one of them crossed inside that step: the
high-major `player_assists` underdog side at 111, the high-major
`player_rebounds` favourite side at 123, the high-major `spread` away side at
125, and the mid-major `player_rebounds_assists` favourite side at exactly 128 —
the last hypothesis of the 27 is the one that withdrew it. None of them had been
retracted at 101, and all of them are retracted now.

**The nine are the price of asking 27 questions.** They were not paid to buy a
finding: of the 27, exactly one survived its own correction, and that one
(`d_def_reb_pct`) is a replication of `d_orb`, which the ledger already held. So
this registration withdrew nine published deficits and added no new claim. That
is the honest arithmetic of a search, and the reason the count is written down
before the search rather than after it.

## Five rows left this table on 2026-09-17, and neither cause was a correction

A row here is a claim that a specific reading was withdrawn **by the family
growing**. Five stopped being true at once, for two different reasons, and both
are the opposite of the usual one: the readings did not dissolve under a wider
correction, they stopped being retracted because the measurement under them
changed.

**Four were player-market baseline readings** — `high_major / player_assists`,
`high_major / player_rebounds`, `mid_major / player_rebounds_assists` and
`mid_major / player_threes`, all on the blind null-baseline side. They left
`cbb_price_backtest.json` entirely when the backtest declared its scope: it
measures TEAM markets, and a prop is `run_prop_grading.py`'s, under the
per-wager accounting that script files and the backtest never has. The blind
baseline went from 280 readings to 160. Those four readings are not retracted
now; they are **not in this record at all**, which is a different statement and
has to be made differently.

They are still retracted where they still exist. The rows for
`holdout/cbb_price_backtest.json` stand untouched, because that record has not
been re-scored.

**The fifth, `high_major / spread / always away`, is a team reading that came
back.** Refusing the neutral-court side wagers it could not orient removed
noise from that cell rather than signal — a misgraded row is a sign flip, which
biases a return toward zero and inflates its variance — so the reading sharpened
and stopped being dissolved by the correction at 130.

That is worth stating plainly because it cuts against the direction this file
usually records: **the restatement withdrew nothing and returned one reading.**
It also added two demonstrated deficits that were not there before,
`moneyline / mid_major` and the `low_major` tier. A cleaner measurement found
more losing, not less.
