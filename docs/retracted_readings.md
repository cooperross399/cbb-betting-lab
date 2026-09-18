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

`tests/test_the_forward_window_is_pre_registered.py` compares this table
against the published readings it can walk, **in both directions**: a
retraction missing from this table fails, and a row here for a reading that is
*not* retracted fails too. The second half is what stops the table being
pre-filled to buy silence.

**"Every scored reading in every published record" is what this section said
until 2026-09-18, and it was false.** The walker recognises a reading by a
stored point estimate beside a stored standard error, and `cbb_ratings_fit.json`
-- a published record, on the generated record census, scored at its own family
size -- keys its point estimate `mean`, which the walker did not read. That
record contributed nothing, and the test that exists to catch a record missing
from the roster could not report it, because that test derives its own
expectation by calling the same walker: the roster and the walker agreed with
each other and neither could see the hole. That is this repository's own written
lesson, *a roster only guards what it names*, with the walker standing in the
roster's place. The walker reads `mean` now and the record is on the roster.

**The limit that remains, stated rather than rounded off.** A retraction is a
statement about an interval's width, so a cell that publishes a verdict with no
stored standard error cannot be classified as retracted at all and is not
walked. Five records hold at least one such cell — `cbb_forecast_skill.json`,
`cbb_prop_grading.json`, `cbb_retention_probe.json`,
`cbb_what_we_can_claim.json` and `cbb_why_the_model.json` — and that list is
not typed on trust:
`test_the_records_this_file_says_the_walker_cannot_classify_are_the_records_it_cannot_classify`
derives it from the records and fails if this paragraph names a record too many
or too few. Those verdicts are re-derived at the ledger's cumulative count by
the reports that render them, which is a different check and a weaker one.

The prose account of what these cost — which verdict moved, and what it means —
lives in `CLAUDE.md`. This file is the ledger of the fact.

| record | block | leaf | season | tier | label | market | band | rule | ROI | demonstrated at | crossed at |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|---:|---:|---:|

**The table is empty, and that is a state rather than a clean bill of health.**
Every row it has ever carried is accounted for in the generated block below,
which is read from the records at the revisions that changed them. A row was
never a claim that was wrong: each was a correctly measured deficit at the
family its record held when it was scored.

**Why the mechanism is GENERATED and not written.** A claim about why a reading
left this table is a diff of two records across a commit — what the estimate
did, what the standard error did, what the population did, and at what family
size the reading stopped excluding zero. Three successive adversarial reviews
found one of those claims false on this page, and every one of the three was
false in the direction that flattered this lab: a cell said to carry no scored
reading that the repository's own walker finds and reads; a cell said to have
"come back" and "sharpened" whose estimate-over-error FELL across the very
restatement being narrated; five cells said to have "come back" of which none
did and four blunted. A false and flattering sentence in the retraction ledger is
the worst thing this repository can publish, because this file's only purpose is
to be honest about what was withdrawn.

The rule taken from that is the one already applied to the counts, one layer
further in: **a mechanism that is not computed is not asserted.** The prose here
frames, dates and explains the policy. It states no estimate, no error, no
population, no crossing point and no direction. Those are below, rendered by
`scripts/splice_headline_table.py` from `git show <rev>:<path>`, with the family
size held FIXED at the ledger's count across every state so that what moves in
the block is the measurement and never the search.

<!-- BEGIN GENERATED: retraction_history -->

**What each reading this table has ever named actually did.** Every row below is read from the records with `git show`, at the ledger's 133 cumulative hypotheses held FIXED across every state, so what moves here is the measurement and never the family. **That is why this block cannot be read as evidence about what the family did** — it is built to exclude exactly that, and the `Scored at` column is the only place the family appears. Three of the readings below moved because the count they were scored at grew; the prose beneath names them and shows the arithmetic. The roster is the table's own history: a reading this file has ever listed as retracted is a reading this block accounts for. `|est|/se` is the estimate over its own standard error — a reading that SHARPENED across a restatement has a larger one after than before, and one that BLUNTED has a smaller one. Nothing in the prose of this file states a direction; this is where a direction may be read.

| Stage | State | Reading | Estimate | Standard error | Bets | \|est\|/se | Scored at | Crossed at | Verdict | Retracted at today's count |
|:---|:---|:---|---:|---:|---:|---:|---:|---:|:---|:---|
| before | 524aae8 | `cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | -0.07997 | 0.02281 | 3,200 | 3.51 | 95 | 111 | demonstrated deficit | yes |
| after | a2850ff — Restate the backtest with the neutral-court rows excluded (#83) | `cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | — | — | — | — | — | — | not in the record | no |
| today | on disk | `cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | -0.04563 | 0.01291 | 4,070 | 3.54 | 95 | 123 | demonstrated deficit | yes |
| after | a2850ff — Restate the backtest with the neutral-court rows excluded (#83) | `cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | — | — | — | — | — | — | not in the record | no |
| today | on disk | `cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.04024 | 0.01137 | 18,780 | 3.54 | 95 | 125 | demonstrated deficit | yes |
| after | a2850ff — Restate the backtest with the neutral-court rows excluded (#83) | `cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.03310 | 0.01262 | 15,267 | 2.62 | 130 | 6 | no demonstrated edge | no |
| today | on disk | `cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.03310 | 0.01262 | 15,267 | 2.62 | 133 | 6 | no demonstrated edge | no |
| before | 524aae8 | `cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | -0.06681 | 0.01885 | 2,081 | 3.54 | 95 | 128 | demonstrated deficit | yes |
| after | a2850ff — Restate the backtest with the neutral-court rows excluded (#83) | `cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | — | — | — | — | — | — | not in the record | no |
| today | on disk | `cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | -0.07297 | 0.02099 | 3,758 | 3.48 | 95 | 99 | demonstrated deficit | yes |
| after | a2850ff — Restate the backtest with the neutral-court rows excluded (#83) | `cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | — | — | — | — | — | — | not in the record | no |
| today | on disk | `cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | — | — | — | — | — | — | not in the record | no |
| before | 129ce0f | `core_team_only/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.04024 | 0.01137 | 18,780 | 3.54 | 30 | 125 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `core_team_only/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.03310 | 0.01262 | 15,267 | 2.62 | 130 | 6 | no demonstrated edge | no |
| today | on disk | `core_team_only/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.03310 | 0.01262 | 15,267 | 2.62 | 130 | 6 | no demonstrated edge | no |
| before | 129ce0f | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always away | -0.03346 | 0.01020 | 23,392 | 3.28 | 30 | 49 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always away | -0.03779 | 0.01066 | 21,393 | 3.54 | 130 | 127 | no demonstrated edge | no |
| today | on disk | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always away | -0.03779 | 0.01066 | 21,393 | 3.54 | 130 | 127 | no demonstrated edge | no |
| before | 129ce0f | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always home | -0.03409 | 0.01018 | 23,392 | 3.35 | 30 | 62 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always home | -0.02985 | 0.01065 | 21,393 | 2.80 | 130 | 10 | no demonstrated edge | no |
| today | on disk | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always home | -0.02985 | 0.01065 | 21,393 | 2.80 | 130 | 10 | no demonstrated edge | no |
| before | 129ce0f | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always the favourite | -0.07485 | 0.02198 | 1,320 | 3.41 | 30 | 76 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always the favourite | -0.07419 | 0.02285 | 1,220 | 3.25 | 130 | 43 | no demonstrated edge | no |
| today | on disk | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always the favourite | -0.07419 | 0.02285 | 1,220 | 3.25 | 130 | 43 | no demonstrated edge | no |
| before | 129ce0f | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / team_total / always over | -0.03753 | 0.01169 | 15,715 | 3.21 | 30 | 38 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / team_total / always over | -0.03335 | 0.01238 | 14,552 | 2.69 | 130 | 8 | no demonstrated edge | no |
| today | on disk | `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / team_total / always over | -0.03335 | 0.01238 | 14,552 | 2.69 | 130 | 8 | no demonstrated edge | no |
| before | 524aae8 | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | -0.07997 | 0.02281 | 3,200 | 3.51 | 95 | 111 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | — | — | — | — | — | — | not in the record | no |
| today | on disk | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_assists / always the underdog | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | -0.04563 | 0.01291 | 4,070 | 3.54 | 95 | 123 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | — | — | — | — | — | — | not in the record | no |
| today | on disk | `holdout/cbb_price_backtest.json` / null_baseline / high_major / player_rebounds / always the favourite | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `holdout/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.05142 | 0.01453 | 11,163 | 3.54 | 95 | 125 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `holdout/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.04685 | 0.01590 | 9,047 | 2.95 | 130 | 16 | no demonstrated edge | no |
| today | on disk | `holdout/cbb_price_backtest.json` / null_baseline / high_major / spread / always away | -0.04685 | 0.01590 | 9,047 | 2.95 | 130 | 16 | no demonstrated edge | no |
| before | 524aae8 | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | -0.06681 | 0.01885 | 2,081 | 3.54 | 95 | 128 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | — | — | — | — | — | — | not in the record | no |
| today | on disk | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_rebounds_assists / always the favourite | — | — | — | — | — | — | not in the record | no |
| before | 524aae8 | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | -0.07297 | 0.02099 | 3,758 | 3.48 | 95 | 99 | demonstrated deficit | yes |
| after | 72d0f0b — Restate the held-out and core-team cuts the same way (#84) | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | — | — | — | — | — | — | not in the record | no |
| today | on disk | `holdout/cbb_price_backtest.json` / null_baseline / mid_major / player_threes / always the underdog | — | — | — | — | — | — | not in the record | no |
| before | 129ce0f | `holdout/cbb_replication.json` / markets / holdout / mid_major / total_points | -0.06364 | 0.01836 | 8,214 | 3.47 | 62 | 95 | demonstrated deficit | yes |
| after | c8f902d — Hand the model the roster frame it declares, and re-measure everything (#87) | `holdout/cbb_replication.json` / markets / holdout / mid_major / total_points | -0.06364 | 0.01836 | 8,214 | 3.47 | 133 | 95 | no demonstrated edge | no |
| today | on disk | `holdout/cbb_replication.json` / markets / holdout / mid_major / total_points | -0.06538 | 0.01847 | 8,267 | 3.54 | 133 | 125 | no demonstrated edge | no |

**Of the 8 reading(s) whose verdict moved, 3 moved because the family grew.** Each row takes the AFTER measurement and corrects it at the count the reading was scored under BEFORE: still a deficit there means the measurement did not remove it and the search did. This block holds the family fixed everywhere else, so this is the only place it can be read.

| reading | after-measurement | at the family it was scored under before | at the family it was scored under after |
|:---|---:|---:|---:|
| `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always away | -0.03779 ± 0.01066 | 30: high **-0.00427** | 130: high **+0.00007** |
| `core_team_only/cbb_price_backtest.json` / null_baseline / low_major / spread / always the favourite | -0.07419 ± 0.02285 | 30: high **-0.00235** | 130: high **+0.00694** |
| `holdout/cbb_replication.json` / markets / holdout / mid_major / total_points | -0.06364 ± 0.01836 | 62: high **-0.00212** | 133: high **+0.00166** |

*16 reading(s) this table has named; 16 of them stopped being retracted at a state this block can name, 0 did not.*

**How many demonstrated deficits each walked record holds today.** A tier or a cell whose corrected interval lies entirely below zero is a demonstrated deficit — a different statement from *no demonstrated edge*, and one this file has published as ZERO about a record that held dozens. Counted here from the `verdict` each record stores, per block, so neither the tally nor the population can be typed.

| Record | Graded bets | Games | Demonstrated deficits, by block |
|:---|---:|---:|:---|
| `cbb_forecast_skill.json` | — | — | by_tier 9, pooled 20, selected 20 |
| `cbb_price_backtest.json` | 175,690 | 26,622 | all_opinions 1, by_market_and_tier 5, by_tier 2, null_baseline 31, pooled 4 |
| `cbb_prop_grading.json` | — | — | by_market_and_tier 5 |
| `cbb_ratings_fit.json` | — | — | none |
| `cbb_what_we_can_claim.json` | — | — | claims 5, pooled 4 |
| `core_team_only/cbb_price_backtest.json` | 145,739 | 26,615 | all_opinions 1, by_market_and_tier 5, by_tier 3, null_baseline 27, pooled 4 |
| `holdout/cbb_price_backtest.json` | 110,682 | 16,812 | all_opinions 1, by_market_and_tier 1, null_baseline 23, pooled 3 |
| `holdout/cbb_replication.json` | — | — | by_tier 2, markets 5, pooled 4 |

*Generated by `scripts/splice_headline_table.py` from the records in `data/outputs/` and from each revision that changed them. Do not edit between the markers; re-run the script.*

<!-- END GENERATED -->

**What the block above will and will not tell you.** It says what each reading
did and when. It does not say what CAUSED the record to change — that is a
statement about a commit's intent, not about two blobs, and where it is known it
is written in the dated sections below beside the commit that made it. Where it
is not known it is not established, and this file says so in those words rather
than reaching for the likely-sounding reason. The likely-sounding reason has now
been wrong here three times running.

**The residual search of 2026-09-15 is the one cause this file can still name
without diffing anything.** Registering the 27 residual-regression features took
the family from 101 to 128, and rows were withdrawn by that step alone: a wider
correction can only ever retract, so a reading whose crossing point lies inside
`[101, 128]` was withdrawn by the registration and by nothing else. Which
readings those are, how many, and where each crossed is the `Crossed at` column
of the block above — counted there rather than stated here, because a tally
typed into prose is the class of figure this page spent five rounds removing.
They were not paid to buy a finding: of the 27, exactly one survived its own
correction, and that one (`d_def_reb_pct`) is a replication of `d_orb`, which
the ledger already held. So the registration withdrew published deficits and
added no new claim. That is the honest arithmetic of a search, and
the reason the count is written down before the search rather than after it.

## 2026-09-17: every row left this table, and three of them left because the family grew

A row here is a claim that a specific reading was withdrawn **by the family
growing**. Every one of them stopped being true on one day. Until 2026-09-18
this section said that growth of the family removed none of them, and reasoned
it from the block above — which holds the correction FIXED at the ledger's count
across every state. **That reasoning is backwards and the claim was false.** The
block fixes the family precisely so that what moves in it is the measurement;
fixing it is therefore the one thing that makes the block unable to say what the
family did. The sentence used a design decision as evidence for the conclusion
that decision was built to exclude, and it did so in the flattering direction:
it told a reader the lab's registrations had cost these readings nothing.

**The block above now answers it, generated.** It takes each reading whose
verdict moved, corrects the AFTER measurement at the count that reading was
scored under BEFORE, and reports how many were still a deficit there — which
means the measurement did not remove them and the search did. The count and the
per-reading arithmetic are in the block; they are not restated here, because a
figure typed beside a generated one is the thing this whole file keeps getting
wrong. The clearest of them has an estimate, a standard error and a bet count
that are byte-identical at `129ce0f` and `c8f902d`, with the count it was scored
at as the only field that moved. Nothing about that measurement changed. The
search did, and the reading went.

**Why the table above is nonetheless empty, and this is a limit rather than a
result.** `tests/test_the_forward_window_is_pre_registered.py` decides retraction
from a record's OWN window: the count it stores as scored, against the ledger's
count today. All three records were re-scored at the wider count, so each window
is zero wide and the test sees no retraction — and, because the table is checked
in both directions, a row added for any of these three would fail as a row for a
reading that is not retracted. The table cannot hold them.

So the file's title promises more than its table can carry. The title is about
readings the correction has withdrawn ACROSS published records; the table is
about readings a single record's own window shows as withdrawn. The three above
are the gap, they are named here because prose is the only place they fit, and
the emptiness of the table is not evidence that the family cost nothing.

What moved the other five was the records underneath, which were rebuilt three
times in that day. What each reading did across each rebuild is in the block, per
reading, before and after. What follows is the dated account of why each rebuild
happened — the part a diff cannot supply, and the only part this prose is
allowed to assert.

**2026-09-17, the neutral-court exclusion (#83, #84).** `home` in a price
selection is the team the PRICE PROVIDER designated home; `home_away` in the
results table is ESPN's, and on a neutral court the two disagree about a third
of the time. Side wagers this store cannot orient are refused rather than
graded, in all three price-backtest cuts. That moves the population under every
blind baseline side, and therefore the estimate and the standard error under
every one of them — in whichever direction the arithmetic goes. The directions
are in the block above, and this paragraph asserts none of them.

**2026-09-17, the scope declaration (#83, #84).** The price backtest measures
TEAM markets; a prop is `run_prop_grading.py`'s, under the per-wager accounting
that script files and the backtest never has. The prop rows left `all_opinions`
and `null_baseline` in the full-store and discovery cuts. A reading that is not
in a record is not retracted and is not un-retracted — it is a different
statement, and the block above makes it by printing *not in the record* rather
than a number. The core-team cut carries only the four core team markets, so it
never held a prop reading to lose.

**2026-09-17, the roster seam (#87).** The price backtest was found never to
have handed the ratings model its roster evidence: the pricer passed the player
table under the walk-forward guard's name, `player_history`, while
`models.ratings.matchups_for` declares `player_games`, so the frame was dropped
and the parameter's default absorbed it. Every measurement this lab had
published was made by a model with its roster terms switched off. All three
price-backtest cuts and the replication were re-measured against the connected
model, and the replication's held-out cell — the one row here that was never a
blind null-baseline side, the one `CLAUDE.md` discusses by name — left in that
rebuild.

### Three claims this file made about those rebuilds, and what each was worth

Every one of the three was written by hand, every one asserted a MECHANISM, and
every one was found false by the next adversarial review — each time in the
direction that flattered this lab. They are listed rather than deleted, because
a retraction file that edits its own history is not a record of anything, and
because three in three rounds is the evidence that this class of sentence does
not survive being typed.

1. **"That cell no longer carries a scored reading at all — its sample fell
   below the bar."** Said of the replication's held-out `total_points` /
   mid-major cell. The repository's own walker yields that cell and the block
   above prints its reading, its population and its verdict. What actually
   removed the row is structural and duller: the record was re-scored at the
   ledger's current count, so the row now stores the same count it is compared
   against, the retraction window `[scored, looks]` is zero wide, and
   `_readings_across_every_record` can classify nothing in that record as
   retracted. The row cannot be restored either — the surplus half of
   `test_the_registration_cost_is_paid_by_everything_already_published` would
   reject it, correctly, for a reading that is not retracted at today's count.

2. **"A team reading that came back … the reading sharpened."** Said of
   `high_major / spread / always away` after the neutral-court exclusion. The
   block above prints estimate-over-error on both sides of that commit.

3. **"Five were team readings in `core_team_only/` that came back … sharpened
   out of being dissolved."** The block above prints all five, before and
   after. It also prints the verdict each carries today.

None of the three needed judgement to get right; each is two `git show`s and a
division. They were wrong because they were typed, and that is the whole reason
the block above exists.

**A fourth claim, about which record a reading left.** This file said that five
readings left `holdout/cbb_price_backtest.json` when the backtest declared its
scope. `high_major / spread / always away` is a team side, not a prop: it
survived the scope declaration and was re-measured by the exclusion, and the
block above prints its reading in that record today.

**What the rebuilds did to the findings is COUNTED, in the second table of the
generated block above.** This section published *"the record in
`data/outputs/holdout/` still shows ZERO demonstrated deficits … before and
after"*, in the present tense and with no scope, until 2026-09-18. That record
holds demonstrated deficits today; one of them arrived in the very rebuild this
section narrates; and the population quoted beside the claim was one no record
on disk stated. The fifth round's response to that sentence was to attach a
source marker to the stale figure rather than to correct the sentence — and
removing a guard's ability to see a false sentence is not fixing the sentence.

**And that record is the DISCOVERY window, not the held-out one.** The sentence
here first called it "the held-out cut ... the result that matters most", which
was wrong, and wrong in the direction that flatters: `data/outputs/holdout/` is
the directory a replication run points `--output-dir` at, and the price-backtest
record inside it covers seasons **2021-2024** — the discovery window, 16,812
games. The genuinely held-out seasons are 2025 and 2026, 9,810 games, and their
result lives only inside `holdout/cbb_replication.json`, where it remains **0
replicated / 0 did not replicate / 0 reversed**.

So whatever that record shows, it shows it over the seasons the model was
developed on, which is a weaker and different thing than what was published
here — and the sentence that stood here made the stronger claim twice over,
once by naming the wrong window and once by stating a deficit count that was
false. Both are corrected in place rather than rewritten, because this is the
file that records what this lab got wrong. The deficit counts themselves are in
the generated block above, per record, and are not restated in prose.

The mechanism was the same one that produced the settlement defect four commits
earlier: two vocabularies sharing a word — `holdout/` the directory and "held
out" the seasons — joined on the word. `price_backtest.render` stored
`season_label` in every record and printed it in none, so no report could tell
the two windows apart. It prints the seasons now. How many demonstrated
deficits each cut holds after the rebuilds is counted in the generated block
above, per record and per block; it used to be typed here and it went stale the
next time a record was rendered.

## The table is empty, and the narration is what survives

**Every row this file ever held has now left it.** That is not a clean bill of
health and should not be read as one: the table is empty because the records
underneath it were rebuilt three times in two days — the neutral-court
exclusion, the scope declaration and the roster seam — and a retraction is a
statement about a specific reading in a specific record. What each of those
readings did is in the generated block at the top of this file. What survives in
prose is the dated account of why the rebuilds happened, and the list of the
claims this file got wrong about them.

## 2026-09-17: five published `demonstrated edge` verdicts were withdrawn, and the family did not withdraw any of them

The graded export's column projection was fixed on 2026-09-17 and
`cbb_forecast_skill.json` was regenerated for the first time since
2026-09-05. Five records in `data/outputs/` were rewritten by this change and every
other one was left byte-identical. Comparing **every** verdict cell in all five
against the counterpart it had before — 170 in the forecast record, of which 31
had a counterpart to be compared against and 139 are cells that record gained;
208 in `cbb_price_backtest.json`, 316 in `cbb_prop_grading.json`, 76 in
`holdout/cbb_replication.json` and 100 in `cbb_why_the_model.json` — **five
verdicts moved, all in the same direction, all five in the forecast record, and
all five the disagreement coefficient**. The price backtest moved 0 of 208, the
prop grading 0 of 316, the replication 0 of 76 and the why-the-model record 0 of
the 58 it already had; the 42 it gained are the anti-predictive block, which had
never rendered.

**Until 2026-09-18 this paragraph said FOUR records and enumerated four.** The
one it omitted was `cbb_prop_grading.json`, and it was the worst one to omit:
its family widened from 95 to 133 in this same change, which is the one kind of
move that can only ever retract, and the sweep that claimed to compare *every*
verdict cell skipped all 316 of them. They moved 0, so the conclusion held — but
it held by luck rather than by the check, and the sentence was in the present
tense with no marker, which is the same structural position as the two false
completeness claims corrected above it.

| cell | published | today | rows |
|:---|:---|:---|---:|
| `selected / by_tier / high_major / fit / disagreement` | +0.23943, [+0.00271, +0.47615], *demonstrated edge* | +0.13048, [-0.12026, +0.38122], **no demonstrated edge** | 24,600 [superseded: 24,600 on 2026-09-17] → 21,296 |
| `selected / by_tier / mid_major / fit / disagreement` | +0.26710, [+0.01906, +0.51514], *demonstrated edge* | +0.08320, [-0.17717, +0.34356], **no demonstrated edge** | 51,053 [superseded: 51,053 on 2026-09-17] → 46,905 |
| `selected / pooled / fit / disagreement` | +0.23471, [+0.08805, +0.38136], *demonstrated edge* | +0.10444, [-0.05139, +0.26027], **no demonstrated edge** | 110,316 [superseded: 110,316 on 2026-09-17] → 100,856 |
| `pooled / fit / disagreement` | +0.09421, [+0.00305, +0.18537], *demonstrated edge* | +0.03190, [-0.06675, +0.13056], **no demonstrated edge** | 293,661 [superseded: 293,661 on 2026-09-17] → 270,504 |
| `raw_market_fit / disagreement` | +0.09387, [+0.00268, +0.18505], *demonstrated edge* | +0.03160, [-0.06707, +0.13028], **no demonstrated edge** | 293,661 [superseded: 293,661 on 2026-09-17] → 270,504 |

The "published" intervals above are each cell's old measurement **already
widened to today's family of 133** — which is how they were being published,
because `scripts/splice_headline_table.py` re-corrects a record's stored
standard error at the current count every time it renders. Only the first row
reached the two hand-written documents; the other four were published in
`data/outputs/cbb_forecast_skill.{json,md}`. The last two are pooled Division I
cells and are not headline figures here for that reason.

**No row of the table above belongs in the table at the top of this file, and
the reason is the whole point of separating the two causes.** A row there is a
claim that a reading was withdrawn **by the family growing**. None of these was.
Both counterfactuals were computed with the repository's own
`stats.bonferroni_z`:

| cell | family 30→133 alone | re-measurement alone | family's share of the move |
|:---|:---|:---|---:|
| selected / high_major | -0.02827, **still excludes zero** | -0.12216, **crosses zero** | 18.8% |
| selected / mid_major | -0.02948, **still excludes zero** | -0.19552, **crosses zero** | 13.1% |
| selected / pooled | -0.01754, **still excludes zero** | -0.13891, **crosses zero** | 11.2% |
| all-opinions / pooled | -0.01101, **still excludes zero** | -0.06937, **crosses zero** | 13.7% |
| raw_market_fit | -0.01101, **still excludes zero** | -0.06932, **crosses zero** | 13.7% |

(The share is the mean of the two orderings — family first, then data; data
first, then family — because the two paths do not attribute identically and
picking one would be a choice, not a measurement. Each counterfactual's
zero-crossing verdict is the same in both orderings.)

Read the columns and the arithmetic is unambiguous: **the family did not retract
any of these, and would not have.** Held at the old measurement, the old
estimate still excluded zero at 133 registrations in every one of the five. Cell
by cell, the family size each would have needed to cross: **156** for
`selected / high_major`, **390** for `selected / mid_major`, **211** for
`pooled` (all opinions), **200** for `raw_market_fit`, and
`selected / pooled` does not cross until a family size in the millions —
a search no lab could run, which is a stronger statement than any
particular ceiling and needs no figure typed to make it.
Held at the old family of 30, the NEW measurement already spans zero in all
five. Four of the five do not exclude zero **even uncorrected, at a single
look**: the raw z on the new measurements is 1.851, 1.136, 1.150 and 1.139, and
only `selected / pooled` (2.384) clears 1.96 before any correction at all.

**And it is the estimate that moved, not the sample.** The populations fell 8%
to 13%, which lifted the standard errors by only 5% to 8%; the point estimates
fell by 46% to 69%. Substituting the new standard error into the old estimate
leaves two of the five still above zero, and the other three only just below it
(-0.011, -0.004 and -0.005 against total moves of -0.150, -0.080 and -0.080). A reading withdrawn because a lab
asked more questions and a reading withdrawn because the number itself changed
are different facts, and these are the second kind.

**What is NOT established here is which change moved the measurement.** The
committed record was rendered 2026-09-05 at `record_version: 4`; the
regenerated one is `record_version: 6`, twelve days and five commits later. In
that window the neutral-court side wagers were refused, the backtest declared
its team-market scope, and the ratings model was handed the roster frame it
declares and re-measured — any of which moves a disagreement coefficient, and
the last of them is a change to the model's own probabilities. The frame those
older numbers were fitted on is not retained, so the per-commit attribution
cannot be computed from anything on disk and is not asserted. What is asserted
is the split above, which can be.

**The previous delivery report said "the restoration retracts nothing already
published."** That was false, and it is recorded here rather than corrected
silently, because a file that edits its own history is not a record of anything.

### A third consequence, which is not a retraction and has to be recorded somewhere

The same regeneration made `why_the_model.render`'s anti-predictive paragraph
reachable for the first time. It had never run: the block is gated on the
forecast record's version and on the block being populated, and until the
realised-return column was carried it was neither. The first sentence it emits
contained the word *guaranteed* — about overconfidence being an artefact of the
model's own selection, not about a result — and that word is in
`what_we_can_claim.FORBIDDEN_PHRASES`, which `why_the_model.write_report`
applies to the **rendered text**. So `scripts/run_why_the_model.py` exited 2 and
`docs/why_the_model_does_or_does_not_have_an_edge.md` could no longer be rebuilt
at all. At the commit before, the same command exits 0.

That is worth stating because of how it would have read. The four red
`test_why_the_model` tests were red at that commit too, so "pre-existing" was a
true description of the RED and a false description of the REMEDY: before, the
document was stale and one command fixed it; after, the command refused. The
sentence is reworded — not the gate — and the document is rebuilt, which is
where the low-major demonstrated deficit and the other 23 measured buckets reach
a reader for the first time.

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
   **This is now the first thing to reach for on this page and not the last.**
   The `retraction_history` fence renders what each reading this table has ever
   named actually did — estimate, standard error, population, crossing point
   and verdict, at the state before a restatement, at the state after it, and
   on disk today — by reading the records at each revision with
   `git show <rev>:<path>`. A MECHANISM is as generatable as a count, and three
   rounds of false-and-flattering mechanisms on this page are what it cost to
   learn that.
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

- [src: 9,810 in data/outputs/holdout/cbb_replication.json#/holdout/games] — games in the genuinely held-out seasons.
- [src: 16,812 in data/outputs/holdout/cbb_price_backtest.json#/games] — games in the discovery window.
- [src: 21,296 in data/outputs/cbb_forecast_skill.json#/selected/by_tier/0/rows] — rows behind the re-scored `selected / high_major` reading.
- [src: 46,905 in data/outputs/cbb_forecast_skill.json#/selected/by_tier/1/rows] — rows behind the re-scored `selected / mid_major` reading.
- [src: 100,856 in data/outputs/cbb_forecast_skill.json#/populations/selected/rows] — rows behind the re-scored `selected / pooled` reading.
- [src: 270,504 in data/outputs/cbb_forecast_skill.json#/populations/all_opinions/rows] — rows behind the two re-scored all-opinions readings.

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
