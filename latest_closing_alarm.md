# CBB closing-line alarm

As of 2026-11-03. Whether the model's leans (frozen full-game team rows with an edge of at least 2%) beat the closing line, per tier and main market, from the settled forward ledger and the line-movement captures (69 capture(s) read). Intervals are clustered by game and corrected across 152 cumulative hypotheses (x1.8324). Closing-line value is not a return, and a lean that beat the close can still lose.

**Alarm: high_major / total_points.** The corrected interval of closing-line value lies entirely below zero over enough leans and games. Each is a candidate for withdrawal from the allowlist; this report withdraws nothing.

| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |
|:---|:---|---:|---:|---:|:---|---:|:---|
| high-major | moneyline | 51 | 51 | +0.8% | +0.2% to +1.3% | 84% | 37 / 5 / 9 |
| high-major | spread | 151 | 56 | -0.63 | -1.51 to +0.25 | 23% | 74 / 33 / 44 |
| high-major | total_points | 125 | 45 | -1.49 | -2.47 to -0.51 | 15% | 65 / 20 / 40 |
| mid-major | moneyline | 51 | 51 | +0.2% | -0.9% to +1.3% | 61% | 31 / 9 / 11 |
| mid-major | spread | 123 | 51 | -0.01 | -0.70 to +0.69 | 42% | 80 / 24 / 19 |
| mid-major | total_points | 123 | 48 | -0.82 | -1.65 to +0.01 | 23% | 69 / 20 / 34 |
| low-major | moneyline | 5 | 5 | -2.7% | -7.5% to +2.1% | 0% | 3 / 0 / 2 |
| low-major | spread | 11 | 6 | -0.64 | -1.87 to +0.60 | 9% | 7 / 2 / 2 |
| low-major | total_points | 12 | 6 | -1.88 | -6.78 to +3.03 | 33% | 4 / 4 / 4 |

Spread and total values are points; moneyline values are probability, the closing de-vigged price minus the frozen price's implied probability. Unknown survival means the next capture did not cover the event, and is never counted as gone.
