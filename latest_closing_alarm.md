# CBB closing-line alarm

As of 2026-11-06. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (94 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points, mid_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 75 | 75 | +0.5% | -0.1% to +1.1% | 79% | 49 / 10 / 16 |
| high-major | spread | 239 | 91 | -0.91 | -1.61 to -0.20 | 22% | 101 / 51 / 87 |
| high-major | total_points | 197 | 77 | -1.27 | -1.99 to -0.55 | 16% | 100 / 37 / 60 |
| mid-major | moneyline | 67 | 67 | +0.3% | -0.7% to +1.3% | 61% | 35 / 15 / 17 |
| mid-major | spread | 158 | 67 | -0.03 | -0.62 to +0.56 | 41% | 96 / 30 / 32 |
| mid-major | total_points | 159 | 64 | -0.77 | -1.54 to -0.00 | 25% | 85 / 27 / 47 |
| low-major | moneyline | 16 | 16 | -1.0% | -4.0% to +2.1% | 38% | 6 / 2 / 8 |
| low-major | spread | 32 | 16 | -0.73 | -2.32 to +0.86 | 25% | 11 / 9 / 12 |
| low-major | total_points | 37 | 19 | -1.28 | -3.21 to +0.64 | 19% | 10 / 10 / 17 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
