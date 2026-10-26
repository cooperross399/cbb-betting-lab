"""The second-opinion fetcher reads both export shapes and resolves names.

The source cannot be reached from the container this lab is developed in, so
the parser is exercised on fixtures shaped like the two exports, and the fetch
itself is verified from an Actions log. What is pinned here: a header is read
by name, a headerless table by value, a table whose columns cannot be told
apart is refused, names resolve through the provider index with the table's
own spellings, and the written file is what `card_factors` reads.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.data import second_opinion as SO
from cbb_betting_lab.models import card_factors as CF

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_data"
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "fetch_second_opinion.py"


def _header_table(names, *, star: str | None = None) -> bytes:
    lines = ["rank,team,conf,record,adjoe,oe Rank,adjde,de Rank,barthag,adjt"]
    for i, name in enumerate(names, start=1):
        off = 118.0 if name == star else 100.0 + (i % 9)
        # Offence and defence are both points per 100 and average alike across
        # a league, which the parser checks.
        lines.append(f"{i},{name},ACC,10-2,{off:.1f},{i},{100.0 + ((i + 4) % 9):.1f},{i},0.5,{66.0 + (i % 4):.1f}")
    return ("\n".join(lines) + "\n").encode()


def _headerless_table(names) -> bytes:
    lines = []
    for i, name in enumerate(names, start=1):
        # rank, team, conf, G, record, AdjOE, AdjDE, Barthag, ..., AdjT, WAB
        lines.append(
            f"{i},{name},ACC,{20 + i % 5},10-2,{100.0 + (i % 9):.1f},{100.0 + ((i + 4) % 9):.1f},"
            f"0.55,51.2,48.9,17.1,19.2,30.1,28.3,33.0,30.5,{66.0 + (i % 4):.1f},{1.5 - i * 0.01:.2f}"
        )
    return ("\n".join(lines) + "\n").encode()


def test_a_header_is_read_by_name():
    frame = SO.parse(_header_table(["Duke", "Kansas", "Michigan St."] * 5))
    assert list(frame.columns) == ["team", "adj_off", "adj_def", "adj_tempo"]
    assert len(frame) == 15
    assert frame["team"].iloc[2] == "Michigan St."


def test_a_headerless_table_is_read_by_value():
    frame = SO.parse(_headerless_table([f"Team {i}" for i in range(40)]))
    assert len(frame) == 40
    assert frame["adj_off"].between(100, 109).all()
    assert frame["adj_def"].between(100, 109).all()
    assert frame["adj_tempo"].between(66, 70).all()


def test_a_table_whose_columns_cannot_be_told_apart_is_refused():
    with pytest.raises(SO.SecondOpinionError):
        SO.parse(b"a,b\n1,2\n3,4\n")
    # Offence and defence averaging ten points apart is a column mistaken for
    # one of them.
    lines = ["team,adjoe,adjde,adjt"] + [f"T{i},110,95,67" for i in range(30)]
    with pytest.raises(SO.SecondOpinionError):
        SO.parse(("\n".join(lines) + "\n").encode())


def test_names_resolve_through_the_provider_index_with_the_tables_spellings():
    schedule = pd.read_parquet(FIXTURES / "mbb_schedule_2027.parquet")
    frame = pd.DataFrame(
        {"team": ["Michigan St.", "Duke", "St. John's", "Not A School"],
         "adj_off": [110.0, 112.0, 105.0, 99.0], "adj_def": [95.0, 96.0, 99.0, 104.0],
         "adj_tempo": [66.0, 70.0, 68.0, 65.0]}
    )
    resolved, unresolved = SO.resolve(frame, schedule)
    assert unresolved == ["Not A School"]
    assert resolved["team_id"].notna().sum() == 3
    assert "Michigan State" in SO.spellings("Michigan St.")
    assert "Saint John's" in SO.spellings("St. John's")


def test_the_script_writes_what_the_card_reads(tmp_path, monkeypatch):
    # The fixture schedule names 227 home clubs, under the real floor of
    # 300, so the floor is lowered here; the thin case below still sits under it.
    monkeypatch.setattr(CF, "SECOND_OPINION_MIN_TEAMS", 200)
    raw = tmp_path / "raw"
    schedules = raw / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    (schedules / "mbb_schedule_2027.parquet").write_bytes(
        (FIXTURES / "mbb_schedule_2027.parquet").read_bytes()
    )
    schedule = pd.read_parquet(FIXTURES / "mbb_schedule_2027.parquet")
    names = sorted(set(schedule["home_location"].dropna().astype(str)))
    payload = tmp_path / "table.csv"
    payload.write_bytes(_header_table(names))

    spec = importlib.util.spec_from_file_location("fetch_second_opinion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    code = module.main([
        "--season", "2027", "--as-of", "2026-11-05", "--raw-dir", str(raw),
        "--payload", str(payload),
    ])
    assert code == 0
    path = CF.second_opinion_path(raw, 2027)
    written = pd.read_csv(path)
    assert list(written.columns) == list(CF.SECOND_OPINION_COLUMNS)
    assert written["as_of"].iloc[0] == "2026-11-05"
    sidecar = json.loads(path.with_suffix(".unresolved.json").read_text())
    assert sidecar["season"] == 2027
    read, why = CF.load_second_opinion(raw, season=2027, day="2026-11-05")
    assert read is not None, why
    assert len(read) >= CF.SECOND_OPINION_MIN_TEAMS

    # Under the floor: written, and refused by the card, with exit 2.
    payload.write_bytes(_header_table(names[:50]))
    assert module.main([
        "--season", "2027", "--as-of", "2026-11-05", "--raw-dir", str(raw),
        "--payload", str(payload),
    ]) == 2
    thin, why = CF.load_second_opinion(raw, season=2027, day="2026-11-05")
    assert thin is None and "under the" in why
