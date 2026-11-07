# CBB closing-line alarm

As of 2026-11-07. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (97 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 99 | 99 | +0.6% | +0.1% to +1.2% | 81% | 64 / 12 / 23 |
| high-major | spread | 323 | 128 | -0.73 | -1.34 to -0.12 | 26% | 136 / 67 / 120 |
| high-major | total_points | 276 | 112 | -1.08 | -1.74 to -0.42 | 20% | 145 / 53 / 78 |
| mid-major | moneyline | 79 | 79 | +0.3% | -0.8% to +1.3% | 61% | 39 / 21 / 19 |
| mid-major | spread | 193 | 79 | -0.12 | -0.70 to +0.47 | 40% | 115 / 35 / 43 |
| mid-major | total_points | 191 | 78 | -0.71 | -1.64 to +0.22 | 26% | 105 / 30 / 56 |
| low-major | moneyline | 18 | 18 | -0.2% | -4.0% to +3.7% | 44% | 7 / 3 / 8 |
| low-major | spread | 37 | 18 | -0.39 | -2.10 to +1.33 | 32% | 15 / 9 / 13 |
| low-major | total_points | 38 | 20 | -1.25 | -3.12 to +0.62 | 18% | 11 / 10 / 17 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
