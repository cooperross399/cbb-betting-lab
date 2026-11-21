# CBB closing-line alarm

As of 2026-11-21. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (285 capture(s) read). Intervals are clustered by game and corrected across 218 cumulative hypotheses (x1.8798). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 182 | 182 | +0.3% | -0.4% to +0.9% | 71% | 110 / 36 / 37 |
| high-major | spread | 677 | 289 | -0.15 | -0.57 to +0.27 | 38% | 257 / 201 / 219 |
| high-major | total_points | 647 | 257 | -0.34 | -0.82 to +0.14 | 34% | 294 / 177 / 176 |
| high-major | alternate_spread | 6,988 | 297 | -2.7% | -3.9% to -1.5% | 33% | 0 / 0 / 6,988 |
| high-major | alternate_total_points | 6,036 | 276 | -2.8% | -3.8% to -1.8% | 22% | 0 / 0 / 6,036 |
| high-major | team_total | 965 | 296 | -3.2% | -4.2% to -2.2% | 22% | 0 / 0 / 965 |
| mid-major | moneyline | 217 | 217 | +0.1% | -0.6% to +0.7% | 56% | 102 / 56 / 59 |
| mid-major | spread | 543 | 234 | +0.10 | -0.23 to +0.44 | 45% | 255 / 145 / 143 |
| mid-major | total_points | 541 | 222 | -0.24 | -0.81 to +0.33 | 37% | 251 / 132 / 158 |
| mid-major | alternate_spread | 4,884 | 240 | -2.1% | -3.1% to -1.1% | 30% | 0 / 0 / 4,884 |
| mid-major | alternate_total_points | 4,980 | 223 | -2.9% | -4.2% to -1.6% | 20% | 0 / 0 / 4,980 |
| mid-major | team_total | 823 | 236 | -3.7% | -4.7% to -2.7% | 17% | 0 / 0 / 823 |
| low-major | moneyline | 71 | 71 | +1.0% | -0.6% to +2.7% | 58% | 28 / 21 / 22 |
| low-major | spread | 158 | 78 | +0.47 | -0.24 to +1.18 | 51% | 59 / 45 / 54 |
| low-major | total_points | 183 | 80 | -0.74 | -2.01 to +0.53 | 34% | 73 / 49 / 61 |
| low-major | alternate_spread | 1,487 | 82 | -1.1% | -3.3% to +1.2% | 39% | 0 / 0 / 1,487 |
| low-major | alternate_total_points | 1,786 | 82 | -3.9% | -6.2% to -1.6% | 17% | 0 / 0 / 1,786 |
| low-major | team_total | 223 | 78 | -4.0% | -5.8% to -2.1% | 12% | 0 / 0 / 223 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
