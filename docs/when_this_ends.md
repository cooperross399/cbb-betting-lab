# When this ends, decided before the data exists

**Written 2026-09-01, before the 2026-27 season starts, before a single price
has been bought, and before a single forward opinion has been frozen.** That
timing is the entire point. A stopping rule chosen after the numbers arrive is
not a stopping rule, it is a justification — and this project has already
watched two sibling labs run to completion, and watched one of them retract its
own headline three times in four days.

Cooper's requirement, verbatim: *"The loop must be able to conclude 'no edge'
and stop. A search that can only terminate in a finding is a random number
generator with good prose."*

## The rule

**Decision date: 2027-04-19.** Fourteen days after the national championship
game on Monday 2027-04-05 — fourteen because that is the settlement patience
window, so every opinion that can settle has. The season runs Sunday 2026-11-01
(one game, Notre Dame v Villanova in Rome) through 2027-04-05; both dates are
verified against the NCAA's own published calendar rather than assumed.

**The measurement**: the forward ledger's pooled return on frozen opinions, one
bet per wager at the best price the card could have taken, clustered by game and
by day, corrected across the experiment ledger's **cumulative** count.

Opinions, not bets: the card is dark and places none, but a frozen opinion
scored against the price it was frozen at is the same test.

**Reported per conference tier, never pooled across Division I.** The rule below
is applied to each tier separately and to the pooled figure, and the pooled
figure is never the headline.

**Sample floor: 10,000 settled opinions across at least 2,000 distinct games.**

That floor is derived, not chosen. About **5,750 D-I-versus-D-I games** are
played a season; books quote the great majority of them; the card prices four to
five team markets a game and freezes an opinion wherever it has a view. A
working pipeline should produce on the order of 23,000 opinions across 4,600
games. **The floor is set at roughly 40% of that**, because a pipeline that
reaches less than half the season did not produce a test — and that is a finding
about the pipeline, not about the model.

It is deliberately more than triple the NHL lab's 3,000. A floor set below what
a season trivially produces is not a floor.

| Result | What it means | What happens |
|:---|:---|:---|
| Corrected interval **excludes zero, positive** | A candidate, on one season | **Not a green light.** A second season confirms or kills it. No stake is placed on one season, ever. |
| Corrected interval **spans zero** | No edge after a clean out-of-sample season | **Stop.** Archive the lab, disable the routines, write the closing note. |
| Corrected interval **excludes zero, negative** | Confirmed loser | **Stop**, same as above. |
| Fewer than 10,000 settled opinions, or fewer than 2,000 games | The test did not run | Diagnose the pipeline. **Do not read the number.** |

### The tier clause

A tier that clears while the pooled figure does not is a **candidate in that
tier only**, and it inherits the same rule: one season is not a green light. A
policy that wins in low-major games and loses in high-major ships in low-major
only, if it ships at all.

And it carries one extra bar that the pooled figure does not, because the whole
reason to look at low-major games is also the reason a low-major result is
suspect: **an edge that lives only in prices that did not survive to the next
capture is reported as not reachable**, in those words, and a not-reachable
candidate does not extend the project. See the reachability section of
`docs/what_we_can_and_cannot_claim.md`.

## What may change before that date, and what may not

**May**: defect fixes. A broken join, a settlement error, a ledger that stops
accumulating, an upstream restatement. Each recorded in `CLAUDE.md` with its
date and what it changed — because **a fix that silently alters what is being
measured is indistinguishable from tuning.**

**May not**: the model, the edge bar, the market list, the staking rule, the
tier definitions, the minimum sample thresholds, or anything else that changes
what is being tested. Not in December because November looked bad. Not in March
because February looked good. **The ledger is a test, and a test whose subject
changes mid-run measures nothing.**

The conference-tier cut points (`conferences.HIGH_MAJOR_MARGIN = 8.0`,
`MID_MAJOR_MARGIN = −3.0`) are named here explicitly because they are the most
tempting thing to adjust: a tier boundary moved by two points can turn a null
into a finding, and there is no honest reason to move one after seeing a return.

**If a mid-season result looks strong, the correct action is nothing.** Write it
down and wait for the date.

## What ends it earlier

Three things, and all three are failures of the instrument rather than of the
model:

1. **The delivery chain stops landing a card** for fourteen consecutive game
   days and the cause cannot be fixed. A lab that cannot deliver is not
   accumulating anything.
2. **A settlement source is withdrawn or its licence changes** such that the
   ledger cannot be settled honestly. A frozen opinion that can never settle is
   not evidence.
3. **The experiment ledger's cumulative count passes the point where nothing
   could clear.** If the correction factor grows large enough that a plausible
   edge could not clear it on a season's sample, the search has spent its
   budget and continuing it is arithmetic theatre. The ledger's own
   `correction_factor()` and `stats.bets_needed_to_detect()` decide that
   together, and it is checked every week rather than noticed in April.

## The honest prior

**Everything measured in the two finished sibling labs says this comes back
null.** The NHL lab bought its full population and found −0.3% over 25,949
wagers with an interval spanning zero. The football lab bought every NFL game
for which historical props exist and found 0 of 18 markets clearing the bars it
had declared in advance. Its deepest result — that the model is a *worse
forecaster than the price it bets into*, Brier 0.26057 against 0.22703 over
74,345 bets — is the one that generalises, because it needs no settlement rule,
no vig assumption and no edge threshold.

The season is worth running because it costs a cron job and a few hundred
thousand credits against an allowance in the millions, and because college
basketball is the one place where a season is large enough to answer the
question decisively either way. **It is not worth running because the odds are
good.**

**A null in April is a real result**, and it is the outcome this document
expects to record.
