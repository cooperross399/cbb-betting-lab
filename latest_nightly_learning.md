# What the model learned from 2026-11-26

**23 finished game(s) graded**, each priced walk-forward through the card's own seam and layers, fitted only on games before 2026-11-26. Error is final minus projection, home side, in points.

## How last night's projections did

| Tier | Games | Margin miss (avg) | Margin bias | Total miss (avg) | Total bias | Winner called |
|:---|---:|---:|---:|---:|---:|---:|
| high-major | 14 | 8.1 | -4.8 | 13.6 | +8.1 | 64.3% |
| mid-major | 6 | 4.8 | +2.5 | 11.5 | -9.2 | 100.0% |
| low-major | 3 | 15.0 | -12.8 | 6.9 | -6.9 | 33.3% |

Per tier, never pooled. These are forecast-accuracy figures on free data: they say how close the projections were, not whether any bet had an edge. Bets are graded on the Record tab and in the forward ledger.

**Biggest misses:**
- Army at UTSA: projected +11.3 (home), finished -18; total 146.8 projected, 140 scored.
- Miami at Michigan: projected -2.4 (home), finished -27; total 162.9 projected, 167 scored.
- Oklahoma at Purdue: projected +11.3 (home), finished -7; total 137.8 projected, 133 scored.
- Tennessee at Iowa State: projected +6.1 (home), finished -11; total 133.4 projected, 139 scored.
- UCLA at Saint Mary's: projected +1.7 (home), finished +15; total 148.5 projected, 155 scored.

## What the ratings took from it

Refitted on 1,076 game(s) this season, through 2026-11-26 (was 1,054, through 2026-11-25). 132 team(s) moved by 0.05 points per 100 or more.

Median share of each rating still carried by the preseason prior: offence 27% → 27%, defence 40% → 40%, tempo 24% → 24%. This falls as the season's results take over.

**Biggest risers** (net rating, points per 100 on a neutral floor):

| Team | Tier | Before | After | Change |
|:---|:---|---:|---:|---:|
| Army | low-major | -16.67 | -13.23 | +3.44 |
| Miami | high-major | +21.62 | +24.34 | +2.72 |
| Saint Mary's | mid-major | +26.23 | +28.55 | +2.32 |
| Oklahoma | high-major | +8.80 | +10.92 | +2.12 |
| Tennessee | high-major | +19.59 | +20.99 | +1.40 |
| Pittsburgh | high-major | +14.76 | +16.05 | +1.29 |
| Louisville | high-major | +20.11 | +21.19 | +1.08 |
| Creighton | high-major | +19.52 | +20.56 | +1.04 |
| South Carolina | high-major | +11.71 | +12.71 | +1.00 |
| Stanford | high-major | +7.77 | +8.47 | +0.70 |

**Biggest fallers** (net rating, points per 100 on a neutral floor):

| Team | Tier | Before | After | Change |
|:---|:---|---:|---:|---:|
| UTSA | mid-major | -2.13 | -5.57 | -3.44 |
| Michigan | high-major | +24.36 | +21.56 | -2.80 |
| Purdue | high-major | +26.77 | +24.46 | -2.31 |
| UCLA | high-major | +29.14 | +27.30 | -1.84 |
| Iowa State | high-major | +22.16 | +20.72 | -1.44 |
| DePaul | high-major | +20.59 | +19.23 | -1.36 |
| Arizona State | high-major | +14.84 | +13.78 | -1.06 |
| TCU | high-major | +24.44 | +23.49 | -0.95 |
| Saint Louis | mid-major | +22.30 | +21.52 | -0.78 |
| St. John's | high-major | +27.35 | +26.68 | -0.67 |

## The other two learners

- Trust in the model against the price, per tier (0 is the market, 1 is the model as it stands): high-major 0.000 (seed 0.046, 86,304 settled forward row(s), 48,252 closing-line row(s)); low-major 0.123 (seed 0.011, 27,628 settled forward row(s), 16,408 closing-line row(s)); mid-major 0.000 (seed 0.032, 83,648 settled forward row(s), 46,608 closing-line row(s)). Every wager's probability is pulled to market + trust x (model - market) before the edge bar; a wager with no two-sided price carries no trusted opinion.
- Layer audit (2026-11-27): on the card: Home court, Rest, Who is missing, Second opinion, Three-point defence luck, Spread bias against the market.
- Switched from the declared card: Last five games, Three-point defence luck.

## The season so far

| Night | Games | Margin miss | Total miss | Winner called | Prior share |
|:---|---:|---:|---:|---:|---:|
| 2026-11-13 | 55 | 10.54 | 11.83 | 76.4% | 46% |
| 2026-11-14 | 57 | 10.07 | 15.07 | 66.7% | 45% |
| 2026-11-15 | 35 | 11.78 | 14.73 | 77.1% | 44% |
| 2026-11-16 | 22 | 13.30 | 17.51 | 81.8% | 39% |
| 2026-11-17 | 55 | 10.54 | 13.06 | 76.4% | 38% |
| 2026-11-18 | 61 | 9.75 | 13.99 | 90.2% | 37% |
| 2026-11-19 | 29 | 9.89 | 10.08 | 58.6% | 37% |
| 2026-11-20 | 51 | 10.57 | 13.87 | 60.8% | 33% |
| 2026-11-21 | 51 | 10.90 | 12.10 | 68.6% | 32% |
| 2026-11-22 | 38 | 10.84 | 13.27 | 63.2% | 37% |
| 2026-11-23 | 34 | 8.59 | 14.72 | 76.5% | 32% |
| 2026-11-24 | 76 | 10.15 | 12.76 | 69.7% | 28% |
| 2026-11-25 | 58 | 9.14 | 14.55 | 63.8% | 27% |
| 2026-11-26 | 23 | 8.16 | 12.16 | 69.6% | 27% |
