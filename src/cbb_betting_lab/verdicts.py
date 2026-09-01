"""Recorded experiment verdicts, read by the things that obey them.

Nothing in this repository ships a modelling policy by assertion. An experiment
measures the policy against real prices, records its verdict as a `ships` list
in a JSON file under `data/outputs/`, and the card and the model read that list
rather than hard-coding the decision — so the shipped configuration is
**auditable against the measurement that made it**, and reverting a policy is
re-running its experiment rather than editing code.

A missing or unreadable verdict file ships nothing. The conservative reading of
"no recorded decision" is "no policy in force".

## Why a file rather than a constant

A constant in code says *what* is in force. It cannot say *why*, *when*, or *on
what evidence*, and it cannot be checked against the experiment that supposedly
justified it. Six months later nobody can tell whether a flag was set because a
measurement won or because it looked sensible on a Tuesday.

## The rule that matters most here

**Each variant tested against the same bought season burns a degree of
freedom.** So a verdict file records `variants_tested`, every report that cites
it prints that count, and a verdict claiming an edge on a season the variant
was selected on is a **candidate**, not a finding.

The football lab learned that the hard way twice over. Its recency-weighting
verdict "was a single-season coin flip": the script scored one season and wrote
a verdict file with one name, so the policy shipped or did not depending on
which season had been run last — +2.3% on 2025 shipped it, −1.8% on 2023 did
not, same policy, same script, opposite verdicts. So a verdict here carries the
**seasons it cleared**, and `ships()` is false unless it cleared all of them.

## Champion/challenger, and the one direction promotion may move

Promotion criteria are pre-registered on disk before a comparison is run
(:data:`PROMOTION_CRITERIA_FILENAME`). A challenger may replace the champion
only by beating it on the price backtest, out of sample, by a margin declared
before the comparison, with the experiment ledger's correction applied.

**Demotion is automatic; promotion of an allowlisted market never is.** An
allowlisted market whose forward ROI interval falls below the floor declared at
approval is auto-withdrawn by `withdraw()`. Granting an allowlist always
requires a receipt Cooper signs. The machine may take a market away from
itself, never give itself one — the NHL lab's precedent, where Claude withdrew
an approval whose evidence had moved and could not have granted it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import OUTPUTS_DIR


#: Where the champion/challenger promotion rules are declared, before any
#: comparison is run. A criteria file written after the numbers are in hand is
#: not a pre-registration, and a test pins its declared_on date against the
#: first promotion that cites it.
PROMOTION_CRITERIA_FILENAME = "promotion_criteria.json"


#: Every verdict this repository can record, and the experiment that records it.
#: A policy absent from here has no door to come through, which is the point:
#: `ships()` raises on an unknown policy rather than returning False, because a
#: typo that silently disables a policy is worse than one that stops a run.
VERDICT_FILES: dict[str, str] = {
    # The preseason prior's weight schedule: how fast this season's games
    # displace the prior built from returning minutes, transfers and
    # recruiting. November is a prior, not a fit, and how quickly that stops
    # being true is a measured question rather than a chosen constant.
    "november_prior_schedule": "november_prior_experiment",
    # Whether a venue-level home effect, shrunk toward the league mean, beats
    # a single league-wide constant on the price backtest.
    "venue_home_effect": "home_advantage_experiment",
    # Whether an explicit end-game segment (clock, margin, foul state) beats
    # extrapolating full-game efficiency through the last two minutes.
    "endgame_segment_model": "endgame_experiment",
    # Whether overtime modelled as its own segment beats scaling the
    # regulation distribution.
    "overtime_segment_model": "overtime_experiment",
    # Whether the schedule-state adjustments (rest, travel, altitude,
    # conference-tournament fatigue) ship. A measured adjustment ships because
    # it wins the price backtest; a better-calibrated one that loses is refused.
    "schedule_state_adjustment": "schedule_states_experiment",
    # Whether per-conference-tier fits beat one pooled fit.
    "conference_tier_fits": "tier_fit_experiment",
    # Whether walk-forward isotonic calibration ships. Calibration can rule a
    # model out and never in, so this verdict is decided by the price backtest.
    "calibration_correction": "calibration_experiment",
    # Whether a player prop may produce a selection for a player whose
    # availability cannot be confirmed. Expected to stay off: D-I basketball
    # has no mandated injury report, and a gate that reads a missing feed as
    # "nobody is injured" clears an entire slate.
    "props_selectable_when_unconfirmed": "availability_policy",
    # Which model is champion. Written only by the promotion run, and only
    # when the pre-registered criteria are met.
    "champion_model": "champion_challenger",
}


@dataclass(frozen=True)
class Verdict:
    """One recorded decision, and the evidence that made it."""

    policy: str
    ships: bool
    measured_on: str = ""
    variants_tested: int = 0
    seasons_cleared: tuple[int, ...] = ()
    seasons_tested: tuple[int, ...] = ()
    summary: str = ""

    def citation(self) -> str:
        """The sentence a report prints beside anything this verdict governs."""
        state = "in force" if self.ships else "not in force"
        line = f"`{self.policy}` is **{state}**"
        if self.measured_on:
            line += f", decided on {self.measured_on}"
        if self.variants_tested > 1:
            line += (
                f", one of **{self.variants_tested} variants** tested against "
                "the same data — a degree of freedom spent, and the reason "
                "this is a candidate rather than a finding"
            )
        if self.seasons_tested:
            line += (
                f", cleared {len(self.seasons_cleared)} of "
                f"{len(self.seasons_tested)} seasons tested"
            )
        return line + ("." if not self.summary else f". {self.summary}")


def verdict_path(
    policy: str, competition: Competition, output_dir: Path | None = None
) -> Path:
    stem = VERDICT_FILES.get(str(policy))
    if stem is None:
        raise KeyError(
            f"No experiment records a verdict for {policy!r}. Known: "
            f"{sorted(VERDICT_FILES)}"
        )
    directory = Path(output_dir) if output_dir else Path(OUTPUTS_DIR)
    return directory / competition.output_name(stem, ".json")


def read(
    policy: str, competition: Competition, *, output_dir: Path | None = None
) -> Verdict:
    """The recorded verdict, or a not-in-force one when there is none."""
    path = verdict_path(policy, competition, output_dir)
    absent = Verdict(policy=policy, ships=False, summary="No verdict is recorded.")
    if not path.is_file():
        return absent
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return Verdict(
            policy=policy,
            ships=False,
            summary=f"The verdict file at {path.name} could not be read.",
        )
    if not isinstance(payload, dict):
        return absent
    listed = payload.get("ships")
    named = isinstance(listed, list) and str(policy) in [str(x) for x in listed]
    cleared = tuple(int(s) for s in payload.get("seasons_cleared", []) or [])
    tested = tuple(int(s) for s in payload.get("seasons_tested", []) or [])

    # The football lab's single-season coin flip, closed. A policy that cleared
    # one of three seasons and was written up on the season it happened to be
    # run against last is not a policy that cleared. Where a verdict names the
    # seasons it was tested on, it ships only if it cleared all of them.
    shipped = named and (not tested or set(cleared) >= set(tested))
    summary = str(payload.get("summary", ""))
    if named and not shipped:
        summary = (
            f"Recorded as shipping, but it cleared only {sorted(cleared)} of "
            f"{sorted(tested)} seasons tested, so it does not ship. " + summary
        ).strip()
    return Verdict(
        policy=policy,
        ships=shipped,
        measured_on=str(payload.get("measured_on", "")),
        variants_tested=int(payload.get("variants_tested", 0) or 0),
        seasons_cleared=cleared,
        seasons_tested=tested,
        summary=summary,
    )


def ships(
    policy: str, competition: Competition, *, output_dir: Path | None = None
) -> bool:
    """Whether the recorded verdict for `policy` says it is in force."""
    return read(policy, competition, output_dir=output_dir).ships


def record(
    policy: str,
    competition: Competition,
    *,
    ships_it: bool,
    measured_on: str,
    variants_tested: int,
    summary: str,
    seasons_cleared: tuple[int, ...] = (),
    seasons_tested: tuple[int, ...] = (),
    output_dir: Path | None = None,
) -> Path:
    """Write a verdict. Only an experiment calls this, never the card.

    The separation is the design: the thing that measures writes the verdict,
    the thing that prices reads it, and neither can quietly become the other.
    """
    path = verdict_path(policy, competition, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "policy": policy,
                "competition": competition.key,
                "ships": [policy] if ships_it else [],
                "measured_on": measured_on,
                "variants_tested": variants_tested,
                "seasons_cleared": list(seasons_cleared),
                "seasons_tested": list(seasons_tested),
                "summary": summary,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def describe(competition: Competition, *, output_dir: Path | None = None) -> str:
    """One line per policy, for run logs and the card."""
    return ", ".join(
        f"{policy}="
        f"{'in force' if ships(policy, competition, output_dir=output_dir) else 'off'}"
        for policy in sorted(VERDICT_FILES)
    )
