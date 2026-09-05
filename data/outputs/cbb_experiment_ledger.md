# Everything this lab has ever tested

**A search that runs every week is not twelve tests. It is twelve tests a week, forever.** Correcting today's findings across today's twelve is a lie if twelve more were tested last week. At a nominal 5% threshold roughly one look in twenty clears by chance, so an automated edge-hunter without a cumulative tally does not find edges — it manufactures them on a schedule, with clean intervals and good prose.

College basketball's large sample makes this **more** urgent, not less. A bigger n narrows every interval, including the intervals of the hypotheses that are wrong. Sample size buys power, never innocence.

**95 distinct hypotheses tested.** Any new 95% interval must be widened by **x1.77** before it means what it says.

**Alpha budget: 6 new hypotheses a week**, declared 2026-09-01. Six new hypotheses a week, declared before the season opened and before a single price had been measured. Six is what a weekly refit-and-measure can genuinely pre-register with a falsifiable direction for each; the queue that feeds it is `data/manual/weekly_search_queue.json`, which the loop reads and never writes. When that queue is empty the loop spends nothing, which is the steady state — re-measuring a hypothesis already in this ledger on another week's data is the same look, not a new one, and `Hypothesis.key()` makes that structural rather than a promise.

**63 discovery, 32 holdout.** Putting a discovery finding to the holdout is a second look and is counted as one.

| Search | Hypotheses |
|:---|---:|
| replication | 32 |
| player_props_vs_devig | 30 |
| ladders_and_halves | 11 |
| core_team_markets | 4 |
| conference_tier | 4 |
| model_structure | 4 |
| schedule_states | 4 |
| player_props_vs_role_prior | 3 |
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
| 63 | player_props_vs_devig | player_points / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 64 | player_props_vs_devig | player_points / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 65 | player_props_vs_devig | player_points / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 66 | player_props_vs_devig | player_rebounds / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 67 | player_props_vs_devig | player_rebounds / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 68 | player_props_vs_devig | player_rebounds / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 69 | player_props_vs_devig | player_assists / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 70 | player_props_vs_devig | player_assists / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 71 | player_props_vs_devig | player_assists / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 72 | player_props_vs_devig | player_threes / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 73 | player_props_vs_devig | player_threes / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 74 | player_props_vs_devig | player_threes / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 75 | player_props_vs_devig | player_pra / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 76 | player_props_vs_devig | player_pra / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 77 | player_props_vs_devig | player_pra / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 78 | player_props_vs_devig | player_steals / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 79 | player_props_vs_devig | player_steals / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 80 | player_props_vs_devig | player_steals / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 81 | player_props_vs_devig | player_turnovers / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 82 | player_props_vs_devig | player_turnovers / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 83 | player_props_vs_devig | player_turnovers / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 84 | player_props_vs_devig | player_points_rebounds / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 85 | player_props_vs_devig | player_points_rebounds / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 86 | player_props_vs_devig | player_points_rebounds / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 87 | player_props_vs_devig | player_points_assists / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 88 | player_props_vs_devig | player_points_assists / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 89 | player_props_vs_devig | player_points_assists / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 90 | player_props_vs_devig | player_rebounds_assists / high_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 91 | player_props_vs_devig | player_rebounds_assists / mid_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 92 | player_props_vs_devig | player_rebounds_assists / low_major: the model's mean log loss is below the de-vigged two-sided fair price's | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 93 | player_props_vs_role_prior | high_major: the full model's mean log loss is below the identity-blind role-prior control's, pooled across the ten priceable markets | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 94 | player_props_vs_role_prior | mid_major: the full model's mean log loss is below the identity-blind role-prior control's, pooled across the ten priceable markets | discovery | lower | — | 2024 | 2026-09-05 | pending |
| 95 | player_props_vs_role_prior | low_major: the full model's mean log loss is below the identity-blind role-prior control's, pooled across the ten priceable markets | discovery | lower | — | 2024 | 2026-09-05 | pending |

## 7 quantities declared descriptive-only

**These cost no hypotheses and may never be reported as a finding.** They are computed and printed because a run that hides its own diagnostics is worse than one that shows them, and they pay no family correction because none of them is a claim about edge. That exemption is enforced rather than promised: `ExperimentLedger.record()` raises `PromotionRefused` on a hypothesis carrying one of these names, and `save()` refuses to drop a declaration — because deleting the declaration is how the refusal would be got around. Promoting one after the fact would read a look nobody counted as a result, and the temptation to do it arrives with exactly the numbers that came out well.

| Search | Quantity | Declared | Why it can never be a finding |
|:---|:---|:---|:---|
| player_props_diagnostics | the over/under split within every priced cell | 2026-09-05 | A mandatory disclosure, never netted: a cell that is +4% on overs and -4% on unders is a side bias, not an edge. Reading either half on its own doubles the cells without doubling the family, which is the subgroup search this ledger exists to price. |
| player_props_diagnostics | calibration by \|z\| bucket | 2026-09-05 | z = (line - mu)/sd IS the edge statistic. The design refuses to gate on it, because deleting the wagers where model and book most disagree makes the reported calibration true by construction. Printing it as a diagnostic is safe; reading a good bucket as a result is the same selection wearing a different hat. |
| player_props_diagnostics | mean(actual)/mean(mu) per cell, and its matched non-quoted comparison | 2026-09-05 | It reads settled outcomes, so it cannot run at T-60 and it deletes the cells where the answer was bad — which makes the Bonferroni correction anticonservative rather than conservative. It has no power to refuse anything and no standing to be a finding. The matched non-quoted arm exists to say what the ratio MEANS (level drift versus selection-by-being-quoted), not to score the model. |
| player_props_diagnostics | the refusal census, per tier and per reason | 2026-09-05 | A count of what the model declined to price, R1 through R5, with a missing entry (no opinion) counted separately from a refusal. It describes coverage. It is not a claim about returns, and the per-tier name-resolution rate inside it is a stop condition — the run halts if it moves more than 2pp across tiers — never a result. |
| player_props_diagnostics | the minutes-projection R-squared and residual SD | 2026-09-05 | A fit statistic on an input, not a return on a wager. The minutes model is explicitly unable to know whether a player will play, so a flattering R-squared here would say nothing about edge and everything about how predictable rotation minutes are. |
| player_props_diagnostics | the robustness row for minutes half-life in {2, 3, 4, 5} | 2026-09-05 | Half-life 4 is DECLARED, not selected: the fit-window curve is flat within 1% from 2 to 5. Printing the four is robustness. Picking the best of four after the fact is a four-way search reported as one number, and it is precisely how the rival design spent a holdout season on a 0.08% difference. |
| player_props_diagnostics | every unapplied diagnostic column (pace ratio, opponent allowance) | 2026-09-05 | Computed and stored, never applied to a price. They exist so a later session inherits the evidence rather than the temptation, and the bar to admit one was declared in advance: more than 2% of held-out RMSE, fitted on seasons strictly earlier than the validation season. Measured today at 0.13-0.29%. A column that priced nothing cannot have earned anything. |

The correction is Bonferroni on the cumulative count — conservative on purpose. Holm and Benjamini-Hochberg need every p-value in hand at once, and this lab's tests arrive one week at a time over a season. A correction that can be computed incrementally and is slightly too wide beats one that is exactly right and cannot be computed until the season is over.

**This is not a substitute for a held-out season.** A correction widens an interval; it cannot tell you whether a result reproduces. Replication remains the bar.
