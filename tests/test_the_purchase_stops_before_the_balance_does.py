"""An empty account is a fact about our wallet, never a fact about the archive.

Two defects on the paid-data purchase path, both of which end with a report
stating something false as measured.

**1. A zero-billed response was charged the pessimistic bound.** `Spend.record`
parsed `x-requests-last`, set the cost to 0 when the parse failed, and then ran
`if actual <= 0: actual = fallback`. That one test conflates three different
answers from the provider — the header was absent, the header was unreadable,
and the header said **0** — and charges all three the full bound. The Odds API
really does bill 0 for some responses. Charging those the bound is a guess
overriding a measurement the provider actually reported: a run whose responses
mostly bill nothing burns its cap against spending that never happened, stops
early, and the record and the rendered report then state that phantom spend as
fact.

**2. There was no balance floor and no circuit-breaker.**
`odds_api.sufficient_quota` existed and two of the FOUR spending scripts called
it — `run_gameday_card.py`, and `run_retention_probe.py` behind
`--skip-quota-check`; `buy_historical_prices.py` — the script that spends by
far the most, at ten times the live rate — never did, and neither did
`capture_line_movement.py`, which this docstring called "the three spending
scripts" while it sat outside the count. Nothing anywhere read
`x-requests-remaining` DURING a run. `Spend.quota_remaining` was written and
then only printed.

The consequence is the one this repository's whole census discipline exists to
prevent. When the account empties mid-run the provider stops returning quotes.
Those responses stage no rows, the segments after them are never requested at
all, and the census reason they land under reads as the provider not retaining
that market. An exhausted balance is then published as a statement about the
archive's retention — a fabricated fact about the provider, from a true fact
about our balance.

**3. The breaker was fitted to `historical.buy` and not to `probe`.** That was
the first round's mistake and it repaired the narrower of the two sites.
`historical.buy`'s census says only *what did not become a row*.
`reports/retention_probe.probe` publishes the word `NOT_RETAINED`, and it was
left with no in-run breaker at all. An emptied account is not caught by the
`NOT_PROBED` machinery there, because the provider keeps answering: the payload
holds no bookmakers, `asked` records every key in the chunk as asked, nothing is
priced against them, and `MarketRoll.verdict()` returns `NOT_RETAINED`. The
run's own cap was never hit, so the report reached its completed branch and
printed *"a `NOT_RETAINED` verdict below is a fact about the archive rather than
a fact about the budget"* — the exact false statement, published, in the module
whose output is the retention claim.

**4. `Spend.quota_remaining` was sticky.** Written only `if value`, so one
`x-requests-remaining` early in a run armed every reader of it for the rest of
the run. A provider or proxy that stops sending the header while the account
drains leaves the breaker comparing a healthy five thousand against its floor
for ever, `quota_ever_reported` True, the "nothing to watch" notice suppressed,
and the stale figure published as the balance the run ended on.

Every test here drives the real code with a fake requester or a fake provider.
Nothing opens a socket and nothing spends a credit.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
from pathlib import Path

import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.providers.odds_api import (
    CARD_STARVATION,
    FALLBACK_ABSENT,
    FALLBACK_NEGATIVE,
    FALLBACK_UNREADABLE,
    MOVEMENT_STARVATION,
    PROBE_STARVATION,
    PURCHASE_STARVATION,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    QuotaExhausted,
    Spend,
    sufficient_quota,
)
from cbb_betting_lab.reports import retention_probe as RP

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "buy_historical_prices.py"
CAPTURE_SCRIPT = REPO / "scripts" / "capture_line_movement.py"
WINDOW = H.CARD_WINDOW


@pytest.fixture()
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("This test must not open a socket.")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


# ---------------------------------------------------------------------------
# 1. What a response cost, as the provider reported it
# ---------------------------------------------------------------------------


def test_a_response_the_provider_billed_at_zero_is_charged_zero():
    """The authoritative answer, and it is authoritative at zero too.

    `x-requests-last: 0` is the provider saying this response cost nothing.
    Charging the pessimistic bound over the top of it is a bound overriding a
    measurement, and it spends a cap against money that was never spent.
    """
    spend = Spend()
    charged = spend.record({"x-requests-last": "0"}, fallback=160)

    assert charged == 0, "a zero-billed response was charged something"
    assert spend.credits_spent == 0
    assert spend.zero_billed_responses == 1
    assert not spend.fallback_charges, (
        "zero was counted as a failure to report a cost; it is a reported cost"
    )


def test_a_run_of_zero_billed_responses_does_not_consume_the_cap():
    """The consequence, at the scale it bites. Forty zero-billed responses
    against a bound of 160 apiece is 6,400 credits of phantom spend — enough to
    stop a capped run and to be published as what the run cost."""
    spend = Spend()
    for _ in range(40):
        spend.record({"x-requests-last": "0"}, fallback=160)

    assert spend.credits_spent == 0
    assert spend.zero_billed_responses == 40
    assert "40 of which the provider billed at zero" in spend.summary_line()


@pytest.mark.parametrize(
    "headers,kind",
    [
        ({}, FALLBACK_ABSENT),
        ({"x-requests-last": "   "}, FALLBACK_ABSENT),
        ({"x-requests-last": "seventeen"}, FALLBACK_UNREADABLE),
        ({"x-requests-last": "-3"}, FALLBACK_NEGATIVE),
    ],
)
def test_the_three_ways_of_not_reporting_a_cost_each_charge_the_bound_under_their_own_name(
    headers, kind
):
    """All three charge the pessimistic bound — guessing low lets a run drift
    past its cap while reporting that it has not — and all three are counted
    apart, because an absent header is the provider changing, an unreadable one
    is an assumption of ours breaking, and a negative one is the provider
    itself. One counter for all three cannot tell an operator which."""
    spend = Spend()
    charged = spend.record(headers, fallback=160)

    assert charged == 160
    assert spend.credits_spent == 160
    assert spend.fallback_charges == {kind: 1}
    assert spend.zero_billed_responses == 0
    assert len(spend.notes) == 1 and kind in spend.notes[0].lower()


def test_one_note_per_kind_however_many_responses(monkeypatch):
    """A note appended per response puts tens of thousands of identical strings
    into the run record and the rendered report. The kinds are named once; the
    counts carry the number."""
    spend = Spend()
    for _ in range(500):
        spend.record({}, fallback=4)

    assert spend.fallback_charges == {FALLBACK_ABSENT: 500}
    assert len(spend.notes) == 1


def test_the_remaining_quota_is_none_rather_than_a_number_when_none_was_reported():
    """`None` is a third answer. Returning 0 would read as an empty account and
    returning a large number would read as a healthy one; both are inventions,
    and rule 3 forbids inventing a fact about the provider."""
    assert Spend().remaining_credits() is None
    assert Spend(quota_remaining="not a number").remaining_credits() is None
    assert Spend(quota_remaining="4321").remaining_credits() == 4321
    assert Spend(quota_remaining="0").remaining_credits() == 0


def test_a_balance_the_provider_stops_reporting_is_not_carried_forward():
    """THE FIELD IS THE MOST RECENT RESPONSE'S, NOT THE LAST ONE EVER SEEN.

    `quota_remaining` was written only `if value`, so one header at the start
    of a run stayed there for the whole of it. Every reader — the breaker,
    `summary_line`, the run record, both renderers — then read a stale number
    as the current balance. The three responses below are deliberately
    different: a reported balance, then two that report none, so the count of
    unreported ones is separately observable from the fact of any.
    """
    spend = Spend()
    spend.record({"x-requests-last": "1", "x-requests-remaining": "5000"}, fallback=1)
    assert spend.remaining_credits() == 5000

    spend.record({"x-requests-last": "1"}, fallback=1)
    spend.record({"x-requests-last": "1"}, fallback=1)

    assert spend.remaining_credits() is None, (
        "the balance from three responses ago is being reported as the current "
        "one; a breaker reading it compares a healthy figure against its floor "
        "while the account drains to zero"
    )
    assert spend.quota_remaining_last_reported == "5000"
    assert spend.responses_since_quota_reported == 2
    line = spend.summary_line()
    assert "2 response(s) ago" in line and "5000 remaining." not in line, (
        "the summary states a stale balance as the current one"
    )


def test_a_balance_that_keeps_being_reported_is_current_every_time():
    """The control for the test above. Without it, clearing the field on every
    response — a breaker that can never read anything — would pass."""
    spend = Spend()
    spend.record({"x-requests-last": "1", "x-requests-remaining": "5000"}, fallback=1)
    spend.record({"x-requests-last": "1", "x-requests-remaining": "4990"}, fallback=1)

    assert spend.remaining_credits() == 4990
    assert spend.responses_since_quota_reported == 0
    assert "4990 remaining." in spend.summary_line()


# ---------------------------------------------------------------------------
# 2. The circuit-breaker inside the run
# ---------------------------------------------------------------------------


def _event(index: int) -> RP.ProbeEvent:
    return RP.ProbeEvent(
        game_id=600_000 + index,
        season=2025,
        slate_date="2025-01-15",
        commence_time="2025-01-15T23:00:00Z",
        snapshot=f"2025-01-1{index % 5}T22:00:00Z",
        tier="high_major",
        month="2025-01",
        window="late",
        home_team_id=index,
        away_team_id=index + 1,
        home_name=f"h{index}",
        away_name=f"a{index}",
    )


def _one_snapshot_event(index: int) -> RP.ProbeEvent:
    """Like `_event`, but every event shares ONE snapshot.

    THE TWO REQUEST PATHS HAVE TO BE SEPARATELY OBSERVABLE. `_event` spreads
    its events over five snapshots, so a run over it makes a slate-listing
    request for most events and the breaker on the LISTING path fires first —
    which made the odds-path check invisible: deleting it left every test
    green. With one snapshot there is exactly one listing request, and every
    response after it is an odds request, so a stop after the first response
    can only have come from the odds path.
    """
    return RP.ProbeEvent(
        game_id=700_000 + index,
        season=2025,
        slate_date="2025-01-15",
        commence_time="2025-01-15T23:00:00Z",
        snapshot="2025-01-15T22:00:00Z",
        tier="high_major",
        month="2025-01",
        window="late",
        home_team_id=index,
        away_team_id=index + 1,
        home_name=f"h{index}",
        away_name=f"a{index}",
    )


def _one_snapshot_segment(wave: str, events: int) -> H.PlanSegment:
    return H.PlanSegment(
        wave=wave,
        season=2025,
        window=WINDOW.name,
        keys=("h2h",),
        keys_refused={},
        events=tuple(_one_snapshot_event(i) for i in range(events)),
        regions=2,
        blocked_reason="",
    )


def _segment(wave: str, events: int) -> H.PlanSegment:
    return H.PlanSegment(
        wave=wave,
        season=2025,
        window=WINDOW.name,
        keys=("h2h",),
        keys_refused={},
        events=tuple(_event(i) for i in range(events)),
        regions=2,
        blocked_reason="",
    )


def _plan(*segments: H.PlanSegment) -> H.PurchasePlan:
    return H.PurchasePlan(segments=tuple(segments), window=WINDOW, seed=1)


class FakeProvider:
    """A provider that answers, bills, and reports a falling balance.

    It charges through the real `Spend.record`, so the run is stopped by the
    same code path a live run would be stopped by.
    """

    regions = "us,us2"
    sport_key = CBB.provider_sport_key

    def __init__(self, *, balances, cost="1"):
        #: One `x-requests-remaining` per response, in order; `None` means the
        #: response carries no such header at all. The last value repeats once
        #: the list runs out, so a list ending in `None` is a provider that
        #: reported a balance and then stopped — the case that used to arm the
        #: breaker for ever off one header.
        self.balances = list(balances)
        #: `None` means the response carries no `x-requests-last` either, which
        #: is a provider (or proxy) reporting neither of the two headers.
        self.cost = cost
        self.responses = 0

    def _headers(self) -> dict[str, str]:
        index = min(self.responses, len(self.balances) - 1)
        self.responses += 1
        headers = {} if self.cost is None else {"x-requests-last": self.cost}
        balance = self.balances[index]
        if balance is not None:
            headers["x-requests-remaining"] = str(balance)
        return headers

    def list_historical_events(self, snapshot, *, spend, credit_cap):
        spend.record(self._headers(), fallback=1)
        return [{"id": "evt-1", "home_team": "h", "away_team": "a"}]

    def historical_event_odds(self, event_id, snapshot, markets, *, spend, credit_cap):
        spend.record(self._headers(), fallback=20)
        return {"bookmakers": []}


@pytest.fixture()
def always_matches(monkeypatch):
    """Name resolution is not what these tests are about."""
    monkeypatch.setattr(
        RP, "match_provider_event", lambda listing, event, index: ("evt-1", "")
    )


def _buy(provider, plan, tmp_path, **kwargs):
    kwargs.setdefault("chunk_size", 1)
    return H.buy(
        plan=plan,
        provider=provider,
        indexes={2025: object()},
        credit_cap=10_000_000,
        cache_dir=tmp_path / "cache",
        generated_at="2026-09-17T00:00:00Z",
        **kwargs,
    )


def test_the_run_stops_when_the_measured_balance_falls_below_the_floor(
    tmp_path, always_matches, no_network
):
    """The breaker, on the measured header and nothing else."""
    provider = FakeProvider(balances=[5_000, 4_000, 3, 3, 3])
    record = _buy(provider, _plan(_segment("core_team", 6)), tmp_path, quota_floor=100)

    assert record["stopped_on_quota"] is True
    assert record["completed"] is False
    assert record["quota_last_measured"] == 3
    assert "STOPPED ON QUOTA" in record["stopped_because"]
    assert provider.responses < 6, (
        "the run kept requesting after the account fell below its floor; a "
        "response the provider no longer answers stages nothing, and nothing "
        "staged reads in a census as a market the archive does not retain"
    )


def test_a_healthy_balance_does_not_stop_the_run(tmp_path, always_matches, no_network):
    """The control. Without it the test above would pass on a breaker wired to
    fire on every run, which stops nothing from being published and stops the
    purchase instead."""
    provider = FakeProvider(balances=[5_000_000])
    record = _buy(provider, _plan(_segment("core_team", 4)), tmp_path, quota_floor=100)

    assert record["stopped_on_quota"] is False
    assert record["completed"] is True
    assert record["unreached_segments"] == []


def test_a_provider_that_reports_no_balance_neither_stops_the_run_nor_is_assumed_healthy(
    tmp_path, always_matches, no_network
):
    """The third answer. The breaker has nothing to watch, and the record says
    so rather than letting the absence of a stop read as a measurement."""
    provider = FakeProvider(balances=[None])
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)

    assert record["completed"] is True
    assert record["stopped_on_quota"] is False
    assert record["quota_ever_reported"] is False
    assert record["quota_last_measured"] is None
    assert (
        "reported no remaining account quota on any response" in H.render(record)
    ), "the report does not say the breaker was never able to watch anything"


def test_the_segments_the_run_never_reached_are_named_rather_than_omitted(
    tmp_path, always_matches, no_network
):
    """A segment table that simply ends where the credits did makes the unbought
    half of the plan invisible, and an invisible plan row is how "we never
    asked" becomes "there was nothing to ask for"."""
    provider = FakeProvider(balances=[5_000, 2])
    record = _buy(
        provider,
        _plan(_segment("core_team", 2), _segment("ladders_and_halves", 2)),
        tmp_path,
        quota_floor=100,
    )

    unreached = [s["wave"] for s in record["unreached_segments"]]
    assert unreached == ["ladders_and_halves"]
    report = H.render(record)
    assert "ladders_and_halves" in report
    assert "never reached" in report and "never asked" in report


def test_a_quota_stop_is_not_rendered_as_the_ordinary_partial_buy(
    tmp_path, always_matches, no_network
):
    """The wording is the whole point of the flag. A capped run is 'the ordinary
    case for this purchase and not a fault' — true, and false for this one."""
    provider = FakeProvider(balances=[5_000, 2])
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)
    report = H.render(record)

    assert "STOPPED ON QUOTA" in report
    assert "the ordinary case for this purchase" not in report
    assert "may be read as a statement about what the archive holds" in report


def test_the_census_of_a_quota_stopped_run_disclaims_provider_retention(
    tmp_path, always_matches, no_network
):
    """The census counts what the responses we RECEIVED contained. After the
    balance went, they contained nothing — so the table must not be readable as
    evidence about retention."""
    provider = FakeProvider(balances=[5_000, 2])
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)
    record = dict(record)
    record["staging_census"] = {"unparseable_selection": 4}

    report = H.render(record)
    assert "attributes anything to the provider's retention" in report


def test_the_default_floor_is_derived_from_the_widest_request_not_invented(
    tmp_path, always_matches, no_network
):
    """Not a magic number: `10 x chunk_size x the widest segment's regions`.

    EVERY TERM IS SEPARATELY OBSERVABLE HERE, which the previous version of
    this test could not claim. It ran `chunk_size=1` over a segment with one
    key and one region count, so `chunk_size`, `len(keys)` and `len(chunk)`
    were all `1` and `max(regions)` had only one segment to choose from — four
    of the formula's terms collapsed onto the same number and the test could
    not tell which one the implementation had read. Here they are 3, 5, 3 and
    max(2, 4): the expected floor is pinned as a LITERAL, and the two most
    likely wrong readings are named and excluded rather than left to chance.
    """
    wide = H.PlanSegment(
        wave="core_team", season=2025, window=WINDOW.name,
        keys=("h2h", "spreads", "totals", "team_totals", "alternate_spreads"),
        keys_refused={}, events=tuple(_event(i) for i in range(2)),
        regions=4, blocked_reason="",
    )
    narrow = H.PlanSegment(
        wave="ladders_and_halves", season=2025, window=WINDOW.name,
        keys=("h2h", "spreads", "totals", "team_totals", "alternate_spreads"),
        keys_refused={}, events=tuple(_event(i) for i in range(2)),
        regions=2, blocked_reason="",
    )
    provider = FakeProvider(balances=[5_000_000])
    record = _buy(provider, _plan(narrow, wide), tmp_path, chunk_size=3)

    assert record["quota_floor"] == 120, (
        "the floor is not 10 x chunk_size(3) x the widest segment's regions(4)"
    )
    assert record["quota_floor"] != 10 * 5 * 4, (
        "the floor was computed from a segment's whole key list rather than "
        "from the chunk actually sent, so in production — where a segment "
        "carries many keys and MARKET_CHUNK_SIZE is not 1 — it would be wrong "
        "by the ratio between them"
    )
    assert record["quota_floor"] != 10 * 3 * 2, (
        "the floor took the FIRST segment's regions rather than the widest in "
        "the plan, so the widest request the run can make could still empty "
        "the account below the floor and be billed for a partial answer"
    )


def test_a_completed_run_whose_balance_was_never_measured_does_not_claim_the_archive(
    tmp_path, always_matches, no_network
):
    """The claim and the measurement that licenses it, held together.

    The completed-run branch printed "Anything absent below is absent from the
    archive rather than absent from the budget" for EVERY run that finished
    inside its cap, including one in which the breaker never read a single
    balance — and the "the breaker had nothing to watch" paragraph was
    appended three lines below it and never retracted it. Two contradictory
    statements about the same absence, the false one first and in the summary
    voice.
    """
    provider = FakeProvider(balances=[None])
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)
    report = H.render(record)

    assert record["completed"] is True
    assert record["quota_ever_reported"] is False
    assert "absent from the archive rather than absent from the budget" not in report, (
        "a run that never measured the account's balance is telling the reader "
        "that what it did not find is a fact about the provider's archive"
    )
    assert "cannot be attributed to the archive" in report
    assert "reported no remaining account quota on any response" in report


def test_a_run_watched_throughout_is_still_allowed_to_name_the_archive(
    tmp_path, always_matches, no_network
):
    """THE CONTROL, and the reason the test above is a gate rather than a
    gag. Same plan, same empty payloads, same completed run — the only thing
    that differs is that the provider reported a healthy balance on every
    response. That is the one state in which the sentence is true, and if it
    never printed at all the report would have lost a real measurement."""
    provider = FakeProvider(balances=[5_000_000])
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)
    report = H.render(record)

    assert record["quota_unwatched_responses"] == 0
    assert "measured on every response" in report
    assert "absent from the archive rather than absent from the budget" in report


def test_a_balance_reported_once_does_not_arm_the_breaker_for_the_rest_of_the_run(
    tmp_path, always_matches, no_network
):
    """The worst of the three states, and the one that read as the best.

    One `x-requests-remaining: 5000` on the first response used to stay in
    `Spend.quota_remaining` for the whole run. `check_quota` re-parsed that
    same 5,000 after every later response, never fired, set
    `quota_ever_reported` True — which SUPPRESSED the "nothing to watch"
    notice — and the record published 5,000 as the balance afterwards, over a
    run that went unanswered.
    """
    provider = FakeProvider(balances=[5_000, None])
    record = _buy(provider, _plan(_segment("core_team", 4)), tmp_path, quota_floor=100)
    report = H.render(record)

    assert record["quota_ever_reported"] is True
    assert record["quota_unwatched_responses"] > 0, (
        "the breaker reported itself as armed for responses on which the "
        "provider told it nothing"
    )
    assert record["quota_remaining"] == "", (
        "the run's last response reported no balance and the record states one"
    )
    assert record["quota_remaining_last_reported"] == "5000"
    assert "stopped reporting a remaining account quota" in report
    assert "absent from the archive rather than absent from the budget" not in report
    assert "not the balance the run ended on" in report


def test_a_provider_that_reports_neither_header_measures_neither_thing(
    tmp_path, always_matches, no_network
):
    """A proxy strips both headers. Nothing in the first round's test set
    exercised this: the cost falls back to the pessimistic bound under its own
    name, the balance is never measured at all, and the report must claim
    neither a measured spend nor a fact about the archive."""
    provider = FakeProvider(balances=[None], cost=None)
    record = _buy(provider, _plan(_segment("core_team", 3)), tmp_path, quota_floor=100)

    assert record["fallback_charges"] == {FALLBACK_ABSENT: record["requests_made"]}
    assert record["quota_ever_reported"] is False
    assert record["quota_remaining"] == ""
    assert record["quota_remaining_last_reported"] == ""

    # The census is the table a reader quotes, so it is given something to
    # count: empty payloads stage nothing and leave it empty, and an empty
    # table carries no claim to disclaim.
    record = dict(record)
    record["staging_census"] = {"unparseable_selection": 4}
    report = H.render(record)

    assert "absent from the archive rather than absent from the budget" not in report
    assert "not evidence about the archive" in report, (
        "the staging census of a run with no measured balance is being offered "
        "as evidence about what the provider retains"
    )


def test_a_record_written_before_the_breaker_is_not_rendered_as_a_measured_all_clear(
    tmp_path, always_matches, no_network
):
    """Defect AD's own shape, inside the row added to prevent it.

    A record that predates the breaker got `none: this record predates the
    balance circuit-breaker` for its floor, `unrecorded: this record predates
    the count` for its zero-billed responses, and then a flat **no** for
    `Stopped on quota` — which reads as a measured all-clear over a run in
    which nothing was measured. It also got a block quote saying the breaker
    "had nothing to watch", describing a mechanism that did not exist.
    """
    provider = FakeProvider(balances=[5_000_000])
    record = dict(
        _buy(provider, _plan(_segment("core_team", 2)), tmp_path, quota_floor=100)
    )
    for key in (
        "stopped_on_quota", "quota_floor", "quota_ever_reported",
        "quota_unwatched_responses", "quota_last_measured",
        "zero_billed_responses",
    ):
        record.pop(key, None)
    report = H.render(record)

    assert "| **Stopped on quota** | unrecorded: this record predates" in report, (
        "a flat 'no' on a run nothing measured, two rows under a floor that "
        "says no breaker existed"
    )
    assert "This record predates the balance circuit-breaker.**" in report
    assert "had nothing to watch" not in report, (
        "the report describes a circuit-breaker that did not exist when this "
        "run was made"
    )
    assert "absent from the archive rather than absent from the budget" not in report


def test_a_blocked_segment_after_a_quota_stop_keeps_its_own_reason(
    tmp_path, always_matches, no_network
):
    """A cut-off is true of a segment whatever the budget did.

    `if not state.completed: break` ran BEFORE the `if not segment.buyable`
    line, so a segment blocked by an archive cut-off that happened to fall
    after a quota stop never reached `per_segment` and was swept into
    `unreached_segments`. The report then replaced its real, known reason —
    the archive does not go back that far — with "we ran out of money before
    we got there".
    """
    blocked = H.PlanSegment(
        wave="futures", season=2025, window=WINDOW.name, keys=("h2h",),
        keys_refused={}, events=tuple(_event(i) for i in range(2)), regions=2,
        blocked_reason="no historical bulk endpoint exists for futures",
    )
    provider = FakeProvider(balances=[5_000, 2])
    record = _buy(
        provider,
        _plan(_segment("core_team", 3), _segment("ladders_and_halves", 2), blocked),
        tmp_path,
        quota_floor=100,
    )

    assert record["stopped_on_quota"] is True
    recorded = {s["wave"] for s in record["segments"]}
    unreached = {s["wave"] for s in record["unreached_segments"]}
    assert "futures" in recorded, (
        "a segment blocked by a cut-off was relabelled as one the budget never "
        "reached, which replaces a true reason with a false one"
    )
    assert "futures" not in unreached
    assert unreached == {"ladders_and_halves"}


def test_the_breaker_raises_its_own_named_exception():
    """`CreditCapReached` and `QuotaExhausted` say opposite things about what a
    run's silence proves, so they are not the same class — and neither may be
    caught by a handler written for the other.

    `assert issubclass(QuotaExhausted, Exception)` used to stand at the top of
    this test. It is true of every exception class in Python and could never
    have failed. The three below can: the first pins the relationship the
    `except ProviderError` handlers in `buy` and `probe` depend on, and the
    other two pin the separation in both directions.
    """
    assert issubclass(QuotaExhausted, ProviderError), (
        "a quota stop escaping the provider-error family would reach callers "
        "that treat any other failure as one request going wrong"
    )
    assert not issubclass(QuotaExhausted, CreditCapReached), (
        "a quota stop caught by the cap handler is recorded as the ordinary "
        "partial buy, which is the wording this whole flag exists to avoid"
    )
    assert not issubclass(CreditCapReached, QuotaExhausted), (
        "a cap stop caught by the quota handler publishes STOPPED ON QUOTA "
        "over a run whose account was never measured at all"
    )


# ---------------------------------------------------------------------------
# 2b. The pre-flight, in the script that spends the most
# ---------------------------------------------------------------------------


def _load_script():
    spec = importlib.util.spec_from_file_location("_buy_historical_prices", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DrainingProvider(FakeProvider):
    """Passes the free pre-flight and then empties mid-run.

    Constructed by the script itself, so it takes the competition positionally
    the way `OddsApiProvider` does.
    """

    def __init__(self, competition, **kwargs):
        super().__init__(balances=[5_000_000, 2])

    def quota(self):
        # Comfortably over any cap the test passes, so the PRE-FLIGHT passes
        # and the only thing that can stop this run is the in-run breaker.
        return {"x-requests-remaining": "9000000"}


class RefusingProvider:
    """Reports a balance far below any cap, and screams if asked to buy."""

    regions = "us,us2"
    sport_key = CBB.provider_sport_key
    bought: list[str] = []

    def __init__(self, competition, **kwargs):
        pass

    def quota(self):
        return {"x-requests-remaining": "12"}

    def list_historical_events(self, snapshot, *, spend, credit_cap):
        RefusingProvider.bought.append(snapshot)
        return []

    def historical_event_odds(self, event_id, snapshot, markets, *, spend, credit_cap):
        RefusingProvider.bought.append(event_id)
        return {}


def test_the_script_refuses_to_start_a_purchase_the_account_cannot_pay_for(
    tmp_path, monkeypatch, no_network, capsys
):
    """`sufficient_quota` existed for the whole of this build and the card and
    the probe both called it — `run_retention_probe.py:228`, behind
    `--skip-quota-check`. This script, the one that spends by far the most,
    did not. (This docstring said "only the card called it" for one round, the
    same false claim as row AD of `docs/ported_defects.md`, and it pointed away
    from the probe — the sibling the first fix left untouched.) Starting short
    is not a cheaper run: it is a run whose later segments go unanswered and
    land in a census that cannot say so.

    Driven through the script's real `main`, because the branch behind `--live`
    is the branch no dry run and no other test ever executes. The population is
    faked: which games exist is not what this test is about, and the tracked
    schedule fixtures cover three of the six seasons this wave spans.
    """
    module = _load_script()
    RefusingProvider.bought = []
    monkeypatch.setattr(module, "OddsApiProvider", RefusingProvider)
    monkeypatch.setattr(
        module.H,
        "load_events",
        lambda **kwargs: ({2025: [_event(0), _event(1)]}, {2025: object()}, {}),
    )
    monkeypatch.setenv("CBB_ODDS_API_KEY", "x" * 32)

    status = module.main(
        [
            "--waves", "core_team",
            "--live",
            "--credit-cap", "1200000",
            "--raw-dir", str(tmp_path / "raw"),
            "--processed-dir", str(tmp_path / "processed"),
            "--output-dir", str(tmp_path / "outputs"),
        ]
    )
    captured = capsys.readouterr()

    assert status == 6, captured.out + captured.err
    assert RefusingProvider.bought == [], (
        "the script started buying against a balance below its own cap"
    )
    assert "Refusing to start" in captured.err
    assert not (tmp_path / "outputs").exists(), (
        "a refused run wrote a record, which a later render would read as a run"
    )


def test_the_preflight_refusal_gives_this_scripts_reason_not_the_cards(
    tmp_path, monkeypatch, no_network, capsys
):
    """`sufficient_quota` carried the CARD's reason inline, and this script
    printed it. The historical purchase writes no ledger, has no slate, and
    buys past seasons in an order whose every prefix is already a sample, so
    "freezes the early tips and drops the late ones, which is a biased subset
    written into the ledger as though it were the night" describes nothing that
    happens here. An operator handed the wrong reason either dismisses a real
    refusal as a copy-paste or acts on the wrong model of what was lost."""
    module = _load_script()
    RefusingProvider.bought = []
    monkeypatch.setattr(module, "OddsApiProvider", RefusingProvider)
    monkeypatch.setattr(
        module.H, "load_events",
        lambda **kwargs: ({2025: [_event(0), _event(1)]}, {2025: object()}, {}),
    )
    monkeypatch.setenv("CBB_ODDS_API_KEY", "x" * 32)

    status = module.main(
        ["--waves", "core_team", "--live", "--credit-cap", "1200000",
         "--raw-dir", str(tmp_path / "raw"),
         "--processed-dir", str(tmp_path / "processed"),
         "--output-dir", str(tmp_path / "outputs")]
    )
    out = capsys.readouterr().out

    assert status == 6
    assert "written into the ledger as though it were the night" not in out, (
        "the purchase refusal prints the nightly card's reason: a frozen slate "
        "and a biased night in a ledger, for a script with neither"
    )
    assert "indistinguishable in the purchase census" in out, (
        "the refusal does not say what an exhausted account actually costs "
        "THIS script — the census reading an empty wallet as the archive"
    )


def test_the_four_callers_each_state_their_own_starvation():
    """The reason is a required argument, not a default anyone can inherit.

    A default would be the same defect waiting for the next caller: whoever
    added one would get the card's sentence for free and never notice. There
    are four now — the fourth, `capture_line_movement.py`, had no pre-flight at
    all until this round, and the constant it passes says what ITS starvation
    costs: a reachability store recording prices as withdrawn when it was the
    account that went.
    """
    with pytest.raises(TypeError):
        sufficient_quota({"x-requests-remaining": "1"}, 10)

    notes = {}
    for name, why in (
        ("purchase", PURCHASE_STARVATION),
        ("card", CARD_STARVATION),
        ("probe", PROBE_STARVATION),
        ("movement", MOVEMENT_STARVATION),
    ):
        enough, note = sufficient_quota({"x-requests-remaining": "1"}, 10, why=why)
        assert enough is False, f"{name} did not refuse a balance of 1 against a cap of 10"
        notes[name] = note

    assert "purchase census" in notes["purchase"]
    assert "written into the ledger as though it were the night" in notes["card"]
    assert "`NOT_RETAINED` verdict" in notes["probe"]
    assert "prices that vanished" in notes["movement"], (
        "the capture's refusal does not say what an exhausted account costs "
        "THIS script — a survival rate computed against movement that did not "
        "happen"
    )
    assert len(set(notes.values())) == 4, "two callers print the same reason"


def test_a_run_that_stops_on_quota_does_not_exit_green(
    tmp_path, monkeypatch, no_network, capsys
):
    """A GREEN EXIT OVER THE EXACT BAD STATE THIS MODULE WAS WRITTEN FOR.

    `H.buy` swallows `QuotaExhausted` internally — correctly, so everything
    bought before the stop is still recorded — and the only trace afterwards is
    `record['stopped_on_quota']` inside a file nobody opens while the job is
    green. The pre-flight refusal exits 6 and a refused rebuild exits 4; the
    in-run stop, which is worse than either, exited 0, so the workflow's Buy
    step passed, the store was rebuilt from a truncated cache, and the operator
    read a successful purchase with the banner hidden in an artifact.
    """
    module = _load_script()
    monkeypatch.setattr(module, "OddsApiProvider", DrainingProvider)
    monkeypatch.setattr(
        module.H, "load_events",
        lambda **kwargs: ({2025: [_event(i) for i in range(4)]}, {2025: object()}, {}),
    )
    monkeypatch.setattr(
        RP, "match_provider_event", lambda listing, event, index: ("evt-1", "")
    )
    monkeypatch.setenv("CBB_ODDS_API_KEY", "x" * 32)

    status = module.main(
        ["--waves", "core_team", "--live", "--credit-cap", "1200000",
         "--chunk-size", "1",
         "--raw-dir", str(tmp_path / "raw"),
         "--processed-dir", str(tmp_path / "processed"),
         "--output-dir", str(tmp_path / "outputs")]
    )
    captured = capsys.readouterr()
    record = json.loads(
        H.record_path(CBB, tmp_path / "outputs").read_text(encoding="utf-8")
    )

    assert record["stopped_on_quota"] is True, "the fixture did not reach the breaker"
    assert status == 7, (
        "a quota-stopped purchase exits green, so CI passes over the one "
        "failure this module's whole census discipline exists to prevent"
    )
    assert status != 0
    assert "STOPPED ON QUOTA" in captured.err
    assert H.report_path(CBB, tmp_path / "outputs").is_file(), (
        "the non-zero exit cost the run its report; everything bought before "
        "the stop must still be written"
    )


# ---------------------------------------------------------------------------
# 3. THE SIBLING SITE: the module that publishes the retention verdicts
#
# `historical.buy`'s census says what did not become a row. `probe` says
# NOT_RETAINED. It had no in-run breaker at all, and its completed branch
# printed "a NOT_RETAINED verdict below is a fact about the archive rather than
# a fact about the budget" — the exact sentence a balance nobody measured
# cannot support.
# ---------------------------------------------------------------------------

ARCHIVE_CLAIM = "is a fact about the archive rather than a fact about the budget"


def _sample_plan(events: int) -> RP.SamplePlan:
    return RP.SamplePlan(
        events=tuple(_event(i) for i in range(events)),
        strata=(),
        seed=1,
        events_per_stratum=1,
    )


def _probe(provider, plan, tmp_path, **kwargs):
    kwargs.setdefault("chunk_size", 1)
    return RP.probe(
        plan=plan,
        provider=provider,
        index=object(),
        provider_keys=("h2h",),
        credit_cap=10_000_000,
        cache_dir=tmp_path / "probe-cache",
        generated_at="2026-09-17T00:00:00Z",
        **kwargs,
    )


def _verdicts(record) -> set[str]:
    return {entry["verdict"] for entry in record["markets"]}


def test_the_probe_stops_when_the_measured_balance_falls_below_the_floor(
    tmp_path, always_matches, no_network
):
    """The breaker the first round fitted to `buy` and not to this.

    Without it an emptied account is invisible here: the provider keeps
    answering, the payload holds no bookmakers, `asked` marks every key in the
    chunk as asked, nothing is priced against them, and `verdict()` returns
    NOT_RETAINED over an empty wallet.
    """
    provider = FakeProvider(balances=[5_000, 4_000, 3, 3, 3])
    record = _probe(
        provider, _sample_plan(6), tmp_path, quota_floor=100, allow_partial=True
    )

    assert record["stopped_on_quota"] is True
    assert record["completed"] is False
    assert record["quota_last_measured"] == 3
    assert provider.responses < 7, (
        "the probe kept asking after the account fell below its floor, and "
        "every answer from here on is an empty payload it will score as "
        "NOT_RETAINED"
    )
    report = RP.render(record)
    assert "STOPPED ON QUOTA" in report
    assert "No verdict in this report is a statement about the archive" in report
    assert ARCHIVE_CLAIM not in report


def test_a_completed_probe_whose_balance_was_never_measured_does_not_claim_the_archive(
    tmp_path, always_matches, no_network
):
    """PROBLEM 1, EXACTLY AS THE REVIEW STATES IT.

    The account empties mid-probe, the provider returns payloads with no
    bookmakers, our own cap is never hit — so `completed` stays True and the
    report reached its `else:` branch and published the archive claim over
    verdicts manufactured out of an empty balance.
    """
    provider = FakeProvider(balances=[None])
    record = _probe(
        provider, _sample_plan(3), tmp_path, quota_floor=100, allow_partial=True
    )
    report = RP.render(record)

    assert record["completed"] is True, "the fixture stopped the run some other way"
    assert record["quota_ever_reported"] is False
    assert RP.Retention.NOT_RETAINED.value in _verdicts(record), (
        "this fixture does not produce the verdict the claim would be made "
        "about, so it cannot test whether the claim is made"
    )
    assert ARCHIVE_CLAIM not in report, (
        "the module that publishes NOT_RETAINED is telling the reader that a "
        "verdict is a fact about the provider's archive, over a run in which "
        "nothing ever measured the account's balance"
    )
    assert "NOT established as a fact about the archive" in report
    assert "reported no remaining account quota on any response" in report
    assert "this run saw no price for it" in report


def test_a_probe_watched_throughout_is_still_allowed_to_name_the_archive(
    tmp_path, always_matches, no_network
):
    """THE CONTROL. Same plan, same empty payloads, same NOT_RETAINED verdicts;
    the only difference is that the balance was measured on every response.
    Without this the test above would pass on a report that had simply lost the
    ability to say anything — and the 2026-09-01 probe's real finding, made
    inside its cap with a healthy balance, is a fact about the archive."""
    provider = FakeProvider(balances=[5_000_000])
    record = _probe(
        provider, _sample_plan(3), tmp_path, quota_floor=100, allow_partial=True
    )
    report = RP.render(record)

    assert record["quota_unwatched_responses"] == 0
    assert RP.Retention.NOT_RETAINED.value in _verdicts(record)
    assert ARCHIVE_CLAIM in report
    assert "measured on every response" in report


def test_a_balance_reported_once_does_not_arm_the_probes_breaker_either(
    tmp_path, always_matches, no_network
):
    """The sticky field, at the site where its consequence is a published
    verdict rather than a census row."""
    provider = FakeProvider(balances=[5_000, None])
    record = _probe(
        provider, _sample_plan(4), tmp_path, quota_floor=100, allow_partial=True
    )
    report = RP.render(record)

    assert record["quota_ever_reported"] is True
    assert record["quota_unwatched_responses"] > 0
    assert record["quota_remaining"] == ""
    assert record["quota_remaining_last_reported"] == "5000"
    assert ARCHIVE_CLAIM not in report
    assert "stopped reporting a remaining account quota" in report
    assert "Every `NOT_RETAINED` in this table means only" in report, (
        "the disclaimer is thirty paragraphs above the table that gets quoted"
    )


def test_a_probe_record_written_before_the_breaker_is_not_a_measured_all_clear(
    tmp_path, always_matches, no_network
):
    """The committed 2026-09-01 record has none of these keys, and its honest
    reading is that nothing measured the balance during it. Every default here
    fails closed rather than rendering it as a watched run."""
    provider = FakeProvider(balances=[5_000_000])
    record = dict(
        _probe(
            provider, _sample_plan(2), tmp_path, quota_floor=100, allow_partial=True
        )
    )
    for key in (
        "stopped_on_quota", "quota_floor", "quota_ever_reported",
        "quota_unwatched_responses", "quota_last_measured",
    ):
        record.pop(key, None)
    report = RP.render(record)

    assert ARCHIVE_CLAIM not in report
    assert "| **Stopped on quota** | unrecorded: this record predates" in report
    assert "This record predates the balance circuit-breaker.**" in report
    assert "had nothing to watch" not in report


# ---------------------------------------------------------------------------
# 4. BOTH REQUEST PATHS, SEPARATELY. A plan whose events share five snapshots
# makes a listing request for most of them, so the listing-path breaker fires
# first and the odds-path one is never reached — which is how deleting the
# odds-path check left every test in this file green. The odds path is the one
# that matters most: it is the response whose emptiness becomes a census reason
# in `buy` and a NOT_RETAINED verdict in `probe`.
# ---------------------------------------------------------------------------


def test_the_buy_breaker_watches_the_odds_requests_not_only_the_listings(
    tmp_path, always_matches, no_network
):
    """One snapshot, so response 1 is the only listing and it reports a healthy
    balance. Every stop after it can only have come from the odds path."""
    provider = FakeProvider(balances=[5_000_000, 5_000_000, 2])
    record = _buy(
        provider,
        _plan(_one_snapshot_segment("core_team", 6)),
        tmp_path,
        quota_floor=100,
    )

    assert record["stopped_on_quota"] is True
    assert provider.responses == 3, (
        "the breaker did not stop the run on the odds response that measured "
        "the balance below the floor"
    )


def test_the_buy_breaker_watches_the_listing_requests_too(
    tmp_path, always_matches, no_network
):
    """The other half. The balance collapses on the very first response, which
    is the slate listing — so a stop here can only have come from the listing
    path, before a single odds request was made."""
    provider = FakeProvider(balances=[2])
    record = _buy(
        provider,
        _plan(_one_snapshot_segment("core_team", 6)),
        tmp_path,
        quota_floor=100,
    )

    assert record["stopped_on_quota"] is True
    assert provider.responses == 1, (
        "the run made an odds request after the slate listing had already "
        "measured the account below its floor"
    )


def test_the_probe_breaker_watches_the_odds_requests_not_only_the_listings(
    tmp_path, always_matches, no_network
):
    """THE MUTANT THAT SURVIVED THE FIRST PASS OF THIS FILE.

    Deleting the probe's odds-path `check_quota` left every test green,
    because the multi-snapshot fixture reached the listing-path breaker first.
    The odds response is the one whose empty payload marks its markets asked
    and unpriced — a NOT_RETAINED verdict — so it is the path that has to be
    watched.
    """
    provider = FakeProvider(balances=[5_000_000, 5_000_000, 2])
    plan = RP.SamplePlan(
        events=tuple(_one_snapshot_event(i) for i in range(6)),
        strata=(), seed=1, events_per_stratum=1,
    )
    record = _probe(provider, plan, tmp_path, quota_floor=100, allow_partial=True)

    assert record["stopped_on_quota"] is True
    assert provider.responses == 3, (
        "the probe did not stop on the odds response that measured the balance "
        "below the floor, so it kept asking for prices nobody would answer and "
        "scoring the empty payloads as NOT_RETAINED"
    )


def test_the_probe_breaker_watches_the_listing_requests_too(
    tmp_path, always_matches, no_network
):
    """The other half, at the site where an unasked market is the honest
    NOT_PROBED answer: the run must stop before it makes an odds request it
    cannot pay for."""
    provider = FakeProvider(balances=[2])
    plan = RP.SamplePlan(
        events=tuple(_one_snapshot_event(i) for i in range(6)),
        strata=(), seed=1, events_per_stratum=1,
    )
    record = _probe(provider, plan, tmp_path, quota_floor=100, allow_partial=True)

    assert record["stopped_on_quota"] is True
    assert provider.responses == 1


def test_a_run_that_bills_nothing_and_reports_no_balance_claims_nothing(
    tmp_path, always_matches, no_network
):
    """PROBLEM 12'S COMPOUND CASE, WHICH THREE CORRECT FIXES ADD UP TO.

    Charging a provider-reported `x-requests-last: 0` as zero is right — it is
    a measurement — but it removes an accidental brake: `credits_spent` never
    grows, so this run's own cap can never stop it. With no
    `x-requests-remaining` either, the breaker has nothing to watch. The run
    then walks the entire plan, stages nothing, records `completed: True`,
    `credits_spent: 0`, `stopped_on_quota: false` — and used to render
    "Anything absent below is absent from the archive rather than absent from
    the budget" over it, which is the reviewer's exact failing scenario.

    The cap is not the thing that had to change. The report is: nothing here
    measured the balance, so nothing here is a statement about the archive.
    """
    provider = FakeProvider(balances=[None], cost="0")
    record = _buy(provider, _plan(_segment("core_team", 4)), tmp_path, quota_floor=100)

    assert record["credits_spent"] == 0
    assert record["zero_billed_responses"] == record["requests_made"]
    assert record["fallback_charges"] == {}, (
        "a zero the provider reported is being charged the pessimistic bound "
        "again, which is the defect the first finding fixed"
    )
    assert record["completed"] is True and record["stopped_on_quota"] is False

    report = H.render(record)
    assert "absent from the archive rather than absent from the budget" not in report
    assert "cannot be attributed to the archive" in report


# ---------------------------------------------------------------------------
# The FOURTH spending script: the line-movement capture
#
# It buys the featured board on a schedule and, until this round, ran no
# pre-flight and no in-run breaker. An emptied account does not make its fetch
# fail: the provider answers with a payload carrying no bookmakers. The capture
# store is this lab's record of which quotes were REACHABLE, so a board
# answered on an empty account is recorded either as a market nobody hung (the
# whole board came back bare, and the script printed the April-to-November
# sentence over it) or — worse, because this one WRITES — as the events the
# balance ran out on, which read at the next capture as prices that vanished.
# That is movement that did not happen, and every survival rate afterwards is
# computed against it.
#
# Every test below drives the script's real `main` through the real
# `OddsApiProvider` with a fake requester. Nothing opens a socket.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, headers):
        self.status_code = 200
        self._payload = payload
        self.headers = headers

    def json(self):
        return self._payload


def _priced_board():
    """One event, three featured markets, one book. Stages to real rows."""
    return [
        {
            "id": "evt-1",
            "sport_key": CBB.provider_sport_key,
            "commence_time": "2027-01-12T23:00:00Z",
            "home_team": "Duke Blue Devils",
            "away_team": "Kansas Jayhawks",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "title": "DraftKings",
                    "last_update": "2027-01-12T19:00:00Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -180},
                                {"name": "Kansas Jayhawks", "price": 150},
                            ],
                        },
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -110, "point": -3.5},
                                {"name": "Kansas Jayhawks", "price": -110, "point": 3.5},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": -110, "point": 142.5},
                                {"name": "Under", "price": -110, "point": 142.5},
                            ],
                        },
                    ],
                }
            ],
        }
    ]


def _load_capture_script():
    spec = importlib.util.spec_from_file_location("_capture_line_movement", CAPTURE_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _capture_provider(*, preflight, balance_after, board, regions="us,us2"):
    """The real adapter over a fake requester, and the requests it was asked.

    `preflight` is what the FREE `/v4/sports` reading reports; `balance_after`
    is what the BILLED response reports (`None` = the header is absent, which
    is the "we do not currently know" case and not a zero).
    """
    asked: list[str] = []

    def requester(url, *, params, timeout):
        asked.append(url)
        if url.endswith("/v4/sports"):
            headers = {}
            if preflight is not None:
                headers["x-requests-remaining"] = str(preflight)
            return _FakeResponse([], headers)
        headers = {"x-requests-last": "6"}
        if balance_after is not None:
            headers["x-requests-remaining"] = str(balance_after)
        return _FakeResponse(board, headers)

    provider = OddsApiProvider(
        CBB,
        environment={"CBB_ODDS_API_KEY": "x" * 20},
        requester=requester,
        regions=regions,
    )
    return provider, asked


def _run_capture(module, monkeypatch, tmp_path, provider):
    monkeypatch.setattr(module, "OddsApiProvider", lambda competition, **kw: provider)
    monkeypatch.setenv("CBB_ODDS_API_KEY", "x" * 32)
    return module.main(
        [
            "--live",
            "--processed-dir", str(tmp_path / "processed"),
            "--output-dir", str(tmp_path / "outputs"),
        ]
    )


def _store_path(tmp_path):
    from cbb_betting_lab import line_movement as LM

    return LM.store_path(CBB, tmp_path / "processed")


def test_the_capture_refuses_to_start_on_a_balance_below_its_cap(
    tmp_path, monkeypatch, no_network, capsys
):
    """Refusal one, and it is free. `/v4/sports` costs nothing.

    The other three paid-data paths have run this since the round that found
    them; this one did not, and `PREFLIGHT_CALLERS` pinned the set at three so
    the gap read as a boundary rather than as the defect it was.
    """
    module = _load_capture_script()
    provider, asked = _capture_provider(
        preflight=12, balance_after=5_000, board=_priced_board()
    )

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    captured = capsys.readouterr()

    assert status == 6, captured.out + captured.err
    assert asked == ["https://api.the-odds-api.com/v4/sports"], (
        f"the capture made {asked} — it billed a request after reading a "
        "balance below its own cap"
    )
    assert "Refusing to start" in captured.out
    assert not _store_path(tmp_path).exists(), "a refused capture wrote a capture"
    assert "prices that vanished" in captured.out, (
        "the refusal does not state what an exhausted account costs THIS "
        "script; an operator handed another caller's reason acts on the wrong "
        "model of what was lost"
    )
    assert "written into the ledger as though it were the night" not in captured.out, (
        "the capture printed the nightly card's reason, for a script with no "
        "ledger and no slate"
    )


def test_the_capture_stops_rather_than_recording_a_board_the_account_could_not_pay_for(
    tmp_path, monkeypatch, no_network, capsys
):
    """THE IN-RUN BREAKER, ON A BOARD THAT CAME BACK WITH QUOTES IN IT.

    This is the case that writes. The pre-flight passed, the response is fully
    formed, and the balance measured ON THAT RESPONSE is below the cost of the
    one request this script makes — so whatever came back cannot be vouched for
    as the whole board. Appending it means the events the account ran out on
    are recorded as present-then-absent, and the next capture reads them as
    prices that were withdrawn. Nothing is written and the run is red.
    """
    module = _load_capture_script()
    provider, asked = _capture_provider(
        preflight=5_000, balance_after=2, board=_priced_board()
    )

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    captured = capsys.readouterr()

    assert status == 7, captured.out + captured.err
    assert len(asked) == 2, f"expected the free reading and one billed call, got {asked}"
    assert "STOPPED ON QUOTA" in captured.err
    assert not _store_path(tmp_path).exists(), (
        "a capture taken on an account measured below its floor was appended "
        "to the reachability store, where it is indistinguishable from a board "
        "the books really did pull"
    )
    assert "no college basketball between April and November" not in captured.out


def test_an_empty_board_on_an_unmeasured_balance_is_not_called_the_off_season(
    tmp_path, monkeypatch, no_network, capsys
):
    """The wallet-as-archive sentence, at its fourth site.

    An emptied account is answered with a payload carrying no bookmakers, which
    is byte-for-byte what a September Tuesday looks like. The script used to
    print "There is no college basketball between April and November, so this
    is an observation and not a fault" over either of them and exit 0. Here the
    provider reported no balance at all on the billed response, so the run has
    not measured which of the two it was and may not name one.
    """
    module = _load_capture_script()
    provider, _ = _capture_provider(preflight=5_000, balance_after=None, board=[])

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    out = capsys.readouterr().out

    assert status == 0, out
    assert not _store_path(tmp_path).exists()
    assert "no college basketball between April and November" not in out, (
        "an empty board on a balance nobody measured was published as a fact "
        "about the calendar"
    )
    assert "cannot say whether the board was empty or the account was" in out


def test_a_measured_healthy_balance_still_calls_an_empty_board_the_off_season(
    tmp_path, monkeypatch, no_network, capsys
):
    """THE CONTROL, and the reason the test above is a gate rather than a gag.

    Same empty payload, same code path; the only difference is that the
    provider reported a healthy balance on the response. That is the one state
    in which "there is no college basketball between April and November" is a
    measurement, and a run that could no longer say it would have lost a real
    observation about the market.
    """
    module = _load_capture_script()
    provider, _ = _capture_provider(preflight=5_000, balance_after=4_994, board=[])

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    out = capsys.readouterr().out

    assert status == 0, out
    assert "no college basketball between April and November" in out
    assert "4,994 credit(s) measured on the account" in out, (
        "the run names the calendar without saying what it measured to be "
        "allowed to"
    )


def test_a_watched_capture_with_quotes_is_still_written(
    tmp_path, monkeypatch, no_network, capsys
):
    """THE SECOND CONTROL. A breaker wired to fire on every run would pass
    every test above while writing nothing all season."""
    module = _load_capture_script()
    provider, _ = _capture_provider(
        preflight=5_000, balance_after=4_994, board=_priced_board()
    )

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    out = capsys.readouterr().out

    assert status == 0, out
    store = _store_path(tmp_path)
    assert store.exists(), "a healthy, watched capture wrote nothing"
    assert len(store.read_text(encoding="utf-8").splitlines()) > 1
    assert "STOPPED ON QUOTA" not in out


def test_the_captures_floor_is_the_cost_of_the_request_it_makes(
    tmp_path, monkeypatch, no_network, capsys
):
    """`bulk keys x regions`, with EACH TERM SEPARATELY OBSERVABLE.

    The floor is a local, so it is read at its boundary rather than asserted as
    a number — and read from both sides of both factors, because a fixture that
    stops at a balance of 2 would stop against a floor of 6, of 3, or of 1, and
    would therefore pin none of them.

    Three featured keys over two regions is 6. A balance of 5 must stop and a
    balance of exactly 6 must not: 6 is a response this run could still have
    been billed for in full, and a floor that refused it would cost the lab
    every capture near the end of a balance. Then the same three keys over
    THREE regions is 9, where a balance of 8 must stop — which a floor that
    forgot `x regions` (3, or 6) would sail past, billing a request the account
    cannot cover and recording whatever partial board came back as the market.
    """
    from cbb_betting_lab import markets as M

    assert len(M.bulk_provider_keys()) == 3, (
        "the bulk call no longer asks three keys; re-pin the literals below"
    )

    module = _load_capture_script()
    just_below, _ = _capture_provider(
        preflight=5_000, balance_after=5, board=_priced_board()
    )
    status = _run_capture(module, monkeypatch, tmp_path / "a", just_below)
    assert status == 7, (
        "5 credits is below the 6 this request costs, and the capture was "
        "taken anyway: a floor read from the keys alone (3) or from one region"
    )
    assert not _store_path(tmp_path / "a").exists()

    at_the_floor, _ = _capture_provider(
        preflight=5_000, balance_after=6, board=_priced_board()
    )
    status = _run_capture(module, monkeypatch, tmp_path / "b", at_the_floor)
    assert status == 0, (
        "a balance of exactly 6 — enough to pay for this request in full — was "
        "refused. The floor is the widest request, not one above it."
    )
    assert _store_path(tmp_path / "b").exists()

    wider, _ = _capture_provider(
        preflight=5_000, balance_after=8, board=_priced_board(), regions="us,us2,uk"
    )
    status = _run_capture(module, monkeypatch, tmp_path / "c", wider)
    capsys.readouterr()
    assert status == 7, (
        "three keys over three regions cost 9 and the run continued on a "
        "measured balance of 8, so the floor dropped `x regions`"
    )
    assert not _store_path(tmp_path / "c").exists()


def test_a_capture_written_on_an_unmeasured_balance_says_the_breaker_was_blind(
    tmp_path, monkeypatch, no_network, capsys
):
    """Quotes came back, so the capture is real and is written. What it cannot
    claim is that it is COMPLETE: with no balance on that response an event
    that came back unpriced could be a market no book hung or one the account
    stopped paying for, and this store's whole output is the difference. The
    absence of a stop is not a measurement."""
    module = _load_capture_script()
    provider, _ = _capture_provider(
        preflight=5_000, balance_after=None, board=_priced_board()
    )

    status = _run_capture(module, monkeypatch, tmp_path, provider)
    out = capsys.readouterr().out

    assert status == 0, out
    assert _store_path(tmp_path).exists(), (
        "an unreported balance is not a reason to withhold a capture that came "
        "back with quotes in it; it is a reason to say it was not watched"
    )
    assert "the breaker had nothing to watch" in out, (
        "a capture nothing measured reads as a fully-observed board"
    )


def test_a_capture_whose_free_reading_cannot_be_taken_does_not_spend(
    tmp_path, monkeypatch, no_network, capsys
):
    """A pre-flight that could not be READ is not a pre-flight that passed.

    `sufficient_quota` deliberately lets an unreadable HEADER through — the
    adapter's cap still holds — but a `/v4/sports` call that raises is a
    different thing: nothing was read at all. Spending after it is spending
    against a number nobody has, which is the swallowed-exit-code defect the
    purchase workflow's `pipefail` was added for.
    """
    module = _load_capture_script()
    provider, asked = _capture_provider(
        preflight=5_000, balance_after=5_000, board=_priced_board()
    )

    def refuse():
        raise ProviderError("the sports listing could not be reached")

    provider.quota = refuse
    status = _run_capture(module, monkeypatch, tmp_path, provider)
    captured = capsys.readouterr()

    assert status == 5, captured.out + captured.err
    assert asked == [], f"the capture billed {asked} after failing to read the balance"
    assert not _store_path(tmp_path).exists()
