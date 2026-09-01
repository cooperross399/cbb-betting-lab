# The build order, against an opening night nine weeks away

**Written as it was executed, 2026-08-31 to 2026-09-01.** Cooper's brief fixed
the order and the reason for it, and it is recorded here rather than only in
commit messages because the *reason* is the reusable part.

> Historical prices can be bought. **Forward evidence cannot be back-dated.**
> Every night the pipeline is not freezing opinions and settling them is a night
> of clean out-of-sample data that is gone permanently — and in this sport a
> night is up to two hundred games.

## 1. The experiment ledger and the verdicts door, before any model existed

So that **the first hypothesis this lab ever tested was already counted.**

The ledger is append-only and its correction factor grows with the cumulative
count. Two additions to the football lab's version, each closing a defect that
lab recorded against itself: a `Hypothesis` cannot be constructed without a
falsifiable `predicted_direction`, and a `stage` of `discovery` or `holdout` is
part of the dedupe key — because **putting a discovery finding to the holdout is
a second look**, and the design collapses if it is not counted as one.

The verdicts door came with it. Nothing ships a modelling policy by assertion:
an experiment writes a verdict file, the model reads it, and the two cannot
drift because there is only one of them. A verdict records the seasons it was
tested on and the seasons it cleared, and `ships()` is false unless those sets
match — which closes the football lab's single-season coin flip, where the same
policy shipped or did not depending on which season had been scored last.

## 2. The data layer, settlement, and the exclusion guards

Eight seasons cached and hashed: 94,194 team-games, 1,493,589 player-games.

The exclusions came before anything was fitted, because a model fitted on the
wrong population cannot be un-fitted. **551 of 6,318 games in 2025-26 have a
non-D-I side and 541 of those fall in November and December** — exactly the
buy-games the brief predicted. Never fitted on, never carded, always counted.

Venue state got three values rather than two on the same principle: **39 of 709
"neutral" games are in a participant's own city and 7 in their own arena.**

**This step found the build's most dangerous defect**, and it found it because
the brief insisted the possession estimator be *validated* rather than assumed.
ESPN's play type is `MadeFreeThrow` — one word — so the obvious
`str.contains("Free Throw")` screen matches none of 253,589 free-throw rows.
Possessions inflated by 15 a game, which was visible. `player_first_basket`
would have settled on whoever made the game's **first free throw**, which was
not.

## 3. The odds staging and the forward-evidence organ, wired and dry-run

Third rather than last, for the reason at the top of this file.

The organ freezes opinions before tip and settles them after, day as unit, never
re-pricing. The CBB-specific rule is that **the first opinion of the day for a
given game is never retroactively replaced** while a later run may still add
games the earlier run could not reach — because the slate spans twelve hours and
one freeze cannot serve it.

Two columns exist here that no sibling lab has, and both are frozen rather than
derived later because neither can be back-dated: `prior_weight`, so a November
number can never be read as a February one, and `tier`, so no pooled Division I
headline can be assembled after the fact.

## 4. Probe retention, then buy the history, then run the price backtest

The step neither sibling lab managed before its season, and the runway existed
to do it.

The arithmetic that makes the probe non-optional: the **pessimistic**
full-catalogue buy is **17.6M credits against a 5M quota**. That bound assumes
every asked-for market returns at every book, which on a low-major Tuesday is
nothing like true — and the only way to replace a bound with a rate is to
measure it. The probe stratifies by conference tier, month and tip window,
because this lab's whole thesis is that the low-major end of the board is priced
differently and a probe that sampled only high-majors would answer a different
question.

## 5. Models: possessions, walk-forward fits, the November prior regime

## 6. Measurement, replication, family-wise correction, reachability

## 7. The weekly loop, the delivery chain, the evidence pack

---

## What the build order got right

**Putting the ledger first.** By the time the first model existed, seven
hypotheses had already been put to the data and counted — the possession
estimator against play-by-play, the day-boundary convention, the season-label
convention, the conference-tier gradient, the overtime rate, the half-tie rate
and the false-neutral rate. Each is a real look, each narrowed something, and a
lab that started counting at its first *model* would have counted none of them.

**Measuring the conventions instead of choosing them.** Three of those seven
looks changed a decision, and two of them reversed one: the day boundary was
reasoned to six hours and measured to zero, and the season label was reasoned
to the starting year and measured to the ending year. Both would have been
silent, and both were caught before a single row was joined.

## What it did not get right

**The card cadence was designed before the slate's shape was measured.** The
first version had one card a day, which the hour-by-hour distribution then made
obviously wrong — 45% of games still to tip at 19:00 ET. It cost nothing because
nothing had been built on it, but the measurement should have come first.

**A test was written that banned a word rather than an assertion**, three
separate times, each in a different module. The house style says an excluded
market is never called a pass or an avoid — and the correct card text *denies*
being those, which the naive check reads as a violation. Recorded in
`docs/ported_defects.md` as a test-writing defect class rather than a one-off.
