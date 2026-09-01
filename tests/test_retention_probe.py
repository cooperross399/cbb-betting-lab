"""Every guard in the retention probe, named after what it protects.

Four of these reproduce a defect a sibling lab actually shipped:

* the football lab's probe cached chunk responses under the chunk's **length**,
  so four ten-market chunks collided and three answers were lost silently;
* it read retention **per provider key**, and three featured prop keys returning
  nothing while their alternate ladders carried the same market read as three
  unmeasurable markets when the true answer was none;
* it could only regenerate its report by re-running the probe, at 7,280 credits
  a time;
* and the NHL lab's probe reported its **own starvation** as market absence.

No test here touches the network. Every provider interaction goes through a fake
requester injected with `OddsApiProvider(requester=...)`, and every input frame
is built in a temporary directory, so the suite says the same thing on a laptop
with the full data cache and in CI with none of it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from cbb_betting_lab import config as CONFIG
from cbb_betting_lab import markets as M
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.providers import team_names
from cbb_betting_lab.providers.odds_api import (
    API_KEY_ENV,
    OddsApiProvider,
    Spend,
    markets_fingerprint,
)
from cbb_betting_lab.reports import retention_probe as RP



def _load_script(name: str):
    """Import a `scripts/` entry point by path.

    `scripts/` is not a package and is not on `pythonpath`, and putting it there
    would change project configuration this module does not own. Loading by path
    also proves the entry points import with no side effects at all — no
    credential read, no directory created, no request made.
    """
    import importlib.util

    path = Path(CONFIG.REPO_ROOT) / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_probe_script_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = _load_script("run_retention_probe")
RERENDER = _load_script("rerender_retention_probe")


EASTERN = ZoneInfo("America/New_York")

#: Obviously not a credential, and asserted never to reach a record or a report.
FAKE_KEY = "not-a-real-credential-0000"

#: Six teams in three conferences whose measured non-conference margins place
#: them in the three tiers. Nothing here is a real programme.
TEAMS = {
    11: ("Alpha", 100),
    12: ("Bravo", 100),
    21: ("Charlie", 200),
    22: ("Delta", 200),
    31: ("Echo", 300),
    32: ("Foxtrot", 300),
}
CONFERENCE_STRENGTH = {100: 25.0, 200: 13.0, 300: 0.0}

#: A small, deliberately shaped key list. `spread_h1` is the market that carries
#: a featured key and an alternate ladder, which is the football lab's finding.
PROBE_KEYS = ("alternate_spreads_h1", "h2h", "spreads", "spreads_h1", "totals")


# ---------------------------------------------------------------------------
# Fixtures: a whole miniature season, built in a temporary directory
# ---------------------------------------------------------------------------


def _iso_utc(day: str, hour: int, minute: int = 0) -> str:
    local = datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00").replace(
        tzinfo=EASTERN
    )
    return local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%MZ")


def _side(prefix: str, team_id: int) -> dict:
    name, conference = TEAMS[team_id]
    return {
        f"{prefix}_id": team_id,
        f"{prefix}_conference_id": float(conference),
        f"{prefix}_location": name,
        f"{prefix}_name": "Aces",
        f"{prefix}_display_name": f"{name} Aces",
        f"{prefix}_short_display_name": name,
        f"{prefix}_abbreviation": name[:3].upper(),
    }


def _game(game_id: int, season: int, day: str, hour: int, home: int, away: int) -> dict:
    margin = CONFERENCE_STRENGTH[TEAMS[home][1]] - CONFERENCE_STRENGTH[TEAMS[away][1]]
    home_score = 70 + margin / 2.0
    away_score = 70 - margin / 2.0
    return {
        "game_id": game_id,
        "season": season,
        "date": _iso_utc(day, hour),
        "home_score": home_score,
        "away_score": away_score,
        **_side("home", home),
        **_side("away", away),
    }


def _prior_schedule(season: int) -> pd.DataFrame:
    """Cross-conference games only, enough of them to clear MINIMUM_GAMES."""
    rows = []
    game_id = season * 1000
    pairs = [
        (a, b)
        for a in TEAMS
        for b in TEAMS
        if TEAMS[a][1] != TEAMS[b][1] and a < b
    ]
    for repeat in range(2):
        for home, away in pairs:
            for first, second in ((home, away), (away, home)):
                game_id += 1
                rows.append(
                    _game(game_id, season, "2024-12-05", 19, first, second)
                    if repeat == 0
                    else _game(game_id, season, "2024-12-12", 19, first, second)
                )
    return pd.DataFrame(rows)


#: The probed season. One game per (tier, month, tip window) cell, so a draw of
#: one per stratum is balanced and a draw of two cannot be.
PROBE_GAMES = [
    # game_id, day, Eastern hour, home, away, expected tier, expected window
    (900001, "2025-11-15", 19, 11, 12, "high_major", "early_evening"),
    (900002, "2025-11-15", 14, 21, 22, "mid_major", "afternoon"),
    (900003, "2025-11-15", 22, 31, 32, "low_major", "late"),
    (900004, "2026-01-10", 19, 11, 31, "high_major", "early_evening"),
    (900005, "2026-01-10", 14, 21, 32, "mid_major", "afternoon"),
    (900006, "2026-01-10", 22, 32, 31, "low_major", "late"),
]


def _probe_schedule() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _game(game_id, 2026, day, hour, home, away)
            for game_id, day, hour, home, away, _, _ in PROBE_GAMES
        ]
    )


def _team_games(schedule: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in schedule.to_dict("records"):
        day = str(row["date"])[:10]
        for side, other in (("home", "away"), ("away", "home")):
            rows.append(
                {
                    "game_id": row["game_id"],
                    "season": row["season"],
                    "slate_date": day,
                    "team_id": row[f"{side}_id"],
                    "opponent_id": row[f"{other}_id"],
                    "home_away": side,
                    "game_state": "countable",
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def lab(tmp_path: Path) -> dict:
    """A processed table, three schedules, a tier table and a name index."""
    processed = tmp_path / "processed"
    raw = tmp_path / "raw" / CBB.data_dir_segment / "schedules"
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)

    probe_schedule = _probe_schedule()
    for season in (2024, 2025):
        _prior_schedule(season).to_parquet(raw / f"mbb_schedule_{season}.parquet")
    probe_schedule.to_parquet(raw / "mbb_schedule_2026.parquet")

    frame = _team_games(probe_schedule)
    # The slate day of a 22:00 Eastern tip is that Eastern date, so the fixture
    # writes the Eastern date rather than the UTC one the `date` column carries.
    frame["slate_date"] = [
        RP.datetime.fromisoformat(
            str(probe_schedule.set_index("game_id").loc[gid, "date"]).replace(
                "Z", "+00:00"
            )
        )
        .astimezone(CBB.timezone)
        .date()
        .isoformat()
        for gid in frame["game_id"]
    ]
    frame.to_csv(processed / "cbb_team_games.csv", index=False)

    team_games, schedule, tiers, index = RP.load_inputs(
        processed_dir=processed, raw_dir=tmp_path / "raw", season=2026
    )
    return {
        "processed_dir": processed,
        "raw_dir": tmp_path / "raw",
        "output_dir": tmp_path / "outputs",
        "team_games": team_games,
        "schedule": schedule,
        "tiers": tiers,
        "index": index,
        "tmp": tmp_path,
    }


def _plan(lab: dict, *, per_stratum: int = 1) -> RP.SamplePlan:
    candidates, _ = RP.candidate_events(
        lab["team_games"], lab["schedule"], lab["tiers"], season=2026
    )
    return RP.stratified_sample(candidates, events_per_stratum=per_stratum, seed=7)


# ---------------------------------------------------------------------------
# The fake archive. No socket is opened anywhere in this file.
# ---------------------------------------------------------------------------


class _Response:
    def __init__(self, payload, headers):
        self.status_code = 200
        self._payload = payload
        self.headers = headers

    def json(self):
        return self._payload


class FakeArchive:
    """A stand-in for the provider's historical endpoints.

    `quotes` maps a provider key to the books quoting it. Bills the way the real
    thing does — ten times unique markets **returned** times regions — so the
    cap tests exercise the same arithmetic the cap is enforced against.
    """

    def __init__(self, quotes: dict[str, list[str]], *, regions: int = 2):
        self.quotes = quotes
        self.regions = regions
        self.calls: list[str] = []
        self.remaining = 5_000_000

    def __call__(self, url, *, params, timeout):
        self.calls.append(url)
        if url.endswith("/v4/sports"):
            return _Response([], {"x-requests-remaining": str(self.remaining)})
        if url.endswith("/events"):
            listing = [
                {
                    "id": f"evt{game_id}",
                    "commence_time": _iso_utc(day, hour),
                    "home_team": f"{TEAMS[home][0]} Aces",
                    "away_team": f"{TEAMS[away][0]} Aces",
                }
                for game_id, day, hour, home, away, _, _ in PROBE_GAMES
            ]
            return _Response(
                {"timestamp": params.get("date"), "data": listing},
                {"x-requests-last": "1", "x-requests-remaining": str(self.remaining)},
            )
        asked = [k for k in str(params.get("markets", "")).split(",") if k]
        returned = {k: self.quotes[k] for k in asked if self.quotes.get(k)}
        payload = {
            "id": url.rsplit("/", 2)[-2],
            "bookmakers": [
                {
                    "key": book,
                    "markets": [
                        {
                            "key": key,
                            "outcomes": [
                                {"name": "Home", "price": -110},
                                {"name": "Away", "price": -110},
                            ],
                        }
                        for key, books in sorted(returned.items())
                        if book in books
                    ],
                }
                for book in sorted({b for books in returned.values() for b in books})
            ],
        }
        charged = 10 * len(returned) * self.regions
        self.remaining -= charged
        return _Response(
            {"timestamp": params.get("date"), "data": payload},
            {
                "x-requests-last": str(charged),
                "x-requests-remaining": str(self.remaining),
            },
        )


def _provider(archive: FakeArchive) -> OddsApiProvider:
    return OddsApiProvider(
        CBB, environment={API_KEY_ENV: FAKE_KEY}, requester=archive
    )


#: The football lab's shape, in miniature: the featured half-spread key is dead
#: across every event while its alternate ladder carries the same market.
DEFAULT_QUOTES = {
    "h2h": ["bookone", "booktwo", "bookthree"],
    "spreads": ["bookone", "booktwo"],
    "totals": [],
    "spreads_h1": [],
    "alternate_spreads_h1": ["bookone", "booktwo"],
}


def _run(lab: dict, *, quotes=None, cap: int = 100_000, **kwargs) -> tuple[dict, FakeArchive]:
    archive = FakeArchive(dict(DEFAULT_QUOTES if quotes is None else quotes))
    record = RP.probe(
        plan=_plan(lab),
        provider=_provider(archive),
        index=lab["index"],
        provider_keys=PROBE_KEYS,
        credit_cap=cap,
        cache_dir=lab["tmp"] / "cache",
        chunk_size=kwargs.pop("chunk_size", 2),
        generated_at="2026-09-01T00:00:00Z",
        **kwargs,
    )
    return record, archive


# ---------------------------------------------------------------------------
# 1. The dry run
# ---------------------------------------------------------------------------


def test_a_dry_run_makes_no_request_and_ends_by_saying_no_credit_was_spent(
    lab, capsys, monkeypatch
):
    """CI greps the last line for the phrase. Without --live nothing may move.

    The guard is deliberately blunt: `requests.get` is replaced with something
    that fails the test if it is called at all, and the credential is removed
    from the environment, so a dry run that quietly needed either one goes red.
    """
    import cbb_betting_lab.providers.odds_api as odds_api

    monkeypatch.delenv(API_KEY_ENV, raising=False)

    def _forbidden(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("A dry run reached the network.")

    monkeypatch.setattr(odds_api.requests, "get", _forbidden)

    exit_code = RUNNER.main(
        [
            "--processed-dir",
            str(lab["processed_dir"]),
            "--raw-dir",
            str(lab["raw_dir"]),
            "--output-dir",
            str(lab["output_dir"]),
        ]
    )
    printed = capsys.readouterr().out.strip().splitlines()

    assert exit_code == 0
    assert printed[-1].endswith(RP.NOTHING_WAS_SPENT), printed[-1]
    assert printed[-1] == (
        "Dry run. Nothing was requested, no credential was read, and "
        "no credit was spent"
    )
    assert not RP.record_path(CBB, lab["output_dir"]).exists()
    assert not RP.report_path(CBB, lab["output_dir"]).exists()


def test_a_dry_run_prints_the_bound_a_live_run_would_need(lab, capsys):
    """A cap set below the plan is the whole starvation failure. Say the number."""
    RUNNER.main(
        [
            "--processed-dir",
            str(lab["processed_dir"]),
            "--raw-dir",
            str(lab["raw_dir"]),
            "--output-dir",
            str(lab["output_dir"]),
            "--credit-cap",
            "10",
        ]
    )
    printed = capsys.readouterr().out
    assert "Pessimistic bound:" in printed
    assert "A live run would refuse to start" in printed
    assert printed.strip().splitlines()[-1].endswith(RP.NOTHING_WAS_SPENT)


# ---------------------------------------------------------------------------
# 2. The cache filename — the football lab's collision
# ---------------------------------------------------------------------------


def test_the_cache_filename_does_not_collide_for_two_different_chunks_of_one_length(
    lab,
):
    """The football lab tagged cached chunks with `len(chunk)`.

    Four ten-market chunks therefore wrote one filename, collided, and three of
    the four answers were lost without an error — the surviving file was a
    perfectly valid response to a real request. The length of a list is not its
    identity; its fingerprint is.
    """
    event = _plan(lab).events[0]
    first = tuple(f"market_{i}" for i in range(10))
    second = tuple(f"other_{i}" for i in range(10))
    third = tuple(f"market_{i}" for i in range(9)) + ("market_x",)

    paths = {
        RP.cache_path(Path("/cache"), event, chunk) for chunk in (first, second, third)
    }
    assert len(paths) == 3, (
        "Two different ten-market chunks share a cache filename. That is the "
        "football lab's defect exactly: three of four answers vanish and the "
        "survivor looks correct."
    )
    for chunk in (first, second, third):
        assert str(len(chunk)) not in RP.cache_path(Path("/cache"), event, chunk).name
        assert (
            markets_fingerprint(chunk)
            in RP.cache_path(Path("/cache"), event, chunk).name
        )


def test_the_same_chunk_in_any_order_reaches_the_same_cache_file(lab):
    """Otherwise a re-run pays again for an answer it already owns."""
    event = _plan(lab).events[0]
    forwards = ("spreads", "totals", "h2h")
    backwards = ("h2h", "totals", "spreads")
    assert RP.cache_path(Path("/c"), event, forwards) == RP.cache_path(
        Path("/c"), event, backwards
    )


def test_two_events_never_share_a_cache_file_for_the_same_chunk(lab):
    events = _plan(lab).events
    chunk = ("h2h", "spreads")
    assert RP.cache_path(Path("/c"), events[0], chunk) != RP.cache_path(
        Path("/c"), events[1], chunk
    )


# ---------------------------------------------------------------------------
# 3. Retention rolls up to the market, never the provider key
# ---------------------------------------------------------------------------


def test_retention_rolls_up_to_the_market_not_the_provider_key(lab):
    """A dead featured key beside a live ladder is a RETAINED market.

    The football lab's probe found three featured prop keys returning nothing
    across all twenty of its probed events while the matching alternate ladders
    carried the same market on the same events. Read per key that is three
    unmeasurable markets; read per market — the unit that gets modelled,
    measured, approved and carded — it is none.
    """
    record, _ = _run(lab)
    by_market = {entry["market"]: entry for entry in record["markets"]}

    half_spread = by_market["spread_h1"]
    assert set(half_spread["provider_keys"]) == {"spreads_h1", "alternate_spreads_h1"}
    assert half_spread["verdict"] == RP.Retention.RETAINED_AND_MEASURABLE.value, (
        "`spreads_h1` returned nothing on every event and "
        "`alternate_spreads_h1` returned on every event. Per key that reads as "
        "a dead market; per market it is retained, and the market is the unit "
        "that gets modelled and approved."
    )
    assert half_spread["events_priced"] == half_spread["events_fully_asked"] > 0

    per_key = {entry["provider_key"]: entry for entry in record["provider_keys_detail"]}
    assert per_key["spreads_h1"]["events_asked"] > 0
    assert per_key["spreads_h1"]["events_priced"] == 0, (
        "The per-key detail must still show the dead key. It is how the key "
        "gets noticed and fixed; it is simply not the verdict."
    )
    assert per_key["alternate_spreads_h1"]["events_priced"] > 0

    report = RP.render(record)
    assert "Per provider key — detail, not a verdict" in report
    assert "`spreads_h1` — nothing on" in report


def test_a_market_with_one_dead_key_and_one_live_key_is_never_not_retained():
    """The rollup rule on its own, with no fetch anywhere near it."""
    observations = {
        1: {"alternate_spreads_h1": RP.KeyObservation(rows=8, books={"a", "b"})},
        2: {"alternate_spreads_h1": RP.KeyObservation(rows=8, books={"a", "b"})},
    }
    asked = {1: {"spreads_h1", "alternate_spreads_h1"}, 2: {"spreads_h1", "alternate_spreads_h1"}}
    rolls = RP.roll_up_to_markets(
        observations,
        asked,
        event_tier={1: "low_major", 2: "low_major"},
        provider_keys=("spreads_h1", "alternate_spreads_h1"),
    )
    assert rolls["spread_h1"].verdict() is RP.Retention.RETAINED_AND_MEASURABLE


def test_a_market_no_key_returned_anything_for_is_not_retained_and_is_not_a_pass(lab):
    record, _ = _run(lab)
    by_market = {entry["market"]: entry for entry in record["markets"]}
    assert by_market["total_points"]["verdict"] == RP.Retention.NOT_RETAINED.value
    assert by_market["total_points"]["events_fully_asked"] > 0


def test_the_report_never_calls_an_unquoted_market_a_pass_or_an_avoid(lab):
    """An excluded market is never a pass, an avoid, or a no-value call.

    Those are claims about a bet, and this probe never priced one. The single
    sentence allowed to use those words is the one saying they do not apply, so
    it is excised by name before the report is scanned — which also means the
    sentence cannot quietly disappear without this test noticing.
    """
    record, _ = _run(lab)
    report = RP.render(record)
    assert RP.NOT_A_BET_DISCLAIMER in report
    scanned = report.replace(RP.NOT_A_BET_DISCLAIMER, "").casefold()
    for forbidden in ("avoid", "no value", "no-value", "fade", "stay away", "a pass"):
        assert forbidden not in scanned, (
            f"The report described a market as {forbidden!r}."
        )
    assert "returned no price" in scanned


def test_one_book_is_never_enough_to_call_a_market_measurable():
    """`best_price_per_wager` collapses to the best of several books.

    With one book that collapse is a no-op and the optimistic and pessimistic
    brackets in `stores.py` become the same number, which is the bracket that
    says whether an edge survives price selection.
    """
    observations = {i: {"h2h": RP.KeyObservation(rows=2, books={"only"})} for i in range(10)}
    rolls = RP.roll_up_to_markets(
        observations,
        {i: {"h2h"} for i in range(10)},
        event_tier={i: "low_major" for i in range(10)},
        provider_keys=("h2h",),
    )
    roll = rolls["moneyline"]
    assert roll.share == 1.0
    assert roll.verdict() is RP.Retention.RETAINED_BUT_THIN
    assert RP.MEASURABLE_BOOK_FLOOR == 2


# ---------------------------------------------------------------------------
# 4. The report re-renders from the record
# ---------------------------------------------------------------------------


def test_the_report_re_renders_byte_identically_from_the_run_record(lab, capsys):
    """Improving a sentence must never cost credits twice.

    The football lab's probe cost 7,280 credits and its report could only be
    regenerated by re-running it. Here the record is the artefact and `render`
    is a pure function of it.
    """
    record, archive = _run(lab)
    output_dir = lab["output_dir"]
    record_file = RP.write_record(record, RP.record_path(CBB, output_dir))
    report_file = RP.write_report(record, RP.report_path(CBB, output_dir))
    original = report_file.read_bytes()

    calls_before = len(archive.calls)
    rerendered = lab["tmp"] / "again.md"
    assert (
        RERENDER.main(
            [
                "--record",
                str(record_file),
                "--report",
                str(rerendered),
            ]
        )
        == 0
    )
    assert rerendered.read_bytes() == original, (
        "The report is supposed to be a pure function of the run record. A "
        "clock, a network call or an unsorted dict has got into `render`."
    )
    assert len(archive.calls) == calls_before, "Re-rendering reached the provider."
    printed = capsys.readouterr().out
    assert printed.strip().splitlines()[-1].endswith(RP.NOTHING_WAS_SPENT)

    # And the --check mode catches a report edited by hand, which is the other
    # way a generated file and its record drift apart.
    assert RERENDER.main(["--record", str(record_file), "--report", str(report_file)]) == 0
    report_file.write_text(original.decode("utf-8") + "\nhand edited\n", encoding="utf-8")
    assert (
        RERENDER.main(
            ["--record", str(record_file), "--report", str(report_file), "--check"]
        )
        == 1
    )


def test_the_renderer_refuses_a_record_from_a_different_schema(lab):
    """A report with silently missing sections is worse than no report."""
    record, _ = _run(lab)
    record["schema_version"] = RP.RECORD_SCHEMA_VERSION + 1
    with pytest.raises(RP.ProbeError):
        RP.render(record)


def test_re_rendering_a_missing_record_says_so_rather_than_writing_an_empty_report(
    lab, capsys
):
    assert RERENDER.main(["--record", str(lab["tmp"] / "nope.json"), "--report", str(lab["tmp"] / "out.md")]) == 2
    assert not (lab["tmp"] / "out.md").exists()


# ---------------------------------------------------------------------------
# 5. The cap, and starvation that cannot masquerade as absence
# ---------------------------------------------------------------------------


def test_the_cap_refuses_a_request_that_would_breach_it(lab):
    """Checked before the request, against the measured running total.

    The NHL lab's purchase was capped at 200,000 and spent 289,984 because it
    estimated from markets *asked* while the provider bills per market
    *returned*. Here the guard bounds the next request pessimistically and adds
    it to what `x-requests-last` says has already gone.
    """
    archive = FakeArchive(dict(DEFAULT_QUOTES))
    # 45 buys the slate listing (1) and the first chunk (40) of the first event
    # and cannot bound the second, so `spreads` and `totals` are never asked.
    record = RP.probe(
        plan=_plan(lab),
        provider=_provider(archive),
        index=lab["index"],
        provider_keys=PROBE_KEYS,
        credit_cap=45,
        cache_dir=lab["tmp"] / "cache",
        chunk_size=2,
        allow_partial=True,
        generated_at="2026-09-01T00:00:00Z",
    )
    assert record["completed"] is False
    assert "cap" in record["stopped_because"]
    assert record["credits_spent"] <= record["credit_cap"], (
        "The run spent more than its cap. That is the NHL lab's 289,984 "
        "against 200,000, reproduced."
    )

    verdicts = {entry["market"]: entry["verdict"] for entry in record["markets"]}
    assert verdicts["spread"] == RP.Retention.NOT_PROBED.value, (
        "A starved run must leave the markets it never reached as NOT_PROBED. "
        "The NHL lab's probe reported its own starvation as market absence."
    )
    assert verdicts["total_points"] == RP.Retention.NOT_PROBED.value
    assert RP.Retention.NOT_RETAINED.value not in verdicts.values(), (
        "Nothing was asked often enough to establish an absence, so nothing "
        "may claim one."
    )
    assert verdicts["spread_h1"] == RP.Retention.RETAINED_BUT_THIN.value, (
        "One of this market's two keys was asked and priced. That establishes "
        "retention and cannot establish a share, so it cannot be measurable."
    )
    for entry in record["markets"]:
        if entry["verdict"] == RP.Retention.NOT_RETAINED.value:
            assert entry["events_fully_asked"] > 0, (
                "NOT_RETAINED was reported for a market no event finished "
                "asking about."
            )

    report = RP.render(record)
    assert "This run did not complete" in report
    assert "NOT_PROBED" in report


def test_a_cap_below_the_plans_bound_refuses_to_start_at_all(lab):
    """Without --allow-partial the run does not begin.

    A cap below the plan's pessimistic bound is a cap that starves it, and a
    starved fetch and an unquoted market look identical in the reports.
    """
    archive = FakeArchive(dict(DEFAULT_QUOTES))
    with pytest.raises(RP.ProbeError) as raised:
        RP.probe(
            plan=_plan(lab),
            provider=_provider(archive),
            index=lab["index"],
            provider_keys=PROBE_KEYS,
            credit_cap=10,
            cache_dir=lab["tmp"] / "cache",
        )
    assert "starves" in str(raised.value)
    assert archive.calls == [], "It reached the provider before refusing."


def test_a_market_that_was_never_asked_is_never_called_not_retained():
    """The class exists so that this conflation is impossible to express."""
    rolls = RP.roll_up_to_markets(
        {}, {}, event_tier={}, provider_keys=("h2h", "spreads")
    )
    assert rolls["moneyline"].verdict() is RP.Retention.NOT_PROBED
    assert RP.Retention.NOT_PROBED.value not in RP.VERDICT_PROSE[
        RP.Retention.NOT_RETAINED.value
    ]


def test_the_report_always_states_the_cap_the_spend_and_whether_it_completed(lab):
    """A starved fetch and an unquoted market look identical. Print all three."""
    record, _ = _run(lab)
    report = RP.render(record)
    assert "| Credit cap |" in report
    assert "| Credits actually spent |" in report
    assert "| Pessimistic bound of the plan |" in report
    assert "| Run completed |" in report
    assert f"{record['credit_cap']:,}" in report
    assert f"{record['credits_spent']:,}" in report


def test_the_measured_total_and_not_the_estimate_is_what_was_reported(lab):
    """`x-requests-last` is the truth; the multiplier is only a bound."""
    record, _ = _run(lab)
    assert record["credits_spent"] > 0
    assert record["credits_spent"] < record["credits_estimated"], (
        "Every asked-for market returned, so the measured spend equalled the "
        "estimate. The fixture is supposed to leave some markets unquoted, "
        "which is exactly the gap the report reads as information."
    )
    assert record["credits_spent"] <= record["pessimistic_bound"]


# ---------------------------------------------------------------------------
# 6. The stratification, reported rather than assumed
# ---------------------------------------------------------------------------


def test_the_sample_is_stratified_by_tier_month_and_tip_window(lab):
    plan = _plan(lab)
    cells = {tuple(s["stratum"].split("|")) for s in plan.strata}
    assert len(cells) == len(PROBE_GAMES)
    assert {c[0] for c in cells} == {"high_major", "mid_major", "low_major"}
    assert {c[1] for c in cells} == {"2025-11", "2026-01"}
    assert {c[2] for c in cells} == {"afternoon", "early_evening", "late"}
    expected = {
        game_id: (tier, window)
        for game_id, _, _, _, _, tier, window in PROBE_GAMES
    }
    for event in plan.events:
        assert (event.tier, event.window) == expected[event.game_id]


def test_an_unbalanced_draw_reports_itself_as_unbalanced(lab):
    """An unbalanced probe that reports itself as balanced is worse than none."""
    balanced = _plan(lab, per_stratum=1)
    assert balanced.balanced

    # A cell that cannot supply the target is still short. That the shortfall
    # was unavoidable is a reason, not a licence to call the design balanced.
    exhausted = _plan(lab, per_stratum=2)
    assert not exhausted.balanced
    assert len(exhausted.underfilled) == len(PROBE_GAMES)
    assert all(s["exhausted"] for s in exhausted.underfilled)

    # And a truncated plan is short for the other reason: the cells it dropped.
    candidates, _ = RP.candidate_events(
        lab["team_games"], lab["schedule"], lab["tiers"], season=2026
    )
    truncated = RP.stratified_sample(candidates, events_per_stratum=1, seed=7, max_events=3)
    assert len(truncated.events) == 3
    assert not truncated.balanced
    assert len(truncated.underfilled) == len(PROBE_GAMES) - 3
    assert not any(s["exhausted"] for s in truncated.underfilled)

    record = RP.dry_run_record(
        competition=CBB,
        plan=truncated,
        keys=PROBE_KEYS,
        chunk_size=2,
        credit_cap=1_000,
        regions="us,us2",
        sport_key=CBB.provider_sport_key,
    )
    report = RP.render(record)
    assert "NOT balanced" in report
    assert "⚠" in report

    exhausted_report = RP.render(
        RP.dry_run_record(
            competition=CBB,
            plan=exhausted,
            keys=PROBE_KEYS,
            chunk_size=2,
            credit_cap=1_000,
            regions="us,us2",
            sport_key=CBB.provider_sport_key,
        )
    )
    assert "the cell holds no more" in exhausted_report


def test_a_game_whose_tip_carries_no_timezone_is_excluded_and_counted(lab):
    """Guessing a zone moves a game by hours, and therefore into another cell."""
    schedule = lab["schedule"].copy()
    schedule.loc[0, "date"] = "2026-01-10 19:00:00"
    candidates, census = RP.candidate_events(
        lab["team_games"], schedule, lab["tiers"], season=2026
    )
    assert census["tip_time_carried_no_timezone"] == 1
    assert len(candidates) == len(PROBE_GAMES) - 1


@pytest.mark.parametrize(
    "hour,expected",
    [
        (11, "afternoon"),
        (16, "afternoon"),
        (17, "early_evening"),
        (20, "early_evening"),
        (21, "late"),
        (23, "late"),
        (1, "late"),
    ],
)
def test_the_tip_windows_split_where_the_measured_distribution_does(hour, expected):
    """A 20:00 Honolulu tip is 01:00 Eastern and is a late game, not an early one."""
    assert RP.tip_window(_iso_utc("2026-01-10", hour), CBB) == expected


def test_a_game_takes_the_higher_of_its_two_sides_tiers(lab):
    """A low-major visiting a high-major is priced as a high-major game.

    Which is what makes the low-major cell mean *both sides are low-major* —
    the end of the board this lab was built to look at.
    """
    tiers = lab["tiers"]
    assert RP.game_tier(11, 31, tiers) == "high_major"
    assert RP.game_tier(31, 11, tiers) == "high_major"
    assert RP.game_tier(31, 32, tiers) == "low_major"


def test_the_tier_table_never_looks_at_the_season_being_probed(lab):
    """Walk-forward, like everything else."""
    assert lab["tiers"].seasons == (2024, 2025)
    assert 2026 not in lab["tiers"].seasons


# ---------------------------------------------------------------------------
# 7. Joins, credentials and the things that must never be guessed
# ---------------------------------------------------------------------------


def test_a_game_that_cannot_be_matched_is_never_scored_as_a_missing_price(lab):
    """A school this lab cannot spell is not a market the provider drops."""

    class Unrecognisable(FakeArchive):
        def __call__(self, url, *, params, timeout):
            if url.endswith("/events"):
                return _Response(
                    {"data": [{"id": "x", "home_team": "Nowhere State",
                               "away_team": "Elsewhere Tech"}]},
                    {"x-requests-last": "1"},
                )
            return super().__call__(url, params=params, timeout=timeout)

    archive = Unrecognisable(dict(DEFAULT_QUOTES))
    record = RP.probe(
        plan=_plan(lab),
        provider=_provider(archive),
        index=lab["index"],
        provider_keys=PROBE_KEYS,
        credit_cap=100_000,
        cache_dir=lab["tmp"] / "cache",
        chunk_size=2,
        generated_at="2026-09-01T00:00:00Z",
    )
    assert len(record["unmatched_events"]) == len(PROBE_GAMES)
    for entry in record["markets"]:
        assert entry["events_fully_asked"] == 0
        assert entry["verdict"] == RP.Retention.NOT_PROBED.value, (
            "An unmatched game must sit in no denominator. Scoring it as a "
            "missing price turns a name this lab cannot resolve into a market "
            "the provider does not retain."
        )
    assert "in no denominator anywhere" in RP.render(record)


def test_no_credential_reaches_the_run_record_or_the_report(lab):
    record, _ = _run(lab)
    serialised = json.dumps(record)
    assert FAKE_KEY not in serialised
    assert "apiKey" not in serialised
    assert FAKE_KEY not in RP.render(record)


def test_the_cached_raw_responses_are_reused_rather_than_bought_twice(lab):
    """Bought evidence cannot be re-derived for free. Ask once."""
    record, archive = _run(lab)
    first_calls = len(archive.calls)
    assert record["credits_spent"] > 0

    second, archive_two = _run(lab)
    assert archive_two.calls == [], "A cached run reached the provider again."
    assert second["credits_spent"] == 0
    assert second["responses_served_from_cache"] > 0
    assert first_calls > 0
    # And the answer is the same one, market for market.
    assert {e["market"]: e["verdict"] for e in second["markets"]} == {
        e["market"]: e["verdict"] for e in record["markets"]
    }


def test_a_market_present_with_no_outcomes_is_not_counted_as_a_price():
    """An empty shell is not retention."""
    payload = {
        "bookmakers": [
            {"key": "bookone", "markets": [{"key": "h2h", "outcomes": []}]},
            {"key": "booktwo", "markets": [{"key": "spreads", "outcomes": [{"name": "A"}]}]},
        ]
    }
    counted = RP.count_payload(payload)
    assert "h2h" not in counted
    assert counted["spreads"].rows == 1


def test_the_probe_refuses_a_season_the_archive_cannot_answer_for(lab):
    """Otherwise it measures the archive's start date and calls it absence."""
    events = _plan(lab).events
    old = tuple(
        RP.ProbeEvent(**{**event.to_json(), "slate_date": "2021-12-01"})
        for event in events
    )
    with pytest.raises(RP.ProbeError) as raised:
        RP.guard_history_window(old, PROBE_KEYS)
    assert RP.ADDITIONAL_HISTORY_FROM in str(raised.value)
    # Featured markets reach back further, so the same games are fine for them.
    RP.guard_history_window(old, ("h2h", "spreads", "totals"))


def test_the_declared_thresholds_are_in_the_module_and_in_the_report(lab):
    """Declared in advance, and printed beside every number they judge."""
    assert RP.MEASURABLE_EVENT_SHARE == 0.50
    assert RP.MEASURABLE_BOOK_FLOOR == 2
    record, _ = _run(lab)
    assert record["thresholds"]["measurable_event_share"] == RP.MEASURABLE_EVENT_SHARE
    assert record["thresholds"]["measurable_book_floor"] == RP.MEASURABLE_BOOK_FLOOR
    report = RP.render(record)
    assert "Measurable, declared in advance:" in report
    assert "50.0%" in report


def test_every_reported_share_carries_its_denominator(lab):
    """No number in this lab is printed without its sample size."""
    record, _ = _run(lab)
    report = RP.render(record)
    for entry in record["markets"]:
        if entry["events_fully_asked"]:
            needle = f"{entry['events_priced']}/{entry['events_fully_asked']}"
            assert needle in report, f"{entry['market']} printed a share without its n."


def test_book_coverage_is_reported_by_conference_tier(lab):
    """The most decision-relevant number this probe can produce for this lab."""
    record, _ = _run(lab)
    tiers = {entry["tier"] for entry in record["book_coverage_by_tier"]}
    assert tiers == {"high_major", "mid_major", "low_major"}
    for entry in record["book_coverage_by_tier"]:
        assert entry["events_probed"] > 0
        assert entry["mean_books_per_event"] > 0
    report = RP.render(record)
    assert "Which books appear, and where" in report
    assert "Mean books/event" in report
    for book in ("bookone", "booktwo", "bookthree"):
        assert f"`{book}`" in report


def test_every_wired_provider_key_in_the_probed_tiers_is_actually_asked_for():
    """A key silently absent from the plan reads later as an absent market."""
    keys = set(RP.probe_provider_keys((1, 2, 3)))
    for market in M.MARKETS:
        if market.tier <= 3:
            assert set(market.provider_keys) <= keys, (
                f"{market.key} has a provider key the probe never asks for, so "
                "its retention could never be established."
            )
    assert not any(
        key in keys for market in M.markets_in_tier(4) for key in market.provider_keys
    ), "Futures are a different sport key and are not per-event."


def test_the_spend_object_charges_the_pessimistic_bound_when_the_header_is_missing():
    """Guessing low lets a run drift past its cap while reporting that it has not."""
    spend = Spend()
    charged = spend.record({}, fallback=160)
    assert charged == 160
    assert spend.credits_spent == 160
    assert spend.notes
