# CBB closing-line alarm

As of 2026-11-09. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (115 capture(s) read). Intervals are clustered by game and corrected across 200 cumulative hypotheses (x1.8685). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 108 | 108 | +0.3% | -0.5% to +1.1% | 77% | 69 / 13 / 26 |
| high-major | spread | 342 | 138 | -0.73 | -1.32 to -0.15 | 25% | 137 / 76 / 129 |
| high-major | total_points | 297 | 120 | -1.04 | -1.68 to -0.41 | 21% | 156 / 60 / 81 |
| high-major | alternate_spread | 3,549 | 138 | -4.7% | -6.4% to -3.0% | 23% | 0 / 0 / 3,549 |
| high-major | alternate_total_points | 2,733 | 130 | -4.2% | -5.6% to -2.9% | 11% | 0 / 0 / 2,733 |
| high-major | team_total | 430 | 141 | -4.3% | -5.5% to -3.2% | 13% | 0 / 0 / 430 |
| mid-major | moneyline | 113 | 113 | +0.1% | -0.8% to +1.0% | 60% | 58 / 26 / 29 |
| mid-major | spread | 266 | 112 | -0.18 | -0.69 to +0.32 | 38% | 144 / 52 / 70 |
| mid-major | total_points | 252 | 104 | -0.74 | -1.57 to +0.09 | 29% | 137 / 45 / 70 |
| mid-major | alternate_spread | 2,497 | 114 | -2.9% | -4.3% to -1.4% | 25% | 0 / 0 / 2,497 |
| mid-major | alternate_total_points | 2,373 | 106 | -3.7% | -5.6% to -1.8% | 15% | 0 / 0 / 2,373 |
| mid-major | team_total | 332 | 111 | -4.3% | -5.5% to -3.2% | 11% | 0 / 0 / 332 |
| low-major | moneyline | 32 | 32 | +0.6% | -2.1% to +3.3% | 47% | 14 / 5 / 13 |
| low-major | spread | 64 | 35 | -0.02 | -1.19 to +1.14 | 36% | 23 / 18 / 23 |
| low-major | total_points | 75 | 35 | -1.23 | -3.80 to +1.35 | 31% | 28 / 18 / 29 |
| low-major | alternate_spread | 648 | 37 | -2.3% | -6.2% to +1.6% | 30% | 0 / 0 / 648 |
| low-major | alternate_total_points | 754 | 36 | -4.9% | -9.3% to -0.5% | 17% | 0 / 0 / 754 |
| low-major | team_total | 70 | 31 | -5.1% | -8.9% to -1.4% | 10% | 0 / 0 / 70 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
