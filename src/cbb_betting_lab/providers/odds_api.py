"""The Odds API adapter. Shadow-only by construction.

What this module does: reach the provider, count what it costs, and hand back
raw payloads. What it does not do, ever: decide anything, or normalise anything
into this lab's vocabulary — that is `providers/staging.py`, deliberately a
different file, so the thing that spends money and the thing that interprets
the answer cannot quietly become one.

The card cannot read `data/staging/`. It reads only markets a reviewed policy
allowlists. So a fetch can be wrong, incomplete, or surprising without a single
pick changing.

## The credential

Read from `CBB_ODDS_API_KEY` in the environment (a GitHub secret in CI, a
gitignored `.env` locally). It is never written to a report, a provenance file,
a staged row, or a log line. Every string that reaches a report goes through
`redact`, and `tests/test_no_secrets_committed.py` fails the build if a key
shape ever reaches a tracked file.

**The key is never passed as a command-line argument.** A process list is
world-readable on a shared machine and a CI log echoes commands.

## What a fetch costs

* `/v4/sports` and `/v4/sports/{sport}/events` — **free**.
* `/v4/sports/{sport}/odds` — `markets x regions`, whole slate.
* `/v4/sports/{sport}/events/{id}/odds` — `unique markets **returned** x
  regions`. An asked-for market nobody quotes costs nothing.
* `/v4/sports/{sport}/scores?daysFrom=N` — 2.
* every `/v4/historical/...` equivalent — **10x** the live rate.

Every entry point states its cost before spending it and takes a hard cap, so a
probe cannot become a bill by accident. The cap is checked **before** each
request against the pessimistic bound, and the real spend is read afterwards
from `x-requests-last` rather than assumed.

That last sentence is the NHL lab's most expensive lesson in this file. Its
purchase estimated cost from the markets it *asked* for; the provider bills per
market *returned*, and every alternate ladder bills on its own. A run capped at
200,000 spent **289,984** while the code and its test both asserted the cap
"cannot be breached". The estimate is still the documented multiplier, because
a guess dressed as a bound is worse than a guess — but the cap is enforced
against the measured running total, which is the gate that cannot be
mis-specified.

## The sport key comes from the competition registry

Never from a literal here. That is what makes this machinery copyable, and
`tests/test_competition_registry_is_the_only_place.py` fails the build if this
module ever writes one.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.providers.env_file import redact


API_KEY_ENV = "CBB_ODDS_API_KEY"
API_BASE_URL_ENV = "CBB_ODDS_API_BASE_URL"
DEFAULT_API_BASE_URL = "https://api.the-odds-api.com"

#: Only these hosts. A base-URL override is a convenience for testing against a
#: local mock, not a way to point the credential at an arbitrary server.
ALLOWED_API_HOSTS = frozenset({"api.the-odds-api.com", "ipv6-api.the-odds-api.com"})

PROVIDER_KEY = "odds_api"
PROVIDER_NAME = "the_odds_api"
PROVIDER_TYPE = "odds_api"

#: Cooper's instruction: regions stay `us,us2`. A price at a book he cannot
#: open is not reachable and manufactures untakeable edges, which is the single
#: most important thing this lab is trying not to do.
DEFAULT_REGIONS = "us,us2"

#: The only markets the bulk endpoint will serve. Anything else there makes the
#: provider refuse the whole request with a 422 that names nothing — which took
#: down every team-market fetch in the NHL lab and looked like an off-season
#: for two rounds of debugging, because the season genuinely had not started.
BULK_SAFE_MARKETS: frozenset[str] = frozenset({"h2h", "spreads", "totals"})

#: The only response headers that may be recorded. Everything else in a
#: response's headers is either useless here or a place a credential could
#: hide; an allowlist is the safe shape.
SAFE_RESPONSE_HEADERS = (
    "x-requests-remaining",
    "x-requests-used",
    "x-requests-last",
)

#: Historical endpoints bill ten times the live rate. Used only as a pre-flight
#: upper bound, so the cap can be over-respected but never breached. Real spend
#: is read from `x-requests-last`.
HISTORICAL_MULTIPLIER = 10

#: The historical events listing. Documented flatly at 1, and free when it
#: finds nothing.
HISTORICAL_EVENTS_LIST_COST = 1


class ProviderError(RuntimeError):
    """The provider could not be used. Never carries a credential."""


class MissingCredentialError(ProviderError):
    """No key is available, so nothing live may be attempted."""


class CreditCapReached(ProviderError):
    """The next request could breach the cap, so it was not made."""


Requester = Callable[..., Any]


def _default_requester(url: str, *, params: Mapping[str, str], timeout: float) -> Any:
    return requests.get(url, params=dict(params), timeout=timeout)


def markets_fingerprint(markets: tuple[str, ...]) -> str:
    """A stable short digest of a market list, for cache filenames.

    Ported from the NHL lab because the football lab's probe **did not port
    it** and paid for that: it cached chunk responses under a filename tagged
    with the chunk's *length*, so four ten-market chunks collided and three
    were lost. The length of a list is not its identity. This is.
    """
    joined = ",".join(sorted(str(m) for m in markets))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


@dataclass
class Spend:
    """What a run actually cost, measured rather than estimated."""

    credits_spent: int = 0
    requests_made: int = 0
    quota_remaining: str = ""
    quota_used: str = ""
    #: What the pessimistic pre-flight bound would have predicted, kept so the
    #: two can be compared in the report. A large gap is information: it means
    #: most asked markets are not quoted.
    credits_estimated: int = 0
    notes: list[str] = field(default_factory=list)

    def record(self, headers: Mapping[str, str], *, fallback: int) -> int:
        """Charge one response, preferring the measured cost over the guess.

        A missing `x-requests-last` charges the pessimistic fallback. Guessing
        low would let a run drift past its cap while reporting that it had not.
        """
        self.requests_made += 1
        try:
            actual = int(str(headers.get("x-requests-last", "")).strip())
        except (TypeError, ValueError):
            actual = 0
        if actual <= 0:
            actual = int(fallback)
            self.notes.append(
                "A response carried no `x-requests-last`; charged the "
                f"pessimistic estimate of {fallback} against the cap instead."
            )
        self.credits_spent += actual
        for header, attribute in (
            ("x-requests-remaining", "quota_remaining"),
            ("x-requests-used", "quota_used"),
        ):
            value = str(headers.get(header, "")).strip()
            if value:
                setattr(self, attribute, value)
        return actual

    def summary_line(self) -> str:
        line = (
            f"{self.credits_spent:,} credit(s) actually spent over "
            f"{self.requests_made} request(s)"
        )
        if self.credits_estimated:
            line += f"; the pessimistic pre-flight bound was {self.credits_estimated:,}"
        if self.quota_remaining:
            line += f"; {self.quota_remaining} remaining"
        return line + "."


def _guard(spend: Spend, credit_cap: int, bound: int, what: str) -> None:
    """Refuse a request that could take the run past its cap.

    Checked against the **measured** running total plus the pessimistic bound
    for the request about to be made. Both halves matter: measuring the total
    is what the NHL lab lacked, and bounding the next request pessimistically
    is what stops the last request of a run overshooting by a ladder's worth.
    """
    if credit_cap <= 0:
        raise CreditCapReached(
            f"Refusing to fetch {what}: the credit cap is {credit_cap}."
        )
    if spend.credits_spent + bound > credit_cap:
        raise CreditCapReached(
            f"Refusing to fetch {what}: {spend.credits_spent:,} credits already "
            f"spent and this request is bounded at {bound:,}, which would "
            f"exceed the cap of {credit_cap:,}. Nothing was fetched."
        )


class OddsApiProvider:
    """One door to the provider. Every request in this repository goes through it.

    One door on purpose. Two callers building their own requests is how a
    credential reaches a log, how a cap gets bypassed, and how two copies of the
    billing rules drift apart.
    """

    def __init__(
        self,
        competition: Competition,
        *,
        environment: Mapping[str, str] | None = None,
        requester: Requester | None = None,
        regions: str = DEFAULT_REGIONS,
        timeout_seconds: float = 30.0,
        sport_key: str | None = None,
    ) -> None:
        self.competition = competition
        self.environment = dict(os.environ if environment is None else environment)
        self.requester = requester or _default_requester
        self.regions = (regions or DEFAULT_REGIONS).strip()
        self.timeout_seconds = float(timeout_seconds)
        # Futures live under their own sport keys, which come from the registry
        # too. An override is how a futures fetch reaches them without a second
        # provider class holding a second copy of the billing rules.
        self._sport_key_override = str(sport_key or "").strip()
        self._validate_base_url()

    # -- configuration ---------------------------------------------------

    @property
    def api_key(self) -> str:
        return str(self.environment.get(API_KEY_ENV, "")).strip()

    @property
    def base_url(self) -> str:
        return (
            str(self.environment.get(API_BASE_URL_ENV) or DEFAULT_API_BASE_URL)
            .strip()
            .rstrip("/")
        )

    @property
    def sport_key(self) -> str:
        """From the registry. Never a literal in this module."""
        if self._sport_key_override:
            if self._sport_key_override not in (
                self.competition.provider_sport_key,
                *self.competition.futures_sport_keys,
            ):
                raise ProviderError(
                    f"Sport key {self._sport_key_override!r} is not one this "
                    "competition declares. The registry is the only place a "
                    "sport key may be written down."
                )
            return self._sport_key_override
        return self.competition.provider_sport_key

    def _validate_base_url(self) -> None:
        host = (urlparse(self.base_url).hostname or "").lower()
        if host in ALLOWED_API_HOSTS:
            return
        if host in {"localhost", "127.0.0.1", "::1"}:
            # A local mock is the only other permitted target, and only because
            # a test that cannot run offline is a test nobody runs.
            return
        raise ProviderError(
            f"Refusing to send the credential to host {host!r}. Allowed: "
            f"{sorted(ALLOWED_API_HOSTS)} or a localhost mock."
        )

    def _require_credential(self) -> None:
        if not self.api_key:
            raise MissingCredentialError(
                f"A live fetch requires `{API_KEY_ENV}` from the environment, a "
                "gitignored local `.env`, or a GitHub Secret. Never pass the "
                "key as a command argument and never commit it."
            )

    # -- the one request path --------------------------------------------

    def _get(self, url: str, params: Mapping[str, str]) -> tuple[Any, dict[str, str]]:
        try:
            response = self.requester(
                url, params=dict(params), timeout=self.timeout_seconds
            )
        except (requests.RequestException, OSError, TimeoutError) as exc:
            raise ProviderError(
                redact(
                    f"The odds provider could not be reached "
                    f"({type(exc).__name__}). Nothing was written."
                )
            ) from exc
        status = int(getattr(response, "status_code", 0) or 0)
        if status != 200:
            # The status alone, never the URL: the URL carries the key.
            raise ProviderError(
                f"The odds provider returned HTTP {status or 'unknown'}. "
                "Nothing was written."
            )
        try:
            payload = response.json()
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProviderError("The odds provider returned unreadable JSON.") from exc
        headers = getattr(response, "headers", {}) or {}
        safe = {
            name: str(headers.get(name, ""))
            for name in SAFE_RESPONSE_HEADERS
            if headers.get(name) is not None
        }
        return payload, safe

    # -- free endpoints ---------------------------------------------------

    def quota(self) -> dict[str, str]:
        """Remaining and used, from the free `/v4/sports` listing."""
        self._require_credential()
        _, headers = self._get(f"{self.base_url}/v4/sports", {"apiKey": self.api_key})
        return headers

    def list_sports(self) -> list[dict[str, Any]]:
        """Every sport key the provider serves. Free.

        Used to establish which basketball keys actually exist rather than
        assuming them, which is how the futures keys got into the registry.
        """
        self._require_credential()
        payload, _ = self._get(
            f"{self.base_url}/v4/sports", {"apiKey": self.api_key, "all": "true"}
        )
        if not isinstance(payload, list):
            raise ProviderError("The sports listing is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    def list_events(self) -> list[dict[str, Any]]:
        """The upcoming slate. Free, and **upcoming only**.

        Pointing this at a past window returns nothing, which looks exactly
        like "the provider has no data" and is not. Past slates come from
        `list_historical_events`.
        """
        self._require_credential()
        payload, _ = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/events",
            {"apiKey": self.api_key, "dateFormat": "iso"},
        )
        if not isinstance(payload, list):
            raise ProviderError("The events list is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    # -- live prices ------------------------------------------------------

    def fetch_bulk(
        self, markets: tuple[str, ...], *, spend: Spend, credit_cap: int
    ) -> list[dict[str, Any]]:
        """The featured markets for the whole slate, in one call.

        Billed `markets x regions` regardless of how many events come back,
        which is why the featured markets are never asked for per event. On a
        hundred-game January Tuesday that distinction is the difference between
        six credits and six hundred.
        """
        self._require_credential()
        forbidden = tuple(m for m in markets if m not in BULK_SAFE_MARKETS)
        if forbidden:
            raise ProviderError(
                f"{forbidden} cannot be asked of the bulk endpoint; the "
                "provider refuses the whole request with a 422 that names "
                "nothing. Ask them per event."
            )
        bound = len(markets) * self._region_count()
        _guard(spend, credit_cap, bound, "the bulk slate")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
        )
        spend.record(headers, fallback=bound)
        if not isinstance(payload, list):
            raise ProviderError("The bulk odds response is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    def fetch_event_odds(
        self,
        event_id: str,
        markets: tuple[str, ...],
        *,
        spend: Spend,
        credit_cap: int,
    ) -> dict[str, Any]:
        """One event's non-featured markets.

        Billed `unique markets **returned** x regions`, so an asked-for market
        nobody quotes costs nothing — which is why the ladders and props are
        carried on every game rather than written off, and why a market
        unquoted in September establishes nothing about December.
        """
        self._require_credential()
        bound = len(markets) * self._region_count()
        _guard(spend, credit_cap, bound, f"event {event_id}")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/events/{event_id}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
            },
        )
        spend.record(headers, fallback=bound)
        return payload if isinstance(payload, Mapping) else {}

    def fetch_scores(
        self, *, days_from: int, spend: Spend, credit_cap: int
    ) -> list[dict[str, Any]]:
        """Final scores for recent games. Billed flat at 2.

        Not the settlement source — that is the box score — but the fastest way
        to know a game has *finished*, which is what the tip-time guard and the
        settlement scheduler need.
        """
        self._require_credential()
        _guard(spend, credit_cap, 2, "scores")
        spend.credits_estimated += 2
        payload, headers = self._get(
            f"{self.base_url}/v4/sports/{self.sport_key}/scores",
            {
                "apiKey": self.api_key,
                "daysFrom": str(int(days_from)),
                "dateFormat": "iso",
            },
        )
        spend.record(headers, fallback=2)
        if not isinstance(payload, list):
            raise ProviderError("The scores response is not a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    def _region_count(self) -> int:
        return len([r for r in self.regions.split(",") if r.strip()]) or 1

    # -- historical -------------------------------------------------------

    def list_historical_events(
        self, snapshot: str, *, spend: Spend, credit_cap: int
    ) -> list[dict[str, Any]]:
        """Events on the slate at a past instant, plus what the lookup cost."""
        self._require_credential()
        _guard(spend, credit_cap, HISTORICAL_EVENTS_LIST_COST, "a historical slate")
        spend.credits_estimated += HISTORICAL_EVENTS_LIST_COST
        payload, headers = self._get(
            f"{self.base_url}/v4/historical/sports/{self.sport_key}/events",
            {"apiKey": self.api_key, "date": str(snapshot), "dateFormat": "iso"},
        )
        spend.record(headers, fallback=HISTORICAL_EVENTS_LIST_COST)
        data = payload.get("data") if isinstance(payload, Mapping) else payload
        return [item for item in (data or []) if isinstance(item, dict)]

    def historical_event_odds(
        self,
        event_id: str,
        snapshot: str,
        markets: tuple[str, ...],
        *,
        spend: Spend,
        credit_cap: int,
    ) -> dict[str, Any]:
        """One event's prices at a past instant.

        Billed at `10 x unique markets **returned** x regions`, so a market
        nobody retained costs nothing — but the cap is checked against every
        market being returned, which is the only direction it is safe to be
        wrong in.
        """
        self._require_credential()
        bound = HISTORICAL_MULTIPLIER * len(markets) * self._region_count()
        _guard(spend, credit_cap, bound, f"event {event_id}")
        spend.credits_estimated += bound
        payload, headers = self._get(
            f"{self.base_url}/v4/historical/sports/{self.sport_key}/events/"
            f"{event_id}/odds",
            {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": ",".join(markets),
                "oddsFormat": "american",
                "dateFormat": "iso",
                "date": str(snapshot),
            },
        )
        spend.record(headers, fallback=bound)
        data = payload.get("data") if isinstance(payload, Mapping) else payload
        return data if isinstance(data, Mapping) else {}


def sufficient_quota(headers: Mapping[str, str], credit_cap: int) -> tuple[bool, str]:
    """Whether there are enough credits left to start a run at all.

    Refusing is the safe direction. A run that starts with less than its cap
    gets partway through the slate and stops, leaving a snapshot holding the
    games it happened to reach — a biased subset frozen into the ledger as
    though it were the day, and forward evidence cannot be re-made.

    In this sport the bias has a shape: the fetch works through the slate in
    tip order, so a starved run keeps the early games and drops the late ones —
    which is exactly the West Coast, low-major end of the board this lab was
    built to look at.

    An unreadable header does **not** block the run: the guard exists to catch
    a known shortfall, not to make an unreadable response fatal, and the
    adapter's own cap still cannot be breached.
    """
    remaining = str(headers.get("x-requests-remaining", "")).strip()
    if not remaining.lstrip("-").isdigit():
        return True, (
            "The provider did not report a remaining quota. Proceeding: the "
            "per-request cap still cannot be breached."
        )
    left = int(remaining)
    if left < credit_cap:
        return False, (
            f"Only {left:,} credits remain against a cap of {credit_cap:,}. "
            "Refusing to start: a run that stops halfway through the slate "
            "freezes the early tips and drops the late ones, which is a biased "
            "subset written into the ledger as though it were the night."
        )
    return True, f"{left:,} credits remain against a cap of {credit_cap:,}."
