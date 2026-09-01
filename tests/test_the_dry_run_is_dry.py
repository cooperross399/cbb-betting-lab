"""The credit-spending scripts, proved dry rather than described as dry.

Every script here that can spend money is dry by default and spends only under
`--live`. That promise is worth exactly what enforces it, and until this file
the enforcement was a CI step grepping the script's last line — which proves
the sentence was printed, not that nothing was requested.

So these tests **block the network at the socket layer** and **hide the
credential**, then run the real entry points. A dry run that tried to open a
connection raises here rather than passing quietly, and one that read a
credential would be reading `None`.

The football lab's probe cost 7,280 credits. A script that spent that by
default, once, would be a bad afternoon; a script that spent it because a
`--live` check was inverted and the test only read stdout would be worse,
because nothing would have caught it.
"""

from __future__ import annotations

import runpy
import socket
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


class NetworkWasTouched(AssertionError):
    """Raised instead of connecting. The message is the failure report."""


@pytest.fixture()
def no_network(monkeypatch):
    """Every route to a socket, closed."""

    def refuse(*args, **kwargs):
        raise NetworkWasTouched(
            "A dry run tried to open a network connection. Dry means dry: "
            "nothing may be requested without --live."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    return refuse


@pytest.fixture()
def no_credential(monkeypatch):
    """The credential is not merely unused; it is not there to be used."""
    for name in ("CBB_ODDS_API_KEY", "ODDS_API_KEY", "THE_ODDS_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def run_script(name: str, *argv: str) -> int:
    """Run a script the way a shell would, and return its exit status."""
    path = SCRIPTS / name
    assert path.is_file(), f"{name} does not exist."
    saved = sys.argv[:]
    sys.argv = [str(path), *argv]
    try:
        runpy.run_path(str(path), run_name="__main__")
        return 0
    except SystemExit as exit_code:
        return int(exit_code.code or 0)
    finally:
        sys.argv = saved


@pytest.mark.parametrize(
    "script,argv",
    [
        ("run_retention_probe.py", ()),
        ("estimate_credit_cost.py", ()),
        # The gameday card is the script the workflow runs four times a day
        # through the season, and it is the one that spends the most. Its dry
        # path prints what it would fetch and stops.
        ("run_gameday_card.py", ("--card-slot", "morning")),
    ],
)
def test_the_default_path_opens_no_socket(
    script, argv, no_network, no_credential, tmp_path
):
    """With no cache these exit non-zero saying so, which is correct.

    The assertion is deliberately NOT about the exit status — a missing input
    may legitimately exit 1 or 2, and pinning that would make this test about
    argparse rather than about money. What is asserted is that we get here at
    all: `NetworkWasTouched` is an `AssertionError`, so a script that tried to
    connect fails this test by raising out of `run_script` rather than by
    returning anything.
    """
    status = run_script(script, "--raw-dir", str(tmp_path), *argv)
    assert isinstance(status, int)


def test_the_probe_is_dry_even_with_a_cache(no_network, no_credential):
    """The stronger case: a probe that CAN build its sample still must not
    request anything without --live."""
    raw = REPO / "data" / "raw" / "cbb" / "schedules"
    if not any(raw.glob("mbb_schedule_*.parquet")):
        pytest.skip("No cached schedule locally; the empty-cache case covers CI.")
    status = run_script("run_retention_probe.py")
    assert status == 0


def test_the_probe_says_so_in_the_words_the_reader_expects(capsys, no_network, no_credential):
    raw = REPO / "data" / "raw" / "cbb" / "schedules"
    if not any(raw.glob("mbb_schedule_*.parquet")):
        pytest.skip("No cached schedule locally.")
    run_script("run_retention_probe.py")
    assert "no credit was spent" in capsys.readouterr().out


def test_live_is_spelled_the_same_way_in_every_spending_script():
    """One flag name across every entry point that can spend. A script whose
    override were `--real` or `--go` would be one a hurried operator could
    trigger while believing they were doing something else."""
    for path in sorted(SCRIPTS.glob("*.py")):
        text = path.read_text()
        if "credit" not in text.lower() and "odds" not in text.lower():
            continue
        for wrong in ('"--real"', '"--go"', '"--execute"', '"--spend"'):
            assert wrong not in text, f"{path.name} uses {wrong} rather than --live."
