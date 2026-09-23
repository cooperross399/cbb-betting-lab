#!/usr/bin/env python3
"""Build `board.json` for the CBB page of the Maverick Hightower projections site.

    PYTHONPATH=src python web/build_board_json.py --lab . --out dist/data

Runs INSIDE cbb-betting-lab after CBB Gameday Refresh, with that run's
artifacts restored into data/. Publishes to this repository's own GitHub
Pages; the site (hosted from nhl-betting-lab) reads
https://cooperross399.github.io/cbb-betting-lab/data/board.json in the browser.

Sources, each one read through the lab's own module rather than a spelling
copied out of it:
  * ESPN's public men's college basketball scoreboard (keyless, groups=50 is
    all of Division I): tonight's slate, tip, venue, TV, records, finals.
  * `data/staging/cbb/<date>_<slot>.csv`, the path
    `providers.staging.staging_path` builds: the whole board, every book. Its
    columns are `providers.staging.STAGED_COLUMNS`, and its `market` column
    carries **this lab's** market key, never the provider's — see
    :data:`PROVIDER_KEYS`.
  * `data/archive/priced_snapshots/<date>.csv`, the path
    `forward_evidence.snapshot_path` builds: the frozen wagers, one row per
    wager at the best price, columns `forward_evidence.SNAPSHOT_COLUMNS`.
  * `data/outputs/cbb_card_state.json`, the path
    `reports.gameday_card.state_path` builds: the slot and decision the last
    card recorded for its slate day.
  * The lab's ratings, through `reports.card_matchups.matchups_for_card` —
    the same seam the card prices through — for projected points and
    probabilities. Absent inputs mean no model, not a zero.
  * `data/outputs/cbb_forward_evidence.json`, whose shape is
    `forward_evidence.report_payload`: per **market and tier**, never pooled
    across Division I.

Nothing here fetches odds, spends a credit, or places a bet.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
USER_AGENT = "cbb-betting-lab-site/1.0 (+https://github.com/cooperross399/cbb-betting-lab)"
SEASON = "2026–27"
MARKETS = {"moneyline": "Moneyline", "spread": "Spread", "total": "Total"}

#: The board's three market slots, and the key `markets.py` gives each one.
#: The staged and frozen rows carry the **lab's** market key in their `market`
#: column (`providers.staging.stage_event` writes `market.key`), so these three
#: strings are what a row is actually spelled with. `total_points` is the one
#: the drop guessed wrong: there is no market called `total` in the registry.
BOARD_MARKETS = {"moneyline": "moneyline", "spread": "spread", "total": "total_points"}


def _provider_keys() -> dict[str, str]:
    """market spelling -> board slot, built from `markets.py` where it can be.

    Both vocabularies are accepted because both exist on disk: the `market`
    column is the lab's key and the `provider_key` column beside it is the
    provider's. The registry is asked for the provider spellings rather than
    having them copied, so a key renamed there fails here loudly (KeyError)
    instead of quietly dropping a market off the board.

    The ladders (`alternate_spreads`, `alternate_totals`) are deliberately not
    folded in: they are their own markets in the registry, they are priced at
    rungs rather than at the featured line, and pooling them into the featured
    row would move the consensus line this file computes.
    """
    mapping = {lab_key: slot for slot, lab_key in BOARD_MARKETS.items()}
    try:
        from cbb_betting_lab.markets import MARKETS_BY_KEY  # type: ignore
    except ImportError:
        # The package is not importable (a bare checkout of web/). Fall back to
        # the provider keys `markets.py` carries today, which is a copy and is
        # marked as one.
        mapping.update({"h2h": "moneyline", "spreads": "spread", "totals": "total"})
        return mapping
    for slot, lab_key in BOARD_MARKETS.items():
        for provider_key in MARKETS_BY_KEY[lab_key].provider_keys:
            mapping[provider_key] = slot
    return mapping


#: Every spelling of the three board markets -> the board's slot.
PROVIDER_KEYS = _provider_keys()


def _full_game() -> str:
    """`selection.FULL_GAME`, read from the module that defines it.

    The halves are separate market keys on separate rows, and a first-half
    total must never reach a full-game cell. The literal is the fallback for a
    checkout with no package on the path, and it is a copy: `selection.py`
    is the definition.
    """
    try:
        from cbb_betting_lab.selection import FULL_GAME as SEGMENT  # type: ignore
    except ImportError:
        return "game"
    return str(SEGMENT)


FULL_GAME = _full_game()


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - fixed host
        return json.load(resp)


def slate_for(day: date) -> list[dict]:
    payload = fetch_json(f"{ESPN}?dates={day:%Y%m%d}&groups=50&limit=400")
    out = []
    for ev in payload.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        h, a = sides.get("home", {}), sides.get("away", {})
        tv = " / ".join(sorted({b.get("names", [""])[0] for b in comp.get("broadcasts", []) if b.get("names")})) or "—"
        rec = lambda c: next((r.get("summary", "") for r in c.get("records", []) if r.get("type") == "total"), "")  # noqa: E731
        out.append({
            "id": str(ev.get("id")), "tip": ev.get("date"), "neutral": bool(comp.get("neutralSite")),
            "venue": (comp.get("venue") or {}).get("fullName", ""), "city": ((comp.get("venue") or {}).get("address") or {}).get("city", ""), "tv": tv,
            "state": ((ev.get("status") or {}).get("type") or {}).get("state", "pre"),
            "home": {"name": (h.get("team") or {}).get("displayName", ""), "abbr": (h.get("team") or {}).get("abbreviation", ""), "color": (h.get("team") or {}).get("color"), "record": rec(h), "score": h.get("score")},
            "away": {"name": (a.get("team") or {}).get("displayName", ""), "abbr": (a.get("team") or {}).get("abbreviation", ""), "color": (a.get("team") or {}).get("color"), "record": rec(a), "score": a.get("score")},
        })
    return out


def ink_for(hex_color: str) -> str:
    h = (hex_color or "14151a").lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return "#FFFFFF"
    return "#000000" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#FFFFFF"


def finite(value: object):
    """`value` as a float, or None when it is not a number this file may print.

    Two reasons, and they are the same reason. `json.dumps` writes a NaN or an
    infinity as the bare words `NaN` and `Infinity`, which are not JSON and
    which `JSON.parse` refuses — one of them anywhere in `board.json` takes
    the whole page down. And a missing number is missing: the lab's own rule
    is that `0` is not a price and a blank cell is not a zero, so a value that
    is not a number becomes null rather than something that reads as one.
    """
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def percent(value: object):
    """A share as a percentage to one decimal, or None. See :func:`finite`."""
    number = finite(value)
    return None if number is None else round(100 * number, 1)


def to_american(p: float) -> int:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def read_csvs(pattern: str) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(pattern)):
        with open(path, newline="", encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def norm_market(r: dict) -> str:
    return PROVIDER_KEYS.get((r.get("market") or "").lower(), (r.get("market") or "").lower())


def resolve(lab_names, label: str) -> str:
    """Provider/ESPN team string -> the lab's canonical key, via providers/team_names."""
    try:
        return lab_names(label) or label
    except Exception:
        return label


def group_rows(rows, key):
    """Full-game team rows, grouped by the resolved `(home, away)` pair.

    Grouped once rather than filtered per game. The board is a whole night —
    up to ~200 games at this sport's peak, against every book's quote for
    every market — and a scan of the staged rows per game is that product,
    with a name resolution inside it. One pass builds the index instead.

    The segment is checked rather than assumed. `selection.py` keeps the
    segment in every join key precisely so a first half cannot join a full
    game, and a row with no segment column at all is read as a full game
    because that is what every pre-segment file held.
    """
    out: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if (r.get("segment") or FULL_GAME) != FULL_GAME:
            continue
        if (r.get("player") or "").strip():
            continue
        out.setdefault((key(r.get("home_team", "")), key(r.get("away_team", ""))), []).append(r)
    return out


def best(rows, market, selection, line=None):
    out = None
    for r in rows:
        if norm_market(r) != market or (r.get("selection") or "").lower() != selection:
            continue
        if line is not None:
            try:
                if abs(float(r.get("line") or 0) - line) > 1e-6:
                    continue
            except ValueError:
                continue
        try:
            price = float(r["american_odds"])
        except (KeyError, ValueError):
            continue
        out = price if out is None or price > out else out
    return None if out is None else int(out)


def consensus_line(rows, market, selection=None):
    lines = []
    for r in rows:
        if norm_market(r) != market or (selection and (r.get("selection") or "").lower() != selection):
            continue
        try:
            lines.append(float(r["line"]))
        except (KeyError, ValueError):
            pass
    return max(set(lines), key=lines.count) if lines else None


def load_names(lab: Path, day: date):
    """ESPN/provider spelling -> the hoopR team id, as a string.

    `providers.team_names` has no `resolve_team`: it builds a `TeamIndex` from
    the season's cached schedule — the feed that also supplies settlement, so
    the two sides of the join cannot describe different universes — and
    `TeamIndex.resolve` returns a team **id** or None. An unresolved name
    keeps its own spelling, which joins nothing: that is the safe direction
    and the one the module asks for ("`None`, never a guess").

    With no cached schedule there is no index, and every label is its own key.
    """
    try:
        from cbb_betting_lab.providers import team_names  # type: ignore
        from cbb_betting_lab.reports.card_matchups import InputsAbsent, load_schedule  # type: ignore
        from cbb_betting_lab.season import season_for_slate_date  # type: ignore
    except ImportError:
        return lambda label: label
    try:
        schedule = load_schedule(season_for_slate_date(day.isoformat()), lab / "data" / "raw")
    except InputsAbsent:
        return lambda label: label
    index = team_names.build_index(schedule)
    #: Memoised: `TeamIndex.resolve` normalises and expands a name on every
    #: call, and this is asked the same ~365 spellings once per staged row.
    seen: dict[str, str] = {}

    def to_key(label):
        text = str(label)
        if text not in seen:
            team = index.resolve(label)
            seen[text] = text if team is None else str(team)
        return seen[text]

    return to_key


def load_model(lab: Path, day: date, slate: list[dict]):
    """The lab's ratings, or None. `(home_key, away_key, neutral) -> dict|None`.

    Priced through `reports.card_matchups.matchups_for_card`, which is the
    seam the gameday card itself prices through: the same walk-forward cut
    (`price_backtest.history_before`), the same model
    (`price_backtest.DEFAULT_MODEL`, `models.ratings:matchups_for`), the same
    name resolution, and the same fixture join on hoopR's game id. A second
    pricing path is the defect this lab's own modules are arranged against, so
    there is not one here.

    The subject is tonight's ESPN slate rather than the board's quotes: the
    site draws a row per scheduled game whether or not a book has quoted it.
    `matchups_for_card` wants the provider's vocabulary — `event_id` and the
    two school names — and ESPN's display names are the same strings the
    index's aliases are built from.

    Returns None when the model cannot be asked at all: `InputsAbsent` is
    raised for a missing `cbb_team_games.csv`, `cbb_player_games.csv` or
    cached schedule, and the publish runner restores none of the three. The
    board then carries the slate, the prices and the frozen wagers' own model
    probabilities, and says so. Nothing else is caught: a model that raises
    for any other reason fails this build rather than publishing a board that
    silently has no numbers in it.

    Each answer is:
        {"hp": projected home points, "ap": projected away points,
         "home_win": P(home wins), "cover": fn(line)->P(home covers line),
         "over": fn(total)->P(over), "margin_triple", "total_triple",
         "venueState": ..., "priorWeight": ...}
    Points come off the joint distribution rather than off the matchup's
    per-possession numbers, so they include overtime exactly as the
    probabilities beside them do. `cover` and `over` are the two
    probabilities asked for, and they exclude the push; the `_triple`
    accessors beside them return `GameDistribution.margin`/`.total` whole —
    `(win, push, loss)` — because a fair two-way price needs the push and
    this file reads both off one call rather than two.

    **The neutral-site flag is honoured by refusing to disagree with it.** The
    lab prices from `population.VenueState`, read off the classified schedule;
    ESPN's `neutralSite` is the flag on the same fixture. Where the two
    disagree the game is declined rather than published at a venue effect
    computed for the other answer — CLAUDE.md's "a game mislabelled neutral is
    a multi-point error applied to every market on it" — and the count of
    declines is carried on the callable so the board can say it happened.
    """
    try:
        import pandas as pd  # type: ignore
        from cbb_betting_lab.competitions import CBB  # type: ignore
        from cbb_betting_lab.models import ratings  # type: ignore
        from cbb_betting_lab.reports import card_matchups  # type: ignore
        from cbb_betting_lab.selection import HOME, OVER  # type: ignore
    except ImportError:
        return None

    subjects = [g for g in slate if g["id"] and g["home"]["name"] and g["away"]["name"]]
    if not subjects:
        return None
    rows = pd.DataFrame(
        [
            {"event_id": g["id"], "home_team": g["home"]["name"], "away_team": g["away"]["name"],
             "market": "", "player": ""}
            for g in subjects
        ]
    )
    try:
        built = card_matchups.matchups_for_card(
            rows,
            competition=CBB,
            day=day.isoformat(),
            processed_dir=lab / "data" / "processed",
            raw_dir=lab / "data" / "raw",
        )
    except card_matchups.InputsAbsent:
        return None

    by_pair: dict[tuple[str, str], object] = {}
    for game in built.matchups.values():
        home, away = getattr(game, "home_team_id", None), getattr(game, "away_team_id", None)
        if home is None or away is None:
            continue
        by_pair[(str(home), str(away))] = game
    if not by_pair:
        return None

    neutral_states = {"neutral", "quasi_neutral"}
    cache: dict[tuple[str, str], dict | None] = {}
    state = {"asked": len(by_pair), "priced": 0, "refused": 0, "declined_on_venue": 0, "unjoined": 0}

    def price(home_key: str, away_key: str, neutral: bool):
        game = by_pair.get((str(home_key), str(away_key)))
        if game is None:
            state["unjoined"] += 1
            return None
        # Priceable first: a matchup the ratings refused has no number to
        # withhold, and counting it as a venue disagreement would overstate
        # how often the two sources disagree about where a game is played.
        if not getattr(game, "priceable", False):
            state["refused"] += 1
            return None
        if (str(getattr(game, "venue_state", "")) in neutral_states) != bool(neutral):
            state["declined_on_venue"] += 1
            return None
        key = (str(home_key), str(away_key))
        if key not in cache:
            state["priced"] += 1
            dist = ratings.to_distribution(game)
            margin, total = dist.expected_margin, dist.expected_total
            cache[key] = {
                "hp": (total + margin) / 2.0,
                "ap": (total - margin) / 2.0,
                "home_win": dist.moneyline(HOME),
                "cover": lambda line, d=dist: d.margin(float(line), HOME)[0],
                "over": lambda line, d=dist: d.total(float(line), OVER)[0],
                # The same two markets with the push kept, for a fair price.
                "margin_triple": lambda line, d=dist: d.margin(float(line), HOME),
                "total_triple": lambda line, d=dist: d.total(float(line), OVER),
                "venueState": str(getattr(game, "venue_state", "")),
                "priorWeight": getattr(game, "prior_weight", None),
            }
        return cache[key]

    price.state = state  # type: ignore[attr-defined]
    price.summary_line = built.summary_line  # type: ignore[attr-defined]
    return price


def fair_two_way(win: float, loss: float):
    """A fair American price from a win/loss pair, the push held out.

    `GameDistribution.margin` and `.total` return `(win, push, loss)` so that
    no caller can drop the push and re-normalise the other two — which is how
    a −3 comes to be priced as if it were a −3.5. A two-way price is the
    conditional on not pushing, and it is only defined when something can
    happen.
    """
    live = float(win) + float(loss)
    if live <= 0:
        return None
    return to_american(float(win) / live)


def load_frozen(lab: Path, day: date) -> list[dict]:
    """`data/archive/priced_snapshots/<day>.csv` — `forward_evidence.snapshot_path`."""
    return read_csvs(str(lab / "data" / "archive" / "priced_snapshots" / f"{day.isoformat()}.csv"))


def pick_from_frozen(frozen_rows: list[dict], home_abbr: str, away_abbr: str) -> dict | None:
    """The highest-edge frozen opinion on this game, and what it is.

    **`kind` is never `bet` here.** A frozen row is an opinion the card priced
    and froze; a *selection* is a row that cleared every bar in
    `reports/card_pricing.select`, and the first of those bars is that the
    market is allowlisted by a reviewed policy — no market is. The snapshot
    carries no column saying "selected", so this file cannot invent one: every
    pick is published as `pass`, which is the site's word for a model opinion
    that is not a recommendation, and the notice says why.
    """
    team = [r for r in frozen_rows if norm_market(r) in MARKETS]
    if not team:
        return None

    def edge_of(row: dict) -> float:
        """The row's edge for the ranking only. A row carrying no readable
        edge sorts as if it had none, and the number PUBLISHED below is null
        rather than this 0.0 — sorting with a default and printing one are
        different things."""
        number = finite(row.get("edge"))
        return 0.0 if number is None else number

    top = max(team, key=edge_of)
    m, s = norm_market(top), (top.get("selection") or "").lower()
    side = home_abbr if s == "home" else away_abbr if s == "away" else s.capitalize()
    try:
        price = int(float(top["american_odds"]))
    except (KeyError, TypeError, ValueError):
        return None
    line = top.get("line")
    label = {"moneyline": f"{side} ML", "spread": f"{side} {float(line):+.1f}".replace("-", "−") if line else side, "total": f"{s.capitalize()} {float(line):g}" if line else s}[m]
    model_probability = finite(top.get("model_probability"))
    return {"kind": "pass", "market": MARKETS[m], "label": label, "price": price, "book": top.get("book"), "tier": top.get("tier") or None,
            "units": None, "edgePct": percent(top.get("edge")),
            "modelProb": None if model_probability is None else round(model_probability, 4)}


def load_status(lab: Path, day: date) -> dict:
    """The card's own state file, for this slate day only.

    `reports.gameday_card.state_path(CBB, data/outputs)` is
    `data/outputs/cbb_card_state.json`, and `scripts/run_gameday_card._write_
    state` writes `{slate_date, card_slot, fingerprint, decision,
    generated_at}` into it. It rides in the gameday artifact, which
    `latest_status.json` — the same facts, written by the workflow onto the
    `card-feed` branch — does not.

    **The day is checked, not merely recorded**, which is the rule
    `_previous_fingerprint` states next door: a state file for another day is
    not an error and not evidence about this one, so last night's slot and
    decision are not stamped onto tonight's board.
    """
    candidates = [lab / "data" / "outputs" / "cbb_card_state.json",
                  lab / "latest_status.json"]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("slate_date", "")) != day.isoformat():
            continue
        return payload
    return {}


def load_record(lab: Path) -> dict:
    """The forward record, in the shape `forward_evidence.report_payload` writes.

    That payload has **no `markets` mapping**: it carries `rows`, one per
    `(cut, market, tier)` with `bets`, `roi`, `low`, `high`, `adjusted_low`,
    `adjusted_high` and `verdict`, plus `frozen_opinions`, `measurable_rows`,
    `minimum_bets` and `bet_threshold`. The drop read `fe["markets"]` and then
    `int(fe["rows"])`, which is a list.

    **Nothing pooled across Division I is published here.** `render_ledger`
    prints "No figure pooled across the whole of Division I appears here" and
    the payload states `no_pooled_division_one_headline`; high-major,
    mid-major and low-major are different distributions. So a market's headline
    row is emitted only when every settled row in that market sits in one
    tier — in which case the lab's own row for that `(market, tier)` IS the
    market's number and is copied verbatim — and the per-tier rows are carried
    beside it under `marketsByTier` either way. The `bets` cut is used, which
    is the cut the card's comment prints.
    """
    out = {"markets": [], "marketsByTier": [], "clvPoints": None, "beatClosePct": None,
           "opinionsNeeded": 10_000, "opinionsSoFar": 0, "pooled": None}
    try:
        from cbb_betting_lab.reports.what_we_can_claim import SAMPLE_FLOOR_OPINIONS  # type: ignore

        out["opinionsNeeded"] = int(SAMPLE_FLOOR_OPINIONS)
    except ImportError:
        pass  # docs/when_this_ends.md: 10,000 settled opinions. Copied, and marked.
    path = lab / "data" / "outputs" / "cbb_forward_evidence.json"
    if not path.is_file():
        return out
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return out
    if not isinstance(payload, dict):
        return out
    out["opinionsSoFar"] = int(payload.get("measurable_rows") or 0)
    by_market: dict[str, list[dict]] = {}
    for row in payload.get("rows") or []:
        if not isinstance(row, dict) or row.get("cut") != "bets":
            continue
        slot = PROVIDER_KEYS.get(str(row.get("market") or "").lower())
        if slot is None:
            continue  # a player prop or a half; the site's three cards are full-game team markets
        by_market.setdefault(slot, []).append(row)

    # `stats.interval_two_way` returns **±inf and no standard error** rather
    # than `roi ± 0` for a single cluster, so a bound here is genuinely not
    # always a number. `percent` carries those as null and the row they belong
    # to never becomes a headline card.
    def rendered(slot: str, row: dict, label: str) -> dict:
        return {"market": slot, "label": label, "tier": row.get("tier"),
                "bets": int(row.get("bets") or 0),
                "roiPct": percent(row.get("roi")),
                "ciLowPct": percent(row.get("low")), "ciHighPct": percent(row.get("high")),
                "adjustedCiLowPct": percent(row.get("adjusted_low")),
                "adjustedCiHighPct": percent(row.get("adjusted_high")),
                "clusters": row.get("clusters"), "clusterUnit": row.get("cluster_unit"),
                "verdict": row.get("verdict") or "no demonstrated edge"}

    for slot in ("spread", "total", "moneyline"):
        tier_rows = by_market.get(slot) or []
        for row in tier_rows:
            out["marketsByTier"].append(rendered(slot, row, f"{MARKETS[slot]} · {row.get('tier')}"))
        if len(tier_rows) != 1:
            continue
        card = rendered(slot, tier_rows[0], MARKETS[slot])
        if None not in (card["roiPct"], card["ciLowPct"], card["ciHighPct"]):
            out["markets"].append(card)
    out["pooled"] = (
        "This lab publishes no figure pooled across Division I: high-major, "
        "mid-major and low-major are different distributions and are measured "
        "as such. A market card is blank whenever its settled rows span more "
        "than one tier; the per-tier rows are in `marketsByTier`."
    )
    return out


def load_policy(lab: Path):
    """The provider policy the card reads, or None if it cannot be read.

    Imported lazily and inside a try: this script also runs offline against a
    checkout that may not have the package importable, and a board that fails
    to build because it could not read a policy is worse than a board that
    says "no market is allowlisted" — which is this repository's standing
    state and the safe thing to say when the answer is unavailable.

    None therefore reads as "nothing allowlisted", which is the same direction
    the policy loader itself fails in: every unreadable state there resolves
    to an allowlist of nothing.
    """
    try:
        from cbb_betting_lab import staging_provider_policy as spp
    except Exception:
        return None
    try:
        return spp.load(Path(lab) / "data" / "manual")
    except Exception as exc:
        print(f"policy unreadable, board will say nothing is allowlisted: {exc}")
        return None


def build(lab: Path, day: date) -> dict:
    now = datetime.now(timezone.utc)
    status = load_status(lab, day)
    slot = status.get("card_slot") or ("evening" if datetime.now(ET).hour >= 12 else "morning")
    names = load_names(lab, day)

    def by_name(label):
        return resolve(names, label)

    priced_rows = group_rows(read_csvs(str(lab / "data" / "staging" / "cbb" / f"{day.isoformat()}_*.csv")), by_name)
    frozen_rows = group_rows(load_frozen(lab, day), by_name)
    slate = slate_for(day)
    model = load_model(lab, day, slate)
    teams, games = {}, []
    for g in slate:
        h, a = g["home"], g["away"]
        ha, aa = h["abbr"] or h["name"][:4].upper(), a["abbr"] or a["name"][:4].upper()
        for abbr, t in ((ha, h), (aa, a)):
            color = f"#{t['color']}" if t.get("color") else "#14151a"
            teams.setdefault(abbr, {"name": t["name"], "short": t["name"].replace(" Fighting", "").replace(" Blue Devils", "").split(" ")[0] if len(t["name"]) > 18 else t["name"], "color": color, "fg": ink_for(color)})
        hk, ak = resolve(names, h["name"]), resolve(names, a["name"])
        mine = priced_rows.get((hk, ak), [])
        my_frozen = frozen_rows.get((hk, ak), [])
        # One slot for the whole board: `forward_evidence.SNAPSHOT_COLUMNS`
        # carries no `card_slot`, so a per-game slot read off a frozen row
        # would be a column that does not exist reading as "morning" forever.
        row = {"id": g["id"], "tip": g["tip"], "venue": g["venue"], "city": g["city"], "tv": g["tv"], "neutral": g["neutral"], "started": g["state"] != "pre",
               "cardSlot": slot,
               "home": {"abbr": ha, "record": h["record"]}, "away": {"abbr": aa, "record": a["record"]}, "pick": pick_from_frozen(my_frozen, ha, aa)}
        spread_line = total_line = None
        if mine:
            spread_line = consensus_line(mine, "spread", "home")
            total_line = consensus_line(mine, "total")
            row["moneyline"] = {"open": None, "current": {"home": best(mine, "moneyline", "home"), "away": best(mine, "moneyline", "away")}, "fair": None}
            row["spread"] = {"open": None, "current": spread_line, "homePrice": best(mine, "spread", "home", spread_line), "proj": None}
            row["total"] = {"open": None, "current": total_line, "overPrice": best(mine, "total", "over", total_line), "proj": None}
            # Model probabilities the freeze recorded, when there is no live
            # model to ask. Through `finite`, because the column is a CSV
            # round-trip: an empty cell reads back as the float NaN and a
            # `float()` on it would put `NaN` into the published JSON.
            ml_home = next(
                (p for p in (
                    finite(r.get("model_probability")) for r in my_frozen
                    if norm_market(r) == "moneyline" and (r.get("selection") or "").lower() == "home"
                ) if p is not None),
                None,
            )
            if ml_home is not None:
                row["home"]["winProb"], row["away"]["winProb"] = round(ml_home, 4), round(1 - ml_home, 4)
                row["moneyline"]["fair"] = {"home": to_american(ml_home), "away": to_american(1 - ml_home)}
        pr = model(hk, ak, g["neutral"]) if model else None
        if pr:
            row["home"].update(projPts=round(pr["hp"], 1), winProb=round(pr["home_win"], 4))
            row["away"].update(projPts=round(pr["ap"], 1), winProb=round(1 - pr["home_win"], 4))
            row["priorWeight"] = None if pr["priorWeight"] is None else round(float(pr["priorWeight"]), 4)
            row["venueState"] = pr["venueState"]
            row.setdefault("moneyline", {"open": None, "current": None})["fair"] = {"home": to_american(pr["home_win"]), "away": to_american(1 - pr["home_win"])}
            row.setdefault("spread", {"open": None, "current": None, "homePrice": None})["proj"] = round(-(pr["hp"] - pr["ap"]), 1)
            row.setdefault("total", {"open": None, "current": None, "overPrice": None})["proj"] = round(pr["hp"] + pr["ap"], 1)
            if spread_line is not None:
                covered, _push, missed = pr["margin_triple"](spread_line)
                row["spread"]["coverProb"] = round(covered, 4)
                row["spread"]["fairHomePrice"] = fair_two_way(covered, missed)
            if total_line is not None:
                over, _push, under = pr["total_triple"](total_line)
                row["total"]["overProb"] = round(over, 4)
                row["total"]["fairOverPrice"] = fair_two_way(over, under)
        games.append(row)
    # "No market is allowlisted" was written into both sentences as a
    # constant. It is a fact about a file that Cooper can change in one pull
    # request, and a page that states it from a string keeps stating it after
    # it stops being true. So the sentence reads the policy the card reads.
    #
    # "No demonstrated edge" is NOT conditional and does not move with the
    # allowlist: approving a market says its prices may be used, not that the
    # model beats them. All 32 measured market-and-tier cells come back no
    # demonstrated edge, not enough evidence, or a demonstrated deficit, and
    # none of the three is an edge.
    policy = load_policy(lab)
    allowlisted = sorted(policy.allowlist) if policy else []
    forced_manual = bool(policy and policy.receipt_failures)
    if forced_manual:
        gate = (
            f"{len(allowlisted)} market(s) are listed in the policy but at "
            "least one lacks a valid human acceptance receipt, so the card "
            "reads nothing from staging"
        )
    elif allowlisted:
        gate = f"{len(allowlisted)} market(s) are allowlisted"
    else:
        gate = "no market is allowlisted"

    if not any(g["pick"] for g in games):
        notice = (f"No selection is published: {gate} and the model has no demonstrated edge. "
                  "The slate, the board's prices and the model's numbers are shown; nothing here is a recommendation.")
    elif allowlisted and not forced_manual:
        notice = (f"{gate.capitalize()}, so the picks below are the card's own selections. "
                  "The model still has no demonstrated edge in any measured market: every one comes back "
                  "no demonstrated edge, not enough evidence, or a demonstrated deficit. "
                  "Allowlisting says a market's prices may be used, not that the model beats them.")
    else:
        notice = (f"Every pick shown is a frozen opinion, not a recommendation: {gate}, "
                  "so nothing on this board cleared the bar that would make it a bet.")
    # A MODEL THAT ANSWERED NOTHING IS NOT A MODEL THAT WAS NEVER ASKED, and
    # the two look identical on a board full of dashes. `card_matchups` says
    # the same thing about the card itself: it must say it priced no opinion,
    # and it may never silently price none. So the census is published beside
    # the board and the notice reads off it.
    census = dict(getattr(model, "state", {})) if model else {
        "asked": 0, "priced": 0, "refused": 0, "declined_on_venue": 0, "unjoined": 0}
    census["available"] = bool(model)
    census["games"] = len(games)
    census["summary"] = model.summary_line() if model else ""
    if not model:
        notice += " Projected scores are absent this run: the ratings were not available to the site build."
    elif not census.get("priced"):
        notice += (f" The ratings were asked about {census.get('asked', 0)} game(s) and priced none of them"
                   f" ({census.get('refused', 0)} refused); every projected score on this board is absent"
                   " because the model declined, not because it was never asked.")
    declined = census.get("declined_on_venue", 0)
    if declined:
        notice += (f" {declined} game(s) carry no projection: the schedule this lab prices from and "
                   "tonight's neutral-site flag disagree about where they are played, and a game "
                   "mislabelled neutral is a multi-point error on every market on it.")
    return {"generatedAt": now.isoformat(timespec="seconds").replace("+00:00", "Z"), "season": SEASON, "slateDate": day.isoformat(), "cardSlot": slot,
            "decision": status.get("decision"), "notice": notice, "unitDollars": 25, "record": load_record(lab),
            "model": census, "teams": teams, "games": games}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lab", default=".")
    ap.add_argument("--out", default="dist/data")
    ap.add_argument("--date", default="", help="Slate date (default: today in New York).")
    args = ap.parse_args(argv)
    day = date.fromisoformat(args.date) if args.date else datetime.now(ET).date()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    board = build(Path(args.lab), day)
    # `allow_nan=False`: Python writes a NaN or an infinity as the bare words
    # `NaN` and `Infinity`, which are not JSON and which `JSON.parse` refuses
    # — one of them anywhere in this file takes the whole page down and
    # nothing here would have looked wrong. It raises instead.
    text = json.dumps(board, indent=1, ensure_ascii=False, allow_nan=False)
    (out / "board.json").write_text(text, encoding="utf-8")
    hist = out / "history"; hist.mkdir(exist_ok=True)
    frozen = hist / f"{day.isoformat()}_{board['cardSlot']}.json"
    if not frozen.exists():
        frozen.write_text(text, encoding="utf-8")
    print(f"board {day} ({board['cardSlot']}): {len(board['games'])} games. No odds were fetched, no credit was spent, and no bet was placed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
