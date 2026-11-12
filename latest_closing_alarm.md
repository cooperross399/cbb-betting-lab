# CBB closing-line alarm

As of 2026-11-12. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (157 capture(s) read). Intervals are clustered by game and corrected across 203 cumulative hypotheses (x1.8705). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 131 | 131 | +0.2% | -0.5% to +1.0% | 73% | 83 / 19 / 30 |
| high-major | spread | 451 | 191 | -0.61 | -1.09 to -0.12 | 27% | 171 / 108 / 172 |
| high-major | total_points | 438 | 173 | -0.70 | -1.25 to -0.15 | 26% | 208 / 106 / 124 |
| high-major | alternate_spread | 4,746 | 195 | -4.1% | -5.6% to -2.7% | 25% | 0 / 0 / 4,746 |
| high-major | alternate_total_points | 4,035 | 189 | -3.5% | -4.6% to -2.3% | 16% | 0 / 0 / 4,035 |
| high-major | team_total | 609 | 197 | -3.7% | -5.0% to -2.4% | 19% | 0 / 0 / 609 |
| mid-major | moneyline | 155 | 155 | +0.1% | -0.7% to +0.9% | 57% | 78 / 34 / 43 |
| mid-major | spread | 388 | 164 | +0.06 | -0.36 to +0.47 | 44% | 194 / 89 / 105 |
| mid-major | total_points | 372 | 152 | -0.30 | -0.99 to +0.38 | 36% | 197 / 69 / 106 |
| mid-major | alternate_spread | 3,663 | 167 | -2.3% | -3.4% to -1.1% | 29% | 0 / 0 / 3,663 |
| mid-major | alternate_total_points | 3,423 | 153 | -3.0% | -4.5% to -1.4% | 20% | 0 / 0 / 3,423 |
| mid-major | team_total | 629 | 166 | -3.9% | -4.9% to -2.8% | 15% | 0 / 0 / 629 |
| low-major | moneyline | 42 | 42 | +0.8% | -1.6% to +3.2% | 50% | 18 / 8 / 16 |
| low-major | spread | 91 | 45 | +0.14 | -0.75 to +1.03 | 43% | 36 / 28 / 27 |
| low-major | total_points | 109 | 48 | -0.96 | -2.87 to +0.95 | 35% | 47 / 27 / 35 |
| low-major | alternate_spread | 861 | 47 | -2.1% | -5.2% to +1.0% | 31% | 0 / 0 / 861 |
| low-major | alternate_total_points | 1,060 | 49 | -4.3% | -7.7% to -1.0% | 19% | 0 / 0 / 1,060 |
| low-major | team_total | 116 | 44 | -5.2% | -7.9% to -2.5% | 9% | 0 / 0 / 116 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
