# NCAA Division I men's basketball — price backtest

Generated 2026-09-04T19:59:28Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**118,050 graded bets** from 436,672 graded wagers offered, across 16,634 games and 513 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | always home | 4,733 | 61 | -4.1% | -23.5% to +15.3% | -35.2% to +27.0% | no demonstrated edge |
| high_major | alternate_spread | always away | 4,732 | 61 | -12.9% | -29.2% to +3.5% | -39.1% to +13.4% | no demonstrated edge |
| high_major | alternate_spread | always the favourite | 2,285 | 74 | -15.9% | -31.7% to -0.1% | -41.2% to +9.4% | no demonstrated edge |
| high_major | alternate_spread | always the underdog | 2,205 | 73 | +1.3% | -24.4% to +27.1% | -39.9% to +42.6% | no demonstrated edge |
| high_major | alternate_total_points | always over | 6,618 | 94 | +20.5% | +0.3% to +40.7% | -11.9% to +52.9% | no demonstrated edge |
| high_major | alternate_total_points | always under | 6,618 | 94 | -25.3% | -41.4% to -9.1% | -51.2% to +0.7% | no demonstrated edge |
| high_major | alternate_total_points | always the favourite | 6,645 | 94 | -11.0% | -14.9% to -7.1% | -17.3% to -4.7% | demonstrated deficit |
| high_major | alternate_total_points | always the underdog | 6,591 | 94 | +6.3% | -8.1% to +20.7% | -16.8% to +29.4% | no demonstrated edge |
| high_major | moneyline | always home | 4,837 | 513 | +3.2% | +0.1% to +6.3% | -1.8% to +8.2% | no demonstrated edge |
| high_major | moneyline | always away | 4,837 | 4,837 | -10.8% | -17.3% to -4.2% | -21.3% to -0.3% | demonstrated deficit |
| high_major | moneyline | always the favourite | 4,844 | 4,837 | -1.2% | -3.0% to +0.5% | -4.1% to +1.6% | no demonstrated edge |
| high_major | moneyline | always the underdog | 4,830 | 4,830 | -6.3% | -13.3% to +0.6% | -17.4% to +4.7% | no demonstrated edge |
| high_major | moneyline_h1 | always home | 93 | 93 | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always away | 93 | 93 | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the favourite | 93 | 93 | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the underdog | 93 | 93 | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always home | 49 | 38 | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always away | 49 | 49 | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the favourite | 49 | 38 | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the underdog | 49 | 49 | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | spread | always home | 11,071 | 513 | -1.8% | -4.6% to +1.1% | -6.4% to +2.8% | no demonstrated edge |
| high_major | spread | always away | 11,071 | 513 | -5.2% | -8.0% to -2.3% | -9.7% to -0.6% | demonstrated deficit |
| high_major | spread | always the favourite | 332 | 95 | -3.5% | -12.4% to +5.5% | -17.8% to +10.9% | no demonstrated edge |
| high_major | spread | always the underdog | 170 | 71 | — | — | — | not enough evidence (170 bets, below the 200 declared in advance) |
| high_major | spread_h1 | always home | 368 | 94 | +0.8% | -20.0% to +21.5% | -32.6% to +34.1% | no demonstrated edge |
| high_major | spread_h1 | always away | 368 | 94 | -10.6% | -31.6% to +10.4% | -44.3% to +23.1% | no demonstrated edge |
| high_major | spread_h1 | always the favourite | 46 | 12 | — | — | — | not enough evidence (46 bets, below the 200 declared in advance) |
| high_major | spread_h1 | always the underdog | 42 | 10 | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always home | 133 | 89 | — | — | — | not enough evidence (133 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always away | 133 | 89 | — | — | — | not enough evidence (133 bets, below the 200 declared in advance) |
| high_major | team_total | always over | 1,995 | 735 | +3.1% | -2.7% to +8.8% | -6.2% to +12.3% | no demonstrated edge |
| high_major | team_total | always under | 1,995 | 735 | -13.9% | -19.8% to -8.0% | -23.4% to -4.5% | demonstrated deficit |
| high_major | team_total | always the favourite | 2,297 | 722 | -6.7% | -9.4% to -4.0% | -11.1% to -2.4% | demonstrated deficit |
| high_major | team_total | always the underdog | 1,529 | 689 | -3.5% | -7.9% to +0.9% | -10.5% to +3.6% | no demonstrated edge |
| high_major | total_points | always over | 14,269 | 513 | -2.1% | -5.0% to +0.7% | -6.7% to +2.4% | no demonstrated edge |
| high_major | total_points | always under | 14,269 | 513 | -5.6% | -8.5% to -2.8% | -10.2% to -1.1% | demonstrated deficit |
| high_major | total_points | always the favourite | 20,279 | 4,856 | -4.0% | -4.8% to -3.2% | -5.3% to -2.7% | demonstrated deficit |
| high_major | total_points | always the underdog | 8,259 | 4,497 | -3.6% | -5.6% to -1.6% | -6.9% to -0.4% | demonstrated deficit |
| high_major | total_points_h1 | always over | 368 | 94 | +1.7% | -19.0% to +22.4% | -31.6% to +35.0% | no demonstrated edge |
| high_major | total_points_h1 | always under | 368 | 94 | -11.8% | -32.4% to +8.8% | -44.9% to +21.3% | no demonstrated edge |
| high_major | total_points_h1 | always the favourite | 448 | 61 | -2.9% | -8.4% to +2.6% | -11.7% to +5.9% | no demonstrated edge |
| high_major | total_points_h1 | always the underdog | 288 | 60 | -8.4% | -17.6% to +0.8% | -23.2% to +6.4% | no demonstrated edge |
| high_major | total_points_h2 | always over | 84 | 56 | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always under | 84 | 56 | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the favourite | 108 | 84 | — | — | — | not enough evidence (108 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the underdog | 60 | 46 | — | — | — | not enough evidence (60 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | always home | 18,066 | 107 | -21.7% | -29.5% to -14.0% | -34.2% to -9.3% | demonstrated deficit |
| mid_major | alternate_spread | always away | 18,073 | 107 | -5.3% | -13.1% to +2.5% | -17.8% to +7.2% | no demonstrated edge |
| mid_major | alternate_spread | always the favourite | 9,369 | 315 | -12.6% | -19.2% to -5.9% | -23.2% to -1.9% | demonstrated deficit |
| mid_major | alternate_spread | always the underdog | 8,957 | 104 | -14.0% | -25.5% to -2.5% | -32.4% to +4.5% | no demonstrated edge |
| mid_major | alternate_team_total | always over | 134 | 9 | — | — | — | not enough evidence (134 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always under | 134 | 9 | — | — | — | not enough evidence (134 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the favourite | 78 | 6 | — | — | — | not enough evidence (78 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the underdog | 78 | 6 | — | — | — | not enough evidence (78 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | always over | 25,981 | 107 | -14.7% | -23.1% to -6.3% | -28.2% to -1.2% | demonstrated deficit |
| mid_major | alternate_total_points | always under | 25,981 | 107 | -6.2% | -15.0% to +2.5% | -20.3% to +7.8% | no demonstrated edge |
| mid_major | alternate_total_points | always the favourite | 26,138 | 352 | -2.9% | -5.1% to -0.7% | -6.5% to +0.7% | no demonstrated edge |
| mid_major | alternate_total_points | always the underdog | 25,824 | 352 | -18.1% | -25.1% to -11.1% | -29.4% to -6.9% | demonstrated deficit |
| mid_major | moneyline | always home | 9,170 | 536 | +1.4% | -0.8% to +3.7% | -2.2% to +5.1% | no demonstrated edge |
| mid_major | moneyline | always away | 9,170 | 536 | -7.6% | -11.3% to -3.9% | -13.5% to -1.7% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 9,188 | 536 | -1.8% | -3.2% to -0.5% | -4.0% to +0.3% | no demonstrated edge |
| mid_major | moneyline | always the underdog | 9,152 | 536 | -4.3% | -8.6% to -0.1% | -11.1% to +2.5% | no demonstrated edge |
| mid_major | moneyline_h1 | always home | 345 | 345 | -14.4% | -23.0% to -5.7% | -28.3% to -0.5% | demonstrated deficit |
| mid_major | moneyline_h1 | always away | 345 | 345 | +20.7% | +3.2% to +38.2% | -7.3% to +48.8% | no demonstrated edge |
| mid_major | moneyline_h1 | always the favourite | 350 | 106 | -6.4% | -14.6% to +1.8% | -19.5% to +6.7% | no demonstrated edge |
| mid_major | moneyline_h1 | always the underdog | 340 | 105 | +13.1% | -5.9% to +32.0% | -17.3% to +43.4% | no demonstrated edge |
| mid_major | moneyline_h2 | always home | 198 | 198 | — | — | — | not enough evidence (198 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always away | 198 | 198 | — | — | — | not enough evidence (198 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always the favourite | 202 | 198 | -7.8% | -17.4% to +1.8% | -23.3% to +7.7% | no demonstrated edge |
| mid_major | moneyline_h2 | always the underdog | 194 | 194 | — | — | — | not enough evidence (194 bets, below the 200 declared in advance) |
| mid_major | spread | always home | 21,764 | 536 | -2.3% | -4.3% to -0.2% | -5.6% to +1.1% | no demonstrated edge |
| mid_major | spread | always away | 21,764 | 536 | -4.6% | -6.7% to -2.5% | -7.9% to -1.3% | demonstrated deficit |
| mid_major | spread | always the favourite | 839 | 181 | -5.4% | -10.5% to -0.3% | -13.6% to +2.8% | no demonstrated edge |
| mid_major | spread | always the underdog | 403 | 146 | -2.1% | -13.0% to +8.8% | -19.6% to +15.4% | no demonstrated edge |
| mid_major | spread_h1 | always home | 1,362 | 345 | -15.2% | -26.2% to -4.3% | -32.8% to +2.4% | no demonstrated edge |
| mid_major | spread_h1 | always away | 1,362 | 345 | +6.0% | -5.1% to +17.1% | -11.8% to +23.8% | no demonstrated edge |
| mid_major | spread_h1 | always the favourite | 150 | 42 | — | — | — | not enough evidence (150 bets, below the 200 declared in advance) |
| mid_major | spread_h1 | always the underdog | 128 | 39 | — | — | — | not enough evidence (128 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always home | 588 | 334 | -2.6% | -13.4% to +8.2% | -20.0% to +14.8% | no demonstrated edge |
| mid_major | spread_h2 | always away | 588 | 334 | -10.8% | -21.6% to -0.0% | -28.1% to +6.5% | no demonstrated edge |
| mid_major | spread_h2 | always the favourite | 10 | 4 | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always the underdog | 10 | 4 | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| mid_major | team_total | always over | 7,161 | 2,761 | -2.8% | -5.7% to +0.1% | -7.5% to +1.8% | no demonstrated edge |
| mid_major | team_total | always under | 7,161 | 2,761 | -8.2% | -11.1% to -5.2% | -12.9% to -3.4% | demonstrated deficit |
| mid_major | team_total | always the favourite | 8,185 | 138 | -4.2% | -5.9% to -2.6% | -6.9% to -1.6% | demonstrated deficit |
| mid_major | team_total | always the underdog | 5,533 | 137 | -7.4% | -10.1% to -4.7% | -11.7% to -3.1% | demonstrated deficit |
| mid_major | total_points | always over | 28,296 | 536 | -2.4% | -4.5% to -0.3% | -5.7% to +0.9% | no demonstrated edge |
| mid_major | total_points | always under | 28,296 | 536 | -5.4% | -7.5% to -3.3% | -8.7% to -2.1% | demonstrated deficit |
| mid_major | total_points | always the favourite | 40,215 | 9,183 | -3.8% | -4.4% to -3.3% | -4.7% to -2.9% | demonstrated deficit |
| mid_major | total_points | always the underdog | 16,377 | 8,536 | -4.0% | -5.4% to -2.6% | -6.3% to -1.8% | demonstrated deficit |
| mid_major | total_points_h1 | always over | 1,337 | 106 | -14.3% | -24.9% to -3.6% | -31.3% to +2.8% | no demonstrated edge |
| mid_major | total_points_h1 | always under | 1,337 | 106 | +3.2% | -7.7% to +14.1% | -14.3% to +20.6% | no demonstrated edge |
| mid_major | total_points_h1 | always the favourite | 1,615 | 106 | -4.9% | -7.8% to -2.0% | -9.6% to -0.2% | demonstrated deficit |
| mid_major | total_points_h1 | always the underdog | 1,059 | 104 | -6.5% | -12.8% to -0.2% | -16.5% to +3.6% | no demonstrated edge |
| mid_major | total_points_h2 | always over | 388 | 331 | -3.0% | -16.2% to +10.2% | -24.2% to +18.1% | no demonstrated edge |
| mid_major | total_points_h2 | always under | 388 | 331 | -9.0% | -21.4% to +3.4% | -28.9% to +10.9% | no demonstrated edge |
| mid_major | total_points_h2 | always the favourite | 488 | 104 | -9.7% | -16.3% to -3.0% | -20.4% to +1.0% | no demonstrated edge |
| mid_major | total_points_h2 | always the underdog | 288 | 95 | +0.2% | -12.9% to +13.3% | -20.8% to +21.2% | no demonstrated edge |
| low_major | alternate_spread | always home | 6,637 | 163 | -14.1% | -26.6% to -1.7% | -34.1% to +5.9% | no demonstrated edge |
| low_major | alternate_spread | always away | 6,637 | 163 | +0.9% | -13.1% to +14.9% | -21.6% to +23.3% | no demonstrated edge |
| low_major | alternate_spread | always the favourite | 3,455 | 70 | -6.7% | -19.9% to +6.6% | -27.8% to +14.5% | no demonstrated edge |
| low_major | alternate_spread | always the underdog | 3,341 | 70 | +0.4% | -22.5% to +23.3% | -36.3% to +37.1% | no demonstrated edge |
| low_major | alternate_team_total | always over | 12 | 1 | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always under | 12 | 1 | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the favourite | 6 | 1 | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the underdog | 6 | 1 | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | always over | 9,791 | 75 | -14.6% | -28.5% to -0.7% | -36.9% to +7.7% | no demonstrated edge |
| low_major | alternate_total_points | always under | 9,791 | 75 | +3.0% | -12.0% to +18.0% | -21.1% to +27.0% | no demonstrated edge |
| low_major | alternate_total_points | always the favourite | 9,866 | 163 | -7.5% | -10.9% to -4.1% | -12.9% to -2.0% | demonstrated deficit |
| low_major | alternate_total_points | always the underdog | 9,716 | 163 | -4.1% | -14.0% to +5.8% | -20.0% to +11.8% | no demonstrated edge |
| low_major | moneyline | always home | 5,930 | 466 | -2.3% | -5.2% to +0.6% | -7.0% to +2.4% | no demonstrated edge |
| low_major | moneyline | always away | 5,930 | 5,930 | -4.3% | -8.0% to -0.6% | -10.2% to +1.7% | no demonstrated edge |
| low_major | moneyline | always the favourite | 5,954 | 5,930 | -1.4% | -3.1% to +0.4% | -4.2% to +1.4% | no demonstrated edge |
| low_major | moneyline | always the underdog | 5,906 | 466 | -5.2% | -9.6% to -0.8% | -12.3% to +1.9% | no demonstrated edge |
| low_major | moneyline_h1 | always home | 159 | 75 | — | — | — | not enough evidence (159 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always away | 159 | 75 | — | — | — | not enough evidence (159 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the favourite | 161 | 159 | — | — | — | not enough evidence (161 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the underdog | 157 | 157 | — | — | — | not enough evidence (157 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always home | 98 | 98 | — | — | — | not enough evidence (98 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always away | 98 | 98 | — | — | — | not enough evidence (98 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the favourite | 101 | 98 | — | — | — | not enough evidence (101 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the underdog | 95 | 95 | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | spread | always home | 13,773 | 466 | -5.0% | -7.6% to -2.3% | -9.2% to -0.7% | demonstrated deficit |
| low_major | spread | always away | 13,773 | 466 | -1.9% | -4.5% to +0.8% | -6.1% to +2.4% | no demonstrated edge |
| low_major | spread | always the favourite | 669 | 221 | -5.6% | -11.3% to +0.1% | -14.7% to +3.5% | no demonstrated edge |
| low_major | spread | always the underdog | 307 | 160 | +0.3% | -12.5% to +13.0% | -20.1% to +20.7% | no demonstrated edge |
| low_major | spread_h1 | always home | 654 | 75 | -16.9% | -34.4% to +0.5% | -44.9% to +11.1% | no demonstrated edge |
| low_major | spread_h1 | always away | 654 | 75 | +7.4% | -10.3% to +25.0% | -20.9% to +35.6% | no demonstrated edge |
| low_major | spread_h1 | always the favourite | 109 | 19 | — | — | — | not enough evidence (109 bets, below the 200 declared in advance) |
| low_major | spread_h1 | always the underdog | 69 | 18 | — | — | — | not enough evidence (69 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always home | 233 | 159 | -10.8% | -26.2% to +4.7% | -35.5% to +14.0% | no demonstrated edge |
| low_major | spread_h2 | always away | 233 | 159 | -1.6% | -16.6% to +13.4% | -25.7% to +22.5% | no demonstrated edge |
| low_major | spread_h2 | always the favourite | 8 | 4 | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always the underdog | 8 | 4 | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | team_total | always over | 3,093 | 1,312 | -4.4% | -8.6% to -0.3% | -11.1% to +2.2% | no demonstrated edge |
| low_major | team_total | always under | 3,093 | 1,312 | -6.5% | -10.6% to -2.3% | -13.1% to +0.2% | no demonstrated edge |
| low_major | team_total | always the favourite | 3,565 | 115 | -6.2% | -8.7% to -3.7% | -10.3% to -2.1% | demonstrated deficit |
| low_major | team_total | always the underdog | 2,369 | 114 | -4.4% | -8.4% to -0.4% | -10.8% to +2.0% | no demonstrated edge |
| low_major | total_points | always over | 17,750 | 466 | -1.9% | -4.6% to +0.8% | -6.3% to +2.4% | no demonstrated edge |
| low_major | total_points | always under | 17,750 | 466 | -5.8% | -8.5% to -3.1% | -10.2% to -1.5% | demonstrated deficit |
| low_major | total_points | always the favourite | 25,302 | 5,931 | -4.1% | -4.8% to -3.4% | -5.2% to -2.9% | demonstrated deficit |
| low_major | total_points | always the underdog | 10,198 | 5,489 | -3.4% | -5.2% to -1.6% | -6.3% to -0.6% | demonstrated deficit |
| low_major | total_points_h1 | always over | 652 | 75 | -7.8% | -27.2% to +11.6% | -38.9% to +23.4% | no demonstrated edge |
| low_major | total_points_h1 | always under | 652 | 75 | -2.5% | -21.8% to +16.8% | -33.5% to +28.5% | no demonstrated edge |
| low_major | total_points_h1 | always the favourite | 769 | 159 | -2.7% | -6.7% to +1.4% | -9.2% to +3.8% | no demonstrated edge |
| low_major | total_points_h1 | always the underdog | 535 | 152 | -8.7% | -15.1% to -2.3% | -19.0% to +1.6% | no demonstrated edge |
| low_major | total_points_h2 | always over | 129 | 123 | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always under | 129 | 123 | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the favourite | 167 | 62 | — | — | — | not enough evidence (167 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the underdog | 91 | 51 | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| unplaced | moneyline | always home | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. **6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention.

| Tier | Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | 2,551 | 70 | -10.4% | -33.0% to +12.2% | -46.7% to +25.9% | no demonstrated edge |
| high_major | alternate_total_points | 2,114 | 64 | -1.1% | -31.0% to +28.7% | -49.0% to +46.7% | no demonstrated edge |
| high_major | moneyline | 3,466 | 458 | -0.6% | -8.1% to +6.9% | -12.6% to +11.4% | no demonstrated edge |
| high_major | moneyline_h1 | 54 | 44 | — | — | — | not enough evidence (54 bets, below the 200 declared in advance) |
| high_major | spread | 7,645 | 457 | -1.1% | -4.5% to +2.2% | -6.5% to +4.3% | no demonstrated edge |
| high_major | spread_h1 | 223 | 72 | -24.7% | -47.9% to -1.5% | -62.0% to +12.6% | no demonstrated edge |
| high_major | team_total | 1,210 | 622 | -6.1% | -12.2% to -0.0% | -15.9% to +3.7% | no demonstrated edge |
| high_major | total_points | 7,244 | 441 | -2.9% | -6.7% to +0.9% | -9.0% to +3.2% | no demonstrated edge |
| high_major | total_points_h1 | 184 | 57 | — | — | — | not enough evidence (184 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | 9,319 | 93 | -3.4% | -13.9% to +7.1% | -20.3% to +13.5% | no demonstrated edge |
| mid_major | alternate_team_total | 91 | 6 | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | 7,467 | 230 | -17.0% | -29.7% to -4.2% | -37.4% to +3.5% | no demonstrated edge |
| mid_major | moneyline | 6,616 | 483 | -4.4% | -8.6% to -0.2% | -11.1% to +2.3% | no demonstrated edge |
| mid_major | moneyline_h1 | 184 | 79 | — | — | — | not enough evidence (184 bets, below the 200 declared in advance) |
| mid_major | spread | 14,422 | 480 | -1.8% | -4.4% to +0.9% | -6.1% to +2.6% | no demonstrated edge |
| mid_major | spread_h1 | 799 | 238 | -7.4% | -21.2% to +6.5% | -29.6% to +14.8% | no demonstrated edge |
| mid_major | team_total | 4,236 | 130 | -4.8% | -8.1% to -1.5% | -10.1% to +0.6% | no demonstrated edge |
| mid_major | total_points | 14,905 | 476 | +0.0% | -2.7% to +2.8% | -4.4% to +4.4% | no demonstrated edge |
| mid_major | total_points_h1 | 594 | 202 | -2.4% | -17.4% to +12.6% | -26.5% to +21.7% | no demonstrated edge |
| low_major | alternate_spread | 3,510 | 127 | -2.1% | -19.2% to +15.0% | -29.5% to +25.4% | no demonstrated edge |
| low_major | alternate_team_total | 11 | 1 | — | — | — | not enough evidence (11 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | 3,785 | 121 | -10.5% | -30.3% to +9.4% | -42.3% to +21.3% | no demonstrated edge |
| low_major | moneyline | 4,584 | 409 | -7.7% | -13.0% to -2.4% | -16.2% to +0.7% | no demonstrated edge |
| low_major | moneyline_h1 | 82 | 82 | — | — | — | not enough evidence (82 bets, below the 200 declared in advance) |
| low_major | spread | 9,512 | 409 | -0.2% | -3.2% to +2.8% | -5.1% to +4.6% | no demonstrated edge |
| low_major | spread_h1 | 405 | 121 | +5.0% | -14.9% to +25.0% | -26.9% to +37.0% | no demonstrated edge |
| low_major | team_total | 1,973 | 107 | -5.1% | -10.1% to -0.1% | -13.1% to +2.9% | no demonstrated edge |
| low_major | total_points | 10,532 | 4,206 | -5.2% | -8.3% to -2.1% | -10.2% to -0.2% | demonstrated deficit |
| low_major | total_points_h1 | 326 | 106 | -11.4% | -32.3% to +9.5% | -44.9% to +22.2% | no demonstrated edge |
| unplaced | moneyline | 1 | 1 | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 24,691 | 3,829 | -3.1% | -7.4% to +1.2% | -10.0% to +3.8% | no demonstrated edge |
| mid_major | 58,633 | 486 | -4.1% | -7.2% to -1.0% | -9.0% to +0.9% | no demonstrated edge |
| low_major | 34,720 | 5,337 | -4.3% | -7.8% to -0.7% | -10.0% to +1.4% | no demonstrated edge |
| unplaced | 6 | 2 | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| alternate_spread | 15,380 | 464 | -4.3% | -12.3% to +3.8% | -17.1% to +8.6% | no demonstrated edge |
| alternate_team_total | 102 | 10 | — | — | — | not enough evidence (102 bets, below the 200 declared in advance) |
| alternate_total_points | 13,366 | 415 | -12.6% | -22.9% to -2.4% | -29.1% to +3.8% | no demonstrated edge |
| moneyline | 14,667 | 512 | -4.5% | -7.7% to -1.4% | -9.6% to +0.6% | no demonstrated edge |
| moneyline_h1 | 320 | 320 | +7.6% | -10.9% to +26.1% | -22.1% to +37.3% | no demonstrated edge |
| spread | 31,582 | 511 | -1.1% | -2.8% to +0.6% | -3.9% to +1.6% | no demonstrated edge |
| spread_h1 | 1,427 | 431 | -6.6% | -16.9% to +3.8% | -23.1% to +10.0% | no demonstrated edge |
| team_total | 7,419 | 134 | -5.1% | -7.6% to -2.6% | -9.1% to -1.0% | demonstrated deficit |
| total_points | 32,683 | 12,933 | -2.3% | -4.1% to -0.6% | -5.2% to +0.5% | no demonstrated edge |
| total_points_h1 | 1,104 | 365 | -5.5% | -16.7% to +5.6% | -23.4% to +12.4% | no demonstrated edge |
| every market | 118,050 | 16,634 | -3.9% | -6.0% to -1.9% | -7.2% to -0.7% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 19,974 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.0%), **2** (6.0%), **4** (5.8%), **8** (5.4%), **7** (5.3%), **6** (5.2%), **9** (4.9%), **10** (4.8%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 84.4% of 116,891 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 11,524 | 9.0% [8.5%, 9.6%] | +3.0 pp | 415 | 2.4% [1.3%, 4.4%] | -5.0 pp |
| 10%–20% | 16,153 | 20.8% [20.2%, 21.4%] | +5.5 pp | 2,345 | 7.8% [6.8%, 9.0%] | -7.8 pp |
| 20%–30% | 24,884 | 32.8% [32.2%, 33.3%] | +7.4 pp | 3,804 | 15.1% [14.0%, 16.3%] | -10.3 pp |
| 30%–40% | 45,905 | 43.7% [43.2%, 44.2%] | +8.1 pp | 5,884 | 24.9% [23.8%, 26.0%] | -10.1 pp |
| 40%–50% | 92,762 | 49.2% [48.9%, 49.5%] | +3.9 pp | 6,621 | 34.3% [33.2%, 35.5%] | -10.8 pp |
| 50%–60% | 87,668 | 51.1% [50.7%, 51.4%] | -3.5 pp | 49,261 | 49.2% [48.7%, 49.6%] | -6.7 pp |
| 60%–70% | 41,549 | 57.2% [56.8%, 57.7%] | -7.2 pp | 29,274 | 52.0% [51.4%, 52.5%] | -12.2 pp |
| 70%–80% | 22,980 | 68.1% [67.5%, 68.7%] | -6.5 pp | 11,328 | 58.4% [57.5%, 59.3%] | -15.9 pp |
| 80%–90% | 15,096 | 80.0% [79.3%, 80.6%] | -4.8 pp | 5,398 | 69.0% [67.7%, 70.2%] | -15.4 pp |
| 90%–100% | 11,381 | 91.3% [90.7%, 91.8%] | -2.7 pp | 2,561 | 84.3% [82.8%, 85.6%] | -10.1 pp |

- **Overall: 0.5 pp underconfident** over 369,902 graded rows in 10 usable bucket(s).
- **Selected: 10.0 pp overconfident** over 116,891 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 1,159 push, 29 unsettleable. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
