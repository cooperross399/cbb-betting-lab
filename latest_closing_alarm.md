# CBB closing-line alarm

As of 2026-11-28. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (396 capture(s) read). Intervals are clustered by game and corrected across 230 cumulative hypotheses (x1.8867). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 229 | 229 | +0.1% | -0.5% to +0.8% | 66% | 127 / 61 / 42 |
| high-major | spread | 817 | 351 | -0.07 | -0.45 to +0.30 | 39% | 301 / 281 / 235 |
| high-major | total_points | 790 | 315 | -0.30 | -0.74 to +0.13 | 35% | 348 / 252 / 190 |
| high-major | alternate_spread | 8,615 | 364 | -2.4% | -3.4% to -1.3% | 34% | 0 / 0 / 8,615 |
| high-major | alternate_total_points | 7,517 | 335 | -2.8% | -3.6% to -1.9% | 22% | 0 / 0 / 7,517 |
| high-major | team_total | 1,180 | 359 | -3.2% | -4.1% to -2.2% | 22% | 0 / 0 / 1,180 |
| mid-major | moneyline | 282 | 282 | -0.1% | -0.7% to +0.6% | 53% | 125 / 86 / 71 |
| mid-major | spread | 690 | 302 | +0.13 | -0.17 to +0.42 | 46% | 306 / 221 / 163 |
| mid-major | total_points | 745 | 301 | -0.20 | -0.68 to +0.29 | 38% | 319 / 209 / 217 |
| mid-major | alternate_spread | 6,291 | 312 | -1.9% | -2.8% to -1.1% | 31% | 0 / 0 / 6,291 |
| mid-major | alternate_total_points | 7,065 | 299 | -2.9% | -4.0% to -1.8% | 21% | 0 / 0 / 7,065 |
| mid-major | team_total | 1,172 | 311 | -3.6% | -4.4% to -2.7% | 18% | 0 / 0 / 1,172 |
| low-major | moneyline | 101 | 101 | +0.8% | -0.5% to +2.0% | 55% | 35 / 36 / 30 |
| low-major | spread | 232 | 112 | +0.46 | -0.08 to +0.99 | 51% | 85 / 70 / 77 |
| low-major | total_points | 253 | 112 | -0.69 | -1.68 to +0.30 | 33% | 97 / 74 / 82 |
| low-major | alternate_spread | 2,143 | 113 | -1.0% | -2.7% to +0.6% | 38% | 0 / 0 / 2,143 |
| low-major | alternate_total_points | 2,527 | 116 | -3.8% | -5.6% to -2.0% | 16% | 0 / 0 / 2,527 |
| low-major | team_total | 340 | 110 | -3.7% | -5.3% to -2.1% | 14% | 0 / 0 / 340 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
