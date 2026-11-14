# CBB closing-line alarm

As of 2026-11-14. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (180 capture(s) read). Intervals are clustered by game and corrected across 203 cumulative hypotheses (x1.8705). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / alternate_spread, high_major / alternate_total_points, high_major / team_total, mid_major / alternate_spread, mid_major / alternate_total_points, mid_major / team_total, low_major / alternate_total_points, low_major / team_total.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing, and the closing-line gate takes the cell off the card while the alarm holds.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 148 | 148 | +0.2% | -0.5% to +0.9% | 71% | 93 / 23 / 33 |
| high-major | spread | 522 | 223 | -0.40 | -0.87 to +0.06 | 32% | 201 / 130 / 191 |
| high-major | total_points | 514 | 201 | -0.51 | -1.04 to +0.03 | 30% | 237 / 127 / 150 |
| high-major | alternate_spread | 5,491 | 227 | -3.6% | -4.9% to -2.2% | 28% | 0 / 0 / 5,491 |
| high-major | alternate_total_points | 4,701 | 219 | -3.1% | -4.2% to -2.0% | 20% | 0 / 0 / 4,701 |
| high-major | team_total | 681 | 229 | -3.5% | -4.7% to -2.3% | 20% | 0 / 0 / 681 |
| mid-major | moneyline | 175 | 175 | +0.0% | -0.7% to +0.8% | 55% | 83 / 41 / 51 |
| mid-major | spread | 440 | 189 | +0.07 | -0.31 to +0.46 | 45% | 212 / 104 / 124 |
| mid-major | total_points | 434 | 179 | -0.25 | -0.92 to +0.41 | 37% | 222 / 87 / 125 |
| mid-major | alternate_spread | 4,089 | 191 | -2.2% | -3.4% to -1.1% | 29% | 0 / 0 / 4,089 |
| mid-major | alternate_total_points | 3,950 | 180 | -2.9% | -4.4% to -1.4% | 21% | 0 / 0 / 3,950 |
| mid-major | team_total | 668 | 190 | -3.8% | -4.8% to -2.8% | 16% | 0 / 0 / 668 |
| low-major | moneyline | 55 | 55 | +1.0% | -1.0% to +3.0% | 55% | 24 / 12 / 19 |
| low-major | spread | 119 | 57 | +0.30 | -0.53 to +1.13 | 46% | 47 / 35 / 37 |
| low-major | total_points | 130 | 57 | -0.86 | -2.56 to +0.85 | 37% | 52 / 32 / 46 |
| low-major | alternate_spread | 1,100 | 59 | -1.4% | -4.1% to +1.3% | 37% | 0 / 0 / 1,100 |
| low-major | alternate_total_points | 1,232 | 59 | -4.2% | -7.3% to -1.1% | 20% | 0 / 0 / 1,232 |
| low-major | team_total | 132 | 56 | -4.5% | -7.1% to -1.9% | 14% | 0 / 0 / 132 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Alternate ladders and team totals are probability too: the main market's close, read at the row's own number through a normal, minus the frozen price's implied probability, so their hold counts against them. A tripped cell is taken off the card by the closing-line gate. Unknown survival means the next capture did not cover the event, and is never counted as gone.
