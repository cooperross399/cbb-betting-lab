# What the model learned from 

No finished game from  could be graded against a projection, so nothing is reported for it. The ratings still refit on every result the tables hold.
- The results tables are not on disk (/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/processed/cbb_team_games.csv does not exist, so the model cannot be asked for an opinion on any game. Run `scripts/fetch_cbb_data.py` and then `scripts/build_datasets.py`. Nothing was priced and nothing was frozen: a card with no opinion on anything is indistinguishable from a card whose model was never asked, and this run refuses to publish that ambiguity as a night of evidence.).
