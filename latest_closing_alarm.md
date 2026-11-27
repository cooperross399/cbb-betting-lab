# CBB closing-line alarm

As of 2026-11-27. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (387 capture(s) read). Intervals are clustered by game and corrected across 230 cumulative hypotheses (x1.8867). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 211 | 211 | +0.2% | -0.4% to +0.8% | 68% | 123 / 48 / 41 |
| high-major | spread | 763 | 326 | -0.08 | -0.47 to +0.31 | 39% | 289 / 243 / 231 |
| high-major | total_points | 726 | 290 | -0.29 | -0.74 to +0.16 | 35% | 326 / 212 / 188 |
| high-major | alternate_spread | 8,012 | 338 | -2.4% | -3.5% to -1.3% | 34% | 0 / 0 / 8,012 |
| high-major | alternate_total_points | 6,870 | 311 | -2.8% | -3.7% to -1.9% | 22% | 0 / 0 / 6,870 |
| high-major | team_total | 1,130 | 336 | -3.1% | -4.1% to -2.2% | 22% | 0 / 0 / 1,130 |
| mid-major | moneyline | 272 | 272 | +0.0% | -0.6% to +0.6% | 54% | 121 / 80 / 71 |
| mid-major | spread | 663 | 291 | +0.16 | -0.14 to +0.46 | 47% | 299 / 203 / 161 |
| mid-major | total_points | 715 | 287 | -0.22 | -0.71 to +0.28 | 38% | 304 / 194 / 217 |
| mid-major | alternate_spread | 6,108 | 301 | -1.9% | -2.8% to -1.0% | 32% | 0 / 0 / 6,108 |
| mid-major | alternate_total_points | 6,650 | 285 | -3.0% | -4.1% to -1.9% | 21% | 0 / 0 / 6,650 |
| mid-major | team_total | 1,120 | 298 | -3.5% | -4.4% to -2.6% | 18% | 0 / 0 / 1,120 |
| low-major | moneyline | 95 | 95 | +0.7% | -0.6% to +2.1% | 55% | 34 / 32 / 29 |
| low-major | spread | 220 | 105 | +0.42 | -0.13 to +0.98 | 50% | 82 / 63 / 75 |
| low-major | total_points | 243 | 107 | -0.71 | -1.73 to +0.32 | 33% | 94 / 67 / 82 |
| low-major | alternate_spread | 2,004 | 106 | -1.2% | -3.0% to +0.6% | 37% | 0 / 0 / 2,004 |
| low-major | alternate_total_points | 2,407 | 111 | -3.9% | -5.8% to -2.0% | 15% | 0 / 0 / 2,407 |
| low-major | team_total | 312 | 104 | -4.0% | -5.4% to -2.6% | 10% | 0 / 0 / 312 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
