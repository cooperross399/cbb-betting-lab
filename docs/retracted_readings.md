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

They were still retracted where they still existed — for one day. On
2026-09-17 the held-out and core-team cuts were re-scored the same way, and
their rows went too.

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

## Ten more rows left on 2026-09-17, when the other two cuts were restated

`holdout/` and `core_team_only/` carried the same defect as the record above and
were re-scored with the same exclusion. Ten more rows stopped being true, by the
same two mechanisms and in the same proportion.

**Five were prop baseline readings in `holdout/`** — the same four families as
before plus `high_major / spread / always away` — which left that record when
the backtest declared its scope. They are not retracted; they are not in that
record. The sentence above, written the day before, said those rows stood
untouched because the record had not been re-scored. It has now, and the
sentence is corrected rather than quietly deleted, because a retraction file
that edits its own history is not a record of anything.

**Five were team readings in `core_team_only/` that came back** — four low-major
sides and one high-major — sharpened out of being dissolved once the 39,909
neutral-court wagers that cut cannot orient were refused.

**What the two restatements did to the findings.** The record in
`data/outputs/holdout/` still shows ZERO demonstrated deficits over 110,839
bets, before and after.

**And that record is the DISCOVERY window, not the held-out one.** The sentence
here first called it "the held-out cut ... the result that matters most", which
was wrong, and wrong in the direction that flatters: `data/outputs/holdout/` is
the directory a replication run points `--output-dir` at, and the price-backtest
record inside it covers seasons **2021-2024** — the discovery window, 16,815
games. The genuinely held-out seasons are 2025 and 2026, 9,776 games, and their
result lives only inside `holdout/cbb_replication.json`, where it remains **0
replicated / 0 did not replicate / 0 reversed**.

So zero deficits over 2021-2024 is a statement about the seasons the model was
developed on, which is a weaker and different thing than the one that was
published here. It is corrected in place rather than rewritten, because this is
the file that records what this lab got wrong.

The mechanism was the same one that produced the settlement defect four commits
earlier: two vocabularies sharing a word — `holdout/` the directory and "held
out" the seasons — joined on the word. `price_backtest.render` stored
`season_label` in every record and printed it in none, so no report could tell
the two windows apart. It prints the seasons now. The core-team cut went
from five demonstrated deficits to **seven**: `high_major` joined mid- and
low-major, so on the four core team markets every measured tier is now a
demonstrated deficit.

Across all three records the direction is the same one this file keeps having to
record in the unusual direction: the correction withdrew nothing and returned
six readings, and cleaner measurement found MORE losing rather than less.

## And the last row went when the model was given its roster

`holdout/cbb_replication.json | markets | holdout | mid_major | total_points`
was the one row here that was never a blind null-baseline side — the
replication's held-out cell, the one `CLAUDE.md` discusses by name. It is not
retracted any more, and the reason is not a correction either.

On 2026-09-17 the price backtest was found never to have handed the ratings
model its roster evidence: the pricer passed the player table under the
walk-forward guard's name, `player_history`, while `models.ratings.matchups_for`
declares `player_games`, so the frame was dropped and the parameter's default
absorbed it. Every measurement this lab has published was made by a model with
its roster terms switched off. Re-scored with them connected, that cell no
longer carries a scored reading at all — its sample fell below the bar — so a
row claiming it was withdrawn by the family growing is no longer true.

**Every row this file ever held has now left it.** That is not a clean bill of
health and should not be read as one: the table is empty because the records
underneath it were rebuilt three times in two days — the neutral-court
exclusion, the scope declaration, and the roster seam — and a retraction is a
statement about a specific reading in a specific record. What survives is the
narration above, which is why it is kept.
