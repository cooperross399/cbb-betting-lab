# CBB closing-line alarm

As of 2026-11-22. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (307 capture(s) read). Intervals are clustered by game and corrected across 221 cumulative hypotheses (x1.8815). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 186 | 186 | +0.3% | -0.3% to +0.9% | 71% | 113 / 36 / 38 |
| high-major | spread | 691 | 296 | -0.13 | -0.55 to +0.29 | 38% | 262 / 206 / 223 |
| high-major | total_points | 658 | 262 | -0.34 | -0.81 to +0.13 | 34% | 300 / 179 / 179 |
| high-major | alternate_spread | 7,193 | 304 | -2.6% | -3.8% to -1.5% | 34% | 0 / 0 / 7,193 |
| high-major | alternate_total_points | 6,155 | 281 | -2.8% | -3.8% to -1.9% | 22% | 0 / 0 / 6,155 |
| high-major | team_total | 984 | 303 | -3.2% | -4.2% to -2.2% | 21% | 0 / 0 / 984 |
| mid-major | moneyline | 236 | 236 | +0.0% | -0.6% to +0.7% | 55% | 108 / 62 / 66 |
| mid-major | spread | 577 | 253 | +0.12 | -0.19 to +0.44 | 46% | 269 / 162 / 146 |
| mid-major | total_points | 598 | 244 | -0.27 | -0.82 to +0.28 | 37% | 263 / 145 / 190 |
| mid-major | alternate_spread | 5,265 | 262 | -2.0% | -2.9% to -1.1% | 31% | 0 / 0 / 5,265 |
| mid-major | alternate_total_points | 5,543 | 244 | -3.0% | -4.3% to -1.8% | 20% | 0 / 0 / 5,543 |
| mid-major | team_total | 859 | 256 | -3.7% | -4.7% to -2.7% | 17% | 0 / 0 / 859 |
| low-major | moneyline | 87 | 87 | +0.7% | -0.7% to +2.1% | 55% | 32 / 26 / 29 |
| low-major | spread | 191 | 95 | +0.38 | -0.23 to +1.00 | 49% | 68 / 55 / 68 |
| low-major | total_points | 218 | 96 | -0.72 | -1.85 to +0.41 | 34% | 86 / 60 / 72 |
| low-major | alternate_spread | 1,794 | 97 | -1.4% | -3.3% to +0.6% | 35% | 0 / 0 / 1,794 |
| low-major | alternate_total_points | 2,161 | 100 | -4.0% | -6.0% to -1.9% | 17% | 0 / 0 / 2,161 |
| low-major | team_total | 258 | 94 | -4.1% | -5.7% to -2.4% | 11% | 0 / 0 / 258 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
