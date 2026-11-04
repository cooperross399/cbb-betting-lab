# CBB closing-line alarm

As of 2026-11-04. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (80 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / spread, high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 62 | 62 | +0.7% | +0.2% to +1.2% | 82% | 43 / 5 / 14 |
| high-major | spread | 184 | 69 | -0.81 | -1.62 to -0.00 | 21% | 81 / 37 / 66 |
| high-major | total_points | 149 | 58 | -1.31 | -2.17 to -0.45 | 15% | 77 / 22 / 50 |
| mid-major | moneyline | 55 | 55 | +0.3% | -0.8% to +1.4% | 60% | 34 / 9 / 12 |
| mid-major | spread | 132 | 55 | +0.03 | -0.65 to +0.71 | 43% | 88 / 25 / 19 |
| mid-major | total_points | 130 | 52 | -0.76 | -1.56 to +0.04 | 24% | 74 / 20 / 36 |
| low-major | moneyline | 6 | 6 | -2.9% | -7.0% to +1.1% | 0% | 3 / 0 / 3 |
| low-major | spread | 12 | 7 | -0.75 | -1.89 to +0.39 | 8% | 7 / 2 / 3 |
| low-major | total_points | 15 | 7 | -1.60 | -5.54 to +2.34 | 27% | 6 / 4 / 5 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
