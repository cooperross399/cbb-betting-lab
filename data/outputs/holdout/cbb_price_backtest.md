# NCAA Division I men's basketball — price backtest

Generated 2026-09-17T09:40:00Z.

**Walk-forward only.** Every model that priced a game was built from games strictly earlier than it, and every bet carries the day it was priced through. The stamp is checked rather than the code path: the football lab's compound markets looked good because a distribution loaded once outside the season loop had seen the future.

**One wager is one bet, at the best price.** Twenty-one books quoting one game is not twenty-one bets — counting it that way narrowed the NHL lab's intervals by about √2.83 and turned three markets that span zero into three demonstrated losses.

**110,839 graded bets** from 411,034 graded wagers offered, seasons 2021-2024, across 16,815 games and 513 slate days, at an edge threshold of 2% declared in advance.

**Family correction: 130 cumulative hypotheses** in the experiment ledger, widening every 95% interval by x1.81. That is the ledger's cumulative count and never the day's — correcting today's findings across today's tests is a lie if more were tested last week.

**Below 200 bets there is no number**, only the words *not enough evidence*. That floor was declared before any price was bought.

## The null baseline, first

*The question that broke the football lab's best result was never "is this robust". It was: what would betting one side with no model at all return?* So it is answered here, before any model number appears, and every model result below is read against it.

| Tier | Market | Blind side | Bets | Clusters | ROI | 95% interval | Family-corrected | Could detect | Verdict |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|:---|
| high_major | alternate_spread | always home | 3,825 | 51 days | -8.9% | -30.8% to +13.0% | -48.6% to +30.7% | ±39.6% | no demonstrated edge |
| high_major | alternate_spread | always away | 3,824 | 51 days | -8.9% | -26.7% to +8.9% | -41.1% to +23.4% | ±32.3% | no demonstrated edge |
| high_major | alternate_spread | always the favourite | 1,626 | 57 games | -14.8% | -32.4% to +2.8% | -46.7% to +17.1% | ±31.9% | no demonstrated edge |
| high_major | alternate_spread | always the underdog | 1,592 | 56 games | -3.4% | -33.3% to +26.6% | -57.6% to +50.9% | ±54.2% | no demonstrated edge |
| high_major | alternate_total_points | always over | 6,618 | 94 games | +20.5% | +0.3% to +40.7% | -16.0% to +57.1% | ±36.6% | no demonstrated edge |
| high_major | alternate_total_points | always under | 6,618 | 94 games | -25.3% | -41.4% to -9.1% | -54.5% to +4.0% | ±29.3% | no demonstrated edge |
| high_major | alternate_total_points | always the favourite | 6,645 | 94 games | -11.0% | -14.9% to -7.1% | -18.1% to -3.9% | ±7.1% | demonstrated deficit |
| high_major | alternate_total_points | always the underdog | 6,591 | 94 games | +6.3% | -8.1% to +20.7% | -19.8% to +32.4% | ±26.1% | no demonstrated edge |
| high_major | moneyline | always home | 3,950 | 448 days | +1.9% | -1.0% to +4.8% | -3.4% to +7.2% | ±5.3% | no demonstrated edge |
| high_major | moneyline | always away | 3,950 | 3,950 games | -16.7% | -23.9% to -9.5% | -29.8% to -3.6% | ±13.1% | demonstrated deficit |
| high_major | moneyline | always the favourite | 3,953 | 3,950 games | +0.2% | -1.6% to +2.1% | -3.2% to +3.6% | ±3.4% | no demonstrated edge |
| high_major | moneyline | always the underdog | 3,947 | 3,947 games | -15.0% | -22.6% to -7.5% | -28.7% to -1.4% | ±13.6% | demonstrated deficit |
| high_major | moneyline_h1 | always home | 76 | 76 games | — | — | — | — | not enough evidence (76 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always away | 76 | 76 games | — | — | — | — | not enough evidence (76 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the favourite | 76 | 76 games | — | — | — | — | not enough evidence (76 bets, below the 200 declared in advance) |
| high_major | moneyline_h1 | always the underdog | 76 | 76 games | — | — | — | — | not enough evidence (76 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always home | 42 | 33 days | — | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always away | 42 | 42 games | — | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the favourite | 42 | 42 games | — | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | moneyline_h2 | always the underdog | 42 | 42 games | — | — | — | — | not enough evidence (42 bets, below the 200 declared in advance) |
| high_major | spread | always home | 9,047 | 3,971 games | -2.3% | -5.4% to +0.8% | -7.9% to +3.3% | ±5.6% | no demonstrated edge |
| high_major | spread | always away | 9,047 | 3,971 games | -4.7% | -7.8% to -1.6% | -10.3% to +1.0% | ±5.6% | no demonstrated edge |
| high_major | spread | always the favourite | 225 | 69 days | -7.5% | -18.6% to +3.7% | -27.6% to +12.7% | ±20.2% | no demonstrated edge |
| high_major | spread | always the underdog | 109 | 47 days | — | — | — | — | not enough evidence (109 bets, below the 200 declared in advance) |
| high_major | spread_h1 | always home | 306 | 77 games | +0.8% | -22.0% to +23.5% | -40.5% to +42.0% | ±41.3% | no demonstrated edge |
| high_major | spread_h1 | always away | 306 | 77 games | -10.4% | -33.5% to +12.6% | -52.2% to +31.4% | ±41.8% | no demonstrated edge |
| high_major | spread_h1 | always the favourite | 29 | 7 games | — | — | — | — | not enough evidence (29 bets, below the 200 declared in advance) |
| high_major | spread_h1 | always the underdog | 25 | 5 games | — | — | — | — | not enough evidence (25 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always home | 110 | 72 games | — | — | — | — | not enough evidence (110 bets, below the 200 declared in advance) |
| high_major | spread_h2 | always away | 110 | 72 games | — | — | — | — | not enough evidence (110 bets, below the 200 declared in advance) |
| high_major | team_total | always over | 1,616 | 610 games | +2.3% | -4.1% to +8.7% | -9.3% to +13.9% | ±11.6% | no demonstrated edge |
| high_major | team_total | always under | 1,616 | 610 games | -13.1% | -19.6% to -6.5% | -25.0% to -1.2% | ±11.9% | demonstrated deficit |
| high_major | team_total | always the favourite | 1,862 | 599 games | -7.5% | -10.5% to -4.5% | -13.0% to -2.1% | ±5.4% | demonstrated deficit |
| high_major | team_total | always the underdog | 1,246 | 571 games | -2.2% | -7.1% to +2.7% | -11.1% to +6.6% | ±8.8% | no demonstrated edge |
| high_major | total_points | always over | 14,394 | 513 days | -2.1% | -4.9% to +0.7% | -7.2% to +3.0% | ±5.1% | no demonstrated edge |
| high_major | total_points | always under | 14,394 | 513 days | -5.7% | -8.5% to -2.8% | -10.8% to -0.5% | ±5.1% | demonstrated deficit |
| high_major | total_points | always the favourite | 20,449 | 4,891 games | -4.1% | -4.9% to -3.3% | -5.5% to -2.6% | ±1.4% | demonstrated deficit |
| high_major | total_points | always the underdog | 8,339 | 4,532 games | -3.5% | -5.5% to -1.5% | -7.1% to +0.2% | ±3.7% | no demonstrated edge |
| high_major | total_points_h1 | always over | 368 | 94 games | +1.7% | -19.0% to +22.4% | -35.9% to +39.3% | ±37.6% | no demonstrated edge |
| high_major | total_points_h1 | always under | 368 | 94 games | -11.8% | -32.4% to +8.8% | -49.2% to +25.5% | ±37.4% | no demonstrated edge |
| high_major | total_points_h1 | always the favourite | 448 | 61 days | -2.9% | -8.4% to +2.6% | -12.9% to +7.0% | ±10.0% | no demonstrated edge |
| high_major | total_points_h1 | always the underdog | 288 | 60 days | -8.4% | -17.6% to +0.8% | -25.1% to +8.3% | ±16.7% | no demonstrated edge |
| high_major | total_points_h2 | always over | 84 | 56 days | — | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always under | 84 | 56 days | — | — | — | — | not enough evidence (84 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the favourite | 108 | 84 games | — | — | — | — | not enough evidence (108 bets, below the 200 declared in advance) |
| high_major | total_points_h2 | always the underdog | 60 | 46 days | — | — | — | — | not enough evidence (60 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | always home | 15,628 | 101 days | -20.8% | -28.9% to -12.6% | -35.6% to -6.0% | ±14.8% | demonstrated deficit |
| mid_major | alternate_spread | always away | 15,635 | 306 games | -6.8% | -15.0% to +1.4% | -21.6% to +8.1% | ±14.9% | no demonstrated edge |
| mid_major | alternate_spread | always the favourite | 7,854 | 271 games | -10.6% | -17.7% to -3.4% | -23.5% to +2.4% | ±12.9% | no demonstrated edge |
| mid_major | alternate_spread | always the underdog | 7,468 | 98 days | -18.8% | -30.2% to -7.5% | -39.5% to +1.8% | ±20.6% | no demonstrated edge |
| mid_major | alternate_team_total | always over | 36 | 3 games | — | — | — | — | not enough evidence (36 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always under | 36 | 3 games | — | — | — | — | not enough evidence (36 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the favourite | 24 | 2 games | — | — | — | — | not enough evidence (24 bets, below the 200 declared in advance) |
| mid_major | alternate_team_total | always the underdog | 24 | 2 games | — | — | — | — | not enough evidence (24 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | always over | 25,981 | 107 days | -14.7% | -23.1% to -6.3% | -29.9% to +0.5% | ±15.2% | no demonstrated edge |
| mid_major | alternate_total_points | always under | 25,981 | 107 days | -6.2% | -15.0% to +2.5% | -22.1% to +9.6% | ±15.8% | no demonstrated edge |
| mid_major | alternate_total_points | always the favourite | 26,138 | 352 games | -2.9% | -5.1% to -0.7% | -7.0% to +1.1% | ±4.0% | no demonstrated edge |
| mid_major | alternate_total_points | always the underdog | 25,824 | 352 games | -18.1% | -25.1% to -11.1% | -30.8% to -5.4% | ±12.7% | demonstrated deficit |
| mid_major | moneyline | always home | 8,113 | 478 days | +0.1% | -2.1% to +2.4% | -4.0% to +4.3% | ±4.1% | no demonstrated edge |
| mid_major | moneyline | always away | 8,113 | 478 days | -9.8% | -13.7% to -5.9% | -16.9% to -2.7% | ±7.1% | demonstrated deficit |
| mid_major | moneyline | always the favourite | 8,130 | 478 days | -0.5% | -1.9% to +0.9% | -3.0% to +2.1% | ±2.5% | no demonstrated edge |
| mid_major | moneyline | always the underdog | 8,096 | 478 days | -9.2% | -13.6% to -4.9% | -17.1% to -1.3% | ±7.9% | demonstrated deficit |
| mid_major | moneyline_h1 | always home | 304 | 304 games | -12.9% | -22.0% to -3.9% | -29.4% to +3.5% | ±16.4% | no demonstrated edge |
| mid_major | moneyline_h1 | always away | 304 | 304 games | +18.4% | -0.5% to +37.4% | -15.9% to +52.8% | ±34.4% | no demonstrated edge |
| mid_major | moneyline_h1 | always the favourite | 309 | 100 days | -6.4% | -14.9% to +2.1% | -21.8% to +9.0% | ±15.4% | no demonstrated edge |
| mid_major | moneyline_h1 | always the underdog | 299 | 99 days | +12.2% | -7.7% to +32.2% | -23.9% to +48.4% | ±36.2% | no demonstrated edge |
| mid_major | moneyline_h2 | always home | 185 | 185 games | — | — | — | — | not enough evidence (185 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always away | 185 | 185 games | — | — | — | — | not enough evidence (185 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always the favourite | 189 | 185 games | — | — | — | — | not enough evidence (189 bets, below the 200 declared in advance) |
| mid_major | moneyline_h2 | always the underdog | 181 | 181 games | — | — | — | — | not enough evidence (181 bets, below the 200 declared in advance) |
| mid_major | spread | always home | 19,239 | 478 days | -1.9% | -4.2% to +0.4% | -6.0% to +2.2% | ±4.1% | no demonstrated edge |
| mid_major | spread | always away | 19,239 | 478 days | -4.9% | -7.2% to -2.7% | -9.1% to -0.8% | ±4.1% | demonstrated deficit |
| mid_major | spread | always the favourite | 698 | 151 days | -8.4% | -14.0% to -2.9% | -18.5% to +1.6% | ±10.1% | no demonstrated edge |
| mid_major | spread | always the underdog | 332 | 121 days | +4.2% | -7.8% to +16.2% | -17.5% to +25.9% | ±21.7% | no demonstrated edge |
| mid_major | spread_h1 | always home | 1,157 | 304 games | -15.4% | -27.0% to -3.8% | -36.5% to +5.6% | ±21.0% | no demonstrated edge |
| mid_major | spread_h1 | always away | 1,157 | 304 games | +6.1% | -5.6% to +17.7% | -15.1% to +27.2% | ±21.1% | no demonstrated edge |
| mid_major | spread_h1 | always the favourite | 120 | 35 games | — | — | — | — | not enough evidence (120 bets, below the 200 declared in advance) |
| mid_major | spread_h1 | always the underdog | 100 | 32 games | — | — | — | — | not enough evidence (100 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always home | 488 | 98 days | +2.6% | -9.4% to +14.7% | -19.2% to +24.5% | ±21.8% | no demonstrated edge |
| mid_major | spread_h2 | always away | 488 | 98 days | -14.0% | -25.3% to -2.6% | -34.6% to +6.7% | ±20.6% | no demonstrated edge |
| mid_major | spread_h2 | always the favourite | 4 | 2 games | — | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |
| mid_major | spread_h2 | always the underdog | 4 | 2 games | — | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |
| mid_major | team_total | always over | 6,528 | 2,522 games | -2.3% | -5.4% to +0.7% | -7.8% to +3.2% | ±5.5% | no demonstrated edge |
| mid_major | team_total | always under | 6,528 | 2,522 games | -8.7% | -11.9% to -5.6% | -14.4% to -3.1% | ±5.6% | demonstrated deficit |
| mid_major | team_total | always the favourite | 7,459 | 124 days | -4.6% | -6.4% to -2.8% | -7.8% to -1.4% | ±3.2% | demonstrated deficit |
| mid_major | team_total | always the underdog | 5,025 | 124 days | -7.0% | -9.9% to -4.1% | -12.2% to -1.8% | ±5.2% | demonstrated deficit |
| mid_major | total_points | always over | 28,738 | 536 days | -2.5% | -4.5% to -0.4% | -6.2% to +1.2% | ±3.7% | no demonstrated edge |
| mid_major | total_points | always under | 28,738 | 536 days | -5.3% | -7.4% to -3.2% | -9.0% to -1.6% | ±3.7% | demonstrated deficit |
| mid_major | total_points | always the favourite | 40,829 | 9,313 games | -3.9% | -4.4% to -3.3% | -4.9% to -2.9% | ±1.0% | demonstrated deficit |
| mid_major | total_points | always the underdog | 16,647 | 8,655 games | -4.0% | -5.3% to -2.6% | -6.5% to -1.4% | ±2.5% | demonstrated deficit |
| mid_major | total_points_h1 | always over | 1,337 | 106 days | -14.3% | -24.9% to -3.6% | -33.5% to +5.0% | ±19.3% | no demonstrated edge |
| mid_major | total_points_h1 | always under | 1,337 | 106 days | +3.2% | -7.7% to +14.1% | -16.6% to +22.9% | ±19.7% | no demonstrated edge |
| mid_major | total_points_h1 | always the favourite | 1,615 | 106 days | -4.9% | -7.8% to -2.0% | -10.2% to +0.4% | ±5.3% | no demonstrated edge |
| mid_major | total_points_h1 | always the underdog | 1,059 | 104 days | -6.5% | -12.8% to -0.2% | -17.8% to +4.9% | ±11.3% | no demonstrated edge |
| mid_major | total_points_h2 | always over | 388 | 331 games | -3.0% | -16.2% to +10.2% | -26.9% to +20.9% | ±23.9% | no demonstrated edge |
| mid_major | total_points_h2 | always under | 388 | 331 games | -9.0% | -21.4% to +3.4% | -31.5% to +13.5% | ±22.5% | no demonstrated edge |
| mid_major | total_points_h2 | always the favourite | 488 | 104 days | -9.7% | -16.3% to -3.0% | -21.8% to +2.4% | ±12.1% | no demonstrated edge |
| mid_major | total_points_h2 | always the underdog | 288 | 95 days | +0.2% | -12.9% to +13.3% | -23.5% to +23.9% | ±23.7% | no demonstrated edge |
| low_major | alternate_spread | always home | 6,182 | 151 games | -13.3% | -26.1% to -0.4% | -36.6% to +10.1% | ±23.3% | no demonstrated edge |
| low_major | alternate_spread | always away | 6,182 | 151 games | -1.3% | -15.5% to +12.9% | -27.1% to +24.5% | ±25.8% | no demonstrated edge |
| low_major | alternate_spread | always the favourite | 3,176 | 61 days | -5.9% | -19.3% to +7.5% | -30.2% to +18.4% | ±24.3% | no demonstrated edge |
| low_major | alternate_spread | always the underdog | 3,084 | 61 days | -3.3% | -25.8% to +19.3% | -44.2% to +37.6% | ±40.9% | no demonstrated edge |
| low_major | alternate_team_total | always over | 12 | 1 games | — | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always under | 12 | 1 games | — | — | — | — | not enough evidence (12 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the favourite | 6 | 1 games | — | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_team_total | always the underdog | 6 | 1 games | — | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | always over | 9,791 | 75 days | -14.6% | -28.5% to -0.7% | -39.7% to +10.6% | ±25.2% | no demonstrated edge |
| low_major | alternate_total_points | always under | 9,791 | 75 days | +3.0% | -12.0% to +18.0% | -24.2% to +30.1% | ±27.2% | no demonstrated edge |
| low_major | alternate_total_points | always the favourite | 9,866 | 163 games | -7.5% | -10.9% to -4.1% | -13.6% to -1.3% | ±6.2% | demonstrated deficit |
| low_major | alternate_total_points | always the underdog | 9,716 | 163 games | -4.1% | -14.0% to +5.8% | -22.0% to +13.8% | ±17.9% | no demonstrated edge |
| low_major | moneyline | always home | 5,471 | 439 days | -2.8% | -5.8% to +0.1% | -8.1% to +2.5% | ±5.3% | no demonstrated edge |
| low_major | moneyline | always away | 5,471 | 5,471 games | -6.0% | -9.8% to -2.2% | -12.8% to +0.8% | ±6.8% | no demonstrated edge |
| low_major | moneyline | always the favourite | 5,493 | 5,471 games | -1.1% | -2.9% to +0.7% | -4.3% to +2.2% | ±3.3% | no demonstrated edge |
| low_major | moneyline | always the underdog | 5,449 | 439 days | -7.8% | -12.1% to -3.4% | -15.7% to +0.1% | ±7.9% | no demonstrated edge |
| low_major | moneyline_h1 | always home | 147 | 147 games | — | — | — | — | not enough evidence (147 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always away | 147 | 68 days | — | — | — | — | not enough evidence (147 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the favourite | 149 | 147 games | — | — | — | — | not enough evidence (149 bets, below the 200 declared in advance) |
| low_major | moneyline_h1 | always the underdog | 145 | 145 games | — | — | — | — | not enough evidence (145 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always home | 96 | 96 games | — | — | — | — | not enough evidence (96 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always away | 96 | 96 games | — | — | — | — | not enough evidence (96 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the favourite | 99 | 96 games | — | — | — | — | not enough evidence (99 bets, below the 200 declared in advance) |
| low_major | moneyline_h2 | always the underdog | 93 | 93 games | — | — | — | — | not enough evidence (93 bets, below the 200 declared in advance) |
| low_major | spread | always home | 12,711 | 439 days | -4.5% | -7.3% to -1.8% | -9.5% to +0.4% | ±5.0% | no demonstrated edge |
| low_major | spread | always away | 12,711 | 439 days | -2.3% | -5.1% to +0.4% | -7.3% to +2.7% | ±5.0% | no demonstrated edge |
| low_major | spread | always the favourite | 637 | 208 games | -5.4% | -11.2% to +0.5% | -16.0% to +5.3% | ±10.6% | no demonstrated edge |
| low_major | spread | always the underdog | 293 | 152 games | -0.3% | -13.4% to +12.8% | -24.0% to +23.5% | ±23.8% | no demonstrated edge |
| low_major | spread_h1 | always home | 593 | 68 days | -19.3% | -37.1% to -1.5% | -51.6% to +12.9% | ±32.3% | no demonstrated edge |
| low_major | spread_h1 | always away | 593 | 68 days | +9.9% | -8.1% to +27.8% | -22.6% to +42.4% | ±32.5% | no demonstrated edge |
| low_major | spread_h1 | always the favourite | 101 | 17 days | — | — | — | — | not enough evidence (101 bets, below the 200 declared in advance) |
| low_major | spread_h1 | always the underdog | 61 | 16 days | — | — | — | — | not enough evidence (61 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always home | 218 | 147 games | -11.5% | -27.5% to +4.5% | -40.5% to +17.5% | ±29.0% | no demonstrated edge |
| low_major | spread_h2 | always away | 218 | 147 games | -0.9% | -16.5% to +14.6% | -29.1% to +27.2% | ±28.2% | no demonstrated edge |
| low_major | spread_h2 | always the favourite | 8 | 4 games | — | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | spread_h2 | always the underdog | 8 | 4 games | — | — | — | — | not enough evidence (8 bets, below the 200 declared in advance) |
| low_major | team_total | always over | 2,995 | 1,278 games | -4.2% | -8.3% to +0.0% | -11.7% to +3.4% | ±7.6% | no demonstrated edge |
| low_major | team_total | always under | 2,995 | 1,278 games | -6.8% | -11.0% to -2.6% | -14.4% to +0.8% | ±7.6% | no demonstrated edge |
| low_major | team_total | always the favourite | 3,469 | 109 days | -6.7% | -9.0% to -4.3% | -11.0% to -2.3% | ±4.3% | demonstrated deficit |
| low_major | team_total | always the underdog | 2,281 | 108 days | -3.7% | -7.5% to +0.0% | -10.6% to +3.1% | ±6.9% | no demonstrated edge |
| low_major | total_points | always over | 17,945 | 466 days | -2.1% | -4.7% to +0.6% | -6.9% to +2.8% | ±4.9% | no demonstrated edge |
| low_major | total_points | always under | 17,945 | 466 days | -5.7% | -8.4% to -3.0% | -10.6% to -0.8% | ±4.9% | demonstrated deficit |
| low_major | total_points | always the favourite | 25,574 | 5,989 games | -4.1% | -4.8% to -3.4% | -5.4% to -2.8% | ±1.3% | demonstrated deficit |
| low_major | total_points | always the underdog | 10,316 | 5,545 games | -3.3% | -5.1% to -1.6% | -6.6% to -0.1% | ±3.2% | demonstrated deficit |
| low_major | total_points_h1 | always over | 652 | 75 days | -7.8% | -27.2% to +11.6% | -42.9% to +27.4% | ±35.2% | no demonstrated edge |
| low_major | total_points_h1 | always under | 652 | 75 days | -2.5% | -21.8% to +16.8% | -37.5% to +32.5% | ±35.0% | no demonstrated edge |
| low_major | total_points_h1 | always the favourite | 769 | 159 games | -2.7% | -6.7% to +1.4% | -10.0% to +4.7% | ±7.4% | no demonstrated edge |
| low_major | total_points_h1 | always the underdog | 535 | 152 games | -8.7% | -15.1% to -2.3% | -20.3% to +2.9% | ±11.6% | no demonstrated edge |
| low_major | total_points_h2 | always over | 129 | 123 games | — | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always under | 129 | 123 games | — | — | — | — | not enough evidence (129 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the favourite | 167 | 62 days | — | — | — | — | not enough evidence (167 bets, below the 200 declared in advance) |
| low_major | total_points_h2 | always the underdog | 91 | 51 days | — | — | — | — | not enough evidence (91 bets, below the 200 declared in advance) |
| unplaced | moneyline | always home | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always away | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the favourite | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | moneyline | always the underdog | 2 | 2 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |
| unplaced | spread | always home | 5 | 2 games | — | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | spread | always away | 5 | 2 games | — | — | — | — | not enough evidence (5 bets, below the 200 declared in advance) |
| unplaced | total_points | always over | 7 | 2 games | — | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always under | 7 | 2 games | — | — | — | — | not enough evidence (7 bets, below the 200 declared in advance) |
| unplaced | total_points | always the favourite | 10 | 2 games | — | — | — | — | not enough evidence (10 bets, below the 200 declared in advance) |
| unplaced | total_points | always the underdog | 4 | 2 games | — | — | — | — | not enough evidence (4 bets, below the 200 declared in advance) |

## The model, per market and per conference tier

The lead table, and the only one that is a headline. The three tiers are three different distributions, and this lab exists because the third is plausibly priced with less attention.

The tier of a team is **measured, not assigned by conference**: `conferences.tier_table` places it by non-conference margin over the declared lookback, so the count in each tier moves with the data. `data/outputs/cbb_ratings_fit.json` carries the shape the fit behind this record placed.

| Tier | Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Could detect | Verdict |
|:---|:---|---:|---:|---:|:---|:---|---:|:---|
| high_major | alternate_spread | 2,148 | 55 games | -5.5% | -30.7% to +19.8% | -51.2% to +40.3% | ±45.8% | no demonstrated edge |
| high_major | alternate_total_points | 2,114 | 64 games | -1.1% | -31.0% to +28.7% | -55.2% to +52.9% | ±54.0% | no demonstrated edge |
| high_major | moneyline | 2,844 | 391 days | -3.8% | -12.4% to +4.8% | -19.4% to +11.8% | ±15.6% | no demonstrated edge |
| high_major | moneyline_h1 | 46 | 38 days | — | — | — | — | not enough evidence (46 bets, below the 200 declared in advance) |
| high_major | spread | 6,352 | 2,928 games | -1.4% | -5.1% to +2.2% | -8.1% to +5.2% | ±6.6% | no demonstrated edge |
| high_major | spread_h1 | 198 | 60 games | — | — | — | — | not enough evidence (198 bets, below the 200 declared in advance) |
| high_major | team_total | 984 | 514 games | -4.8% | -11.4% to +1.7% | -16.7% to +7.1% | ±11.9% | no demonstrated edge |
| high_major | total_points | 7,316 | 442 days | -3.1% | -6.9% to +0.8% | -10.0% to +3.9% | ±6.9% | no demonstrated edge |
| high_major | total_points_h1 | 184 | 57 games | — | — | — | — | not enough evidence (184 bets, below the 200 declared in advance) |
| mid_major | alternate_spread | 8,371 | 88 days | -6.9% | -16.9% to +3.0% | -25.1% to +11.2% | ±18.1% | no demonstrated edge |
| mid_major | alternate_team_total | 11 | 3 games | — | — | — | — | not enough evidence (11 bets, below the 200 declared in advance) |
| mid_major | alternate_total_points | 7,467 | 230 games | -17.0% | -29.7% to -4.2% | -40.1% to +6.2% | ±23.1% | no demonstrated edge |
| mid_major | moneyline | 5,927 | 422 days | -7.3% | -11.7% to -3.0% | -15.2% to +0.5% | ±7.9% | no demonstrated edge |
| mid_major | moneyline_h1 | 165 | 165 games | — | — | — | — | not enough evidence (165 bets, below the 200 declared in advance) |
| mid_major | spread | 12,958 | 421 days | -2.4% | -5.3% to +0.4% | -7.6% to +2.8% | ±5.2% | no demonstrated edge |
| mid_major | spread_h1 | 678 | 217 games | -10.6% | -24.9% to +3.6% | -36.4% to +15.2% | ±25.8% | no demonstrated edge |
| mid_major | team_total | 3,794 | 116 days | -5.4% | -8.8% to -1.9% | -11.6% to +0.9% | ±6.3% | no demonstrated edge |
| mid_major | total_points | 15,113 | 476 days | -0.2% | -2.9% to +2.5% | -5.1% to +4.7% | ±4.9% | no demonstrated edge |
| mid_major | total_points_h1 | 594 | 202 games | -2.4% | -17.4% to +12.6% | -29.6% to +24.8% | ±27.2% | no demonstrated edge |
| low_major | alternate_spread | 3,303 | 120 games | -6.2% | -23.7% to +11.3% | -37.8% to +25.5% | ±31.6% | no demonstrated edge |
| low_major | alternate_team_total | 11 | 1 games | — | — | — | — | not enough evidence (11 bets, below the 200 declared in advance) |
| low_major | alternate_total_points | 3,785 | 121 games | -10.5% | -30.3% to +9.4% | -46.4% to +25.4% | ±35.9% | no demonstrated edge |
| low_major | moneyline | 4,281 | 382 days | -9.5% | -14.8% to -4.1% | -19.2% to +0.2% | ±9.7% | no demonstrated edge |
| low_major | moneyline_h1 | 77 | 77 games | — | — | — | — | not enough evidence (77 bets, below the 200 declared in advance) |
| low_major | spread | 8,888 | 382 days | -1.0% | -4.2% to +2.2% | -6.7% to +4.8% | ±5.8% | no demonstrated edge |
| low_major | spread_h1 | 374 | 114 games | +5.0% | -15.8% to +25.8% | -32.6% to +42.6% | ±37.6% | no demonstrated edge |
| low_major | team_total | 1,890 | 102 days | -5.4% | -10.4% to -0.4% | -14.4% to +3.6% | ±9.0% | no demonstrated edge |
| low_major | total_points | 10,634 | 4,247 games | -5.1% | -8.2% to -2.0% | -10.7% to +0.5% | ±5.6% | no demonstrated edge |
| low_major | total_points_h1 | 326 | 106 games | -11.4% | -32.3% to +9.5% | -49.2% to +26.5% | ±37.9% | no demonstrated edge |
| unplaced | moneyline | 1 | 1 games | — | — | — | — | not enough evidence (1 bets, below the 200 declared in advance) |
| unplaced | spread | 3 | 2 games | — | — | — | — | not enough evidence (3 bets, below the 200 declared in advance) |
| unplaced | total_points | 2 | 1 games | — | — | — | — | not enough evidence (2 bets, below the 200 declared in advance) |

**3 cell(s) are one side wearing a model's clothes.** At least 75% of their bets sit on a single side, so read each against that side's blind return in the table above before reading it as a model result:

- unplaced / moneyline: 100% of bets on **home**.
- unplaced / spread: 100% of bets on **home**.
- unplaced / total_points: 100% of bets on **over**.

### Per tier, across markets

| Tier | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| high_major | 22,186 | 3,717 games | -3.1% | -7.8% to +1.6% | -11.7% to +5.5% | no demonstrated edge |
| mid_major | 55,078 | 7,411 games | -5.3% | -8.3% to -2.2% | -10.8% to +0.3% | no demonstrated edge |
| low_major | 33,569 | 5,324 games | -5.2% | -8.7% to -1.6% | -11.6% to +1.3% | no demonstrated edge |
| unplaced | 6 | 2 games | — | — | — | not enough evidence (6 bets, below the 200 declared in advance) |

## Pooled

**Pooled across Division I. This is never the headline.** High-major, mid-major and low-major are different distributions; a policy that wins in low-major games and loses in high-major ships in low-major only, if it ships at all. `docs/when_this_ends.md` applies the stopping rule to the pooled figure as well as to each tier, which is why it is computed — not so it can be quoted on its own.

| Market | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |
|:---|---:|---:|---:|:---|:---|:---|
| alternate_spread | 13,822 | 419 games | -6.5% | -14.8% to +1.8% | -21.6% to +8.5% | no demonstrated edge |
| alternate_team_total | 22 | 4 games | — | — | — | not enough evidence (22 bets, below the 200 declared in advance) |
| alternate_total_points | 13,366 | 415 games | -12.6% | -22.9% to -2.4% | -31.2% to +5.9% | no demonstrated edge |
| moneyline | 13,053 | 451 days | -7.3% | -10.6% to -4.0% | -13.2% to -1.3% | demonstrated deficit |
| moneyline_h1 | 288 | 288 games | +4.3% | -15.4% to +24.0% | -31.3% to +39.9% | no demonstrated edge |
| spread | 28,201 | 451 days | -1.7% | -3.5% to +0.0% | -5.0% to +1.5% | no demonstrated edge |
| spread_h1 | 1,250 | 391 games | -8.8% | -19.5% to +2.0% | -28.3% to +10.8% | no demonstrated edge |
| team_total | 6,668 | 121 days | -5.3% | -8.0% to -2.6% | -10.1% to -0.5% | demonstrated deficit |
| total_points | 33,065 | 13,076 games | -2.4% | -4.2% to -0.6% | -5.6% to +0.8% | no demonstrated edge |
| total_points_h1 | 1,104 | 365 games | -5.5% | -16.7% to +5.6% | -25.7% to +14.7% | no demonstrated edge |
| every market | 110,839 | 16,454 games | -4.8% | -6.9% to -2.7% | -8.6% to -1.0% | demonstrated deficit |

## Half a point at a key number, or a view of the game

A model that is systematically half a point away from the number has an opinion about rounding rather than about the game, and it evaporates the moment the market moves. The two are reported apart.

Key numbers **measured** from 20,197 games in the fitted population, most frequent first to 54% coverage: **3** (6.2%), **2** (6.0%), **5** (6.0%), **4** (5.8%), **8** (5.4%), **6** (5.2%), **7** (5.2%), **9** (4.9%), **10** (4.8%), **1** (4.5%). Never a list carried over from another sport — the NFL's 3 and 7 are a fact about how football scores.

**Not reported.** The ticket-margin reconstruction agreed with the recorded outcome on 86.9% of 109,735 scorable bets, below the 99% this module requires. The half-point decomposition is refused rather than computed on a convention that has not been verified.

## Calibration, overall and on the bets that were selected

**The overall figure is not evidence.** A model is selected into its bets by its own disagreement with the price, so its bets are the tail of its own error distribution. The NHL lab's model was calibrated across the board and overconfident by 9 to 12 percentage points on precisely what it picked. Read the selected column.

**Calibration can rule a model out and never in.** In the EPL lab a change that improved calibration on every market cost about 140 units in the backtest; in the NHL lab the by-ice-time correction straightened every volume bucket and lost 37.6 units in the only form a card could apply it. A straight line here is not a reason to ship anything.

| Predicted | Overall n | Overall observed | Gap | Selected n | Selected observed | Gap |
|:---|---:|:---|---:|---:|:---|---:|
| 0%–10% | 10,788 | 9.0% [8.5%, 9.6%] | +2.9 pp | 415 | 2.4% [1.3%, 4.4%] | -5.0 pp |
| 10%–20% | 15,290 | 20.8% [20.2%, 21.5%] | +5.5 pp | 2,242 | 8.0% [7.0%, 9.2%] | -7.6 pp |
| 20%–30% | 23,524 | 32.9% [32.3%, 33.5%] | +7.5 pp | 3,525 | 15.0% [13.9%, 16.3%] | -10.5 pp |
| 30%–40% | 43,176 | 43.8% [43.3%, 44.2%] | +8.1 pp | 5,355 | 24.6% [23.4%, 25.7%] | -10.5 pp |
| 40%–50% | 88,675 | 49.2% [48.9%, 49.6%] | +3.8 pp | 5,963 | 34.1% [32.9%, 35.3%] | -11.0 pp |
| 50%–60% | 83,671 | 51.1% [50.7%, 51.4%] | -3.4 pp | 46,981 | 49.2% [48.7%, 49.6%] | -6.7 pp |
| 60%–70% | 39,077 | 57.1% [56.6%, 57.6%] | -7.2 pp | 27,573 | 51.8% [51.2%, 52.4%] | -12.3 pp |
| 70%–80% | 21,704 | 68.0% [67.4%, 68.6%] | -6.6 pp | 10,553 | 57.8% [56.8%, 58.7%] | -16.5 pp |
| 80%–90% | 14,298 | 80.0% [79.3%, 80.6%] | -4.8 pp | 4,945 | 68.6% [67.3%, 69.9%] | -15.8 pp |
| 90%–100% | 10,665 | 91.3% [90.7%, 91.8%] | -2.6 pp | 2,183 | 83.8% [82.2%, 85.3%] | -10.4 pp |

- **Overall: 0.5 pp underconfident** over 350,868 graded rows in 10 usable bucket(s).
- **Selected: 10.1 pp overconfident** over 109,735 graded rows in 10 usable bucket(s).

Excluded from the selected denominator: 1,104 push, 8,465 unsettleable. A push is not half a win and is never folded in as one.

## What this report cannot say

- It cannot say a market is a play. **No market is allowlisted**, `staging_provider_policy` ships manual-only, and that is the correct state. An excluded market is never a pass, an avoid, or a no-value call.
- It cannot say an edge is **reachable**. That is `reachability.py`'s question, and an edge living entirely in prices that vanished is reported there as not reachable regardless of its size.
- It cannot rule a model **in** on calibration. Where a priced test exists, the priced test decides.
- It cannot replicate itself. A held-out season is `replication.py`'s job, and a window that merely fails to contradict is not confirmation.
