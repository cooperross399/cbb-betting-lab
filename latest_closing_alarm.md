# CBB closing-line alarm

As of 2026-11-18. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (238 capture(s) read). Intervals are clustered by game and corrected across 206 cumulative hypotheses (x1.8724). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 162 | 162 | +0.3% | -0.4% to +0.9% | 72% | 102 / 27 / 34 |
| high-major | spread | 583 | 254 | -0.23 | -0.68 to +0.22 | 36% | 226 / 154 / 203 |
| high-major | total_points | 572 | 227 | -0.45 | -0.96 to +0.06 | 31% | 263 / 143 / 166 |
| high-major | alternate_spread | 6,143 | 260 | -3.0% | -4.3% to -1.7% | 32% | 0 / 0 / 6,143 |
| high-major | alternate_total_points | 5,199 | 246 | -2.9% | -4.0% to -1.9% | 22% | 0 / 0 / 5,199 |
| high-major | team_total | 797 | 260 | -3.2% | -4.3% to -2.1% | 21% | 0 / 0 / 797 |
| mid-major | moneyline | 195 | 195 | +0.1% | -0.6% to +0.8% | 57% | 90 / 48 / 57 |
| mid-major | spread | 492 | 214 | +0.08 | -0.28 to +0.43 | 45% | 233 / 121 / 138 |
| mid-major | total_points | 481 | 199 | -0.30 | -0.92 to +0.31 | 36% | 232 / 101 / 148 |
| mid-major | alternate_spread | 4,447 | 215 | -2.2% | -3.3% to -1.2% | 29% | 0 / 0 / 4,447 |
| mid-major | alternate_total_points | 4,348 | 200 | -3.0% | -4.4% to -1.6% | 20% | 0 / 0 / 4,348 |
| mid-major | team_total | 718 | 212 | -3.8% | -4.8% to -2.8% | 15% | 0 / 0 / 718 |
| low-major | moneyline | 61 | 61 | +1.0% | -0.8% to +2.9% | 56% | 26 / 14 / 21 |
| low-major | spread | 136 | 66 | +0.42 | -0.39 to +1.22 | 49% | 52 / 40 / 44 |
| low-major | total_points | 151 | 67 | -0.96 | -2.44 to +0.52 | 32% | 57 / 40 / 54 |
| low-major | alternate_spread | 1,219 | 68 | -1.2% | -3.8% to +1.4% | 39% | 0 / 0 / 1,219 |
| low-major | alternate_total_points | 1,406 | 69 | -4.4% | -7.1% to -1.7% | 18% | 0 / 0 / 1,406 |
| low-major | team_total | 161 | 64 | -4.5% | -6.7% to -2.3% | 12% | 0 / 0 / 161 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
