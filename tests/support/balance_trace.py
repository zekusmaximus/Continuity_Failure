"""Instrumented full playthroughs for balance work.

Run before tuning ANY new pressure (degradation drift, variant starting
states, new advice effects):

    python tests/support/balance_trace.py [variant_id]

With a seed-variant id, every sequence plays against that authored starting
state instead of the baseline.

Prints a per-turn trace of the variables closest to failure thresholds for
the three canonical strategies -- the pinned SURVIVAL_SEQUENCE, contractor
spam, and delay spam -- plus each run's minimum headroom to every failure
threshold. The canonical survival run completes with only ~2 points of
budget headroom, so any added pressure must be checked against these
numbers, not intuition. Include the traces in the commit message of any
change that moves them (which also requires a ruleset-version bump; see
tests/test_ruleset_version.py).

Lives under tests/support/ (not engine/) so the stdlib-only AST scan of the
engine package does not apply; imports only the engine.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine import seed_data, turn                     # noqa: E402
from engine.models import Campaign                     # noqa: E402
from engine.rules import FAILURE_THRESHOLDS            # noqa: E402

SURVIVAL_SEQUENCE = [
    "controlled_disclosure",
    "contractor_pressure",
    "mutual_aid",
    "controlled_disclosure",
    "state_support",
    "controlled_disclosure",
    "mutual_aid",
    "contractor_pressure",
    "controlled_disclosure",
    "mutual_aid",
]

CANONICAL_SEQUENCES = {
    "SURVIVAL_SEQUENCE": SURVIVAL_SEQUENCE,
    "contractor-spam": ["contractor_pressure"] * 10,
    "delay-spam": ["delay_disclosure"] * 10,
}

WATCH = [
    "budget_capacity", "legal_exposure", "state_oversight_risk",
    "water_security", "public_trust", "hospital_stability", "public_order",
    "media_pressure", "contractor_dependency", "power_stability",
]

_THRESHOLDS = {var: (op, threshold) for var, op, threshold in FAILURE_THRESHOLDS}


def headroom(variable: str, value: int):
    """Distance from a failure threshold; None if the variable has none."""
    if variable not in _THRESHOLDS:
        return None
    op, threshold = _THRESHOLDS[variable]
    return value - threshold if op == "<=" else threshold - value


def run_sequence(sequence, variant_id: str = "") -> Campaign:
    """Play a fresh Northbridge campaign through ``sequence``; stop at terminal."""
    campaign = seed_data.create_northbridge_campaign(
        name="balance-trace", variant_id=variant_id
    )
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    return campaign


def trace(name: str, sequence, variant_id: str = "") -> Campaign:
    """Play ``sequence`` printing a per-turn table and min-headroom summary."""
    campaign = seed_data.create_northbridge_campaign(
        name=name, variant_id=variant_id
    )
    print(f"\n=== {name} ===")
    print("turn advice                 "
          + " ".join(f"{v[:12]:>12}" for v in WATCH))
    v = campaign.world_state.variables
    print(f"{'start':>4} {'':22}" + " ".join(f"{v[var]:>12}" for var in WATCH))
    min_headroom = {}
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        resolving = campaign.turn_number
        turn.advance_turn(campaign, advice_id)
        v = campaign.world_state.variables
        print(f"{resolving:>4} {advice_id[:22]:22}"
              + " ".join(f"{v[var]:>12}" for var in WATCH))
        for var in WATCH:
            h = headroom(var, v[var])
            if h is not None and (var not in min_headroom or h < min_headroom[var][0]):
                min_headroom[var] = (h, resolving)
    print(f"outcome: {campaign.status}"
          + (f" — {campaign.failure_reason}" if campaign.failure_reason else ""))
    print("min headroom to failure threshold (value, at turn):")
    for var, (h, at_turn) in sorted(min_headroom.items(), key=lambda kv: kv[1][0]):
        print(f"  {var:24} {h:>3}  (turn {at_turn})")
    return campaign


if __name__ == "__main__":
    variant = sys.argv[1] if len(sys.argv) > 1 else ""
    if variant:
        print(f"seed variant: {variant}")
    for name, sequence in CANONICAL_SEQUENCES.items():
        trace(name, sequence, variant_id=variant)
