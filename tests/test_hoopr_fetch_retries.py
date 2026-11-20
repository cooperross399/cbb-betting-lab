"""A cut-off download is asked for again; a 404 is an answer and is not.

2026-11-20: one IncompleteRead on the current season's play-by-play stopped
the table build, and the morning card ran with no results tables and refused.
"""

from __future__ import annotations

import http.client
import urllib.error

import pytest

from cbb_betting_lab.data import hoopr


def _scripted(monkeypatch, outcomes):
    calls = []

    def once(url, *, timeout):
        calls.append(url)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(hoopr, "_http_get_once", once)
    return calls


def test_a_cut_off_body_is_asked_for_again(monkeypatch):
    calls = _scripted(monkeypatch, [http.client.IncompleteRead(b"x" * 10, 5), b"whole"])
    slept = []
    assert hoopr._http_get("https://x/pbp_2027.parquet", sleep=slept.append) == b"whole"
    assert len(calls) == 2 and slept == [hoopr.FETCH_BACKOFF_S]


def test_a_feed_that_never_arrives_is_a_feed_error_not_a_traceback(monkeypatch):
    cut = http.client.IncompleteRead(b"", 1)
    calls = _scripted(monkeypatch, [cut] * hoopr.FETCH_ATTEMPTS)
    with pytest.raises(hoopr.FeedError, match="IncompleteRead after 4"):
        hoopr._http_get("https://x/pbp_2027.parquet", sleep=lambda s: None)
    assert len(calls) == hoopr.FETCH_ATTEMPTS


def test_a_404_is_an_answer_and_is_not_retried(monkeypatch):
    missing = urllib.error.HTTPError("https://x/a", 404, "nf", {}, None)
    calls = _scripted(monkeypatch, [missing, b"never"])
    with pytest.raises(hoopr.NotPublishedYet):
        hoopr._http_get("https://x/a", sleep=lambda s: None)
    assert len(calls) == 1


def test_a_server_error_is_retried(monkeypatch):
    busy = urllib.error.HTTPError("https://x/a", 503, "busy", {}, None)
    calls = _scripted(monkeypatch, [busy, b"ok"])
    assert hoopr._http_get("https://x/a", sleep=lambda s: None) == b"ok"
    assert len(calls) == 2
