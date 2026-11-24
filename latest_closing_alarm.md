# CBB closing-line alarm

As of 2026-11-24. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (333 capture(s) read). Intervals are clustered by game and corrected across 221 cumulative hypotheses (x1.8815). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 193 | 193 | +0.2% | -0.4% to +0.8% | 70% | 116 / 39 / 39 |
| high-major | spread | 719 | 308 | -0.10 | -0.51 to +0.31 | 39% | 273 / 219 / 227 |
| high-major | total_points | 693 | 275 | -0.32 | -0.78 to +0.13 | 34% | 315 / 194 / 184 |
| high-major | alternate_spread | 7,520 | 320 | -2.5% | -3.7% to -1.3% | 35% | 0 / 0 / 7,520 |
| high-major | alternate_total_points | 6,504 | 295 | -2.8% | -3.7% to -1.9% | 21% | 0 / 0 / 6,504 |
| high-major | team_total | 1,043 | 318 | -3.2% | -4.2% to -2.2% | 21% | 0 / 0 / 1,043 |
| mid-major | moneyline | 269 | 269 | +0.0% | -0.6% to +0.6% | 54% | 118 / 80 / 71 |
| mid-major | spread | 655 | 288 | +0.15 | -0.15 to +0.45 | 46% | 298 / 197 / 160 |
| mid-major | total_points | 711 | 285 | -0.22 | -0.72 to +0.28 | 38% | 302 / 193 / 216 |
| mid-major | alternate_spread | 6,015 | 298 | -1.9% | -2.8% to -1.0% | 31% | 0 / 0 / 6,015 |
| mid-major | alternate_total_points | 6,614 | 283 | -3.0% | -4.1% to -1.9% | 21% | 0 / 0 / 6,614 |
| mid-major | team_total | 1,084 | 295 | -3.6% | -4.4% to -2.7% | 17% | 0 / 0 / 1,084 |
| low-major | moneyline | 95 | 95 | +0.7% | -0.6% to +2.1% | 55% | 34 / 32 / 29 |
| low-major | spread | 220 | 105 | +0.42 | -0.13 to +0.98 | 50% | 82 / 63 / 75 |
| low-major | total_points | 243 | 107 | -0.71 | -1.72 to +0.31 | 33% | 94 / 67 / 82 |
| low-major | alternate_spread | 2,004 | 106 | -1.2% | -3.0% to +0.6% | 37% | 0 / 0 / 2,004 |
| low-major | alternate_total_points | 2,407 | 111 | -3.9% | -5.8% to -2.0% | 15% | 0 / 0 / 2,407 |
| low-major | team_total | 312 | 104 | -4.0% | -5.4% to -2.6% | 10% | 0 / 0 / 312 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
