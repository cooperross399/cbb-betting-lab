# CBB closing-line alarm

As of 2026-11-08. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (108 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 103 | 103 | +0.4% | -0.5% to +1.2% | 79% | 66 / 12 / 25 |
| high-major | spread | 332 | 132 | -0.75 | -1.34 to -0.16 | 25% | 137 / 72 / 123 |
| high-major | total_points | 280 | 113 | -1.07 | -1.72 to -0.41 | 20% | 148 / 53 / 79 |
| mid-major | moneyline | 105 | 105 | +0.1% | -0.7% to +1.0% | 61% | 52 / 26 / 27 |
| mid-major | spread | 245 | 104 | -0.22 | -0.74 to +0.29 | 38% | 131 / 47 / 67 |
| mid-major | total_points | 232 | 97 | -0.76 | -1.62 to +0.10 | 28% | 125 / 41 / 66 |
| low-major | moneyline | 29 | 29 | +0.4% | -2.5% to +3.3% | 45% | 13 / 5 / 11 |
| low-major | spread | 59 | 32 | -0.11 | -1.29 to +1.07 | 34% | 22 / 17 / 20 |
| low-major | total_points | 67 | 32 | -1.72 | -4.19 to +0.74 | 24% | 23 / 16 / 28 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
