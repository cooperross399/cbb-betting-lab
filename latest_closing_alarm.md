# CBB closing-line alarm

As of 2026-11-09. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (111 capture(s) read). Intervals are clustered by game and corrected across 182 cumulative hypotheses (x1.8562). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 108 | 108 | +0.3% | -0.5% to +1.1% | 77% | 69 / 13 / 26 |
| high-major | spread | 342 | 138 | -0.73 | -1.32 to -0.15 | 25% | 137 / 76 / 129 |
| high-major | total_points | 297 | 120 | -1.04 | -1.67 to -0.41 | 21% | 156 / 60 / 81 |
| mid-major | moneyline | 113 | 113 | +0.1% | -0.8% to +1.0% | 60% | 58 / 26 / 29 |
| mid-major | spread | 266 | 112 | -0.18 | -0.68 to +0.32 | 38% | 144 / 52 / 70 |
| mid-major | total_points | 252 | 104 | -0.74 | -1.56 to +0.08 | 29% | 137 / 45 / 70 |
| low-major | moneyline | 32 | 32 | +0.6% | -2.1% to +3.3% | 47% | 14 / 5 / 13 |
| low-major | spread | 64 | 35 | -0.02 | -1.18 to +1.13 | 36% | 23 / 18 / 23 |
| low-major | total_points | 75 | 35 | -1.23 | -3.79 to +1.33 | 31% | 28 / 18 / 29 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
