# What the evidence actually supports

**Written 2026-09-01, before the first measurement, before a single price has
been bought, and before a single forward opinion has been frozen.** That timing
is the whole point of the file. A document explaining how to read a number,
written after the number arrives, is not a rule — it is a justification.

This is the fourth lab to write this document. The EPL lab wrote it late, after
a season of cards had already been produced. The NHL lab wrote it first, and it
is the reason that lab could report a null on 73,918 bets without flinching.
The football lab wrote it first again. This one is written first again, and it
is written knowing something the other three did not know when they started:
**two of them have now finished, and both measured no edge.**

## The current position, stated plainly

**Nothing here has been measured. There is no edge, no model, no bought price
and no settled opinion.** Every claim this project will ever make about college
basketball rests on evidence that does not exist yet. When it does exist, this
document says how to read it.

The honest prior is the two finished labs. The NHL lab bought its full
population — 2,710 events, 1,261,440 price rows — and found **−0.3% over 25,949
wagers, interval −1.5% to +0.9%**, which includes zero. The football lab bought
every NFL game for which historical props exist — 816 events, 5.67M price rows
— and found **0 of 18 markets clearing the bars declared in advance**. Two labs,
two routes, one answer.

This lab starts from the assumption that it will reach the same answer, and its
job is to reach it *decisively* rather than optimistically.

## The rules this document enforces

Carried over from the sibling labs unchanged, because they were earned and
nothing about basketball weakens them.

- **A number without a sample size is not a result.** Every figure in every
  report prints its `n`.
- **An interval that includes zero means "no demonstrated edge".** In those
  exact words — not "promising", not "trending positive", not "small but
  positive". A +12% return over 40 bets and a coin flip are the same claim at
  that sample size.
- **Calibration can rule a model out. It can never rule one in.** Where a
  price-based test exists, it decides. This rule carries its own two receipts:
  in the EPL lab a change that improved calibration on every market cost about
  140 units in the backtest, and in the NHL lab the by-ice-time correction
  straightened every volume bucket and lost 37.6 units in the only form a card
  could actually apply it. The rule without those two receipts is an assertion.
- **"Conditioned on what, known when?"** on every adjustment. The NHL lab found
  a correction worth +162.8u on *actual* ice time that lost −37.6u on *expected*
  ice time — the only version a card can use. Hindsight leaks look exactly like
  edges.
- **Family-wise correction across everything ever tested**, from the experiment
  ledger's cumulative count and never the day's, reported beside the raw figure.
- **Replication on a held-out season** before any claim survives.
- **Minimum sample thresholds per market, declared in advance**, below which the
  verdict is **"not enough evidence"** — not a number.
- **Correlation is a first-order accounting problem.** Exposure is reported per
  game and per slate, correlation-aware, never per selection, and every interval
  accounts for clustering by game and by day.
- **"Retained" and "measurable" are different claims.** A market with historical
  prices on two of twenty probed events is retained and unmeasurable.
- **"Documented is not quoted."** The provider's catalogue is what it will serve
  if a book hangs it. What books actually hang is an in-season question.

## How much data would settle it

This arithmetic does not depend on the sport, so it can be written down now.
To separate a true edge from zero at 95% confidence, against roughly 5%
per-bet variance:

| If the true edge were | Bets needed to separate it from zero |
|----------------------:|-------------------------------------:|
| +5%  | ~1,540 |
| +8%  | ~600 |
| +10% | ~385 |
| +15% | ~171 |

## The sample size is the reason this lab exists, and it is not good news

Division I men's basketball plays on the order of **5,600 games a season across
about 360 teams**. That is more games in one season than the NFL plays in twenty,
and it is the entire reason Cooper authorised a fourth lab: *"If there is an
edge here, this lab can prove it inside one season. If there isn't, it can prove
that too."*

That is true, and this document exists to stop it being read as encouragement.
Four things blunt it, and each one has to be carried beside every number:

1. **Games are not independent observations.** One game supplies a moneyline, a
   spread, a total, two team totals, and a dozen props, and they are the same
   event seen fifteen ways. A 100-game Tuesday is not 1,500 independent
   observations. Every interval in this lab is clustered by game and by day, and
   an unclustered interval on this sport would be wrong by a large factor rather
   than a small one.
2. **Volume in games is not volume in liquid, well-priced games.** A Quad-1 game
   with nine books quoting it and a Tuesday low-major with two are not the same
   instrument. The thesis of this lab is that the second one is softer; the
   counterweight is that the second one is also where the limits are trivial and
   the price vanishes fastest. See `## Reachability` below.
3. **A bigger sample narrows the intervals of the hypotheses that are wrong,
   too.** Sample size buys power, never innocence. It is precisely because this
   lab can run hundreds of tests with tight intervals that the experiment ledger
   and its cumulative correction are the first thing that was built, before any
   model existed.
4. **The measured population will be smaller than the played population**, and
   by how much is an empirical question this lab has not answered yet. Books do
   not quote every D-I game, the provider does not retain every market
   historically, and several hundred November games are against non-D-I
   opponents and are excluded before anything is fitted.

**No pooled headline across the whole of Division I will ever be reported.**
High-major, mid-major and low-major are different distributions, defined
explicitly and recorded, fitted separately and measured separately — the same
rule that keeps NFL and FBS numbers apart in the sibling labs. A policy that
wins in low-major games and loses in high-major ships in low-major only, if it
ships at all.

## Reachability: a soft number you cannot bet is not an edge

This is the college-basketball-specific rule, and it is built in from day one
rather than discovered in March.

The plausible edge in this sport lives in exactly the games where a price is
hardest to actually get. The low-major games with the loosest lines have the
smallest limits and move fastest. So:

- Edge is measured against a price **actually available at the moment the card
  is produced**, at a US book Cooper can open. Regions stay `us,us2`. A price at
  a book he cannot open is not reachable and manufactures untakeable edges.
- Every price records its book, its timestamp, and its **survival**: did it still
  exist at the next capture? The edge is reported **separately** for prices that
  survived and prices that did not.
- **A backtest that beats the opening number is not a bet**, and that sentence
  appears wherever such a figure appears.
- If a measured edge lives entirely in prices that vanish within minutes, or at
  books whose limits on low-major games are trivial, the report states that the
  edge is **not reachable**, in those words, regardless of its size or its
  significance.

The NHL lab's line-shopping test is the template for the arithmetic: of 161,891
quotes, only **1,557 — under 1%** — beat a de-vigged leave-one-out consensus of
the other books, and those realised **−3.4%** with an interval spanning zero.
The bet is that 360 teams on a Tuesday night in January behave differently from
32 NHL clubs priced by every book. That is a hypothesis, it is counted in the
ledger like any other, and it is not yet an observation.

## Futures never enter a headline

Conference and tournament futures, season win totals, Final Four and the
championship tie up stake for months, settle on a different clock, and their
return is not comparable to a single-game bet. **No futures return is ever folded
into a headline ROI computed over game bets.** The hold time is stated beside
every futures number.

The NCAA tournament is its own market family and gets both halves of its own
sentence: it is the deepest liquidity and the most public money of the year,
which makes it the most plausible place for a public-bias edge — and it is 67
games, which is an `n` that cannot establish anything on its own. Both facts go
in the report, together, always.

## What cannot be measured at all

To be filled in as it is established, with the date it was established, because
**"the source does not have this" and "we looked in the wrong place" have looked
identical before** — and the second one cost the NHL lab a market for a season.
Candidates already visible from the sibling labs' experience:

- Any market the provider does not retain historically can only accumulate
  forward evidence, never a backtest.
- Any quantity no free source settles against. A market that cannot settle is
  not wired, and it appears in `markets.DEFERRED_MARKETS` with its reason.
- Any player prop whose availability cannot reach `confirmed`. College
  basketball has no mandated injury report, and a gate that read a missing feed
  as "nobody is injured" would clear an entire slate.

## The retraction genre, declared in advance

The football lab retracted its own headline three times in four days, and each
retraction was written in the confident register of something that had already
survived scrutiny. So, pre-committed:

- **A retraction is not evidence that what replaces it is right.**
- **A constant settlement offset replicates by construction.** Replication is
  not evidence against a settlement artefact; replication is what one does.
- **A finding that is really a mechanism is the most persuasive kind and the
  most dangerous**, because it supplies its own explanation and so stops the
  search for another one.
- The question that broke the football lab's best result was never "is this
  robust". It was **"what would betting one side with no model at all return?"**
  That null baseline is built before the backtest, not after it.

## The one thing that is certain

**Forward evidence cannot be back-dated.** Historical prices can be bought at
any time; every night the pipeline is not freezing opinions and settling them is
a night of clean out-of-sample data that is gone permanently — and in this sport
a night is up to a hundred games.

That is why the freeze-and-settle organ is built before the models are worth
anything, and why the build order puts it third rather than last.
