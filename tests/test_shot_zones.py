"""The zone panel, and every way it could describe something it did not measure.

Organised by the way it would be wrong:

1. **Coverage.** A season the feed charted in part is refused, loudly, and
   there is no flag that turns the refusal off.
2. **The frame.** Both teams reach one frame by a rotation, so left stays
   left; a shot belonging to neither team is counted and dropped, never
   guessed at.
3. **The zones.** Every attempt lands in exactly one, the boundaries are the
   measured ones, and a zone below the floor takes no rank.
4. **Membership.** Ranks are over Division I, because a rank of 14th means a
   different thing against 365 teams than against 721.
5. **Direction.** The defensive rank counts the right way round. This is the
   one a reader would not catch.
6. **Restraint.** The panel computes no advantage and prints no verdict.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cbb_betting_lab.reports import shot_zones as SZ  # noqa: E402


# --------------------------------------------------------------------------
# Fixtures: shots at places we choose
# --------------------------------------------------------------------------


def shot(
    *,
    game="G1",
    home=10,
    away=20,
    team=10,
    feet_from_hoop=2.0,
    y=0.0,
    made=True,
    value=2,
    kind="JumpShot",
):
    """One attempt, placed by where it is rather than by a coordinate.

    The caller says "eight feet out, twelve feet left" and this puts it in the
    feed's own frame -- including the sign flip the away team's coordinates
    carry -- so a test never has to hand-write a coordinate and get the
    rotation wrong in the same file that checks the rotation.
    """
    # From the HOOP, not the baseline: the baseline is 5.25 ft further out.
    # This argument was called `feet_from_baseline` and measured from here,
    # which is where the module's own mislabelled `baseline_feet` came from.
    x = SZ.HOOP_X - feet_from_hoop
    if team != home:  # the away team's own frame is the mirror of this one
        x, y = -x, -y
    return {
        "game_id": game,
        "season": 2026,
        "team_id": float(team),
        "home_team_id": np.int32(home),
        "away_team_id": np.int32(away),
        "type_text": kind,
        "shooting_play": True,
        "scoring_play": bool(made),
        "score_value": value,
        "coordinate_x": float(x),
        "coordinate_y": float(y),
    }


def a_season(rows, *, games=None):
    return pd.DataFrame(rows)


def a_schedule(*, di=(10, 20), non_di=()):
    """A schedule whose conference ids mark exactly `di` as Division I."""
    rows = []
    for team in di:
        rows.append(
            {
                "home_id": team,
                "away_id": di[0] if team != di[0] else di[-1],
                "home_conference_id": 1.0,
                "away_conference_id": 1.0,
            }
        )
    for team in non_di:
        rows.append(
            {
                "home_id": di[0],
                "away_id": team,
                "home_conference_id": 1.0,
                "away_conference_id": None,
            }
        )
    return pd.DataFrame(rows)


def a_record(rows, *, schedule=None, season=2026):
    # `schedule or a_schedule()` calls bool() on a DataFrame, which raises.
    return SZ.build_record(
        SZ.ShotZoneInputs(
            pbp=a_season(rows),
            season=season,
            schedule=a_schedule() if schedule is None else schedule,
        )
    )


def enough(**kw):
    """`MINIMUM_ZONE_ATTEMPTS` identical shots, so a zone clears its floor."""
    return [shot(**kw) for _ in range(SZ.MINIMUM_ZONE_ATTEMPTS)]


def a_full_profile(team, opponent, *, made=True, repeat=1):
    """One team with every zone over the floor, so nothing is withheld."""
    places = [
        (2.0, 0.0, 2),        # rim
        (5.0, 0.0, 2),        # short paint
        (12.0, 0.0, 2),       # mid-range
        (2.0, 23.0, 3),       # corner three   -> 23.1 ft from the hoop
        (23.0, 8.0, 3),       # above the break -> 24.4 ft
        (30.0, 0.0, 3),       # deep            -> 30.0 ft
    ]
    rows = []
    for _ in range(repeat):
        for feet, y, value in places:
            rows += enough(
                team=team, home=team, away=opponent,
                feet_from_hoop=feet, y=y, value=value, made=made,
            )
    return rows


# --------------------------------------------------------------------------
# 1. Coverage
# --------------------------------------------------------------------------


def test_a_partly_charted_season_is_refused_and_the_share_is_named():
    """Seven of eight seasons are a sample of games ESPN chose to broadcast."""
    charted = a_full_profile(10, 20)
    uncharted = []
    for index in range(200):  # 200 games with no coordinates at all
        row = shot(game=f"dark{index}")
        row["coordinate_x"] = None
        row["coordinate_y"] = None
        uncharted.append(row)
    with pytest.raises(SZ.NotFullyCharted) as caught:
        a_record(charted + uncharted)
    message = str(caught.value)
    assert "of 201 games" in message, "the refusal has to name what it measured"
    assert "0.5%" in message
    assert "production" in message and "broadcast" in message, (
        "the refusal has to say WHY a partial season is not a small one"
    )


def test_the_coverage_refusal_takes_no_override():
    """A flag would be used, once, by someone in a hurry."""
    source = (REPO / "src/cbb_betting_lab/reports/shot_zones.py").read_text("utf-8")
    body = source.split("def assert_fully_charted", 1)[1].split("\ndef ", 1)[0]
    # The docstring may SAY there is no override; the code must not have one.
    code = body.split('"""', 2)[-1]
    for escape in ("force", "allow_partial", "override", "skip", "strict="):
        assert escape not in code, f"assert_fully_charted grew an escape: {escape}"
    assert "REQUIRED_CHARTED_SHARE" in code


def test_charted_share_counts_games_and_not_shots():
    """A shot-weighted share reads 6% as 'thin' when it means 'absent'."""
    rows = a_full_profile(10, 20)              # one game, fully charted
    dark = [shot(game="dark") for _ in range(5_000)]
    for row in dark:
        row["coordinate_x"] = None
    census = SZ.charted_share(SZ.field_goal_attempts(a_season(rows + dark)))
    assert census["games"] == 2 and census["charted_games"] == 1
    assert census["share"] == pytest.approx(0.5), (
        "5,000 uncharted shots in one game must not outvote 150 charted ones "
        "in another -- the feed charts games, so the share is over games"
    )


# --------------------------------------------------------------------------
# 2. The frame
# --------------------------------------------------------------------------


def test_the_away_team_is_rotated_so_left_stays_left():
    """A mirror puts the hoop in the right place and swaps every corner."""
    left_home = shot(team=10, home=10, away=20, feet_from_hoop=2.0, y=23.0, value=3)
    left_away = shot(team=20, home=10, away=20, feet_from_hoop=2.0, y=23.0, value=3)
    frame = SZ.attacking_frame(a_season([left_home, left_away]))
    assert frame["y"].nunique() == 1, (
        "both shots were taken 23 feet to the same side of the floor and the "
        "frame put them on opposite sides -- that is a reflection, not a "
        "rotation, and it swaps left and right for every away team"
    )
    assert (frame["x_from_hoop"] == 2.0).all()
    assert (frame["baseline_feet"] == SZ.BASELINE_X - SZ.HOOP_X + 2.0).all(), (
        "`baseline_feet` has to measure from the baseline; it is 5.25 ft "
        "further out than `x_from_hoop` and was for a while the same number"
    )
    assert (frame["distance"] > SZ.ARC).all()


def test_a_shot_tagged_to_neither_team_is_counted_and_dropped():
    """Measured: 14 attempts in 2 games. Excluded, never reassigned.

    The stray team is a **Division-I** team that is not in this game, and that
    detail is the test. With a non-D-I id the membership filter drops the row
    on its own, and deleting the attribution drop entirely leaves this passing
    -- which is what it did until a mutant said so.
    """
    # Large enough that ONE stray sits under the declared threshold; the
    # threshold itself is what the next test is for.
    rows = a_full_profile(10, 20, repeat=8)
    rows.append(shot(team=30, home=10, away=20))   # 30 is D-I, and not here
    record = a_record(rows, schedule=a_schedule(di=(10, 20, 30)))
    assert record["attribution"]["unattributed"] == 1
    assert record["attribution"]["unattributed_games"] == 1
    assert record["membership"]["attempts_dropped"] == 0, (
        "the fixture has to make the MEMBERSHIP filter a no-op, or it hides "
        "whether the attribution filter did anything"
    )
    described = sum(r["attempts"] for r in record["league"])
    assert described == len(rows) - 1, (
        "the stray shot reached a zone, which means it was attributed to a "
        "team the feed said it did not belong to"
    )


def test_too_many_unattributed_shots_are_a_join_and_not_a_typo():
    rows = a_full_profile(10, 20)
    rows += [shot(team=999, home=10, away=20) for _ in range(len(rows))]
    with pytest.raises(SZ.ShotsUnattributed) as caught:
        a_record(rows)
    assert "float64" in str(caught.value), (
        "the refusal has to name the dtype trap, because that is what a "
        "100% failure means and a reader will need it"
    )


def test_a_string_comparison_of_the_ids_would_fail_this():
    """`team_id` is float64 and `home_team_id` int32: '10.0' != '10'."""
    frame = SZ.attacking_frame(a_season(a_full_profile(10, 20)))
    census = SZ.attribution_census(frame)
    assert census["unattributed"] == 0, (
        "every shot here belongs to the home team; a non-zero count means "
        "the ids are being compared across types"
    )


# --------------------------------------------------------------------------
# 3. The zones
# --------------------------------------------------------------------------


def test_every_attempt_lands_in_exactly_one_zone():
    """The cascade ends unconditionally, so 'none' is unreachable."""
    rows = []
    for feet in np.arange(0.0, 40.0, 0.5):
        for y in np.arange(-24.0, 25.0, 1.0):
            rows.append(shot(feet_from_hoop=float(feet), y=float(y)))
    frame = SZ.attacking_frame(a_season(rows))
    zones = SZ.assign_zones(frame)
    assert zones.isin(SZ.ZONE_KEYS).all(), "a shot fell outside every zone"
    assert len(zones) == len(frame)
    assert set(zones.unique()) == set(SZ.ZONE_KEYS), (
        "a sweep of the whole floor did not reach every zone, so one of them "
        "is unreachable and the boundaries do not partition the court"
    )


@pytest.mark.parametrize(
    "feet,y,expected",
    [
        (2.0, 0.0, "rim"),
        (4.0, 0.0, "rim"),
        (5.0, 0.0, "short_paint"),
        (6.0, 0.0, "short_paint"),
        (7.0, 0.0, "mid_range"),
        (20.0, 0.0, "mid_range"),
        (2.0, 23.0, "corner_three"),
        (2.0, 20.0, "mid_range"),
        (23.0, 10.0, "above_break_three"),
        (30.0, 0.0, "deep_three"),
    ],
)
def test_the_boundaries_are_the_measured_ones(feet, y, expected):
    frame = SZ.attacking_frame(a_season([shot(feet_from_hoop=feet, y=y)]))
    assert SZ.assign_zones(frame).iloc[0] == expected


def test_the_mid_range_is_one_zone():
    """Six feet to the arc measured 0.738-0.800 with no ordering. A panel
    that split it would draw a line the sport does not draw."""
    assert "short_mid" not in SZ.ZONE_KEYS and "long_mid" not in SZ.ZONE_KEYS
    frame = SZ.attacking_frame(
        a_season([shot(feet_from_hoop=f, y=0.0) for f in (7.0, 12.0, 18.0, 21.0)])
    )
    assert set(SZ.assign_zones(frame)) == {"mid_range"}


def test_a_zone_below_the_floor_takes_no_rank():
    """A rate on nine attempts is read beside rates built on six hundred.

    The fixture must actually CONTAIN a thin zone. The first version of this
    test built a profile where every zone cleared the floor, so its `all(...)`
    ran over an empty list and passed with the floor deleted.
    """
    rows = a_full_profile(10, 20)
    # Team 20 clears the floor in five zones and takes exactly three deep
    # threes, so it has a real zone under the floor rather than a topped-up one.
    for feet, y, value in ((2.0, 0.0, 2), (5.0, 0.0, 2), (12.0, 0.0, 2),
                           (2.0, 23.0, 3), (23.0, 8.0, 3)):
        rows += enough(team=20, home=20, away=10,
                       feet_from_hoop=feet, y=y, value=value)
    rows += [shot(team=20, home=20, away=10, feet_from_hoop=30.0, value=3)
             for _ in range(3)]
    record = a_record(rows)
    thin = [r for r in record["offense"] if not r["enough_attempts"]]
    assert thin, "the fixture produced no zone under the floor to check"
    assert all(r["attempts"] < SZ.MINIMUM_ZONE_ATTEMPTS for r in thin)
    assert all(r["rank"] is None for r in thin), (
        "a zone under the floor was ranked, and the rank will be read against "
        "ranks built on hundreds of attempts"
    )
    assert all(r["points_per_attempt"] is None for r in thin)
    # and the ranks that DO exist are taken only over the zones that qualify
    ranked = [r for r in record["offense"] if r["zone"] == "deep_three" and r["rank"]]
    assert all(r["ranked_of"] == len(ranked) for r in ranked)


# --------------------------------------------------------------------------
# 4. Membership
# --------------------------------------------------------------------------


def test_a_non_division_one_opponent_is_dropped_from_both_profiles():
    """A rim rate padded by a November buy game is a rate against another sport."""
    rows = a_full_profile(10, 20) + a_full_profile(10, 77)
    record = a_record(rows, schedule=a_schedule(di=(10, 20), non_di=(77,)))
    assert record["membership"]["division_one_teams"] == 2
    assert record["membership"]["attempts_dropped"] == len(a_full_profile(10, 77))
    assert {r["team_id"] for r in record["offense"]} == {10}
    assert 77 not in {r["team_id"] for r in record["defense"]}


def test_a_schedule_naming_no_conference_is_refused():
    """An empty membership set would rank every programme the feed has seen."""
    blank = pd.DataFrame(
        {"home_id": [10], "away_id": [20],
         "home_conference_id": [None], "away_conference_id": [None]}
    )
    with pytest.raises(SZ.NoDivisionOne):
        a_record(a_full_profile(10, 20), schedule=blank)


def test_the_schedule_is_not_optional():
    """Without it the first build ranked 721 teams under a D-I heading."""
    import dataclasses
    fields = {f.name: f for f in dataclasses.fields(SZ.ShotZoneInputs)}
    assert fields["schedule"].default is dataclasses.MISSING, (
        "a defaulted schedule lets a caller build a record that silently "
        "ranks Division II inside a Division-I column"
    )


# --------------------------------------------------------------------------
# 5. Direction
# --------------------------------------------------------------------------


def test_the_defensive_rank_counts_the_right_way_round():
    """1 = fewest points allowed. Reversed, the table reads plausibly and is
    exactly backwards, and it is the one column nobody would check."""
    stingy, leaky = 10, 20
    rows = []
    # The DEFENDER is the team that did not shoot. `stingy` defends 30 missed
    # rim attempts and allows nothing; `leaky` defends 30 made ones.
    rows += [shot(team=leaky, home=leaky, away=stingy, feet_from_hoop=2.0,
                  made=False) for _ in range(30)]
    rows += [shot(team=stingy, home=stingy, away=leaky, feet_from_hoop=2.0,
                  made=True) for _ in range(30)]
    record = a_record(rows)
    by_team = {r["team_id"]: r for r in record["defense"] if r["zone"] == "rim"}
    assert by_team[stingy]["points_per_attempt"] == 0.0
    assert by_team[leaky]["points_per_attempt"] == 2.0
    assert by_team[stingy]["rank"] == 1, (
        "the defence that allowed nothing must rank 1st; if it ranks last the "
        "sign of every defensive rank in the panel is inverted"
    )
    assert by_team[leaky]["rank"] == 2


def test_the_offensive_rank_counts_the_other_way():
    good, bad = 10, 20
    rows = [shot(team=good, home=good, away=bad, feet_from_hoop=2.0, made=True)
            for _ in range(30)]
    rows += [shot(team=bad, home=bad, away=good, feet_from_hoop=2.0, made=False)
             for _ in range(30)]
    record = a_record(rows)
    by_team = {r["team_id"]: r for r in record["offense"] if r["zone"] == "rim"}
    assert by_team[good]["rank"] == 1 and by_team[bad]["rank"] == 2


# --------------------------------------------------------------------------
# 6. Restraint
# --------------------------------------------------------------------------


def test_neither_renderer_computes_an_advantage_or_prints_a_verdict():
    """The football chart this is built from prints two rows and no mismatch
    score, and that restraint is why it can be read without being believed."""
    from cbb_betting_lab import stats as S

    rows = a_full_profile(10, 20) + a_full_profile(20, 10)
    record = a_record(rows)
    pages = SZ.render(record) + SZ.render_matchup(record, offense=10, defense=20)
    for reserved in (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT,
                     S.NO_DEMONSTRATED_EDGE):
        assert reserved not in pages, (
            f"the panel printed {reserved!r}; it makes no claim about edge and "
            "may not borrow the vocabulary of the reports that do"
        )
    assert SZ.DESCRIPTIVE_ONLY_SENTENCE in SZ.render(record)
    assert SZ.DESCRIPTIVE_ONLY_SENTENCE in SZ.render_matchup(
        record, offense=10, defense=20
    )
    assert record["descriptive_only"] is True


def test_the_module_computes_no_difference_between_the_two_sides():
    """A column subtracting one rank from the other is a claim in a
    description's clothes, so there must not be one."""
    source = (REPO / "src/cbb_betting_lab/reports/shot_zones.py").read_text("utf-8")
    body = source.split("def render_matchup", 1)[1].split("\ndef ", 1)[0]
    # The docstring is allowed to name what the function refuses to do; the
    # CODE is what must not do it, so the docstring is cut before the search.
    code = body.split('"""', 2)[-1]
    for word in ("advantage", "edge", "mismatch", "differential", "exploit"):
        assert word not in code.lower(), f"render_matchup computes {word!r}"


def test_a_team_absent_from_the_season_is_refused_rather_than_averaged():
    record = a_record(a_full_profile(10, 20))
    with pytest.raises(SZ.ShotZoneError) as caught:
        SZ.render_matchup(record, offense=10, defense=999)
    assert "league-average floor" in str(caught.value)


def test_a_stale_record_is_refused_rather_than_rendered():
    record = a_record(a_full_profile(10, 20))
    record["record_version"] = SZ.RECORD_VERSION + 1
    with pytest.raises(SZ.ShotZoneError):
        SZ.render(record)


def test_the_geometry_refusal_fires_when_the_coordinates_describe_another_floor():
    """Threes charted at the rim mean the coordinates and the labels came
    from different places."""
    rows = a_full_profile(10, 20)
    rows += [shot(team=10, home=10, away=20, feet_from_hoop=2.0, y=0.0, value=3)
             for _ in range(len(rows))]
    with pytest.raises(SZ.GeometryDoesNotReconstruct) as caught:
        a_record(rows)
    assert "different floor" in str(caught.value)


def test_the_committed_report_is_what_the_committed_record_renders_to():
    """A report edited by hand, or left behind by a change to the renderer,
    is a page that says something the record does not."""
    outputs = REPO / "data" / "outputs"
    records = sorted(outputs.glob("cbb_shot_zones_*.json"))
    if not records:
        pytest.skip("no shot-zone record is committed yet")
    for record_path in records:
        report_path = record_path.with_suffix(".md")
        assert report_path.is_file(), f"{record_path.name} has no report beside it"
        record = SZ.read_record(record_path)
        assert report_path.read_text("utf-8") == SZ.render(record), (
            f"{report_path.name} is not what {record_path.name} renders to. "
            "Re-run the panel; it opens no store and spends nothing."
        )


def test_every_committed_record_is_a_fully_charted_season():
    """The refusal is enforced at build time; this is the one that would
    notice a record that got past it and was committed anyway."""
    for record_path in sorted((REPO / "data" / "outputs").glob("cbb_shot_zones_*.json")):
        record = SZ.read_record(record_path)
        assert record["coverage"]["share"] >= SZ.REQUIRED_CHARTED_SHARE, (
            f"{record_path.name} describes a season charted at "
            f"{record['coverage']['share']:.1%}"
        )
        assert record["descriptive_only"] is True


# --------------------------------------------------------------------------
# 8. A rank is only as good as the field it is printed against
#
# Both ranks in the matchup table were divided by `ranked_of`, the count of
# teams with enough attempts to earn a POINTS-PER-ATTEMPT rank. The share rank
# is over every team present, because an attempt share is a count over a
# team's own total and is well measured however small its numerator. The two
# agree exactly while every team clears the floor, which is the only state the
# 2025-26 record is in -- so the defect was invisible in the only season this
# module is allowed to describe.
# --------------------------------------------------------------------------


def _thin_and_thick_season():
    """Two teams, and one of them takes almost no corner threes.

    Team 10 clears the floor in the corner; team 20 takes three there. Both
    clear it at the rim, so the zone that separates the two denominators is
    the corner and nothing else moves.
    """
    rows = []
    for team, home, away in ((10, 10, 20), (20, 10, 20)):
        rows += [
            shot(team=team, home=home, away=away, feet_from_hoop=1.0, y=0.0, value=2)
            for _ in range(SZ.MINIMUM_ZONE_ATTEMPTS)
        ]
    rows += [
        shot(team=10, home=10, away=20, feet_from_hoop=4.0, y=23.0, value=3)
        for _ in range(SZ.MINIMUM_ZONE_ATTEMPTS)
    ]
    rows += [
        shot(team=20, home=10, away=20, feet_from_hoop=4.0, y=23.0, value=3)
        for _ in range(3)
    ]
    return rows


def test_the_two_ranks_are_divided_by_the_fields_they_were_taken_over():
    """`ranked_of` counts teams with a rate; `share_ranked_of` counts teams."""
    record = a_record(_thin_and_thick_season())
    corner = [r for r in record["offense"] if r["zone"] == "corner_three"]
    assert len(corner) == 2, "the fixture did not put both teams in the corner"
    thin = next(r for r in corner if r["attempts"] < SZ.MINIMUM_ZONE_ATTEMPTS)
    assert thin["points_per_attempt"] is None and thin["rank"] is None, (
        "a zone under the floor carries no rate and takes no rank"
    )
    assert thin["share_rank"] is not None, (
        "an attempt share is measured however small its numerator, so the "
        "share rank survives the floor -- which is the whole reason it needs "
        "a denominator of its own"
    )
    for row in corner:
        assert row["ranked_of"] == 1, "only one team has a corner rate"
        assert row["share_ranked_of"] == 2, "both teams have a corner share"
        assert row["share_ranked_of"] > row["ranked_of"], (
            "the fixture is supposed to pull the two denominators apart"
        )


def test_no_rendered_rank_is_larger_than_the_field_it_is_printed_against():
    """`365/364` is the shape of this defect on a real season."""
    import re

    record = a_record(_thin_and_thick_season())
    page = SZ.render_matchup(record, offense=20, defense=10)
    printed = re.findall(r"(\d+)/(\d+)", page)
    assert printed, "the matchup table printed no ranks at all"
    for rank, of in printed:
        assert int(rank) <= int(of), (
            f"the table printed rank {rank} out of a field of {of}, which is "
            "a rank counted over one population and divided by another"
        )


def test_a_zone_a_team_never_shot_from_is_printed_rather_than_dropped():
    """Zero and missing are different, and the row said neither."""
    rows = [
        shot(team=t, home=10, away=20, feet_from_hoop=1.0, y=0.0, value=2)
        for t in (10, 20)
        for _ in range(SZ.MINIMUM_ZONE_ATTEMPTS)
    ]
    record = a_record(rows)
    page = SZ.render_matchup(record, offense=10, defense=20)
    labels = {z["key"]: z["label"] for z in record["zones"]}
    for key, label in labels.items():
        assert label in page, (
            f"{key} vanished from the matchup table. A team that never shot "
            "from a zone is the strongest reading on a page about where shots "
            "come from, and dropping the row prints it as though the zone did "
            "not exist."
        )
    assert "attempted none" in page


def test_the_baseline_is_not_the_hoop():
    """5.25 ft apart, and one number was doing both jobs."""
    assert SZ.BASELINE_X - SZ.HOOP_X == pytest.approx(5.25)
    frame = SZ.attacking_frame(
        a_season([shot(team=10, home=10, away=20, feet_from_hoop=0.0, y=0.0)])
    )
    assert float(frame["x_from_hoop"].iloc[0]) == pytest.approx(0.0), (
        "a shot at the rim is zero feet from the hoop"
    )
    assert float(frame["baseline_feet"].iloc[0]) == pytest.approx(5.25), (
        "and 5.25 feet from the baseline, which is where the hoop stands"
    )


def test_a_version_one_shot_zone_record_is_refused(tmp_path):
    """A version-1 record has no `share_ranked_of`, and rendering one would
    print the share rank against the wrong field again."""
    path = tmp_path / "cbb_shot_zones_2026.json"
    path.write_text(json.dumps({"record_version": 1}), encoding="utf-8")
    with pytest.raises(SZ.ShotZoneError) as caught:
        SZ.read_record(path)
    assert "version 1" in str(caught.value)
