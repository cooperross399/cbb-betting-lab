# CBB closing-line alarm

As of 2026-11-13. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (165 capture(s) read). Intervals are clustered by game and corrected across 203 cumulative hypotheses (x1.8705). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 134 | 134 | +0.2% | -0.5% to +1.0% | 73% | 85 / 20 / 30 |
| high-major | spread | 461 | 196 | -0.57 | -1.05 to -0.08 | 28% | 176 / 110 / 175 |
| high-major | total_points | 451 | 178 | -0.67 | -1.21 to -0.13 | 26% | 213 / 110 / 128 |
| high-major | alternate_spread | 4,861 | 200 | -4.0% | -5.4% to -2.6% | 26% | 0 / 0 / 4,861 |
| high-major | alternate_total_points | 4,157 | 195 | -3.4% | -4.5% to -2.3% | 17% | 0 / 0 / 4,157 |
| high-major | team_total | 617 | 202 | -3.7% | -4.9% to -2.4% | 19% | 0 / 0 / 617 |
| mid-major | moneyline | 162 | 162 | +0.1% | -0.7% to +0.9% | 56% | 80 / 37 / 45 |
| mid-major | spread | 414 | 174 | +0.09 | -0.31 to +0.49 | 44% | 204 / 95 / 115 |
| mid-major | total_points | 399 | 161 | -0.22 | -0.93 to +0.48 | 37% | 209 / 75 / 115 |
| mid-major | alternate_spread | 3,825 | 177 | -2.2% | -3.3% to -1.0% | 29% | 0 / 0 / 3,825 |
| mid-major | alternate_total_points | 3,637 | 162 | -2.8% | -4.4% to -1.3% | 21% | 0 / 0 / 3,637 |
| mid-major | team_total | 644 | 176 | -3.8% | -4.8% to -2.8% | 16% | 0 / 0 / 644 |
| low-major | moneyline | 48 | 48 | +1.0% | -1.2% to +3.2% | 54% | 19 / 11 / 18 |
| low-major | spread | 102 | 50 | +0.19 | -0.66 to +1.04 | 44% | 40 / 31 / 31 |
| low-major | total_points | 111 | 50 | -0.86 | -2.76 to +1.03 | 36% | 48 / 27 / 36 |
| low-major | alternate_spread | 967 | 52 | -1.7% | -4.7% to +1.2% | 34% | 0 / 0 / 967 |
| low-major | alternate_total_points | 1,082 | 52 | -4.1% | -7.5% to -0.8% | 21% | 0 / 0 / 1,082 |
| low-major | team_total | 123 | 49 | -4.8% | -7.4% to -2.1% | 13% | 0 / 0 / 123 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
