"""`read_store` refused a column the file lacked, and erased one it had.

`frame[list(columns)]` keeps only the declared columns, and every
`for_append` caller writes the frame it read back over the file: the generic
`stores.append`, the forward snapshot writer, and the forward-ledger append.
So a column the schema stops listing leaves every row already on disk. The
row count rises on that same write, so the shrink guard sees nothing, and
the snapshot and ledger on `card-feed` are the only copies.

On 2026-09-24 no real store carried an undeclared column: both price stores
and the one frozen snapshot match their schemas exactly, and the ledger does
not exist until the season opens. That is why the guard goes in now, when it
costs nothing.
"""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab import stores

COLUMNS = ("event_id", "market", "book", "american_odds")


def _write(path, frame):
    frame.to_csv(path, index=False)


def _rows(*events, extra=None):
    frame = pd.DataFrame(
        [{"event_id": e, "market": "h2h", "book": "dk", "american_odds": -110} for e in events]
    )
    for name, value in (extra or {}).items():
        frame[name] = value
    return frame


def test_an_append_never_erases_a_column_that_holds_data(tmp_path):
    """The reproduction: the old code wrote this file back without `closing`."""
    path = tmp_path / "store.csv"
    _write(path, _rows("e1", "e2", extra={"closing": [-105, -120]}))

    with pytest.raises(stores.UndeclaredColumnError, match="closing"):
        stores.append(_rows("e3"), path, columns=COLUMNS)

    after = pd.read_csv(path)
    assert "closing" in after.columns, "the refused append still touched the file"
    assert list(after["closing"]) == [-105, -120]
    assert len(after) == 2


def test_the_refusal_is_a_corrupt_store_to_every_existing_handler(tmp_path):
    """The weekly loop and the purchase rebuild already stop on this class."""
    path = tmp_path / "store.csv"
    _write(path, _rows("e1", extra={"closing": [-105]}))

    with pytest.raises(stores.CorruptStoreError):
        stores.read_store(path, columns=COLUMNS, for_append=True)


def test_an_empty_leftover_column_is_trimmed_not_refused(tmp_path):
    """A header holding nothing is not evidence; refusing it would make a
    harmless leftover a hard stop on every nightly write."""
    path = tmp_path / "store.csv"
    _write(path, _rows("e1", "e2", extra={"leftover": [None, ""]}))

    assert stores.append(_rows("e3"), path, columns=COLUMNS) == 3
    assert list(pd.read_csv(path).columns) == list(COLUMNS)


def test_a_reader_that_never_writes_still_gets_the_declared_shape(tmp_path):
    """Only the writing path refuses. A render-only read drops nothing on disk."""
    path = tmp_path / "store.csv"
    _write(path, _rows("e1", extra={"closing": [-105]}))

    frame = stores.read_store(path, columns=COLUMNS)
    assert list(frame.columns) == list(COLUMNS)
    assert "closing" in pd.read_csv(path).columns


def test_the_missing_column_direction_still_refuses(tmp_path):
    """The guard that was already here must not have been traded for this one."""
    path = tmp_path / "store.csv"
    _write(path, _rows("e1").drop(columns=["book"]))

    with pytest.raises(stores.CorruptStoreError, match="missing"):
        stores.read_store(path, columns=COLUMNS, for_append=True)


def test_a_store_matching_its_schema_appends_as_before(tmp_path):
    path = tmp_path / "store.csv"
    _write(path, _rows("e1", "e2"))

    assert stores.append(_rows("e3"), path, columns=COLUMNS) == 3
    back = pd.read_csv(path)
    assert list(back.columns) == list(COLUMNS)
    assert list(back["event_id"]) == ["e1", "e2", "e3"]


def test_the_forward_ledger_append_refuses_before_writing(tmp_path):
    """The record this matters most for: it cannot be back-dated."""
    from cbb_betting_lab import forward_evidence as fe

    def row(event):
        return {c: f"{c}-value" for c in fe.LEDGER_COLUMNS} | {
            "event_id": event, "snapshot_date": "2026-11-04",
        }

    path = tmp_path / "forward_evidence.csv"
    older = pd.DataFrame([row("e1")], columns=list(fe.LEDGER_COLUMNS))
    older["retired_column"] = "evidence"
    older.to_csv(path, index=False)

    with pytest.raises(stores.UndeclaredColumnError, match="retired_column"):
        fe.append_ledger(pd.DataFrame([row("e2")]), path)
    assert "retired_column" in pd.read_csv(path).columns
    assert len(pd.read_csv(path)) == 1
