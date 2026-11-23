# CBB closing-line alarm

As of 2026-11-23. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (316 capture(s) read). Intervals are clustered by game and corrected across 221 cumulative hypotheses (x1.8815). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 189 | 189 | +0.2% | -0.4% to +0.8% | 70% | 114 / 37 / 39 |
| high-major | spread | 705 | 302 | -0.12 | -0.53 to +0.29 | 39% | 270 / 209 / 226 |
| high-major | total_points | 672 | 268 | -0.33 | -0.80 to +0.13 | 34% | 307 / 185 / 180 |
| high-major | alternate_spread | 7,374 | 313 | -2.6% | -3.8% to -1.4% | 34% | 0 / 0 / 7,374 |
| high-major | alternate_total_points | 6,293 | 287 | -2.8% | -3.8% to -1.9% | 22% | 0 / 0 / 6,293 |
| high-major | team_total | 998 | 310 | -3.2% | -4.2% to -2.2% | 21% | 0 / 0 / 998 |
| mid-major | moneyline | 250 | 250 | -0.0% | -0.6% to +0.6% | 54% | 114 / 66 / 70 |
| mid-major | spread | 616 | 269 | +0.13 | -0.18 to +0.44 | 46% | 286 / 174 / 156 |
| mid-major | total_points | 655 | 263 | -0.25 | -0.78 to +0.28 | 37% | 283 / 164 / 208 |
| mid-major | alternate_spread | 5,515 | 278 | -2.0% | -2.9% to -1.1% | 31% | 0 / 0 / 5,515 |
| mid-major | alternate_total_points | 6,036 | 262 | -3.1% | -4.2% to -1.9% | 21% | 0 / 0 / 6,036 |
| mid-major | team_total | 895 | 274 | -3.7% | -4.6% to -2.8% | 17% | 0 / 0 / 895 |
| low-major | moneyline | 93 | 93 | +0.7% | -0.6% to +2.1% | 55% | 34 / 30 / 29 |
| low-major | spread | 214 | 102 | +0.43 | -0.14 to +1.00 | 50% | 81 / 58 / 75 |
| low-major | total_points | 232 | 103 | -0.71 | -1.77 to +0.36 | 33% | 94 / 61 / 77 |
| low-major | alternate_spread | 1,951 | 104 | -1.2% | -3.0% to +0.6% | 37% | 0 / 0 / 1,951 |
| low-major | alternate_total_points | 2,280 | 107 | -4.0% | -5.9% to -2.0% | 16% | 0 / 0 / 2,280 |
| low-major | team_total | 271 | 100 | -4.0% | -5.6% to -2.4% | 11% | 0 / 0 / 271 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
