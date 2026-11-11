# CBB closing-line alarm

As of 2026-11-11. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (136 capture(s) read). Intervals are clustered by game and corrected across 200 cumulative hypotheses (x1.8685). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 127 | 127 | +0.2% | -0.5% to +1.0% | 73% | 79 / 19 / 29 |
| high-major | spread | 430 | 182 | -0.65 | -1.15 to -0.16 | 26% | 158 / 103 / 169 |
| high-major | total_points | 417 | 164 | -0.76 | -1.32 to -0.20 | 24% | 193 / 100 / 124 |
| high-major | alternate_spread | 4,514 | 185 | -4.4% | -5.8% to -2.9% | 24% | 0 / 0 / 4,514 |
| high-major | alternate_total_points | 3,844 | 179 | -3.6% | -4.8% to -2.4% | 15% | 0 / 0 / 3,844 |
| high-major | team_total | 549 | 187 | -3.9% | -5.2% to -2.7% | 17% | 0 / 0 / 549 |
| mid-major | moneyline | 138 | 138 | +0.1% | -0.7% to +0.9% | 59% | 66 / 32 / 40 |
| mid-major | spread | 339 | 141 | -0.02 | -0.47 to +0.43 | 42% | 161 / 75 / 103 |
| mid-major | total_points | 309 | 130 | -0.47 | -1.24 to +0.31 | 33% | 152 / 53 / 104 |
| mid-major | alternate_spread | 3,177 | 144 | -2.5% | -3.8% to -1.2% | 28% | 0 / 0 / 3,177 |
| mid-major | alternate_total_points | 2,855 | 131 | -3.4% | -5.1% to -1.6% | 18% | 0 / 0 / 2,855 |
| mid-major | team_total | 389 | 139 | -4.3% | -5.3% to -3.2% | 12% | 0 / 0 / 389 |
| low-major | moneyline | 36 | 36 | +1.1% | -1.6% to +3.8% | 53% | 14 / 6 / 16 |
| low-major | spread | 72 | 38 | +0.05 | -1.04 to +1.13 | 39% | 26 / 22 / 24 |
| low-major | total_points | 84 | 39 | -1.10 | -3.46 to +1.27 | 33% | 30 / 20 / 34 |
| low-major | alternate_spread | 692 | 40 | -2.2% | -5.9% to +1.5% | 30% | 0 / 0 / 692 |
| low-major | alternate_total_points | 828 | 40 | -4.6% | -8.7% to -0.5% | 20% | 0 / 0 / 828 |
| low-major | team_total | 76 | 35 | -4.9% | -8.3% to -1.4% | 12% | 0 / 0 / 76 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
