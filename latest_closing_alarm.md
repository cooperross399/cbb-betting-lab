# CBB closing-line alarm

As of 2026-11-10. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (127 capture(s) read). Intervals are clustered by game and corrected across 200 cumulative hypotheses (x1.8685). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 117 | 117 | +0.3% | -0.5% to +1.1% | 77% | 74 / 16 / 27 |
| high-major | spread | 380 | 158 | -0.69 | -1.23 to -0.15 | 25% | 145 / 93 / 142 |
| high-major | total_points | 342 | 138 | -0.96 | -1.55 to -0.36 | 21% | 169 / 84 / 89 |
| high-major | alternate_spread | 3,972 | 158 | -4.5% | -6.1% to -3.0% | 24% | 0 / 0 / 3,972 |
| high-major | alternate_total_points | 3,171 | 151 | -4.0% | -5.2% to -2.8% | 12% | 0 / 0 / 3,171 |
| high-major | team_total | 467 | 161 | -4.3% | -5.3% to -3.2% | 13% | 0 / 0 / 467 |
| mid-major | moneyline | 122 | 122 | +0.2% | -0.7% to +1.0% | 61% | 60 / 29 / 33 |
| mid-major | spread | 286 | 121 | -0.10 | -0.59 to +0.39 | 40% | 146 / 62 / 78 |
| mid-major | total_points | 261 | 109 | -0.71 | -1.51 to +0.09 | 29% | 139 / 46 / 76 |
| mid-major | alternate_spread | 2,722 | 123 | -2.6% | -4.0% to -1.1% | 27% | 0 / 0 / 2,722 |
| mid-major | alternate_total_points | 2,444 | 111 | -3.6% | -5.5% to -1.8% | 14% | 0 / 0 / 2,444 |
| mid-major | team_total | 344 | 118 | -4.2% | -5.3% to -3.1% | 12% | 0 / 0 / 344 |
| low-major | moneyline | 34 | 34 | +1.0% | -1.8% to +3.8% | 50% | 14 / 6 / 14 |
| low-major | spread | 66 | 36 | +0.05 | -1.11 to +1.22 | 38% | 23 / 19 / 24 |
| low-major | total_points | 80 | 37 | -1.21 | -3.65 to +1.24 | 31% | 28 / 20 / 32 |
| low-major | alternate_spread | 650 | 38 | -2.3% | -6.2% to +1.6% | 30% | 0 / 0 / 650 |
| low-major | alternate_total_points | 797 | 38 | -4.8% | -9.0% to -0.6% | 18% | 0 / 0 / 797 |
| low-major | team_total | 73 | 33 | -5.0% | -8.6% to -1.4% | 11% | 0 / 0 / 73 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
