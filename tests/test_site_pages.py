"""The site pages beside the board: Game, Season, Record, All results, Methods.

What this file holds:

* The board carries, per priced game, the card's steps (`factors`) ending at
  the published win chance, both teams' ratings, tiers and home court; a game
  the model refused carries none of them and never a pass.
* The card's recorded selections publish as `bet`; a frozen opinion the card
  did not select publishes as `pass` with no units.
* `season.json` and `ratings.json` are built from the fit the board priced on,
  and project the games still to play.
* `record.json` and `tracker.json` are built from frozen boards and their
  finals, with the shapes the pages read, and the JSON refuses NaN.
* Every new page loads the shared runtime and libraries, is a CBB page, and
  names no reference site; nor does any feed, builder or sample.
* Publish Board builds the feeds and lists the pages in `site.json`, which is
  how the shared tab strip learns they exist.

Everything runs on the fixture lab with the connectivity refusal lifted,
because 800 team-game rows cannot connect the games graph; nothing asks the
network or a credential.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
import yaml

from cbb_betting_lab.models import ratings as R

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB = PROJECT_ROOT / "web"
REAL_DATA = PROJECT_ROOT / "tests" / "fixtures" / "real_data"
PAGES = ("Game.dc.html", "Season.dc.html", "Record.dc.html", "Tracker.dc.html", "Methods.dc.html")
FEEDS = ("record.json", "tracker.json", "tracker_empty.json", "season.json", "ratings.json")
#: Reference sites the pages must never name; the lab's docs name the source.
REFERENCE_SITES = ("kenpom", "barttorvik", "torvik", "haslametrics", "evanmiya", "sagarin", "teamrankings")
DAY = date(2026, 2, 21)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lab(tmp_path_factory):
    root = tmp_path_factory.mktemp("lab")
    (root / "data" / "raw" / "cbb" / "schedules").mkdir(parents=True)
    (root / "data" / "processed").mkdir(parents=True)
    for p in REAL_DATA.glob("mbb_schedule_*.parquet"):
        shutil.copy(p, root / "data" / "raw" / "cbb" / "schedules" / p.name)
    for name in ("cbb_team_games.csv", "cbb_player_games.csv", "cbb_game_segments.csv"):
        shutil.copy(REAL_DATA / name, root / "data" / "processed" / name)
    return root


def _slate() -> list[dict]:
    """Games on DAY whose two teams the 800-row fixture knows best."""
    schedule = pd.read_parquet(REAL_DATA / "mbb_schedule_2026.parquet")
    schedule["d"] = pd.to_datetime(schedule["game_date"], errors="coerce", utc=True).dt.date
    logs = pd.read_csv(REAL_DATA / "cbb_team_games.csv")
    counts = logs[logs["slate_date"] < DAY.isoformat()].groupby("team_id").size()
    day = schedule[schedule["d"] == DAY].copy()
    day["hn"] = day["home_id"].astype(int).map(counts).fillna(0)
    day["an"] = day["away_id"].astype(int).map(counts).fillna(0)
    day = day[(day["hn"] >= 3) & (day["an"] >= 2)].head(5)
    assert len(day) >= 3, "the fixture lost the games this test prices"
    out = []
    for r in day.to_dict("records"):
        out.append({
            "id": str(r["id"]), "tip": str(r.get("date") or ""), "venue": "", "city": "", "tv": "",
            "neutral": bool(r["neutral_site"]), "state": "pre",
            "home": {"name": r["home_display_name"], "abbr": r["home_abbreviation"], "record": "0–0", "color": ""},
            "away": {"name": r["away_display_name"], "abbr": r["away_abbreviation"], "record": "0–0", "color": ""},
        })
    return out


@pytest.fixture(scope="module")
def built(lab):
    """The board, the builder module and the fit, priced once for the module."""
    before = R.MAX_EFFECTIVE_RESISTANCE
    R.MAX_EFFECTIVE_RESISTANCE = 1e9  # the fixture cannot connect the graph; the refusal is tested elsewhere
    try:
        builder = _load(WEB / "build_board_json.py", "test_site_pages_builder")
        slate = _slate()
        builder.slate_for = lambda d: slate
        board = builder.build(lab, DAY)
    finally:
        R.MAX_EFFECTIVE_RESISTANCE = before
    return builder, board, dict(builder._SIDE)


def test_a_priced_game_carries_its_steps_ending_at_the_published_chance(built):
    _, board, _ = built
    priced = [g for g in board["games"] if g.get("factors")]
    assert priced, "the fixture priced nothing, so there is nothing to show"
    for g in priced:
        keys = [f["key"] for f in g["factors"]]
        assert keys == ["strength", "home_court", "form", "rest", "lineup", "second_opinion"]
        assert g["factors"][-1]["homeWin"] == pytest.approx(g["home"]["winProb"], abs=5e-4)
        assert g["factors"][0]["delta"] == pytest.approx(g["factors"][0]["homeWin"] - 0.5, abs=1e-6)
        for f in g["factors"]:
            assert all(math.isfinite(f[k]) for k in ("homeWin", "delta", "homePts", "awayPts", "possessions"))
        for side in ("home", "away"):
            s = g["ratings"][side]
            assert set(s) >= {"offence", "defence", "net", "tempo", "tier", "form", "restDays", "restBucket", "missing", "lineupFactor", "secondOpinion"}
            assert s["net"] == pytest.approx(s["offence"] - s["defence"], abs=0.02)
        assert set(g["tiers"]) == {"home", "away"}
        assert set(g["homeCourt"]) == {"tierMargin", "departure", "appliedBy"}


def test_a_refused_game_carries_no_steps_and_is_not_a_pass(built):
    _, board, _ = built
    refused = [g for g in board["games"] if g["home"].get("winProb") is None]
    assert refused, "the fixture refused nothing; pick a thinner slate"
    for g in refused:
        assert g.get("factors") is None and g.get("ratings") is None
        assert g.get("pick") is None, "a game with no opinion is never a pass"


def test_the_cards_selection_is_a_bet_and_a_frozen_opinion_is_a_pass(built):
    builder, _, _ = built
    frozen = [
        {"market": "spread", "selection": "home", "line": -3.5, "american_odds": -110, "book": "b", "model_probability": 0.55, "edge": 0.02, "home_team": "ND", "away_team": "NOVA"},
        {"market": "total_points", "selection": "over", "line": 140.5, "american_odds": -105, "book": "b", "model_probability": 0.56, "edge": 0.04, "home_team": "ND", "away_team": "NOVA"},
    ]
    chosen = [{**frozen[0], "tier": "high_major"}]
    bet = builder.pick_from_frozen(frozen, "ND", "NOVA", chosen)
    assert bet["kind"] == "bet" and bet["units"] == 1.0 and bet["market"].lower() == "spread"
    opinion = builder.pick_from_frozen(frozen, "ND", "NOVA", [])
    assert opinion["kind"] == "pass" and opinion["units"] is None
    assert opinion["market"].lower().startswith("total"), "the pass is the frozen opinion with the most edge"


def test_the_card_state_records_its_selections():
    source = (PROJECT_ROOT / "scripts" / "run_gameday_card.py").read_text(encoding="utf-8")
    assert '"selections": [dict(row) for row in run.selections]' in source


def test_season_and_ratings_pages_are_built_from_the_fit(built, lab, tmp_path):
    _, board, fit = built
    assert fit, "the builder kept no fit for the pages"
    site_pages = _load(WEB / "site_pages.py", "test_site_pages_feeds")
    before = R.MAX_EFFECTIVE_RESISTANCE
    R.MAX_EFFECTIVE_RESISTANCE = 1e9
    try:
        written = site_pages.write_model_pages(lab, tmp_path, DAY, fit, board)
    finally:
        R.MAX_EFFECTIVE_RESISTANCE = before
    assert written == ["ratings.json", "season.json"]
    ratings = json.loads((tmp_path / "ratings.json").read_text(encoding="utf-8"))
    assert ratings["rated"] == len(ratings["teams"]) > 100
    assert [t["rank"] for t in ratings["teams"]] == list(range(1, len(ratings["teams"]) + 1))
    assert ratings["teams"][0]["net"] >= ratings["teams"][-1]["net"]
    assert any(t.get("tonight") for t in ratings["teams"]), "tonight's teams are flagged"
    assert set(ratings["league"]) == {"efficiency", "tempo", "marginSd"} and ratings["league"]["marginSd"] > 0
    season = json.loads((tmp_path / "season.json").read_text(encoding="utf-8"))
    assert season["phase"] == "regular" and season["played"] > 0
    assert season["remaining"] > 0 and 0 < season["projected"] <= season["remaining"]
    assert season["conferences"], "conferences are grouped"
    team = season["conferences"][0]["teams"][0]
    assert set(team) >= {"abbr", "name", "tier", "net", "record", "confRecord", "projConf", "projOverall", "remaining", "confRemaining", "projRank"}
    assert team["projRank"] == 1
    for c in season["conferences"]:
        for t in c["teams"]:
            assert t["projOverall"]["w"] + 1e-6 >= t["record"]["w"], "projected wins include the wins already banked"
            assert t["projOverall"]["w"] + t["projOverall"]["l"] <= t["record"]["w"] + t["record"]["l"] + t["remaining"] + 1e-6, "a game the model could not price adds nothing"


def _frozen_board(day: date, teams: dict) -> dict:
    games = [
        {"id": "9001", "tip": f"{day.isoformat()}T23:00:00Z", "neutral": False, "home": {"abbr": "ND", "winProb": 0.64, "projPts": 74.8}, "away": {"abbr": "NOVA", "winProb": 0.36, "projPts": 70.4},
         "moneyline": {"open": {"home": -150, "away": 130}, "current": {"home": -160, "away": 140}, "fair": {"home": -178, "away": 142}},
         "spread": {"open": -3.5, "current": -4.0, "proj": -4.4, "homePrice": -110, "coverProb": 0.53}, "total": {"open": 144.5, "current": 145.0, "proj": 145.2, "overPrice": -110, "overProb": 0.51},
         "tiers": {"home": "high_major", "away": "high_major"},
         "pick": {"kind": "bet", "market": "Moneyline", "label": "Notre Dame ML", "price": -160, "book": "DraftKings", "tier": "high_major", "units": 1.0, "edgePct": 4.1, "side": "home", "line": None}},
        {"id": "9002", "tip": f"{day.isoformat()}T23:30:00Z", "neutral": True, "home": {"abbr": "KU", "winProb": 0.41, "projPts": 70.0}, "away": {"abbr": "DUKE", "winProb": 0.59, "projPts": 73.0},
         "moneyline": {"open": {"home": 120, "away": -140}, "current": {"home": 125, "away": -145}, "fair": {"home": 144, "away": -144}},
         "spread": {"open": 3.0, "current": 3.5, "proj": 3.0, "homePrice": -110, "coverProb": 0.52}, "total": {"open": 142.5, "current": 143.0, "proj": 143.0, "overPrice": -110, "overProb": 0.5},
         "tiers": {"home": "high_major", "away": "mid_major"},
         "pick": {"kind": "pass", "market": "Spread", "label": "Kansas +3.5", "price": -110, "book": "FanDuel", "tier": "high_major", "units": None, "edgePct": 0.4, "side": "home", "line": 3.5}},
    ]
    return {"generatedAt": f"{day.isoformat()}T14:05:00Z", "slateDate": day.isoformat(), "cardSlot": "morning", "teams": teams, "games": games, "lineHistory": {}}


def test_record_and_tracker_pages_are_built_from_frozen_boards_and_finals(tmp_path):
    site_pages = _load(WEB / "site_pages.py", "test_site_pages_record")
    teams = {"ND": {"name": "Notre Dame", "short": "Notre Dame"}, "NOVA": {"name": "Villanova", "short": "Villanova"}, "KU": {"name": "Kansas", "short": "Kansas"}, "DUKE": {"name": "Duke", "short": "Duke"}}
    day = date(2026, 11, 14)
    hist = tmp_path / "history"
    (hist / "finals").mkdir(parents=True)
    (hist / f"{day.isoformat()}_morning.json").write_text(json.dumps(_frozen_board(day, teams)), encoding="utf-8")
    (hist / "finals" / f"{day.isoformat()}.json").write_text(json.dumps({"9001": {"home": 78, "away": 70, "finish": "REG"}, "9002": {"home": 66, "away": 71, "finish": "OT"}}), encoding="utf-8")
    summary = site_pages.write_record_pages(tmp_path, day + timedelta(days=1), fetch=False)
    assert summary == {"games": 2, "nights": 1, "bets": 1, "opinions": 1}
    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record["games"] == 2 and record["through"] == day.isoformat()
    assert sum(b["games"] for b in record["buckets"]) == 2
    assert set(record["byTier"]) == {"High major"}, "a game is filed under the higher tier, by its label"
    assert record["brier"]["games"] == 2 and 0 < record["brier"]["model"] < 0.25
    assert record["markets"]["spread"]["games"] == 2 and record["markets"]["total"]["games"] == 2
    assert record["movement"] == {"toward": 1, "against": 0, "flat": 0, "picks": 1}, "ND shortened from -150 to -160: toward the pick"
    tracker = json.loads((tmp_path / "tracker.json").read_text(encoding="utf-8"))
    assert tracker["overall"] == {"w": 1, "l": 0, "p": 0, "bets": 1, "staked": 1.0, "units": 0.62, "returnPct": 62.0}, "tallies are rounded to the cent; the row keeps 0.625"
    assert tracker["opinions"]["overall"]["bets"] == 1 and tracker["opinions"]["overall"]["staked"] == 0.0
    kinds = {r["kind"]: r for r in tracker["rows"]}
    assert kinds["bet"]["result"] == "win" and kinds["bet"]["units"] == 0.625 and kinds["bet"]["team"] == "ND"
    assert kinds["pass"]["result"] == "loss" and kinds["pass"]["units"] is None and kinds["pass"]["staked"] == 0.0, "Kansas +3.5 lost by 5"
    assert kinds["bet"]["final"] == "NOVA 70, ND 78"
    assert [m["key"] for m in tracker["byMarket"]] == ["Moneyline"]
    assert tracker["byTier"][0]["key"] == "high_major", "the card's own tier spelling"
    for name in ("record.json", "tracker.json"):
        assert "NaN" not in (tmp_path / name).read_text(encoding="utf-8")


def test_the_settled_night_keeps_its_graded_games():
    settle = _load(WEB / "settle_results.py", "test_site_pages_settle")
    night = settle.night_record({"games": [{"id": "1", "home": {"final": 1}, "away": {"final": 0}}], "summary": {"w": 1}})
    assert night["graded"] == [{"id": "1", "home": {"final": 1}, "away": {"final": 0}}] and night["games"] == 1 and night["summary"] == {"w": 1}


@pytest.mark.parametrize("page", PAGES)
def test_each_page_loads_the_shared_runtime_and_is_a_cbb_page(page):
    text = (WEB / page).read_text(encoding="utf-8")
    assert '<script src="./support.js"></script>' in text
    assert 'import("./lib/sports.js")' in text or page == "Methods.dc.html"
    assert 'setAttribute("data-sport","cbb")' in text
    for tab in ("Board.dc.html", "Results.dc.html", "Tracker.dc.html", "Season.dc.html", "Record.dc.html", "Methods.dc.html"):
        assert tab in text, f"{page} lost the {tab} tab"
    assert "never places bets" in text
    lowered = text.lower()
    assert "puck" not in lowered and "goalie" not in lowered, "hockey vocabulary on a basketball page"


@pytest.mark.parametrize("path", [WEB / p for p in PAGES] + [WEB / "site_pages.py", WEB / "build_site_pages.py", WEB / "build_board_json.py", WEB / "SCHEMA.md"] + [WEB / "data" / "sample" / f for f in FEEDS] + [WEB / "data" / "sample" / "board.json"])
def test_no_page_feed_builder_or_sample_names_a_reference_site(path):
    lowered = path.read_text(encoding="utf-8").lower()
    for site in REFERENCE_SITES:
        assert site not in lowered, f"{path.name} names {site}"


@pytest.mark.parametrize("feed", FEEDS)
def test_the_samples_parse_and_carry_no_nan(feed):
    text = (WEB / "data" / "sample" / feed).read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text)


def test_the_sample_board_carries_the_game_page_fields():
    board = json.loads((WEB / "data" / "sample" / "board.json").read_text(encoding="utf-8"))
    for g in board["games"]:
        assert g["factors"][-1]["homeWin"] == pytest.approx(g["home"]["winProb"], abs=1e-6)
        assert set(g["ratings"]) == {"home", "away"} and set(g["tiers"]) == {"home", "away"}
        assert "coverProb" in g["spread"] and "overProb" in g["total"]


def test_publish_board_builds_the_feeds_and_lists_the_pages():
    workflow = yaml.safe_load((PROJECT_ROOT / ".github" / "workflows" / "publish-board.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["build"]["steps"] if "build" in workflow["jobs"] else next(iter(workflow["jobs"].values()))["steps"]
    build = next(s for s in steps if s.get("name") == "Build the board")["run"]
    lines = [line.strip() for line in build.splitlines() if line.strip()]
    assert "python web/settle_results.py --data dist/data --sport cbb" in lines
    assert lines.index("python web/build_site_pages.py --data dist/data") > lines.index("python web/settle_results.py --data dist/data --sport cbb"), "the record pages read what the settle kept"
    site = next(line for line in lines if line.startswith("printf"))
    payload = json.loads(re.search(r"'(\{.*\})'", site).group(1))
    assert payload == {"sport": "cbb", "pages": ["season", "record", "tracker", "methods", "game"]}


def test_the_schema_names_every_feed():
    schema = (WEB / "SCHEMA.md").read_text(encoding="utf-8")
    for feed in ("record.json", "tracker.json", "season.json", "ratings.json", "board.json"):
        assert feed in schema


# --- The game page is for a reader, not an analyst (2026-10-26, evening) ---
#
# Cooper found the first NHL game pages "way too complicated". The CBB page
# follows the plain format they were redone in: our call in one sentence, the
# three biggest reasons, head to head as "+N% vs average", who is out, the
# odds and the result. No waterfall, no formulas, no uncertainty band.

_GAME_DRIVER = r"""
import { readFileSync } from "node:fs";
const [pagePath, boardPath] = process.argv.slice(2);
const page = readFileSync(pagePath, "utf8");
const board = JSON.parse(readFileSync(boardPath, "utf8"));
const m = /<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/.exec(page);
globalThis.location = { search: "", hostname: "localhost" };
class DCLogic { constructor(props) { this.props = props || {}; } setState(s) { Object.assign(this.state, s); } }
const Component = new Function("DCLogic", `${m[1]}; return Component;`)(DCLogic);
const F = { fmtOdds: (v) => (v > 0 ? `+${v}` : String(v)) };
const render = (game, props) => { const c = new Component(props); c.F = F; c.state.board = board; c.state.isSample = true; c.state.game = game; return c.renderVals(); };
const out = {};
for (const [name, id] of Object.entries(Component.PREVIEW)) out[name] = render(board.games.find((g) => String(g.id) === id), { scenario: "Sample game", game: name, afterGame: false });
out.after = render(board.games[0], { scenario: "Sample game", afterGame: true });
const refused = { ...board.games[0], id: "x", home: { abbr: "ND", record: "2–0" }, away: { abbr: "NOVA", record: "1–1" } };
for (const k of ["factors", "ratings", "pick", "moneyline", "spread", "total", "tiers", "homeCourt"]) delete refused[k];
out.refused = render(refused, { scenario: "Sample game" });
process.stdout.write(JSON.stringify(out));
"""


def _render_game_page(tmp_path: Path) -> dict:
    import subprocess

    node = shutil.which("node")
    assert node, "node is not on PATH; this test renders the game page's own component"
    site = tmp_path / "game-render"
    site.mkdir()
    (site / "package.json").write_text('{"type": "module"}\n', encoding="utf-8")
    (site / "render.mjs").write_text(_GAME_DRIVER, encoding="utf-8")
    result = subprocess.run(
        [node, str(site / "render.mjs"), str(WEB / "Game.dc.html"), str(WEB / "data" / "sample" / "board.json")],
        capture_output=True, text=True, timeout=60, check=False,
    )
    assert result.returncode == 0, f"the game page's component threw:\n{result.stderr}"
    text = result.stdout
    assert "NaN" not in text and "undefined" not in text and "Infinity" not in text
    return json.loads(text)


def test_the_game_page_carries_no_waterfall_and_reads_in_sentences():
    text = (WEB / "Game.dc.html").read_text(encoding="utf-8")
    for gone in ("How the number was built", "waterfall", "barWidth", "How to read this", "Fair price", ">Edge<"):
        assert gone not in text, f"the game page still carries {gone!r}"
    for kept in (">Our call<", ">Why<", ">Head to head<", ">Who is out<", ">The odds<", ">After the game<", "no demonstrated edge"):
        assert kept in text, f"the game page lost {kept!r}"


def test_the_game_page_renders_the_sample_games_in_plain_english(tmp_path):
    out = _render_game_page(tmp_path)
    for name, v in out.items():
        if name in ("after", "refused"):
            continue
        assert re.fullmatch(r"(We like .+ to win\. We give them a \d+% chance\.|Close to a coin flip\. We give .+ a slight edge, \d+%\.)", v["headline"]), (name, v["headline"])
        assert v["scoreLine"].startswith("Projected score: ")
        assert 1 <= len(v["why"]) <= 3 and all(w["text"].endswith(".") and w["label"] for w in v["why"]), (name, v["why"])
        assert [r["label"] for r in v["cmp"]] == ["Scoring", "Defence", "Last five games"]
        for r in v["cmp"]:
            for cell in (r["away"], r["home"]):
                assert re.fullmatch(r"Avg|[+−]\d+%", cell), (name, r)
        assert v["cmpNote"] == "Compared with an average Division I team. Plus is better."
        assert v["paceLine"].startswith("Pace: ") and "possessions" in v["paceLine"]
        assert len(v["lineups"]) == 2 and all(k["name"] and k["tag"] for k in v["lineups"])
        assert v["after"]["pending"] is True
        for row in v["markets"]:
            assert row["chance"] != "—" or row["tag"] == "", (name, row)  # a tagged pick always shows its chance
    best, lean, none = out["NOVA @ ND · best bet"], out["SDSU @ ARIZ · lean"], out["MICH @ DUKE · no pick"]
    assert best["pick"]["isBet"] and best["pick"]["sub"].endswith("1 unit")
    assert [r["tag"] for r in best["markets"] if r["tag"]] == ["Best bet"]
    assert lean["pick"]["isLean"] and [r["tag"] for r in lean["markets"] if r["tag"]] == ["Lean"]
    assert none["pick"]["isNone"] and not any(r["tag"] for r in none["markets"])
    after = out["after"]["after"]
    assert after["done"] is True and after["grade"] in ("Win", "Loss", "Push") and after["winnerProb"].endswith("%")
    refused = out["refused"]
    assert refused["unpriced"] and refused["hasWhy"] is False and refused["hasRatings"] is False and refused["priced"] is False
    assert refused["unpricedNote"].startswith("The model had no number")
    assert not refused["pick"]["isNone"], "a refused game is never a pass"


def test_the_board_carries_the_league_averages_the_ratings_are_measured_against(built):
    _builder, board, _fit = built
    assert board["league"]["efficiency"] > 50 and board["league"]["tempo"] > 40


def test_the_sample_board_matches_the_builders_pick_shape():
    board = json.loads((WEB / "data" / "sample" / "board.json").read_text(encoding="utf-8"))
    assert board["league"]["efficiency"] > 50
    for g in board["games"]:
        pick = g.get("pick")
        if not pick:
            continue
        assert pick["units"] == (1.0 if pick["kind"] == "bet" else None), (g["home"]["abbr"], pick)
        assert pick["tier"] in ("high_major", "mid_major", "low_major") and 0 < pick["modelProb"] < 1


def test_closing_line_value_is_the_pick_against_the_last_line_before_tip(tmp_path):
    """A spread or total pick against the last line the board recorded before
    tip, from the bettor's side; a moneyline pick is left out, and a point
    after tip is not the close."""
    site_pages = _load(WEB / "site_pages.py", "test_site_pages_clv")
    teams = {"ND": {"name": "Notre Dame", "short": "Notre Dame"}, "NOVA": {"name": "Villanova", "short": "Villanova"}, "KU": {"name": "Kansas", "short": "Kansas"}, "DUKE": {"name": "Duke", "short": "Duke"}}
    day = date(2026, 11, 14)
    hist = tmp_path / "history"
    (hist / "finals").mkdir(parents=True)
    (hist / "lines").mkdir(parents=True)
    (hist / f"{day.isoformat()}_morning.json").write_text(json.dumps(_frozen_board(day, teams)), encoding="utf-8")
    (hist / "finals" / f"{day.isoformat()}.json").write_text(json.dumps({"9001": {"home": 78, "away": 70, "finish": "REG"}, "9002": {"home": 66, "away": 71, "finish": "OT"}}), encoding="utf-8")
    # Kansas +3.5 was taken; the home line closed at +2.0 before tip and
    # moved to +6.0 after it, which is not the close.
    (hist / "lines" / f"{day.isoformat()}.json").write_text(json.dumps({
        "9002": {"spread": [{"t": f"{day.isoformat()}T14:05:00Z", "v": 3.5}, {"t": f"{day.isoformat()}T22:00:00Z", "v": 2.0}, {"t": f"{day.isoformat()}T23:45:00Z", "v": 6.0}]},
        "9001": {"spread": [{"t": f"{day.isoformat()}T14:05:00Z", "v": -3.5}, {"t": f"{day.isoformat()}T22:00:00Z", "v": -5.0}]},
    }), encoding="utf-8")
    (tmp_path / "board.json").write_text(json.dumps({"record": {"clvPoints": None, "beatClosePct": None}}), encoding="utf-8")
    site_pages.write_record_pages(tmp_path, day + timedelta(days=1), fetch=False)

    record = json.loads((tmp_path / "record.json").read_text(encoding="utf-8"))
    assert record["clv"]["picks"] == 1, "the Notre Dame moneyline bet carries no closing line"
    assert record["clv"]["meanPoints"] == 1.5 and record["clv"]["beatClosePct"] == 100.0
    assert record["clv"]["bets"]["picks"] == 0
    rows = {r["kind"]: r for r in json.loads((tmp_path / "tracker.json").read_text(encoding="utf-8"))["rows"]}
    assert rows["pass"]["closeLine"] == 2.0 and rows["pass"]["clvPoints"] == 1.5
    assert rows["bet"]["clvPoints"] is None
    board = json.loads((tmp_path / "board.json").read_text(encoding="utf-8"))
    assert board["record"]["clvPoints"] == 1.5 and board["record"]["beatClosePct"] == 100.0


def test_closing_value_reads_totals_from_the_bettors_side():
    site_pages = _load(WEB / "site_pages.py", "test_site_pages_clv_total")
    lines = {"total": [{"t": "2026-11-14T20:00:00Z", "v": 146.0}]}
    game = {"tip": "2026-11-14T23:00:00Z"}
    assert site_pages.closing_value({"market": "Total", "side": "over", "line": 144.5}, game, lines)["points"] == 1.5
    assert site_pages.closing_value({"market": "Total", "side": "under", "line": 144.5}, game, lines)["points"] == -1.5
    assert site_pages.closing_value({"market": "Spread", "side": "away", "line": 3.0}, game, {"spread": [{"t": "2026-11-14T20:00:00Z", "v": -2.0}]})["points"] == 1.0
    assert site_pages.closing_value({"market": "Moneyline", "side": "home", "line": None}, game, lines) is None
