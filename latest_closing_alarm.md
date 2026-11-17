# CBB closing-line alarm

As of 2026-11-17. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (229 capture(s) read). Intervals are clustered by game and corrected across 203 cumulative hypotheses (x1.8705). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 154 | 154 | +0.2% | -0.4% to +0.9% | 72% | 98 / 24 / 33 |
| high-major | spread | 545 | 233 | -0.32 | -0.78 to +0.15 | 34% | 212 / 141 / 192 |
| high-major | total_points | 532 | 210 | -0.49 | -1.02 to +0.04 | 30% | 247 / 133 / 152 |
| high-major | alternate_spread | 5,729 | 238 | -3.3% | -4.7% to -2.0% | 30% | 0 / 0 / 5,729 |
| high-major | alternate_total_points | 4,842 | 227 | -3.0% | -4.1% to -1.9% | 21% | 0 / 0 / 4,842 |
| high-major | team_total | 732 | 238 | -3.4% | -4.6% to -2.3% | 20% | 0 / 0 / 732 |
| mid-major | moneyline | 181 | 181 | +0.1% | -0.6% to +0.9% | 56% | 87 / 42 / 52 |
| mid-major | spread | 453 | 196 | +0.08 | -0.29 to +0.46 | 45% | 217 / 109 / 127 |
| mid-major | total_points | 446 | 184 | -0.27 | -0.91 to +0.38 | 36% | 228 / 90 / 128 |
| mid-major | alternate_spread | 4,161 | 198 | -2.2% | -3.3% to -1.1% | 29% | 0 / 0 / 4,161 |
| mid-major | alternate_total_points | 4,025 | 186 | -2.9% | -4.4% to -1.5% | 21% | 0 / 0 / 4,025 |
| mid-major | team_total | 692 | 196 | -3.8% | -4.8% to -2.8% | 16% | 0 / 0 / 692 |
| low-major | moneyline | 56 | 56 | +1.1% | -0.9% to +3.0% | 55% | 25 / 12 / 19 |
| low-major | spread | 124 | 60 | +0.32 | -0.48 to +1.12 | 47% | 49 / 37 / 38 |
| low-major | total_points | 134 | 60 | -0.87 | -2.52 to +0.78 | 36% | 52 / 35 / 47 |
| low-major | alternate_spread | 1,130 | 62 | -1.3% | -4.0% to +1.3% | 38% | 0 / 0 / 1,130 |
| low-major | alternate_total_points | 1,247 | 62 | -4.2% | -7.2% to -1.1% | 20% | 0 / 0 / 1,247 |
| low-major | team_total | 140 | 58 | -4.4% | -6.9% to -1.9% | 13% | 0 / 0 / 140 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
