"""Deterministic-engine tests: turn flow, failure, completion, determinism.

These tests import only the ``engine`` package and must pass with no web server
or FastAPI dependency present (design rule: the engine is framework-free).
"""

from __future__ import annotations

import sys

import pytest

from engine import seed_data, turn
from engine.models import (
    AdviceOption,
    Campaign,
    CampaignStatus,
    DecisionType,
)
from engine.rules import (
    FAILURE_THRESHOLDS,
    AMBIENT_DRIFT,
    check_failure,
)
from engine.state import MIN_VALUE, clamp


VALID_DECISION_TYPES = {
    DecisionType.FOLLOWED,
    DecisionType.PARTIALLY_FOLLOWED,
    DecisionType.MODIFIED,
    DecisionType.DELAYED,
    DecisionType.REJECTED,
}

# A known-good strategy that stabilizes Northbridge without tripping a failure
# threshold. Pinned here so the completion test is explicit, not emergent.
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


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


# ---------------------------------------------------------------------------
# Turn flow
# ---------------------------------------------------------------------------

def test_advance_turn_increments_turn_number():
    campaign = _fresh_campaign()
    assert campaign.turn_number == 1
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert result.turn_number == 1           # the turn that was just resolved
    assert campaign.turn_number == 2         # advanced to next
    assert len(campaign.turn_history) == 1


def test_advance_turn_records_decision_and_diffs():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "full_disclosure")
    assert result.decision.decision_type in VALID_DECISION_TYPES
    assert result.decision.advice_id == "full_disclosure"
    assert result.diffs, "resolving a turn must produce at least one AppliedDiff"
    for diff in result.diffs:
        assert diff.source_type in {
            "advice", "npc_modification", "ambient", "decision"
        }
        assert diff.delta == diff.new_value - diff.old_value


def test_unknown_advice_option_raises():
    campaign = _fresh_campaign()
    with pytest.raises(turn.UnknownAdviceOption):
        turn.advance_turn(campaign, "does_not_exist")


def test_terminal_campaign_refuses_further_turns():
    campaign = _fresh_campaign()
    campaign.status = CampaignStatus.COMPLETED
    with pytest.raises(RuntimeError):
        turn.advance_turn(campaign, "controlled_disclosure")


# ---------------------------------------------------------------------------
# Failure conditions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "variable,op,threshold",
    FAILURE_THRESHOLDS,
    ids=[f"{v}-{op}-{t}" for v, op, t in FAILURE_THRESHOLDS],
)
def test_check_failure_detects_each_threshold(variable, op, threshold):
    """The failure detector must flag every documented threshold."""
    campaign = _fresh_campaign()
    # Set exactly to the failing boundary.
    campaign.world_state.variables[variable] = threshold if op == ">=" else threshold
    reason = check_failure(campaign.world_state.variables)
    assert reason is not None
    assert variable in reason

    # One step back to the safe side must not trip it.
    campaign.world_state.variables[variable] = threshold - 1 if op == ">=" else threshold + 1
    assert check_failure(campaign.world_state.variables) is None


def test_advancing_from_collapsed_state_marks_campaign_failed():
    """A turn resolved with a critical variable already collapsed must fail."""
    campaign = _fresh_campaign()
    # controlled_disclosure does not touch water_security, and ambient pressure
    # only worsens it -- so a collapsed water system stays collapsed.
    campaign.world_state.variables["water_security"] = MIN_VALUE
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert campaign.status == CampaignStatus.FAILED
    assert campaign.failure_reason is not None
    assert "water_security" in campaign.failure_reason
    assert result.status_after == CampaignStatus.FAILED


def test_delay_only_play_triggers_failure():
    """Deliberately poor play (always stalling) must trip a failure threshold."""
    campaign = _fresh_campaign()
    while not campaign.is_terminal():
        turn.advance_turn(campaign, "delay_disclosure")
    assert campaign.status == CampaignStatus.FAILED


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

def test_survival_strategy_completes_ten_turns():
    campaign = _fresh_campaign()
    for advice_id in SURVIVAL_SEQUENCE:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)

    assert campaign.turn_number == campaign.max_turns + 1
    assert len(campaign.turn_history) == campaign.max_turns
    assert campaign.status == CampaignStatus.COMPLETED
    assert campaign.failure_reason is None


def test_completion_requires_exactly_ten_resolved_turns():
    campaign = _fresh_campaign()
    # Resolve nine turns of stable play -- must still be ACTIVE.
    for advice_id in SURVIVAL_SEQUENCE[:9]:
        turn.advance_turn(campaign, advice_id)
    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.turn_number == campaign.max_turns
    # The tenth resolution pushes turn_number past max_turns -> COMPLETED.
    turn.advance_turn(campaign, SURVIVAL_SEQUENCE[9])
    assert campaign.status == CampaignStatus.COMPLETED


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_identical_advice_sequence_is_bit_for_bit_repeatable():
    def play():
        campaign = _fresh_campaign()
        results = []
        for advice_id in SURVIVAL_SEQUENCE:
            if campaign.is_terminal():
                break
            results.append(turn.advance_turn(campaign, advice_id))
        return campaign, results

    campaign_a, results_a = play()
    campaign_b, results_b = play()

    assert campaign_a.status == campaign_b.status
    assert len(results_a) == len(results_b)
    for ra, rb in zip(results_a, results_b):
        assert ra.aftermath_summary == rb.aftermath_summary
        assert ra.decision.decision_type == rb.decision.decision_type
        assert ra.decision.adherence == rb.decision.adherence
        assert [(d.variable, d.new_value, d.delta) for d in ra.diffs] == [
            (d.variable, d.new_value, d.delta) for d in rb.diffs
        ]
    # The live world state must also be identical.
    assert (
        campaign_a.world_state.variables == campaign_b.world_state.variables
    )


# ---------------------------------------------------------------------------
# Independence from web frameworks
# ---------------------------------------------------------------------------

def test_engine_does_not_import_fastapi():
    # Importing the engine must not pull in any web framework.
    for mod in ("engine", "engine.turn", "engine.rules", "engine.seed_data",
                "engine.models", "engine.state", "engine.diffs"):
        assert mod in sys.modules, f"{mod} should be importable standalone"
    assert "fastapi" not in sys.modules, (
        "the deterministic engine must not depend on FastAPI"
    )


def test_engine_runs_without_backend_installed():
    """A full 10-turn campaign resolves using engine APIs alone."""
    campaign = _fresh_campaign()
    while not campaign.is_terminal():
        turn.advance_turn(campaign, "contractor_pressure")
    assert campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.FAILED}
    assert len(campaign.turn_history) >= 1


# ---------------------------------------------------------------------------
# Sanity on seed data shape
# ---------------------------------------------------------------------------

def test_seed_campaign_shape_meets_spec():
    campaign = _fresh_campaign()
    assert campaign.max_turns == 10
    assert len(campaign.world_state.factions) >= 6
    assert len(campaign.advice_options) >= 5
    assert len(campaign.client_calls) >= 5
    # Every playable turn 1..10 has a client call.
    for t in range(1, campaign.max_turns + 1):
        assert t in campaign.client_calls, f"missing client call for turn {t}"


def test_ambient_drift_only_targets_known_variables():
    campaign = _fresh_campaign()
    variables = set(campaign.world_state.variables.keys())
    unknown = set(AMBIENT_DRIFT) - variables
    assert not unknown, f"ambient drift references unknown variables: {unknown}"
