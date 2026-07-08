"""State and diff invariant tests.

These pin the guarantees the engine makes about every world-state value and
every recorded change: bounds are enforced, and every diff is explainable.
"""

from __future__ import annotations

import pytest

from engine import seed_data, turn
from engine.diffs import apply_diffs
from engine.models import Campaign, SourceType
from engine.state import MAX_VALUE, MIN_VALUE, clamp, in_bounds


# ---------------------------------------------------------------------------
# Clamping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    (-5, 0),
    (0, 0),
    (3.4, 3),
    (3.6, 4),
    (50, 50),
    (100, 100),
    (150, 100),
    (99.5, 100),
])
def test_clamp_enforces_bounds(value, expected):
    assert clamp(value) == expected
    assert in_bounds(clamp(value))


def test_clamp_returns_int():
    assert isinstance(clamp(3.7), int)
    assert isinstance(clamp(-1), int)


# ---------------------------------------------------------------------------
# Diff application
# ---------------------------------------------------------------------------

def test_apply_diffs_returns_explainable_records():
    variables = {"water_security": 50, "budget_capacity": 40, "unused": 0}
    diffs = apply_diffs(
        variables,
        {"water_security": +12, "budget_capacity": -5, "missing_var": +3, "unused": 0},
        reason="test advice",
        source_type=SourceType.ADVICE,
    )

    # Only known, non-zero deltas produce diffs.
    assert [d.variable for d in diffs] == ["water_security", "budget_capacity"]
    assert variables["water_security"] == 62
    assert variables["budget_capacity"] == 35
    for diff in diffs:
        assert diff.reason == "test advice"
        assert diff.source_type == SourceType.ADVICE
        assert diff.delta == diff.new_value - diff.old_value
        assert in_bounds(diff.new_value)


def test_apply_diffs_clamps_and_reports_effective_delta():
    variables = {"public_trust": 98}
    diffs = apply_diffs(variables, {"public_trust": +10}, reason="r", source_type="advice")
    assert len(diffs) == 1
    diff = diffs[0]
    assert diff.old_value == 98
    assert diff.new_value == MAX_VALUE          # clamped
    assert diff.delta == 2                       # effective, not requested (10)


# ---------------------------------------------------------------------------
# Bounds invariant across an entire campaign
# ---------------------------------------------------------------------------

def test_all_state_values_remain_in_bounds_through_a_campaign():
    campaign = seed_data.create_northbridge_campaign()
    sequence = [
        "controlled_disclosure", "contractor_pressure", "mutual_aid",
        "controlled_disclosure", "state_support", "controlled_disclosure",
        "mutual_aid", "contractor_pressure", "controlled_disclosure", "mutual_aid",
    ]
    for advice_id in sequence:
        for value in campaign.world_state.variables.values():
            assert MIN_VALUE <= value <= MAX_VALUE
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)

    # Final state after the loop also respects bounds.
    for value in campaign.world_state.variables.values():
        assert in_bounds(value)


def test_starting_state_is_in_bounds():
    campaign = seed_data.create_northbridge_campaign()
    for value in campaign.world_state.variables.values():
        assert in_bounds(value)
    for faction in campaign.world_state.factions:
        assert in_bounds(faction.influence)


# ---------------------------------------------------------------------------
# Required state variables are present
# ---------------------------------------------------------------------------

REQUIRED_VARIABLES = {
    "water_security", "power_stability", "public_trust", "public_order",
    "budget_capacity", "staff_capacity", "legal_exposure", "media_pressure",
    "hospital_stability", "school_disruption", "state_oversight_risk",
    "contractor_dependency", "information_integrity", "player_reputation",
    "player_perceived_neutrality", "player_shadow_authority",
}


def test_seed_state_contains_all_required_variables():
    campaign = seed_data.create_northbridge_campaign()
    present = set(campaign.world_state.variables)
    missing = REQUIRED_VARIABLES - present
    assert not missing, f"missing required state variables: {missing}"


def test_advice_effects_only_reference_known_variables():
    campaign = seed_data.create_northbridge_campaign()
    known = set(campaign.world_state.variables)
    for option in campaign.advice_options:
        unknown = set(option.effects) - known
        assert not unknown, f"{option.id} affects unknown variables: {unknown}"
