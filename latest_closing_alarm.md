# CBB closing-line alarm

As of 2026-11-05. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (83 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 64 | 64 | +0.6% | +0.1% to +1.1% | 81% | 44 / 6 / 14 |
| high-major | spread | 190 | 72 | -0.89 | -1.71 to -0.08 | 21% | 82 / 41 / 67 |
| high-major | total_points | 153 | 60 | -1.27 | -2.11 to -0.42 | 16% | 78 / 24 / 51 |
| mid-major | moneyline | 59 | 59 | +0.3% | -0.7% to +1.3% | 61% | 35 / 10 / 14 |
| mid-major | spread | 140 | 59 | +0.01 | -0.64 to +0.66 | 43% | 91 / 26 / 23 |
| mid-major | total_points | 140 | 56 | -0.71 | -1.54 to +0.12 | 25% | 80 / 22 / 38 |
| low-major | moneyline | 8 | 8 | -2.1% | -5.6% to +1.4% | 12% | 5 / 0 / 3 |
| low-major | spread | 16 | 9 | -1.09 | -3.02 to +0.84 | 12% | 9 / 3 / 4 |
| low-major | total_points | 20 | 9 | -1.00 | -4.36 to +2.36 | 30% | 7 / 4 / 9 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
