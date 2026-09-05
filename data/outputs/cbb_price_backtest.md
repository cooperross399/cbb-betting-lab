# NCAA Division I men's basketball — price backtest

Generated 2026-09-05T13:13:24Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**191,053 graded bets** from 914,392 graded wagers offered, across 26,591 games and 791 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 30 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.60. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | always home | 4,733 | 61 days | -4.1% | -23.5% to +15.3% | -35.2% to +27.0% | no demonstrated edge |
| high_major | alternate_spread | always away | 4,732 | 61 days | -12.9% | -29.2% to +3.5% | -39.1% to +13.4% | no demonstrated edge |
| high_major | alternate_spread | always the favourite | 2,285 | 74 games | -15.9% | -31.7% to -0.1% | -41.2% to +9.4% | no demonstrated edge |
| high_major | alternate_spread | always the underdog | 2,205 | 73 games | +1.3% | -24.4% to +27.1% | -39.9% to +42.6% | no demonstrated edge |
| high_major | alternate_total_points | always over | 6,618 | 94 games | +20.5% | +0.3% to +40.7% | -11.9% to +52.9% | no demonstrated edge |
| high_major | alternate_total_points | always under | 6,618 | 94 games | -25.3% | -41.4% to -9.1% | -51.2% to +0.7% | no demonstrated edge |
| high_major | alternate_total_points | always the favourite | 6,645 | 94 games | -11.0% | -14.9% to -7.1% | -17.3% to -4.7% | demonstrated deficit |
| high_major | alternate_total_points | always the underdog | 6,591 | 94 games | +6.3% | -8.1% to +20.7% | -16.8% to +29.4% | no demonstrated edge |
| high_major | moneyline | always home | 7,687 | 797 days | +2.4% | -0.1% to +4.9% | -1.6% to +6.4% | no demonstrated edge |
| high_major | moneyline | always away | 7,687 | 7,687 games | -13.8% | -18.6% to -8.9% | -21.5% to -6.0% | demonstrated deficit |
| high_major | moneyline | always the favourite | 7,699 | 797 days | -1.5% | -2.9% to -0.0% | -3.8% to +0.8% | no demonstrated edge |
| high_major | moneyline | always the underdog | 7,675 | 797 days | -9.9% | -15.3% to -4.6% | -18.5% to -1.3% | demonstrated deficit |
| high_major | moneyline_h1 | always home | 93 | 93 games | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always away | 93 | 93 games | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the favourite | 93 | 93 games | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the underdog | 93 | 93 games | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always home | 49 | 38 days | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always away | 49 | 49 games | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the favourite | 49 | 38 days | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the underdog | 49 | 49 games | — | — | — | not enough evidence (49 bets, below the 200 declared in advance) |
| high_major | player_assists | always over | 8,745 | 115 days | -15.5% | -22.0% to -8.9% | -26.0% to -4.9% | demonstrated deficit |
| high_major | player_assists | always under | 3,262 | 425 games | -5.4% | -9.6% to -1.2% | -12.1% to +1.3% | no demonstrated edge |
| high_major | player_assists | always the favourite | 3,307 | 425 games | -3.8% | -6.7% to -1.0% | -8.4% to +0.7% | no demonstrated edge |
| high_major | player_assists | always the underdog | 3,217 | 424 games | -7.8% | -12.3% to -3.3% | -15.0% to -0.6% | demonstrated deficit |
| high_major | player_double_double | always over | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| high_major | player_double_double | always under | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| high_major | player_double_double | always the favourite | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| high_major | player_double_double | always the underdog | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| high_major | player_first_basket | always over | 386 | 42 games | -21.9% | -34.4% to -9.4% | -42.0% to -1.9% | demonstrated deficit |
| high_major | player_points | always over | 24,313 | 117 days | -20.8% | -26.1% to -15.4% | -29.4% to -12.1% | demonstrated deficit |
| high_major | player_points | always under | 5,279 | 117 days | -10.1% | -16.0% to -4.3% | -19.6% to -0.7% | demonstrated deficit |
| high_major | player_points | always the favourite | 5,619 | 117 days | -6.3% | -8.8% to -3.8% | -10.3% to -2.3% | demonstrated deficit |
| high_major | player_points | always the underdog | 4,939 | 117 days | +0.2% | -6.0% to +6.4% | -9.7% to +10.1% | no demonstrated edge |
| high_major | player_points_assists | always over | 1,107 | 171 games | -7.2% | -12.5% to -1.9% | -15.6% to +1.3% | no demonstrated edge |
| high_major | player_points_assists | always under | 1,109 | 171 games | -6.3% | -11.6% to -1.0% | -14.8% to +2.2% | no demonstrated edge |
| high_major | player_points_assists | always the favourite | 1,194 | 44 days | -9.5% | -14.4% to -4.6% | -17.4% to -1.6% | demonstrated deficit |
| high_major | player_points_assists | always the underdog | 1,016 | 44 days | -3.7% | -9.9% to +2.5% | -13.7% to +6.2% | no demonstrated edge |
| high_major | player_points_rebounds | always over | 1,418 | 171 games | -12.4% | -17.2% to -7.6% | -20.1% to -4.7% | demonstrated deficit |
| high_major | player_points_rebounds | always under | 1,416 | 171 games | -1.3% | -6.1% to +3.5% | -9.0% to +6.5% | no demonstrated edge |
| high_major | player_points_rebounds | always the favourite | 1,517 | 44 days | -8.8% | -13.3% to -4.4% | -16.0% to -1.7% | demonstrated deficit |
| high_major | player_points_rebounds | always the underdog | 1,307 | 171 games | -4.4% | -10.0% to +1.1% | -13.3% to +4.5% | no demonstrated edge |
| high_major | player_pra | always over | 5,797 | 385 games | -10.7% | -15.0% to -6.4% | -17.6% to -3.8% | demonstrated deficit |
| high_major | player_pra | always under | 2,399 | 385 games | -4.1% | -7.8% to -0.4% | -10.0% to +1.8% | no demonstrated edge |
| high_major | player_pra | always the favourite | 2,824 | 107 days | -8.2% | -11.4% to -5.0% | -13.4% to -3.0% | demonstrated deficit |
| high_major | player_pra | always the underdog | 1,974 | 106 days | -4.4% | -9.3% to +0.6% | -12.3% to +3.6% | no demonstrated edge |
| high_major | player_rebounds | always over | 15,706 | 431 games | -30.7% | -35.9% to -25.5% | -39.0% to -22.4% | demonstrated deficit |
| high_major | player_rebounds | always under | 4,029 | 115 days | +1.7% | -2.2% to +5.6% | -4.6% to +8.0% | no demonstrated edge |
| high_major | player_rebounds | always the favourite | 4,107 | 431 games | -4.9% | -7.5% to -2.4% | -9.1% to -0.8% | demonstrated deficit |
| high_major | player_rebounds | always the underdog | 3,949 | 430 games | -5.9% | -9.9% to -1.8% | -12.4% to +0.6% | no demonstrated edge |
| high_major | player_rebounds_assists | always over | 1,083 | 44 days | -11.7% | -18.1% to -5.3% | -21.9% to -1.5% | demonstrated deficit |
| high_major | player_rebounds_assists | always under | 1,083 | 44 days | -2.7% | -8.9% to +3.5% | -12.7% to +7.2% | no demonstrated edge |
| high_major | player_rebounds_assists | always the favourite | 1,122 | 171 games | -5.3% | -10.7% to +0.1% | -14.0% to +3.4% | no demonstrated edge |
| high_major | player_rebounds_assists | always the underdog | 1,040 | 171 games | -9.1% | -15.8% to -2.5% | -19.8% to +1.5% | no demonstrated edge |
| high_major | player_steals | always over | 2,307 | 86 days | -20.9% | -27.1% to -14.7% | -30.9% to -10.9% | demonstrated deficit |
| high_major | player_steals | always under | 1,864 | 298 games | +2.0% | -2.4% to +6.5% | -5.1% to +9.2% | no demonstrated edge |
| high_major | player_steals | always the favourite | 1,890 | 298 games | -7.6% | -11.2% to -3.9% | -13.5% to -1.7% | demonstrated deficit |
| high_major | player_steals | always the underdog | 1,838 | 298 games | -5.3% | -10.7% to +0.1% | -14.0% to +3.4% | no demonstrated edge |
| high_major | player_threes | always over | 6,771 | 417 games | -28.3% | -34.8% to -21.9% | -38.7% to -18.0% | demonstrated deficit |
| high_major | player_threes | always under | 2,411 | 417 games | -1.3% | -5.8% to +3.1% | -8.5% to +5.8% | no demonstrated edge |
| high_major | player_threes | always the favourite | 2,422 | 417 games | -6.6% | -10.3% to -3.0% | -12.5% to -0.8% | demonstrated deficit |
| high_major | player_threes | always the underdog | 2,400 | 417 games | -4.0% | -9.1% to +1.1% | -12.2% to +4.2% | no demonstrated edge |
| high_major | player_turnovers | always over | 1,961 | 84 days | -11.2% | -15.8% to -6.7% | -18.5% to -3.9% | demonstrated deficit |
| high_major | player_turnovers | always under | 1,961 | 296 games | -4.2% | -8.6% to +0.3% | -11.3% to +2.9% | no demonstrated edge |
| high_major | player_turnovers | always the favourite | 2,014 | 84 days | -5.8% | -9.5% to -2.2% | -11.7% to +0.0% | no demonstrated edge |
| high_major | player_turnovers | always the underdog | 1,908 | 84 days | -9.7% | -14.9% to -4.5% | -18.0% to -1.3% | demonstrated deficit |
| high_major | spread | always home | 18,780 | 7,773 games | -2.8% | -5.0% to -0.6% | -6.4% to +0.7% | no demonstrated edge |
| high_major | spread | always away | 18,780 | 7,773 games | -4.0% | -6.3% to -1.8% | -7.6% to -0.4% | demonstrated deficit |
| high_major | spread | always the favourite | 587 | 184 games | -1.2% | -8.4% to +5.9% | -12.7% to +10.3% | no demonstrated edge |
| high_major | spread | always the underdog | 323 | 140 games | -9.9% | -23.4% to +3.5% | -31.5% to +11.6% | no demonstrated edge |
| high_major | spread_h1 | always home | 368 | 94 games | +0.8% | -20.0% to +21.5% | -32.6% to +34.1% | no demonstrated edge |
| high_major | spread_h1 | always away | 368 | 94 games | -10.6% | -31.6% to +10.4% | -44.3% to +23.1% | no demonstrated edge |
| high_major | spread_h1 | always the favourite | 46 | 12 games | — | — | — | not enough evidence (46 bets, below the 200 declared in advance) |
| high_major | spread_h1 | always the underdog | 42 | 10 games | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always home | 133 | 89 games | — | — | — | not enough evidence (133 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always away | 133 | 89 games | — | — | — | not enough evidence (133 bets, below the 200 declared in advance) |
| high_major | team_total | always over | 10,756 | 406 days | -2.9% | -5.7% to -0.1% | -7.4% to +1.6% | no demonstrated edge |
| high_major | team_total | always under | 10,757 | 406 days | -7.8% | -10.6% to -4.9% | -12.3% to -3.2% | demonstrated deficit |
| high_major | team_total | always the favourite | 11,627 | 3,585 games | -4.7% | -5.9% to -3.5% | -6.7% to -2.8% | demonstrated deficit |
| high_major | team_total | always the underdog | 8,901 | 3,522 games | -6.1% | -7.8% to -4.4% | -8.8% to -3.4% | demonstrated deficit |
| high_major | total_points | always over | 23,252 | 797 days | -2.7% | -5.0% to -0.4% | -6.3% to +1.0% | no demonstrated edge |
| high_major | total_points | always under | 23,252 | 797 days | -5.0% | -7.3% to -2.7% | -8.7% to -1.3% | demonstrated deficit |
| high_major | total_points | always the favourite | 32,227 | 7,773 games | -3.8% | -4.4% to -3.2% | -4.8% to -2.8% | demonstrated deficit |
| high_major | total_points | always the underdog | 14,277 | 7,270 games | -3.9% | -5.4% to -2.4% | -6.3% to -1.5% | demonstrated deficit |
| high_major | total_points_h1 | always over | 368 | 94 games | +1.7% | -19.0% to +22.4% | -31.6% to +35.0% | no demonstrated edge |
| high_major | total_points_h1 | always under | 368 | 94 games | -11.8% | -32.4% to +8.8% | -44.9% to +21.3% | no demonstrated edge |
| high_major | total_points_h1 | always the favourite | 448 | 61 days | -2.9% | -8.4% to +2.6% | -11.7% to +5.9% | no demonstrated edge |
| high_major | total_points_h1 | always the underdog | 288 | 60 days | -8.4% | -17.6% to +0.8% | -23.2% to +6.4% | no demonstrated edge |
| high_major | total_points_h2 | always over | 84 | 56 days | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always under | 84 | 56 days | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the favourite | 108 | 84 games | — | — | — | not enough evidence (108 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the underdog | 60 | 46 days | — | — | — | not enough evidence (60 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | always home | 18,066 | 107 days | -21.7% | -29.5% to -14.0% | -34.2% to -9.3% | demonstrated deficit |
| mid_major | alternate_spread | always away | 18,073 | 107 days | -5.3% | -13.1% to +2.5% | -17.8% to +7.2% | no demonstrated edge |
| mid_major | alternate_spread | always the favourite | 9,369 | 315 games | -12.6% | -19.2% to -5.9% | -23.2% to -1.9% | demonstrated deficit |
| mid_major | alternate_spread | always the underdog | 8,957 | 104 days | -14.0% | -25.5% to -2.5% | -32.4% to +4.5% | no demonstrated edge |
| mid_major | alternate_team_total | always over | 134 | 9 games | — | — | — | not enough evidence (134 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always under | 134 | 9 games | — | — | — | not enough evidence (134 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the favourite | 78 | 6 games | — | — | — | not enough evidence (78 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the underdog | 78 | 6 games | — | — | — | not enough evidence (78 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | always over | 25,981 | 107 days | -14.7% | -23.1% to -6.3% | -28.2% to -1.2% | demonstrated deficit |
| mid_major | alternate_total_points | always under | 25,981 | 107 days | -6.2% | -15.0% to +2.5% | -20.3% to +7.8% | no demonstrated edge |
| mid_major | alternate_total_points | always the favourite | 26,138 | 352 games | -2.9% | -5.1% to -0.7% | -6.5% to +0.7% | no demonstrated edge |
| mid_major | alternate_total_points | always the underdog | 25,824 | 352 games | -18.1% | -25.1% to -11.1% | -29.4% to -6.9% | demonstrated deficit |
| mid_major | moneyline | always home | 14,064 | 815 days | -0.0% | -1.8% to +1.8% | -2.9% to +2.9% | no demonstrated edge |
| mid_major | moneyline | always away | 14,064 | 815 days | -6.8% | -9.8% to -3.8% | -11.6% to -1.9% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 14,091 | 815 days | -2.0% | -3.1% to -0.9% | -3.8% to -0.3% | demonstrated deficit |
| mid_major | moneyline | always the underdog | 14,037 | 815 days | -4.8% | -8.2% to -1.4% | -10.2% to +0.7% | no demonstrated edge |
| mid_major | moneyline_h1 | always home | 345 | 345 games | -14.4% | -23.0% to -5.7% | -28.3% to -0.5% | demonstrated deficit |
| mid_major | moneyline_h1 | always away | 345 | 345 games | +20.7% | +3.2% to +38.2% | -7.3% to +48.8% | no demonstrated edge |
| mid_major | moneyline_h1 | always the favourite | 350 | 106 days | -6.4% | -14.6% to +1.8% | -19.5% to +6.7% | no demonstrated edge |
| mid_major | moneyline_h1 | always the underdog | 340 | 105 days | +13.1% | -5.9% to +32.0% | -17.3% to +43.4% | no demonstrated edge |
| mid_major | moneyline_h2 | always home | 198 | 198 games | — | — | — | not enough evidence (198 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always away | 198 | 198 games | — | — | — | not enough evidence (198 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always the favourite | 202 | 198 games | -7.8% | -17.4% to +1.8% | -23.3% to +7.7% | no demonstrated edge |
| mid_major | moneyline_h2 | always the underdog | 194 | 194 games | — | — | — | not enough evidence (194 bets, below the 200 declared in advance) |
| mid_major | player_assists | always over | 14,848 | 715 games | -19.5% | -23.9% to -15.1% | -26.6% to -12.4% | demonstrated deficit |
| mid_major | player_assists | always under | 5,025 | 715 games | -2.1% | -5.5% to +1.3% | -7.5% to +3.4% | no demonstrated edge |
| mid_major | player_assists | always the favourite | 5,070 | 715 games | -6.7% | -9.1% to -4.3% | -10.6% to -2.8% | demonstrated deficit |
| mid_major | player_assists | always the underdog | 4,976 | 714 games | -3.8% | -7.6% to -0.0% | -9.8% to +2.2% | no demonstrated edge |
| mid_major | player_first_basket | always over | 292 | 33 games | -27.2% | -39.3% to -15.2% | -46.6% to -7.9% | demonstrated deficit |
| mid_major | player_points | always over | 38,322 | 135 days | -19.5% | -23.2% to -15.7% | -25.5% to -13.5% | demonstrated deficit |
| mid_major | player_points | always under | 6,877 | 135 days | -7.4% | -11.7% to -3.1% | -14.3% to -0.6% | demonstrated deficit |
| mid_major | player_points | always the favourite | 7,258 | 135 days | -7.2% | -9.1% to -5.3% | -10.3% to -4.2% | demonstrated deficit |
| mid_major | player_points | always the underdog | 6,494 | 135 days | -1.3% | -5.1% to +2.6% | -7.4% to +4.9% | no demonstrated edge |
| mid_major | player_points_assists | always over | 2,187 | 356 games | -6.6% | -10.4% to -2.7% | -12.8% to -0.3% | demonstrated deficit |
| mid_major | player_points_assists | always under | 2,185 | 356 games | -7.3% | -11.2% to -3.5% | -13.5% to -1.1% | demonstrated deficit |
| mid_major | player_points_assists | always the favourite | 2,346 | 60 days | -7.0% | -11.4% to -2.6% | -14.1% to +0.1% | no demonstrated edge |
| mid_major | player_points_assists | always the underdog | 2,020 | 60 days | -6.8% | -12.3% to -1.3% | -15.6% to +2.0% | no demonstrated edge |
| mid_major | player_points_rebounds | always over | 2,578 | 356 games | -7.9% | -11.7% to -4.2% | -13.9% to -1.9% | demonstrated deficit |
| mid_major | player_points_rebounds | always under | 2,580 | 356 games | -6.0% | -9.8% to -2.3% | -12.0% to -0.0% | demonstrated deficit |
| mid_major | player_points_rebounds | always the favourite | 2,756 | 60 days | -6.0% | -9.8% to -2.2% | -12.0% to +0.0% | no demonstrated edge |
| mid_major | player_points_rebounds | always the underdog | 2,390 | 60 days | -8.2% | -12.8% to -3.5% | -15.6% to -0.7% | demonstrated deficit |
| mid_major | player_pra | always over | 10,924 | 671 games | -6.3% | -9.8% to -2.8% | -12.0% to -0.6% | demonstrated deficit |
| mid_major | player_pra | always under | 3,951 | 671 games | -5.7% | -8.8% to -2.7% | -10.6% to -0.9% | demonstrated deficit |
| mid_major | player_pra | always the favourite | 4,616 | 135 days | -9.0% | -11.4% to -6.6% | -12.8% to -5.2% | demonstrated deficit |
| mid_major | player_pra | always the underdog | 3,274 | 135 days | -3.0% | -6.5% to +0.6% | -8.6% to +2.7% | no demonstrated edge |
| mid_major | player_rebounds | always over | 25,003 | 723 games | -25.1% | -29.5% to -20.8% | -32.1% to -18.2% | demonstrated deficit |
| mid_major | player_rebounds | always under | 5,822 | 135 days | -0.9% | -4.0% to +2.3% | -5.9% to +4.2% | no demonstrated edge |
| mid_major | player_rebounds | always the favourite | 5,934 | 723 games | -5.3% | -7.4% to -3.2% | -8.7% to -2.0% | demonstrated deficit |
| mid_major | player_rebounds | always the underdog | 5,704 | 723 games | -7.1% | -10.1% to -4.1% | -11.9% to -2.2% | demonstrated deficit |
| mid_major | player_rebounds_assists | always over | 2,053 | 60 days | -8.3% | -12.9% to -3.8% | -15.6% to -1.1% | demonstrated deficit |
| mid_major | player_rebounds_assists | always under | 2,053 | 60 days | -5.7% | -10.1% to -1.3% | -12.7% to +1.3% | no demonstrated edge |
| mid_major | player_rebounds_assists | always the favourite | 2,123 | 356 games | -6.7% | -10.5% to -2.9% | -12.8% to -0.6% | demonstrated deficit |
| mid_major | player_rebounds_assists | always the underdog | 1,981 | 356 games | -7.3% | -11.9% to -2.7% | -14.7% to +0.1% | no demonstrated edge |
| mid_major | player_steals | always over | 3,476 | 534 games | -16.6% | -20.4% to -12.7% | -22.8% to -10.4% | demonstrated deficit |
| mid_major | player_steals | always under | 3,182 | 534 games | +0.7% | -2.7% to +4.0% | -4.8% to +6.1% | no demonstrated edge |
| mid_major | player_steals | always the favourite | 3,252 | 103 days | -6.8% | -9.6% to -4.0% | -11.3% to -2.3% | demonstrated deficit |
| mid_major | player_steals | always the underdog | 3,112 | 103 days | -7.0% | -11.2% to -2.8% | -13.7% to -0.3% | demonstrated deficit |
| mid_major | player_threes | always over | 11,042 | 705 games | -23.7% | -29.1% to -18.3% | -32.4% to -15.0% | demonstrated deficit |
| mid_major | player_threes | always under | 3,875 | 135 days | -5.5% | -8.9% to -2.0% | -11.0% to +0.1% | no demonstrated edge |
| mid_major | player_threes | always the favourite | 3,912 | 135 days | -4.6% | -7.7% to -1.6% | -9.5% to +0.2% | no demonstrated edge |
| mid_major | player_threes | always the underdog | 3,838 | 135 days | -7.8% | -12.0% to -3.5% | -14.6% to -0.9% | demonstrated deficit |
| mid_major | player_turnovers | always over | 3,253 | 566 games | -15.4% | -18.8% to -11.9% | -20.9% to -9.8% | demonstrated deficit |
| mid_major | player_turnovers | always under | 3,253 | 566 games | -0.1% | -3.4% to +3.3% | -5.5% to +5.4% | no demonstrated edge |
| mid_major | player_turnovers | always the favourite | 3,344 | 566 games | -5.5% | -8.2% to -2.8% | -9.8% to -1.2% | demonstrated deficit |
| mid_major | player_turnovers | always the underdog | 3,162 | 566 games | -10.0% | -13.8% to -6.3% | -16.0% to -4.0% | demonstrated deficit |
| mid_major | spread | always home | 34,384 | 815 days | -3.6% | -5.2% to -1.9% | -6.2% to -0.9% | demonstrated deficit |
| mid_major | spread | always away | 34,384 | 815 days | -3.2% | -4.9% to -1.6% | -5.9% to -0.5% | demonstrated deficit |
| mid_major | spread | always the favourite | 1,591 | 472 games | -5.1% | -9.0% to -1.2% | -11.4% to +1.1% | no demonstrated edge |
| mid_major | spread | always the underdog | 867 | 372 games | -2.1% | -9.5% to +5.3% | -13.9% to +9.8% | no demonstrated edge |
| mid_major | spread_h1 | always home | 1,362 | 345 games | -15.2% | -26.2% to -4.3% | -32.8% to +2.4% | no demonstrated edge |
| mid_major | spread_h1 | always away | 1,362 | 345 games | +6.0% | -5.1% to +17.1% | -11.8% to +23.8% | no demonstrated edge |
| mid_major | spread_h1 | always the favourite | 150 | 42 games | — | — | — | not enough evidence (150 bets, below the 200 declared in advance) |
| mid_major | spread_h1 | always the underdog | 128 | 39 games | — | — | — | not enough evidence (128 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always home | 588 | 334 games | -2.6% | -13.4% to +8.2% | -20.0% to +14.8% | no demonstrated edge |
| mid_major | spread_h2 | always away | 588 | 334 games | -10.8% | -21.6% to -0.0% | -28.1% to +6.5% | no demonstrated edge |
| mid_major | spread_h2 | always the favourite | 10 | 4 games | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always the underdog | 10 | 4 games | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| mid_major | team_total | always over | 22,392 | 7,669 games | -3.5% | -5.2% to -1.7% | -6.3% to -0.7% | demonstrated deficit |
| mid_major | team_total | always under | 22,392 | 417 days | -7.4% | -9.2% to -5.7% | -10.3% to -4.6% | demonstrated deficit |
| mid_major | team_total | always the favourite | 23,727 | 417 days | -3.9% | -4.8% to -3.0% | -5.4% to -2.5% | demonstrated deficit |
| mid_major | team_total | always the underdog | 18,373 | 415 days | -7.4% | -8.7% to -6.2% | -9.4% to -5.4% | demonstrated deficit |
| mid_major | total_points | always over | 43,265 | 815 days | -3.1% | -4.7% to -1.4% | -5.7% to -0.4% | demonstrated deficit |
| mid_major | total_points | always under | 43,265 | 815 days | -4.6% | -6.3% to -3.0% | -7.3% to -2.0% | demonstrated deficit |
| mid_major | total_points | always the favourite | 60,258 | 14,110 games | -3.8% | -4.3% to -3.3% | -4.5% to -3.1% | demonstrated deficit |
| mid_major | total_points | always the underdog | 26,272 | 13,256 games | -3.9% | -5.0% to -2.9% | -5.7% to -2.2% | demonstrated deficit |
| mid_major | total_points_h1 | always over | 1,337 | 106 days | -14.3% | -24.9% to -3.6% | -31.3% to +2.8% | no demonstrated edge |
| mid_major | total_points_h1 | always under | 1,337 | 106 days | +3.2% | -7.7% to +14.1% | -14.3% to +20.6% | no demonstrated edge |
| mid_major | total_points_h1 | always the favourite | 1,615 | 106 days | -4.9% | -7.8% to -2.0% | -9.6% to -0.2% | demonstrated deficit |
| mid_major | total_points_h1 | always the underdog | 1,059 | 104 days | -6.5% | -12.8% to -0.2% | -16.5% to +3.6% | no demonstrated edge |
| mid_major | total_points_h2 | always over | 388 | 331 games | -3.0% | -16.2% to +10.2% | -24.2% to +18.1% | no demonstrated edge |
| mid_major | total_points_h2 | always under | 388 | 331 games | -9.0% | -21.4% to +3.4% | -28.9% to +10.9% | no demonstrated edge |
| mid_major | total_points_h2 | always the favourite | 488 | 104 days | -9.7% | -16.3% to -3.0% | -20.4% to +1.0% | no demonstrated edge |
| mid_major | total_points_h2 | always the underdog | 288 | 95 days | +0.2% | -12.9% to +13.3% | -20.8% to +21.2% | no demonstrated edge |
| low_major | alternate_spread | always home | 6,637 | 163 games | -14.1% | -26.6% to -1.7% | -34.1% to +5.9% | no demonstrated edge |
| low_major | alternate_spread | always away | 6,637 | 163 games | +0.9% | -13.1% to +14.9% | -21.6% to +23.3% | no demonstrated edge |
| low_major | alternate_spread | always the favourite | 3,455 | 70 days | -6.7% | -19.9% to +6.6% | -27.8% to +14.5% | no demonstrated edge |
| low_major | alternate_spread | always the underdog | 3,341 | 70 days | +0.4% | -22.5% to +23.3% | -36.3% to +37.1% | no demonstrated edge |
| low_major | alternate_team_total | always over | 12 | 1 games | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always under | 12 | 1 games | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the favourite | 6 | 1 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the underdog | 6 | 1 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | always over | 9,791 | 75 days | -14.6% | -28.5% to -0.7% | -36.9% to +7.7% | no demonstrated edge |
| low_major | alternate_total_points | always under | 9,791 | 75 days | +3.0% | -12.0% to +18.0% | -21.1% to +27.0% | no demonstrated edge |
| low_major | alternate_total_points | always the favourite | 9,866 | 163 games | -7.5% | -10.9% to -4.1% | -12.9% to -2.0% | demonstrated deficit |
| low_major | alternate_total_points | always the underdog | 9,716 | 163 games | -4.1% | -14.0% to +5.8% | -20.0% to +11.8% | no demonstrated edge |
| low_major | moneyline | always home | 9,785 | 718 days | -1.4% | -3.5% to +0.8% | -4.8% to +2.0% | no demonstrated edge |
| low_major | moneyline | always away | 9,785 | 9,785 games | -4.6% | -7.6% to -1.6% | -9.5% to +0.2% | no demonstrated edge |
| low_major | moneyline | always the favourite | 9,820 | 9,785 games | -1.9% | -3.3% to -0.5% | -4.1% to +0.3% | no demonstrated edge |
| low_major | moneyline | always the underdog | 9,750 | 718 days | -4.1% | -7.6% to -0.6% | -9.7% to +1.5% | no demonstrated edge |
| low_major | moneyline_h1 | always home | 159 | 75 days | — | — | — | not enough evidence (159 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always away | 159 | 75 days | — | — | — | not enough evidence (159 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the favourite | 161 | 159 games | — | — | — | not enough evidence (161 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the underdog | 157 | 157 games | — | — | — | not enough evidence (157 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always home | 98 | 98 games | — | — | — | not enough evidence (98 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always away | 98 | 98 games | — | — | — | not enough evidence (98 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the favourite | 101 | 98 games | — | — | — | not enough evidence (101 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the underdog | 95 | 95 games | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | player_assists | always over | 299 | 19 games | +5.3% | -15.9% to +26.4% | -28.6% to +39.1% | no demonstrated edge |
| low_major | player_assists | always under | 110 | 19 games | — | — | — | not enough evidence (110 bets, below the 200 declared in advance) |
| low_major | player_assists | always the favourite | 111 | 19 games | — | — | — | not enough evidence (111 bets, below the 200 declared in advance) |
| low_major | player_assists | always the underdog | 109 | 19 games | — | — | — | not enough evidence (109 bets, below the 200 declared in advance) |
| low_major | player_first_basket | always over | 9 | 1 games | — | — | — | not enough evidence (9 bets, below the 200 declared in advance) |
| low_major | player_points | always over | 754 | 19 games | -5.4% | -33.2% to +22.4% | -50.0% to +39.2% | no demonstrated edge |
| low_major | player_points | always under | 141 | 19 games | — | — | — | not enough evidence (141 bets, below the 200 declared in advance) |
| low_major | player_points | always the favourite | 151 | 19 games | — | — | — | not enough evidence (151 bets, below the 200 declared in advance) |
| low_major | player_points | always the underdog | 131 | 19 games | — | — | — | not enough evidence (131 bets, below the 200 declared in advance) |
| low_major | player_points_assists | always over | 85 | 16 games | — | — | — | not enough evidence (85 bets, below the 200 declared in advance) |
| low_major | player_points_assists | always under | 85 | 16 games | — | — | — | not enough evidence (85 bets, below the 200 declared in advance) |
| low_major | player_points_assists | always the favourite | 92 | 16 games | — | — | — | not enough evidence (92 bets, below the 200 declared in advance) |
| low_major | player_points_assists | always the underdog | 78 | 16 games | — | — | — | not enough evidence (78 bets, below the 200 declared in advance) |
| low_major | player_points_rebounds | always over | 90 | 16 games | — | — | — | not enough evidence (90 bets, below the 200 declared in advance) |
| low_major | player_points_rebounds | always under | 90 | 16 games | — | — | — | not enough evidence (90 bets, below the 200 declared in advance) |
| low_major | player_points_rebounds | always the favourite | 97 | 16 games | — | — | — | not enough evidence (97 bets, below the 200 declared in advance) |
| low_major | player_points_rebounds | always the underdog | 83 | 16 games | — | — | — | not enough evidence (83 bets, below the 200 declared in advance) |
| low_major | player_pra | always over | 245 | 16 games | +0.2% | -14.1% to +14.5% | -22.8% to +23.1% | no demonstrated edge |
| low_major | player_pra | always under | 82 | 16 games | — | — | — | not enough evidence (82 bets, below the 200 declared in advance) |
| low_major | player_pra | always the favourite | 96 | 16 games | — | — | — | not enough evidence (96 bets, below the 200 declared in advance) |
| low_major | player_pra | always the underdog | 68 | 16 games | — | — | — | not enough evidence (68 bets, below the 200 declared in advance) |
| low_major | player_rebounds | always over | 507 | 18 games | -18.3% | -50.3% to +13.6% | -69.6% to +32.9% | no demonstrated edge |
| low_major | player_rebounds | always under | 137 | 9 days | — | — | — | not enough evidence (137 bets, below the 200 declared in advance) |
| low_major | player_rebounds | always the favourite | 140 | 9 days | — | — | — | not enough evidence (140 bets, below the 200 declared in advance) |
| low_major | player_rebounds | always the underdog | 134 | 18 games | — | — | — | not enough evidence (134 bets, below the 200 declared in advance) |
| low_major | player_rebounds_assists | always over | 80 | 9 days | — | — | — | not enough evidence (80 bets, below the 200 declared in advance) |
| low_major | player_rebounds_assists | always under | 80 | 9 days | — | — | — | not enough evidence (80 bets, below the 200 declared in advance) |
| low_major | player_rebounds_assists | always the favourite | 81 | 16 games | — | — | — | not enough evidence (81 bets, below the 200 declared in advance) |
| low_major | player_rebounds_assists | always the underdog | 79 | 16 games | — | — | — | not enough evidence (79 bets, below the 200 declared in advance) |
| low_major | player_steals | always over | 95 | 18 games | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | player_steals | always under | 95 | 9 days | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | player_steals | always the favourite | 99 | 9 days | — | — | — | not enough evidence (99 bets, below the 200 declared in advance) |
| low_major | player_steals | always the underdog | 91 | 9 days | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| low_major | player_threes | always over | 227 | 18 games | -40.0% | -57.0% to -23.1% | -67.2% to -12.9% | demonstrated deficit |
| low_major | player_threes | always under | 88 | 18 games | — | — | — | not enough evidence (88 bets, below the 200 declared in advance) |
| low_major | player_threes | always the favourite | 90 | 18 games | — | — | — | not enough evidence (90 bets, below the 200 declared in advance) |
| low_major | player_threes | always the underdog | 86 | 18 games | — | — | — | not enough evidence (86 bets, below the 200 declared in advance) |
| low_major | player_turnovers | always over | 95 | 9 days | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | player_turnovers | always under | 95 | 9 days | — | — | — | not enough evidence (95 bets, below the 200 declared in advance) |
| low_major | player_turnovers | always the favourite | 97 | 18 games | — | — | — | not enough evidence (97 bets, below the 200 declared in advance) |
| low_major | player_turnovers | always the underdog | 93 | 18 games | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| low_major | spread | always home | 23,392 | 718 days | -3.4% | -5.4% to -1.4% | -6.6% to -0.2% | demonstrated deficit |
| low_major | spread | always away | 23,392 | 718 days | -3.3% | -5.3% to -1.3% | -6.6% to -0.1% | demonstrated deficit |
| low_major | spread | always the favourite | 1,320 | 405 games | -7.5% | -11.8% to -3.2% | -14.4% to -0.6% | demonstrated deficit |
| low_major | spread | always the underdog | 720 | 318 games | +3.1% | -5.0% to +11.2% | -9.9% to +16.1% | no demonstrated edge |
| low_major | spread_h1 | always home | 654 | 75 days | -16.9% | -34.4% to +0.5% | -44.9% to +11.1% | no demonstrated edge |
| low_major | spread_h1 | always away | 654 | 75 days | +7.4% | -10.3% to +25.0% | -20.9% to +35.6% | no demonstrated edge |
| low_major | spread_h1 | always the favourite | 109 | 19 days | — | — | — | not enough evidence (109 bets, below the 200 declared in advance) |
| low_major | spread_h1 | always the underdog | 69 | 18 days | — | — | — | not enough evidence (69 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always home | 233 | 159 games | -10.8% | -26.2% to +4.7% | -35.5% to +14.0% | no demonstrated edge |
| low_major | spread_h2 | always away | 233 | 159 games | -1.6% | -16.6% to +13.4% | -25.7% to +22.5% | no demonstrated edge |
| low_major | spread_h2 | always the favourite | 8 | 4 games | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always the underdog | 8 | 4 games | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | team_total | always over | 15,715 | 367 days | -3.8% | -6.0% to -1.5% | -7.4% to -0.1% | demonstrated deficit |
| low_major | team_total | always under | 15,715 | 367 days | -7.3% | -9.6% to -5.0% | -11.0% to -3.7% | demonstrated deficit |
| low_major | team_total | always the favourite | 15,867 | 367 days | -4.8% | -5.9% to -3.8% | -6.5% to -3.2% | demonstrated deficit |
| low_major | team_total | always the underdog | 12,851 | 366 days | -6.4% | -7.7% to -5.0% | -8.6% to -4.2% | demonstrated deficit |
| low_major | total_points | always over | 29,157 | 718 days | -2.4% | -4.4% to -0.3% | -5.7% to +0.9% | no demonstrated edge |
| low_major | total_points | always under | 29,157 | 718 days | -5.3% | -7.4% to -3.2% | -8.6% to -2.0% | demonstrated deficit |
| low_major | total_points | always the favourite | 40,713 | 9,787 games | -3.8% | -4.4% to -3.3% | -4.7% to -3.0% | demonstrated deficit |
| low_major | total_points | always the underdog | 17,601 | 9,132 games | -3.8% | -5.1% to -2.5% | -5.9% to -1.7% | demonstrated deficit |
| low_major | total_points_h1 | always over | 652 | 75 days | -7.8% | -27.2% to +11.6% | -38.9% to +23.4% | no demonstrated edge |
| low_major | total_points_h1 | always under | 652 | 75 days | -2.5% | -21.8% to +16.8% | -33.5% to +28.5% | no demonstrated edge |
| low_major | total_points_h1 | always the favourite | 769 | 159 games | -2.7% | -6.7% to +1.4% | -9.2% to +3.8% | no demonstrated edge |
| low_major | total_points_h1 | always the underdog | 535 | 152 games | -8.7% | -15.1% to -2.3% | -19.0% to +1.6% | no demonstrated edge |
| low_major | total_points_h2 | always over | 129 | 123 games | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always under | 129 | 123 games | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the favourite | 167 | 62 days | — | — | — | not enough evidence (167 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the underdog | 91 | 51 days | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| unplaced | moneyline | always home | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 games | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 games | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 games | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 games | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 games | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 games | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. **6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are three different distributions, and this lab exists because the third is plausibly priced with less attention.

| Tier | Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|:---|---:|---:|---:|:---|:---|:---|
| high_major | alternate_spread | 2,551 | 70 games | -10.4% | -33.0% to +12.2% | -46.7% to +25.9% | no demonstrated edge |
| high_major | alternate_total_points | 2,114 | 64 games | -1.1% | -31.0% to +28.7% | -49.0% to +46.7% | no demonstrated edge |
| high_major | moneyline | 5,510 | 712 days | -3.5% | -9.3% to +2.4% | -12.9% to +6.0% | no demonstrated edge |
| high_major | moneyline_h1 | 54 | 44 days | — | — | — | not enough evidence (54 bets, below the 200 declared in advance) |
| high_major | spread | 13,242 | 712 days | -1.7% | -4.4% to +0.9% | -5.9% to +2.5% | no demonstrated edge |
| high_major | spread_h1 | 223 | 72 games | -24.7% | -47.9% to -1.5% | -62.0% to +12.6% | no demonstrated edge |
| high_major | team_total | 7,109 | 2,933 games | -2.8% | -5.5% to -0.2% | -7.1% to +1.4% | no demonstrated edge |
| high_major | total_points | 12,241 | 688 days | -3.3% | -6.4% to -0.3% | -8.2% to +1.5% | no demonstrated edge |
| high_major | total_points_h1 | 184 | 57 games | — | — | — | not enough evidence (184 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | 9,319 | 93 days | -3.4% | -13.9% to +7.1% | -20.3% to +13.5% | no demonstrated edge |
| mid_major | alternate_team_total | 91 | 6 days | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | 7,467 | 230 games | -17.0% | -29.7% to -4.2% | -37.4% to +3.5% | no demonstrated edge |
| mid_major | moneyline | 10,194 | 736 days | -4.5% | -7.9% to -1.1% | -10.0% to +1.0% | no demonstrated edge |
| mid_major | moneyline_h1 | 184 | 79 days | — | — | — | not enough evidence (184 bets, below the 200 declared in advance) |
| mid_major | spread | 22,891 | 732 days | -1.5% | -3.6% to +0.6% | -4.9% to +1.9% | no demonstrated edge |
| mid_major | spread_h1 | 799 | 238 games | -7.4% | -21.2% to +6.5% | -29.6% to +14.8% | no demonstrated edge |
| mid_major | team_total | 13,478 | 384 days | -5.8% | -7.9% to -3.8% | -9.1% to -2.6% | demonstrated deficit |
| mid_major | total_points | 23,327 | 728 days | -2.3% | -4.5% to -0.2% | -5.9% to +1.2% | no demonstrated edge |
| mid_major | total_points_h1 | 594 | 202 games | -2.4% | -17.4% to +12.6% | -26.5% to +21.7% | no demonstrated edge |
| low_major | alternate_spread | 3,510 | 127 games | -2.1% | -19.2% to +15.0% | -29.5% to +25.4% | no demonstrated edge |
| low_major | alternate_team_total | 11 | 1 games | — | — | — | not enough evidence (11 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | 3,785 | 121 games | -10.5% | -30.3% to +9.4% | -42.3% to +21.3% | no demonstrated edge |
| low_major | moneyline | 7,561 | 632 days | -7.9% | -11.8% to -4.1% | -14.2% to -1.7% | demonstrated deficit |
| low_major | moneyline_h1 | 82 | 82 games | — | — | — | not enough evidence (82 bets, below the 200 declared in advance) |
| low_major | spread | 16,090 | 634 days | -0.1% | -2.4% to +2.3% | -3.8% to +3.7% | no demonstrated edge |
| low_major | spread_h1 | 405 | 121 games | +5.0% | -14.9% to +25.0% | -26.9% to +37.0% | no demonstrated edge |
| low_major | team_total | 9,802 | 334 days | -4.1% | -6.7% to -1.5% | -8.3% to +0.1% | no demonstrated edge |
| low_major | total_points | 17,903 | 7,131 games | -5.2% | -7.5% to -2.8% | -9.0% to -1.3% | demonstrated deficit |
| low_major | total_points_h1 | 326 | 106 games | -11.4% | -32.3% to +9.5% | -44.9% to +22.2% | no demonstrated edge |
| unplaced | moneyline | 1 | 1 games | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 games | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 games | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 43,228 | 6,203 games | -3.2% | -6.0% to -0.5% | -7.6% to +1.2% | no demonstrated edge |
| mid_major | 88,344 | 740 days | -4.3% | -6.5% to -2.1% | -7.8% to -0.8% | demonstrated deficit |
| low_major | 59,475 | 8,870 games | -4.0% | -6.3% to -1.7% | -7.7% to -0.3% | demonstrated deficit |
| unplaced | 6 | 2 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| alternate_spread | 15,380 | 464 games | -4.3% | -12.3% to +3.8% | -17.1% to +8.6% | no demonstrated edge |
| alternate_team_total | 102 | 10 games | — | — | — | not enough evidence (102 bets, below the 200 declared in advance) |
| alternate_total_points | 13,366 | 415 games | -12.6% | -22.9% to -2.4% | -29.1% to +3.8% | no demonstrated edge |
| moneyline | 23,266 | 789 days | -5.4% | -7.9% to -2.8% | -9.5% to -1.3% | demonstrated deficit |
| moneyline_h1 | 320 | 320 games | +7.6% | -10.9% to +26.1% | -22.1% to +37.3% | no demonstrated edge |
| spread | 52,226 | 789 days | -1.1% | -2.4% to +0.2% | -3.2% to +1.0% | no demonstrated edge |
| spread_h1 | 1,427 | 431 games | -6.6% | -16.9% to +3.8% | -23.1% to +10.0% | no demonstrated edge |
| team_total | 30,389 | 412 days | -4.6% | -6.0% to -3.1% | -6.9% to -2.2% | demonstrated deficit |
| total_points | 53,473 | 21,076 games | -3.5% | -4.9% to -2.1% | -5.7% to -1.3% | demonstrated deficit |
| total_points_h1 | 1,104 | 365 games | -5.5% | -16.7% to +5.6% | -23.4% to +12.4% | no demonstrated edge |
| every market | 191,053 | 26,591 games | -4.0% | -5.3% to -2.6% | -6.2% to -1.8% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 31,674 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **5** (6.1%), **4** (6.0%), **2** (5.8%), **8** (5.3%), **7** (5.2%), **6** (5.2%), **9** (4.9%), **10** (4.7%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 85.7% of 189,381 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 12,664 | 10.0% [9.5%, 10.5%] | +3.9 pp | 765 | 2.1% [1.3%, 3.4%] | -5.1 pp |
| 10%–20% | 19,260 | 22.4% [21.8%, 23.0%] | +7.0 pp | 3,175 | 7.7% [6.8%, 8.7%] | -7.8 pp |
| 20%–30% | 33,088 | 35.1% [34.5%, 35.6%] | +9.6 pp | 4,927 | 15.1% [14.1%, 16.1%] | -10.3 pp |
| 30%–40% | 73,156 | 45.3% [45.0%, 45.7%] | +9.6 pp | 7,087 | 24.5% [23.5%, 25.5%] | -10.6 pp |
| 40%–50% | 153,931 | 49.6% [49.3%, 49.8%] | +4.2 pp | 7,932 | 34.6% [33.6%, 35.7%] | -10.5 pp |
| 50%–60% | 146,550 | 50.6% [50.4%, 50.9%] | -3.9 pp | 84,809 | 49.3% [48.9%, 49.6%] | -6.8 pp |
| 60%–70% | 66,570 | 55.3% [54.9%, 55.7%] | -9.0 pp | 52,721 | 51.4% [50.9%, 51.8%] | -12.7 pp |
| 70%–80% | 30,613 | 65.7% [65.2%, 66.2%] | -8.8 pp | 17,538 | 56.4% [55.6%, 57.1%] | -17.9 pp |
| 80%–90% | 18,063 | 78.4% [77.8%, 79.0%] | -6.3 pp | 7,324 | 66.5% [65.4%, 67.6%] | -17.8 pp |
| 90%–100% | 12,475 | 90.4% [89.9%, 90.9%] | -3.5 pp | 3,103 | 80.9% [79.5%, 82.3%] | -13.3 pp |

- **Overall: 0.4 pp underconfident** over 566,370 graded rows in 10 usable bucket(s).
- **Selected: 10.4 pp overconfident** over 189,381 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 1,672 push, 29 unsettleable. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
