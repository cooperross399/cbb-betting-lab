# Everything this lab has ever tested

**A search that runs every week is not twelve tests. It is twelve tests a week, forever.** Correcting today's findings across today's twelve is a lie if twelve more were tested last week. At a nominal 5% threshold roughly one look in twenty clears by chance, so an automated edge-hunter without a cumulative tally does not find edges — it manufactures them on a schedule, with clean intervals and good prose.

College basketball's large sample makes this **more** urgent, not less. A bigger n narrows every interval, including the intervals of the hypotheses that are wrong. Sample size buys power, never innocence.

**62 distinct hypotheses tested.** Any new 95% interval must be widened by **x1.71** before it means what it says.

**Alpha budget: 6 new hypotheses a week**, declared 2026-09-01. Six new hypotheses a week, declared before the season opened and before a single price had been measured. Six is what a weekly refit-and-measure can genuinely pre-register with a falsifiable direction for each; the queue that feeds it is `data/manual/weekly_search_queue.json`, which the loop reads and never writes. When that queue is empty the loop spends nothing, which is the steady state — re-measuring a hypothesis already in this ledger on another week's data is the same look, not a new one, and `Hypothesis.key()` makes that structural rather than a promise.

**30 discovery, 32 holdout.** Putting a discovery finding to the holdout is a second look and is counted as one.

| Search | Hypotheses |
|:---|---:|
| replication | 32 |
| ladders_and_halves | 11 |
| core_team_markets | 4 |
| conference_tier | 4 |
| model_structure | 4 |
| schedule_states | 4 |
| november_prior | 2 |
| reachability | 1 |

| # | Search | Hypothesis | Stage | Predicted | Realised | Seasons | Tested | Outcome |
|---:|:---|:---|:---|:---|:---|:---|:---|:---|
| 1 | core_team_markets | moneyline: ROI at the card-time price is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 2 | core_team_markets | spread: ROI at the card-time price is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 3 | core_team_markets | total_points: ROI at the card-time price is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 4 | core_team_markets | team_total: ROI at the card-time price is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 5 | conference_tier | low_major: team-market ROI is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 6 | conference_tier | mid_major: team-market ROI is above zero | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 7 | conference_tier | high_major: team-market ROI is above zero | discovery | lower | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 8 | conference_tier | low_major ROI exceeds high_major ROI | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 9 | ladders_and_halves | alternate_spread: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 10 | ladders_and_halves | alternate_total_points: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 11 | ladders_and_halves | alternate_team_total: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 12 | ladders_and_halves | spread_h1: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 13 | ladders_and_halves | spread_h2: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 14 | ladders_and_halves | total_points_h1: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 15 | ladders_and_halves | total_points_h2: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 16 | ladders_and_halves | moneyline_h1: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 17 | ladders_and_halves | moneyline_h2: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 18 | ladders_and_halves | team_total_h1: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 19 | ladders_and_halves | team_total_h2: ROI at the card-time price is above zero | discovery | higher | — | 2024, 2025, 2026 | 2026-09-01 | pending |
| 20 | model_structure | explicit end-game segment: ROI exceeds extrapolated full-game efficiency | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 21 | model_structure | overtime as its own segment: ROI exceeds a scaled regulation distribution | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 22 | model_structure | fitted venue-level home effect: ROI exceeds one league-wide constant | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 23 | model_structure | quasi_neutral as a third venue state: ROI exceeds treating it as neutral | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 24 | november_prior | returning-production prior: ROI before December exceeds a flat prior | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 25 | november_prior | November ROI is below the rest of the season's | discovery | lower | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 26 | schedule_states | short rest: ROI with the adjustment exceeds ROI without it | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 27 | schedule_states | travel distance: ROI with the adjustment exceeds ROI without it | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 28 | schedule_states | altitude: ROI with the adjustment exceeds ROI without it | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 29 | schedule_states | conference tournament fatigue (four games in four days): ROI with the adjustment exceeds ROI without it | discovery | higher | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 30 | reachability | ROI among prices that SURVIVED to the next capture exceeds ROI among those that did not | discovery | lower | — | 2021, 2022, 2023, 2024, 2025, 2026 | 2026-09-01 | pending |
| 31 | replication | alternate_spread / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 32 | replication | alternate_total_points / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 33 | replication | moneyline / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 34 | replication | moneyline_h1 / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 35 | replication | spread / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 36 | replication | spread_h1 / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 37 | replication | team_total / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 38 | replication | total_points / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 39 | replication | total_points_h1 / high_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 40 | replication | alternate_spread / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 41 | replication | alternate_team_total / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 42 | replication | alternate_total_points / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 43 | replication | moneyline / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 44 | replication | moneyline_h1 / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 45 | replication | spread / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 46 | replication | spread_h1 / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 47 | replication | team_total / mid_major: the discovery result holds on a season it was not selected on | holdout | lower | — | 2025, 2026 | 2026-09-05 | pending |
| 48 | replication | total_points / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 49 | replication | total_points_h1 / mid_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 50 | replication | alternate_spread / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 51 | replication | alternate_team_total / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 52 | replication | alternate_total_points / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 53 | replication | moneyline / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 54 | replication | moneyline_h1 / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 55 | replication | spread / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 56 | replication | spread_h1 / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 57 | replication | team_total / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 58 | replication | total_points / low_major: the discovery result holds on a season it was not selected on | holdout | lower | — | 2025, 2026 | 2026-09-05 | pending |
| 59 | replication | total_points_h1 / low_major: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 60 | replication | moneyline / unplaced: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 61 | replication | spread / unplaced: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |
| 62 | replication | total_points / unplaced: the held-out return differs from zero in a cell the discovery window claimed nothing in (two-sided) | holdout | either | — | 2025, 2026 | 2026-09-05 | pending |

The correction is Bonferroni on the cumulative count — conservative on purpose. Holm and Benjamini-Hochberg need every p-value in hand at once, and this lab's tests arrive one week at a time over a season. A correction that can be computed incrementally and is slightly too wide beats one that is exactly right and cannot be computed until the season is over.

**This is not a substitute for a held-out season.** A correction widens an interval; it cannot tell you whether a result reproduces. Replication remains the bar.
