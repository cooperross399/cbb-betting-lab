# CBB closing-line alarm

As of 2026-11-20. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (277 capture(s) read). Intervals are clustered by game and corrected across 215 cumulative hypotheses (x1.8780). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 173 | 173 | +0.2% | -0.4% to +0.9% | 71% | 107 / 32 / 35 |
| high-major | spread | 622 | 267 | -0.19 | -0.62 to +0.25 | 37% | 243 / 167 / 212 |
| high-major | total_points | 600 | 239 | -0.37 | -0.88 to +0.14 | 34% | 273 / 152 / 175 |
| high-major | alternate_spread | 6,497 | 274 | -2.9% | -4.1% to -1.6% | 32% | 0 / 0 / 6,497 |
| high-major | alternate_total_points | 5,510 | 258 | -2.8% | -3.9% to -1.8% | 23% | 0 / 0 / 5,510 |
| high-major | team_total | 848 | 274 | -3.2% | -4.3% to -2.1% | 22% | 0 / 0 / 848 |
| mid-major | moneyline | 203 | 203 | +0.0% | -0.7% to +0.7% | 55% | 97 / 48 / 58 |
| mid-major | spread | 509 | 221 | +0.07 | -0.28 to +0.41 | 44% | 239 / 128 / 142 |
| mid-major | total_points | 500 | 206 | -0.29 | -0.88 to +0.31 | 36% | 237 / 108 / 155 |
| mid-major | alternate_spread | 4,578 | 223 | -2.2% | -3.3% to -1.2% | 29% | 0 / 0 / 4,578 |
| mid-major | alternate_total_points | 4,529 | 207 | -3.0% | -4.3% to -1.6% | 20% | 0 / 0 / 4,529 |
| mid-major | team_total | 742 | 220 | -3.8% | -4.7% to -2.8% | 15% | 0 / 0 / 742 |
| low-major | moneyline | 64 | 64 | +1.1% | -0.7% to +2.9% | 58% | 26 / 17 / 21 |
| low-major | spread | 146 | 70 | +0.47 | -0.30 to +1.24 | 51% | 55 / 41 / 50 |
| low-major | total_points | 158 | 71 | -0.95 | -2.36 to +0.47 | 30% | 62 / 41 / 55 |
| low-major | alternate_spread | 1,300 | 72 | -1.0% | -3.5% to +1.5% | 41% | 0 / 0 / 1,300 |
| low-major | alternate_total_points | 1,520 | 73 | -4.4% | -6.9% to -1.8% | 16% | 0 / 0 / 1,520 |
| low-major | team_total | 178 | 68 | -4.2% | -6.5% to -2.0% | 12% | 0 / 0 / 178 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
