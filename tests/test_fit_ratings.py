"""The refit the weekly loop has been asking for since it was written.

`scripts/run_weekly_loop.py` has held `REFIT_SCRIPT = "fit_ratings.py"` from the
day it landed and the file did not exist, so every weekly run reported step 2 as
`MISSING` and finished red with nothing refitted. The first test in this file is
that contract, and it is deliberately the first: a refit that exists and fits
beautifully under a name the loop does not call is still a loop that never
refits.

The rest pin the four things a fit report can get wrong quietly.

1. **Walk-forward.** The football lab's defect 13 was a distribution loaded once
   outside the season loop, and the code path looked right. So the test here is
   the one that lab paid for: corrupt every game after a cut date and assert the
   fits up to the cut are unchanged to the last bit.
2. **Re-renderable.** The record is written first and `render` is pure over it,
   so improving a sentence never costs a re-run. The test points the script at a
   processed directory that does not exist and requires the same markdown back.
3. **The venue audit's instrument.** The report compares a fitted home-court
   effect against a within-pair estimate and reports a disagreement. That
   comparison is only worth anything if the estimator is right, so it is checked
   against a planted home advantage on data where the naive estimator — the mean
   home margin — gets a wrong answer by construction.
4. **The two defects this build found in the seam the card prices through.**
   Both are reproduced here rather than described: `matchups_for` does not cut
   its history to the priced season, and it builds the tier table over the
   priced season as well. Neither is fixed here — `models/ratings.py` is not
   this task's file to edit — so these tests are the record that they were
   found, measured, and left in place deliberately.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier, tier_table
from cbb_betting_lab.models import ratings as R


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


def _load(name: str):
    """Import a script by path. `scripts/` is not a package and never will be."""
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_script_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FR = _load("fit_ratings")


# --------------------------------------------------------------------------
# A synthetic universe, small enough to fit in a second and real enough to fit
# --------------------------------------------------------------------------


#: Four teams to a conference, three conferences, and both numbers earn their
#: place. `tier_table` places a team by its **non-conference** margin, so a
#: two-conference league has only two opponent pools and every team lands high
#: or low with nothing in between; three conferences produce a high-, a mid- and
#: a low-major, which is what makes a per-tier table in these tests a table
#: rather than a row. An even team count lets the season be a proper
#: round-robin, so every team plays on every slate day — see `_rounds`.
DEFAULT_STRENGTHS: dict[int, float] = {
    1: 12.0,
    2: 11.0,
    3: 10.0,
    4: 9.0,
    5: 2.0,
    6: 1.0,
    7: 0.0,
    8: -1.0,
    9: -10.0,
    10: -11.0,
    11: -12.0,
    12: -13.0,
}


def _rounds(teams: list[int]) -> list[list[tuple[int, int]]]:
    """A double round-robin, as a list of days. The circle method.

    **Every team plays on every day**, which is the point and not tidiness. A
    fixture list that gives one game a day moves two teams out of twelve, and
    the median prior weight across teams then steps by whole ranks — so a
    synthetic league scheduled that way fails a decay check that a real board
    passes comfortably, for reasons that are entirely about the fixture. A real
    slate is dozens of games a night and this one is six.
    """
    rotation = list(teams[1:])
    fixed = teams[0]
    first: list[list[tuple[int, int]]] = []
    for index in range(len(teams) - 1):
        day = [(fixed, rotation[0])] if index % 2 == 0 else [(rotation[0], fixed)]
        for offset in range(1, len(teams) // 2):
            day.append((rotation[offset], rotation[-offset]))
        first.append(day)
        rotation = rotation[1:] + rotation[:1]
    # The return fixtures, so every pair meets at both venues and the venue
    # audit's estimator has something to be exact about.
    return first + [[(away, home) for home, away in day] for day in first]


def build_universe(
    root: Path,
    *,
    seasons=(2024, 2025, 2026),
    strengths=None,
    home_advantage: float = 4.0,
    possessions: float = 68.0,
) -> dict:
    """Three seasons of a made-up league, written where the script reads them.

    Every team plays every other twice, once at each venue, so **every pair is
    reciprocal** — the arrangement the venue audit's estimator is defined on,
    and the one that lets a planted home advantage be recovered exactly.

    **Every venue state appears, and that is not decoration.**
    `ratings._venue_effects` builds a design whose two quasi-neutral columns
    carry no ridge, so a league that never plays a quasi-neutral game makes the
    normal matrix singular and `prepare_prior` raises `LinAlgError`. That is the
    same defect class `tests/test_ratings_fit_is_well_posed.py` pins for
    `_season_fit` — *"the four venue columns were the only unregularised columns
    in the design"* — surviving in the second function, where `VENUE_RIDGE` was
    never applied. It is not fixed here, because `models/ratings.py` is not this
    task's file to edit; the fixture plays the games a real season plays, and
    the finding is recorded in this docstring and in the task report.
    """
    strengths = dict(strengths or DEFAULT_STRENGTHS)
    ordered = sorted(strengths)
    conferences = {team: f"C{index // 3}" for index, team in enumerate(ordered)}
    raw = root / "raw" / CBB.data_dir_segment / "schedules"
    raw.mkdir(parents=True, exist_ok=True)
    processed = root / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    team_rows: list[dict] = []
    player_rows: list[dict] = []
    schedule_rows: dict[int, list[dict]] = {}
    rng = np.random.default_rng(20260903)
    game_id = 1

    def play(home: int, away: int) -> tuple[int, int]:
        margin = (
            strengths[home]
            - strengths[away]
            + home_advantage
            + float(rng.normal(0.0, 6.0))
        )
        total = 140.0 + float(rng.normal(0.0, 8.0))
        return round((total + margin) / 2), round((total - margin) / 2)

    for season in seasons:
        fixtures: list[dict] = []
        day = pd.Timestamp(f"{season - 1}-11-04")
        for round_games in _rounds(ordered):
            for home, away in round_games:
                home_score, away_score = play(home, away)
                fixtures.append(
                    {
                        "game_id": game_id,
                        "slate_date": day.strftime("%Y-%m-%d"),
                        "home": home,
                        "away": away,
                        "home_score": home_score,
                        "away_score": away_score,
                        "venue_state": "home",
                        "neutral_site": False,
                        "venue_id": 1000 + home,
                        "city": f"city{home}",
                    }
                )
                game_id += 1
            day = day + pd.Timedelta(days=5)

        # A genuinely neutral court, and a "neutral" game in the nominal home
        # team's own arena — the third venue state, which this sport really has
        # and which the fitted design needs support for.
        for offset, (home, away) in enumerate(
            [(ordered[0], ordered[-1]), (ordered[1], ordered[-2])]
        ):
            for state in ("neutral", "quasi_neutral"):
                home_score, away_score = play(home, away)
                fixtures.append(
                    {
                        "game_id": game_id,
                        "slate_date": (
                            day + pd.Timedelta(days=2 * offset)
                        ).strftime("%Y-%m-%d"),
                        "home": home,
                        "away": away,
                        "home_score": home_score,
                        "away_score": away_score,
                        "venue_state": state,
                        "neutral_site": True,
                        "venue_id": 9000 if state == "neutral" else 1000 + home,
                        "city": "neutralcity" if state == "neutral" else f"city{home}",
                    }
                )
                game_id += 1
        day = day + pd.Timedelta(days=8)

        schedule_rows[season] = [
            {
                "id": game["game_id"],
                "season": season,
                "game_date": game["slate_date"],
                "home_id": game["home"],
                "away_id": game["away"],
                "home_conference_id": conferences[game["home"]],
                "away_conference_id": conferences[game["away"]],
                "home_score": game["home_score"],
                "away_score": game["away_score"],
                "neutral_site": game["neutral_site"],
                "venue_id": game["venue_id"],
                "venue_address_city": game["city"],
                "venue_address_state": "ST",
                "status_type_name": "STATUS_FINAL",
                "notes_headline": "",
            }
            for game in fixtures
        ]
        pd.DataFrame(schedule_rows[season]).to_parquet(
            raw / f"mbb_schedule_{season}.parquet"
        )

        for game in fixtures:
            for side, other in (("home", "away"), ("away", "home")):
                team = game[side]
                team_rows.append(
                    {
                        "game_id": game["game_id"],
                        "season": season,
                        "slate_date": game["slate_date"],
                        "team_id": team,
                        "opponent_id": game[other],
                        "home_away": side,
                        "neutral_site": game["neutral_site"],
                        "venue_state": game["venue_state"],
                        "game_state": "countable",
                        "team_score": game[f"{side}_score"],
                        "opponent_score": game[f"{other}_score"],
                        "margin": game[f"{side}_score"] - game[f"{other}_score"],
                        "total": game["home_score"] + game["away_score"],
                        "periods": 2.0,
                        "overtime": False,
                        "possessions_estimated": possessions,
                    }
                )
                for athlete in range(3):
                    player_rows.append(
                        {
                            "game_id": game["game_id"],
                            "season": season,
                            "slate_date": game["slate_date"],
                            "athlete_id": team * 100 + athlete,
                            "team_id": team,
                            "did_not_play": False,
                            "minutes": 30.0,
                        }
                    )

    pd.DataFrame(team_rows).to_csv(
        processed / CBB.output_name("team_games", ".csv"), index=False
    )
    pd.DataFrame(player_rows).to_csv(
        processed / CBB.output_name("player_games", ".csv"), index=False
    )
    return {
        "processed": processed,
        "raw": root / "raw",
        "outputs": root / "outputs",
        "strengths": strengths,
        "conferences": conferences,
        "home_advantage": home_advantage,
        "teams": ordered,
        "seasons": list(seasons),
    }


@pytest.fixture(autouse=True)
def _no_cached_schedules():
    """`ratings` caches schedules by season and the key does not carry the
    directory, so one test's synthetic 2026 would be served to the next."""
    R.clear_caches()
    yield
    R.clear_caches()


# --------------------------------------------------------------------------
# The contract the weekly loop has been failing on
# --------------------------------------------------------------------------


def test_the_weekly_loop_finds_the_refit_script_it_names():
    """The reason this program exists, pinned as a test rather than a docstring.

    `run_weekly_loop.run_script` treats a missing file as `MISSING` — *"nobody
    has written the refit yet"* — which degrades the run and is exactly what
    happened every week. A refit under any other name is the same outcome with
    a file in the repository to point at.
    """
    loop = _load("run_weekly_loop")
    assert (SCRIPTS / loop.REFIT_SCRIPT).is_file()
    assert loop.REFIT_SCRIPT == "fit_ratings.py"


def test_the_refit_accepts_exactly_what_the_loop_passes_it():
    """`--competition cbb`, and `--seasons` in the spelling the loop uses.

    The loop builds `--seasons` by splitting on whitespace and passing the
    pieces as separate arguments, while `run_price_backtest.py` takes them
    comma-separated in one. A parser that accepts only the second spelling turns
    a healthy week into a `FAILED` step on argparse, which reads as *the refit
    crashed on this week's data*.
    """
    parser = FR.build_parser()
    args = parser.parse_args(["--competition", "cbb", "--seasons", "2025", "2026"])
    assert FR.parse_seasons(args.seasons) == [2025, 2026]
    comma = parser.parse_args(["--competition", "cbb", "--seasons", "2024,2025"])
    assert FR.parse_seasons(comma.seasons) == [2024, 2025]
    assert FR.parse_seasons(parser.parse_args([]).seasons) == []


def test_a_missing_processed_table_exits_non_zero_and_writes_nothing(tmp_path):
    """An empty fit report reads as a fit that found nothing, which is a claim."""
    outputs = tmp_path / "outputs"
    code = FR.main(
        [
            "--competition",
            "cbb",
            "--processed-dir",
            str(tmp_path / "absent"),
            "--raw-dir",
            str(tmp_path / "absent"),
            "--output-dir",
            str(outputs),
        ]
    )
    assert code == FR.EXIT_NOTHING_TO_FIT
    assert not FR.record_path(CBB, outputs).exists()
    assert not FR.report_path(CBB, outputs).exists()


def test_a_season_filter_that_matches_nothing_is_a_refusal(tmp_path):
    world = build_universe(tmp_path)
    code = FR.main(
        [
            "--processed-dir",
            str(world["processed"]),
            "--raw-dir",
            str(world["raw"]),
            "--output-dir",
            str(world["outputs"]),
            "--seasons",
            "1999",
        ]
    )
    assert code == FR.EXIT_NOTHING_TO_FIT
    assert not FR.record_path(CBB, world["outputs"]).exists()


# --------------------------------------------------------------------------
# Walk-forward, tested the way the football lab's defect 13 taught
# --------------------------------------------------------------------------


def _fit_for(world: dict, season: int, team_games: pd.DataFrame) -> "FR.SeasonFit":
    seasons = sorted({int(s) for s in team_games["season"].unique()})
    schedules = FR.load_schedules(seasons, world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    return FR.fit_one_season(
        season=season,
        prepared=prepared,
        schedules=schedules,
        player_games=pd.DataFrame(),
        competition=CBB,
        output_dir=world["outputs"],
    )


def test_corrupting_every_game_after_a_cut_leaves_the_earlier_fits_identical(tmp_path):
    """The test the football lab paid for, on this lab's fitter.

    Its largest silent leak was a per-play distribution loaded once outside the
    season loop: the model pricing 2023 had seen 2025, and only the markets that
    consumed it looked good. A convention cannot catch that. This one corrupts
    every game after a cut date beyond recognition and requires every fit up to
    the cut — the prior weights, the league level, the residual sd, the graph —
    to come back bit-identical.
    """
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    cut = "2026-01-01"

    clean = _fit_for(world, 2026, team_games)
    R.clear_caches()

    corrupted = team_games.copy()
    future = (corrupted["season"] == 2026) & (corrupted["slate_date"] >= cut)
    assert future.sum() > 0
    corrupted.loc[future, "team_score"] = 999
    corrupted.loc[future, "opponent_score"] = 0
    corrupted.loc[future, "margin"] = 999
    corrupted.loc[future, "total"] = 999
    corrupted.loc[future, "possessions_estimated"] = 200.0
    dirty = _fit_for(world, 2026, corrupted)

    before_clean = clean.days[clean.days["day"] <= cut].reset_index(drop=True)
    before_dirty = dirty.days[dirty.days["day"] <= cut].reset_index(drop=True)
    assert len(before_clean) > 5
    assert before_clean["day"].tolist() == before_dirty["day"].tolist()
    for column in (
        "games",
        "team_games",
        "teams",
        "league_efficiency",
        "league_tempo",
        "residual_sd",
    ):
        assert before_clean[column].tolist() == before_dirty[column].tolist(), column
    assert (
        before_clean["prior_weight"].tolist() == before_dirty["prior_weight"].tolist()
    )


def test_every_priced_game_carries_a_stamp_strictly_earlier_than_its_own_day(tmp_path):
    """`assert_walk_forward` reads the stamp, not the code path. So does this."""
    from cbb_betting_lab.reports import price_backtest as PB

    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    fit = _fit_for(world, 2026, team_games)
    PB.assert_walk_forward(fit.games)
    stamped = fit.games[fit.games["priced_through"] != ""]
    assert not stamped.empty
    assert (stamped["priced_through"] < stamped["slate_date"]).all()


def test_a_fit_asked_for_a_day_it_has_already_seen_raises(tmp_path):
    """The second guard, which is `ratings.fit`'s own and is not this file's.

    Two independent refusals rather than one, because the arrangement that
    produced the football lab's leak is precisely one guard that looked right.
    """
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    rows = prepared.rows[prepared.rows["season"] == 2026]
    prior = R.prepare_prior(prepared, season=2026, schedules=schedules)
    day = str(rows["slate_date"].astype(str).min())
    with pytest.raises(R.WalkForwardViolation):
        R.fit(rows, prior=prior, as_of=day, season=2026, output_dir=world["outputs"])


# --------------------------------------------------------------------------
# The record, and the report that is pure over it
# --------------------------------------------------------------------------


def test_the_report_rerenders_from_the_record_with_no_table_present(tmp_path):
    """Improving a sentence must never cost a re-run.

    The processed directory is moved out from under the second call, so a
    re-render that secretly recomputed anything would fail rather than quietly
    produce the same file for the wrong reason.
    """
    world = build_universe(tmp_path)
    argv = [
        "--processed-dir",
        str(world["processed"]),
        "--raw-dir",
        str(world["raw"]),
        "--output-dir",
        str(world["outputs"]),
    ]
    assert FR.main(argv) == FR.EXIT_OK
    first = FR.report_path(CBB, world["outputs"]).read_text(encoding="utf-8")

    world["processed"].rename(tmp_path / "moved-away")
    assert FR.main(argv + ["--rebuild-report-only"]) == FR.EXIT_OK
    assert FR.report_path(CBB, world["outputs"]).read_text(encoding="utf-8") == first


def test_the_record_is_strict_json_with_no_infinity_in_it(tmp_path):
    """`inf` is what the refusal is made of, and `json.dumps` writes it anyway.

    An effective resistance of infinity is the commonest value on the opening
    Monday. Left as a float it makes the record readable by Python and by
    nothing else, and the re-render that is supposed to be free stops being
    free the moment anybody needs another reader.
    """
    world = build_universe(tmp_path)
    assert (
        FR.main(
            [
                "--processed-dir",
                str(world["processed"]),
                "--raw-dir",
                str(world["raw"]),
                "--output-dir",
                str(world["outputs"]),
            ]
        )
        == FR.EXIT_OK
    )
    text = FR.record_path(CBB, world["outputs"]).read_text(encoding="utf-8")
    assert "Infinity" not in text and "NaN" not in text
    json.loads(text, parse_constant=_no_constants)


def _no_constants(name: str):
    raise AssertionError(f"the record carries a non-JSON constant: {name}")


def test_a_stale_record_refuses_to_re_render(tmp_path):
    world = build_universe(tmp_path)
    argv = [
        "--processed-dir",
        str(world["processed"]),
        "--raw-dir",
        str(world["raw"]),
        "--output-dir",
        str(world["outputs"]),
    ]
    assert FR.main(argv) == FR.EXIT_OK
    path = FR.record_path(CBB, world["outputs"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record_version"] = FR.RECORD_VERSION + 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert FR.main(argv + ["--rebuild-report-only"]) == FR.EXIT_STALE_RECORD


def test_the_pooled_row_never_appears_without_its_tier_rows(tmp_path):
    """CLAUDE.md: *never report a pooled headline across the whole of D-I*.

    The pooled row exists — something has to be there for the tier rows to be
    read against — and the rule it lives under is that it is never alone.
    """
    world = build_universe(tmp_path)
    assert (
        FR.main(
            [
                "--processed-dir",
                str(world["processed"]),
                "--raw-dir",
                str(world["raw"]),
                "--output-dir",
                str(world["outputs"]),
            ]
        )
        == FR.EXIT_OK
    )
    record = json.loads(
        FR.record_path(CBB, world["outputs"]).read_text(encoding="utf-8")
    )
    for season in record["seasons_detail"]:
        tiers = [row["tier"] for row in season["per_tier"]]
        assert "POOLED" in tiers
        assert [t for t in tiers if t != "POOLED"], "a pooled row stood alone"
        assert tiers[-1] == "POOLED"
    report = FR.report_path(CBB, world["outputs"]).read_text(encoding="utf-8")
    assert "This is never the headline" in report


# --------------------------------------------------------------------------
# The words an interval is allowed to be described by
# --------------------------------------------------------------------------


def test_an_interval_including_zero_says_no_demonstrated_edge_in_those_words():
    from cbb_betting_lab import stats as S

    spanning = {
        "mean": 0.4,
        "low": -1.2,
        "high": 2.0,
        "n": 5_000,
        "survives_correction": False,
    }
    _mean, _interval, _corrected, words = FR.interval_cells(spanning)
    assert S.NO_DEMONSTRATED_EDGE in words


def test_below_the_declared_floor_there_is_no_number():
    """*A +12% return over 40 bets and a coin flip are the same claim.*"""
    from cbb_betting_lab import stats as S

    thin = {
        "mean": 12.0,
        "low": 11.0,
        "high": 13.0,
        "n": S.MINIMUM_BETS - 1,
        "survives_correction": True,
    }
    mean, interval, corrected, words = FR.interval_cells(thin)
    assert mean == "—" and interval == "—" and corrected == "—"
    assert "not enough evidence" in words
    assert "12" not in mean


# --------------------------------------------------------------------------
# The venue audit's instrument
# --------------------------------------------------------------------------


def test_the_within_pair_estimator_recovers_a_planted_home_advantage(tmp_path):
    """The audit compares a fitted number to this one, so this one has to be right.

    A planted home advantage of 4.0 points at 68 possessions is +5.88 per 100.
    Every pair in the synthetic league is reciprocal, so the estimator should
    recover it whatever the teams are worth — which is the property the whole
    venue section rests on.
    """
    world = build_universe(tmp_path, home_advantage=4.0, possessions=68.0)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    tiers = tier_table(schedules, (2024, 2025))
    rows = FR.reciprocal_home_advantage(
        prepared.rows, tiers=tiers, seasons=(2024, 2025, 2026), looks=1
    )
    pooled = next(row for row in rows if row["tier"] == "POOLED")
    expected = 100.0 * 4.0 / 68.0
    teams = len(world["teams"])
    assert pooled["pairs"] == teams * (teams - 1) // 2 * len(world["seasons"])
    assert pooled["per_100"]["low"] <= expected <= pooled["per_100"]["high"]
    assert pooled["points"]["low"] <= 4.0 <= pooled["points"]["high"]


def test_the_naive_home_margin_is_wrong_where_the_within_pair_estimate_is_not(tmp_path):
    """Why the audit uses subtraction and not a mean.

    The teams here are lopsided and the strong ones share a conference, so the
    mean home margin **inside a tier** is not the home advantage — it carries
    whatever quality gap that tier's home teams happen to enjoy. The within-pair
    estimator cancels it exactly; a tier mean does not, and the difference is
    the reason `ratings._venue_effects` and this report can disagree at all.
    """
    world = build_universe(
        tmp_path,
        strengths={1: 20.0, 2: 18.0, 3: 0.0, 4: -1.0, 5: -18.0, 6: -20.0},
        home_advantage=4.0,
    )
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    rows = prepared.rows[prepared.rows["is_local"].astype(bool)]

    # One team's home games only: a naive mean over them is its quality gap plus
    # the home advantage, and it is wrong by tens of points.
    naive = float(rows[rows["team_id"] == 1]["margin"].mean())
    assert naive > 20.0

    tiers = tier_table(schedules, (2024, 2025))
    measured = FR.reciprocal_home_advantage(
        prepared.rows, tiers=tiers, seasons=(2024, 2025, 2026), looks=1
    )
    pooled = next(row for row in measured if row["tier"] == "POOLED")
    assert pooled["points"]["low"] <= 4.0 <= pooled["points"]["high"]


# --------------------------------------------------------------------------
# The prior's weight, and the check that was wrong the first time
# --------------------------------------------------------------------------


def _decay_days(series: list[tuple[str, float]], teams: int = 300) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "day": day,
                "teams": teams,
                "teams_added": 0,
                "prior_weight": {
                    component: {"0.5": value} for component in FR.COMPONENTS
                },
                "per_team_rises": {
                    component: {"teams": 0, "largest": 0.0, "worst_team": None}
                    for component in FR.COMPONENTS
                },
            }
            for day, value in series
        ]
    )


def test_a_wobble_smaller_than_the_rendering_resolution_is_not_a_failure():
    """The check this file's first version got wrong, kept as a test.

    That version asserted the median prior weight falls between **every** pair
    of consecutive slate days. Run on 2025-26 it failed: 4 rises in offence, 5
    in defence, 3 in tempo out of 114 steps, the largest 0.00027. Two things
    produce them and neither is the ridge running backwards — an order statistic
    over a set that grows by a team, and the negative off-diagonals of `A⁻¹`,
    which make a team's own prior share depend on games played by teams it is
    connected to.

    The assertion was wrong, not the model, and the fix is not a tolerance
    chosen to fit the rises that were found: `DECAY_MATERIAL` is half a
    percentage point because `{prior_weight:.0%}` is how this quantity is
    already rendered everywhere it appears, so a smaller rise cannot reach a
    reader of any output this lab produces.
    """
    days = _decay_days(
        [
            ("2025-11-05", 0.900),
            ("2025-11-06", 0.850),
            ("2025-11-07", 0.850_2),  # up by 0.0002 — invisible when rendered
            ("2025-11-08", 0.800),
            ("2025-12-05", 0.700),
            ("2026-01-05", 0.500),
            ("2026-02-05", 0.300),
        ]
    )
    printed = ["2025-11-05", "2025-12-05", "2026-01-05", "2026-02-05"]
    result = FR.decay_check(days, printed=printed)
    assert result["checked"]
    assert result["monotone"]
    assert result["components"]["offence"]["daily_rise_count"] == 1
    assert result["components"]["offence"]["material_rise_count"] == 0


def test_a_rise_a_reader_could_see_breaks_the_decay():
    days = _decay_days(
        [
            ("2025-11-05", 0.900),
            ("2025-11-06", 0.850),
            ("2025-11-07", 0.870),  # up by two points: visible when rendered
            ("2025-12-05", 0.700),
            ("2026-01-05", 0.500),
            ("2026-02-05", 0.300),
        ]
    )
    result = FR.decay_check(
        days, printed=["2025-11-05", "2025-12-05", "2026-01-05", "2026-02-05"]
    )
    assert not result["monotone"]
    assert result["components"]["offence"]["material_rise_count"] == 1


def test_a_rise_on_the_printed_series_breaks_the_decay_however_small():
    """A number the report tabulates is a claim the report makes."""
    days = _decay_days(
        [
            ("2025-11-05", 0.500),
            ("2025-12-05", 0.400),
            ("2026-01-05", 0.400_1),
            ("2026-02-05", 0.300),
        ]
    )
    result = FR.decay_check(
        days, printed=["2025-11-05", "2025-12-05", "2026-01-05", "2026-02-05"]
    )
    assert not result["monotone"]
    assert not result["components"]["offence"]["printed_monotone"]


def test_a_broken_decay_ends_the_run_non_zero_after_writing_the_evidence(
    tmp_path, monkeypatch
):
    """The record is written first so a failure leaves something to look at.

    A refit that fails silently is a weekly loop that stays green; a refit that
    fails and writes nothing is a red step nobody can diagnose.
    """
    world = build_universe(tmp_path)
    monkeypatch.setattr(
        FR,
        "decay_check",
        lambda days, *, printed, months=FR.DECAY_MONTHS: {
            "checked": True,
            "monotone": False,
            "days": 1,
            "printed_days": 1,
            "months": list(months),
            "material_rise": FR.DECAY_MATERIAL,
            "teams_added": 0,
            "components": {},
        },
    )
    code = FR.main(
        [
            "--processed-dir",
            str(world["processed"]),
            "--raw-dir",
            str(world["raw"]),
            "--output-dir",
            str(world["outputs"]),
        ]
    )
    assert code == FR.EXIT_PRIOR_WEIGHT_NOT_MONOTONE
    assert FR.record_path(CBB, world["outputs"]).is_file()
    assert "IS BROKEN" in FR.report_path(CBB, world["outputs"]).read_text("utf-8")


def test_the_real_prior_weight_falls_across_the_synthetic_season(tmp_path):
    """The property itself, on fitted data rather than on a hand-built frame.

    No threshold is asserted on where it ends up. A synthetic season is twenty
    games a team against a λ measured in the same units, so the level it
    reaches is a fact about the fixture and pinning it would be pinning the
    fixture. What is pinned is the shape: it starts at 1.0 for a team that has
    not played, it never rises by as much as a reader could see, and it has
    fallen a long way by April.
    """
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    fit = _fit_for(world, 2026, team_games)
    series = [row["prior_weight"]["offence"]["0.5"] for row in fit.days.to_dict("records")]
    assert series[0] == pytest.approx(1.0)
    assert series[-1] < series[0] - 0.3
    steps = [b - a for a, b in zip(series, series[1:])]
    assert max(steps) < FR.DECAY_MATERIAL


# --------------------------------------------------------------------------
# The two defects in the seam the card prices through
# --------------------------------------------------------------------------


def test_the_seam_does_not_cut_its_history_to_the_priced_season(tmp_path):
    """Reproduced, measured, and deliberately not fixed here.

    `ratings.fit`'s contract is *history filtered to the season being priced* —
    *"a team is not the team it was last March"* — and `matchups_for` passes it
    every season it was handed, which is what `run_price_backtest.py` gives it.
    The consequence is not cosmetic: the design matrix on the opening Monday
    already holds several seasons of each team's games, so the ridge toward the
    preseason prior is outweighed before a ball is thrown and `prior_weight`
    reads near zero from November to March. That field exists precisely so that
    *a November number can never be printed as if it were a February one*.

    `models/ratings.py` is not this task's file to edit, so this test is the
    record that the defect was found rather than a fix for it. It asserts the
    gap in the direction it was measured; if the seam is ever repaired, this
    test fails and says why, which is the correct way for it to end.
    """
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    prior = R.prepare_prior(
        prepared,
        season=2026,
        tiers=tier_table(
            {s: schedules[s] for s in (2024, 2025)}, (2024, 2025)
        ),
        schedules={s: schedules[s] for s in (2024, 2025)},
    )
    rows = prepared.rows
    day = sorted(rows[rows["season"] == 2026]["slate_date"].astype(str).unique())[6]

    season_only = R.fit(
        rows[(rows["season"] == 2026) & (rows["slate_date"].astype(str) < day)],
        prior=prior,
        as_of=day,
        season=2026,
        output_dir=world["outputs"],
    )
    seam_like = R.fit(
        rows[rows["slate_date"].astype(str) < day],
        prior=prior,
        as_of=day,
        season=2026,
        output_dir=world["outputs"],
    )
    own = season_only.prior_weight_distribution((0.5,))["offence"][0.5]
    pooled = seam_like.prior_weight_distribution((0.5,))["offence"][0.5]
    assert own > 0.5, "an early-season fit on its own season is mostly prior"
    assert pooled < own / 2, (
        "the seam's pooled history should swamp the prior; if this now fails, "
        "matchups_for has been fixed and this test has done its job"
    )


def test_a_season_s_tier_table_does_not_depend_on_what_else_the_run_fits(tmp_path):
    """Found by running `--seasons 2024 2025 2026` and reading the numbers.

    The tier table was built from *every* earlier season the run had loaded, so
    fitting 2026 alone gave it a three-season table and fitting three seasons at
    once gave 2026 a five-season one — different tiers, and therefore different
    per-tier rows and a different home-court effect, for the same season out of
    the same data. A season's numbers must not depend on what else was in the
    same command, so the table is bounded by the prior's own window.
    """
    world = build_universe(tmp_path, seasons=(2022, 2023, 2024, 2025, 2026))
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2022, 2023, 2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)

    wide = FR.fit_one_season(
        season=2026,
        prepared=prepared,
        schedules=schedules,
        player_games=pd.DataFrame(),
        competition=CBB,
        output_dir=world["outputs"],
    )
    narrow = FR.fit_one_season(
        season=2026,
        prepared=prepared,
        schedules={s: schedules[s] for s in (2023, 2024, 2025, 2026)},
        player_games=pd.DataFrame(),
        competition=CBB,
        output_dir=world["outputs"],
    )
    assert wide.prior.tiers.seasons == (2023, 2024, 2025)
    assert wide.prior.tiers.seasons == narrow.prior.tiers.seasons
    assert wide.tier_of == narrow.tier_of
    assert wide.prior.venue.home_margin(Tier.LOW_MAJOR.value) == pytest.approx(
        narrow.prior.venue.home_margin(Tier.LOW_MAJOR.value)
    )


def test_the_seam_builds_its_tier_table_over_the_season_it_is_pricing(tmp_path):
    """The second half of the same finding, on a different quantity.

    `models/ratings.py` states the rule — tiers from *"seasons strictly before,
    which is that module's own rule"* — and `matchups_for` builds the table over
    every season it holds a schedule for. A tier is not a label: it chooses
    which home-court effect is applied, and the tiers' fitted effects differ by
    several points per hundred possessions.
    """
    world = build_universe(tmp_path)
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    leak = FR.tier_leak(schedules, 2026)
    assert leak["checked"]
    assert leak["teams"] > 0
    # The synthetic league is stable, so the count may legitimately be zero here.
    # What is pinned is that the two tables are built from different seasons at
    # all, which is the thing the seam gets wrong.
    assert "2026" not in leak["strictly_before"]
    assert "2026" in leak["including_priced"]


def test_a_missing_local_side_does_not_reach_the_model_as_pandas_na(tmp_path):
    """The one crash this script's own wiring could have produced.

    `prepare` writes an object column, so a game with no identified local side
    carries `pandas.NA` and not `None`. `ratings.matchup` tests `is None` before
    it compares the local side to the two participants, so a `pandas.NA` sails
    past the quasi-neutral refusal and then raises on `NA == home_team_id` —
    one game in a season, landing as a crash rather than as a wrong answer.
    `matchups_for` never meets it because it reads its local side out of a
    plain dict.
    """
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    schedules = FR.load_schedules([2024, 2025, 2026], world["raw"])
    prepared = R.prepare(team_games, schedules=schedules)
    prior = R.prepare_prior(prepared, season=2026, schedules=schedules)
    rows = prepared.rows[prepared.rows["season"] == 2026]
    days = sorted(rows["slate_date"].astype(str).unique())
    ratings = R.fit(
        rows[rows["slate_date"].astype(str) < days[20]],
        prior=prior,
        as_of=days[20],
        season=2026,
        output_dir=world["outputs"],
    )
    home, away = 1, 2
    with pytest.raises(TypeError):
        R.matchup(
            ratings,
            home_team_id=home,
            away_team_id=away,
            venue_state="quasi_neutral",
            local_team_id=pd.NA,
        )
    refused = R.matchup(
        ratings,
        home_team_id=home,
        away_team_id=away,
        venue_state="quasi_neutral",
        local_team_id=FR._or_none(pd.NA),
    )
    assert not refused.priceable
    assert "cannot tell whose" in refused.unpriceable_reason


# --------------------------------------------------------------------------
# Reporting rules that are easy to break by editing prose
# --------------------------------------------------------------------------


def test_refusals_are_grouped_by_reason_and_not_by_their_wording():
    """One refusal, a hundred rows: what the first run of this report printed.

    Every refusal embeds that morning's component count and that pair's
    resistance, so `value_counts()` over the raw strings splits one finding into
    a page of near-duplicates and then truncates each mid-word.
    """
    refused = pd.DataFrame(
        {
            "unpriceable_reason": [
                "the two teams are in different components of the games-played "
                "graph (40 components over 355 teams, 322 games) — no chain",
                "the two teams are in different components of the games-played "
                "graph (105 components over 318 teams, 214 games) — no chain",
                "the effective resistance between them is 2.00 against a bar of "
                "1.00 — less connecting evidence than a single head-to-head",
                "the effective resistance between them is 1.11 against a bar of "
                "1.00 — less connecting evidence than a single head-to-head",
                "team 248 has played no countable game this season, so its "
                "rating is the preseason prior and nothing else",
            ]
        }
    )
    families = FR.refusal_families(refused)
    assert len(families) == 3
    assert families[0]["count"] == 2
    assert all(row["example"] for row in families)


def test_a_game_filed_below_regulation_leaves_the_fit_without_being_counted():
    """Found by running, not by reading. A third group `prepare` does not name.

    `ratings.prepare` keeps rows whose period count **equals** regulation,
    counts those **above** it as overtime and those that are **missing** as
    unknown. A game filed with a period count *below* regulation — 24 of them in
    the eight cached seasons, real scores and all — is in none of the three, so
    it leaves the fit and appears in no count. The module docstring says both
    excluded groups are *"counted, never silently dropped"*; there are three
    groups.

    `PreparedGames.reconciles()` catches it, which is the accounting identity
    doing exactly what it was built for, and `fit_ratings.py` prints the size of
    the gap rather than a boolean. Nothing is fixed here: `models/ratings.py` is
    not this task's file to edit, and this test is the record that the hole was
    found and measured.
    """
    rows = pd.DataFrame(
        {
            "game_id": [1, 1, 2, 2],
            "season": [2026] * 4,
            "slate_date": ["2025-11-10"] * 4,
            "team_id": [10, 20, 10, 20],
            "opponent_id": [20, 10, 20, 10],
            "home_away": ["home", "away", "home", "away"],
            "neutral_site": [False] * 4,
            "venue_state": ["home"] * 4,
            "game_state": ["countable"] * 4,
            "team_score": [70, 68, 71, 69],
            "opponent_score": [68, 70, 69, 71],
            "margin": [2, -2, 2, -2],
            "total": [138, 138, 140, 140],
            # Game 2 is filed with one period. It is neither regulation, nor
            # overtime, nor a missing count.
            "periods": [2.0, 2.0, 1.0, 1.0],
            "overtime": [False] * 4,
            "possessions_estimated": [68.0] * 4,
        }
    )
    prepared = R.prepare(rows)
    assert len(prepared.rows) == 2
    assert prepared.overtime == 0
    assert prepared.periods_unknown == 0
    assert not prepared.reconciles(), "the identity should notice the two lost rows"
    unaccounted = (
        prepared.supplied
        - len(prepared.rows)
        - prepared.not_countable
        - prepared.venue_unknown
        - prepared.overtime
        - prepared.periods_unknown
        - prepared.too_few_possessions
    )
    assert unaccounted == 2


def test_a_bucket_of_games_reports_no_team_count_rather_than_zero(tmp_path):
    """`mixed` is games, not teams, and a zero there would be a claim."""
    world = build_universe(tmp_path)
    team_games = pd.read_csv(world["processed"] / CBB.output_name("team_games", ".csv"))
    fit = _fit_for(world, 2026, team_games)
    rows = FR.per_tier_fits(fit, looks=1)
    mixed = [row for row in rows if row["tier"] == FR.MIXED_TIER]
    for row in mixed:
        assert row["teams"] is None
    for row in rows:
        if row["tier"] not in (FR.MIXED_TIER, "POOLED"):
            assert isinstance(row["teams"], int)


def test_roster_turnover_is_measured_from_the_table_it_was_handed():
    """*Measure the current rate rather than quoting mine.*

    The NHL lab's figure and the football lab's are facts about hockey and
    football, and `models/ratings.py`'s own figures are a fact about the run
    that produced them. A report that printed any of them would look identical
    to one that measured, which is why this asserts a **number** rather than
    grepping for a string: the turnover here is planted, and the measurement has
    to find it.

    Six athletes a team last season, of whom three come back and play the same
    minutes — so exactly half the previous season's minutes are returning — plus
    one athlete who arrives from another school.
    """
    rows = []
    for team in (1, 2):
        for athlete in range(6):
            rows.append(
                {
                    "season": 2025,
                    "slate_date": "2024-12-01",
                    "team_id": team,
                    "athlete_id": team * 100 + athlete,
                    "minutes": 10.0,
                    "did_not_play": False,
                }
            )
        for athlete in range(3):
            rows.append(
                {
                    "season": 2026,
                    "slate_date": "2025-12-01",
                    "team_id": team,
                    "athlete_id": team * 100 + athlete,
                    "minutes": 10.0,
                    "did_not_play": False,
                }
            )
        rows.append(
            {
                "season": 2026,
                "slate_date": "2025-12-01",
                "team_id": team,
                # Athlete 500 played for the *other* team last season.
                "athlete_id": (3 - team) * 100 + 5,
                "minutes": 10.0,
                "did_not_play": False,
            }
        )
    measured = FR.roster_turnover_rows(
        pd.DataFrame(rows), seasons=[2026], division_one={1, 2}
    )
    assert measured["available"]
    row = next(r for r in measured["division_one"] if r["season"] == 2026)
    assert row["teams"] == 2
    assert row["returning_minutes_share"] == pytest.approx(0.5)
    assert row["incoming_transfer_share"] == pytest.approx(0.25)


def test_the_report_prints_no_figure_from_a_sibling_lab(tmp_path):
    world = build_universe(tmp_path)
    assert (
        FR.main(
            [
                "--processed-dir",
                str(world["processed"]),
                "--raw-dir",
                str(world["raw"]),
                "--output-dir",
                str(world["outputs"]),
            ]
        )
        == FR.EXIT_OK
    )
    report = FR.report_path(CBB, world["outputs"]).read_text(encoding="utf-8")
    for foreign in ("20.4%", "9.8%", "NHL", "football lab"):
        assert foreign not in report, f"{foreign} reached the report"


def test_the_report_says_nothing_here_is_a_return(tmp_path):
    world = build_universe(tmp_path)
    assert (
        FR.main(
            [
                "--processed-dir",
                str(world["processed"]),
                "--raw-dir",
                str(world["raw"]),
                "--output-dir",
                str(world["outputs"]),
            ]
        )
        == FR.EXIT_OK
    )
    report = FR.report_path(CBB, world["outputs"]).read_text(encoding="utf-8")
    assert "Nothing in this report is a return" in report
    assert "calibration can rule a model out and never in" in report.lower()


def test_a_walk_forward_violation_ends_the_run_and_writes_no_report(tmp_path, monkeypatch):
    """Either guard firing means nothing may be written.

    A leaked fit produces numbers that look exactly like every other number in
    the report, so the report must not exist. Both guards are caught at the same
    place and both end the run at `EXIT_WALK_FORWARD_LEAK`: `assert_walk_forward`
    reads the stamp on a priced row, `ratings.fit` refuses history that reaches
    the day it is pricing.
    """
    world = build_universe(tmp_path)

    def leak(**_kwargs):
        raise R.WalkForwardViolation("history reaches the day being priced")

    monkeypatch.setattr(FR, "fit_one_season", leak)
    code = FR.main(
        [
            "--processed-dir",
            str(world["processed"]),
            "--raw-dir",
            str(world["raw"]),
            "--output-dir",
            str(world["outputs"]),
        ]
    )
    assert code == FR.EXIT_WALK_FORWARD_LEAK
    assert not FR.record_path(CBB, world["outputs"]).exists()
    assert not FR.report_path(CBB, world["outputs"]).exists()
