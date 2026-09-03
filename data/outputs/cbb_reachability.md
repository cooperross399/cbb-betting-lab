# NCAA Division I men's basketball — reachability

Generated 2026-09-03T23:53:02+00:00.

**A soft number you cannot bet is not an edge.** This report does not ask whether a price would have won; `price_backtest.py` asks that. It asks whether the price was still on the board when a human reached for it, and it reports the return of the prices that survived apart from the return of the prices that did not.

**The two facts point in opposite directions, so both are printed.** The low-major end of the board is the looser end — that is the reason this lab exists — and it is also the end with the smallest limits and the fastest moves. A tier that prices badly and holds its number is a different proposition from a tier that prices badly and is gone in two minutes, and a pooled number hides exactly that difference.

**Regions stay `us,us2`.** Every quote below comes from a book inside those regions, because a price at a book Cooper cannot open is not reachable by definition and manufactures untakeable edges. A book absent from this table was not measured and found unreachable — it was never captured, and the two are different claims.

**Beating an opening number is not a bet.** The first capture of a slate day is the earliest number this lab holds, and a return measured against it describes how the market moved rather than a wager anybody placed. No figure in this report is evidence about a price that had already gone by the time a card was produced.

**Limits are not observable from this instrument.** The provider serves a price and a book; it does not serve the maximum stake that book would accept on a Thursday low-major total. A quote that survived to the next capture is evidence that the *number* was still there, and it is not evidence that a stake of any size would have been taken. The brief names trivial limits and vanishing prices together; this report measures only the second, and a surviving price at a trivial limit is still not a bet.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was captured.

## The instrument

`line_movement.py` is the instrument and this report does not reimplement it. Every survival judgment below is produced by calling `line_movement.survival_between`, which is captured four times a day on a cron and is append-only, because a price that existed at 19:04 and not at 19:19 leaves no trace anywhere else and no amount of money buys it back.

**The store holds no capture at all**, so there is no timestamp range, no book count and no survival to report from it.

**Not enough evidence.** The line-movement store holds no captures. The season opens in November, there is no college basketball between April and November, and the capture script writes nothing when the board is empty — because an empty capture would later read as every price having vanished. This is an observation about the calendar and not a fault.

So no board-level survival rate is printed. It is said in words rather than shown as an empty table, because an empty table reads as a null result and a null result is a claim.

## The staked bets, split by whether the price survived

**0 staked bets**: 0 at a price that survived to the next capture, 0 at a price that was gone by it, and 0 the instrument could not judge. Source: `none`.

No staked bet was supplied, so there was nothing to split. This is a wiring state and not a null result.

**There is nothing to measure.** No staked bet reached this report, so there is no return to split. It is said in words rather than shown as an empty table, because an empty table reads as a null result and a null result is a claim.

## The opening number, which is not a bet

No staked bet reached this report, so nothing could be split by when its price was taken. **Beating an opening number is not a bet.** The first capture of a slate day is the earliest number this lab holds, and a return measured against it describes how the market moved rather than a wager anybody placed. No figure in this report is evidence about a price that had already gone by the time a card was produced.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say a surviving price would have been **filled**. **Limits are not observable from this instrument.** The provider serves a price and a book; it does not serve the maximum stake that book would accept on a Thursday low-major total. A quote that survived to the next capture is evidence that the *number* was still there, and it is not evidence that a stake of any size would have been taken. The brief names trivial limits and vanishing prices together; this report measures only the second, and a surviving price at a trivial limit is still not a bet.
- It cannot judge a bet the capture store never saw. A quote this instrument never held is unjudgeable, never vanished, and the third column carries that all the way through.
- It cannot make an opening number into a bet. **Beating an opening number is not a bet.** The first capture of a slate day is the earliest number this lab holds, and a return measured against it describes how the market moved rather than a wager anybody placed. No figure in this report is evidence about a price that had already gone by the time a card was produced.
- It cannot measure reachability from the historical archive. The archive serves **one snapshot per event**, so a bought price has no next capture and its survival is unmeasured rather than measured and found fine. Forward captures cannot be back-dated, which is why the cron runs before the season.
