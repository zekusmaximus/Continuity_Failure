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
from engine.state import MIN_VALUE, clamp, humanize_variable


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
    assert campaign.world_state.turn_number == campaign.turn_number
    assert campaign.world_state.last_verified == (
        "Turn 2 · Operational snapshot (deterministic)"
    )
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
    assert humanize_variable(variable) in reason

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
    assert "Water Security" in campaign.failure_reason
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
    assert campaign.world_state.turn_number == campaign.turn_number == 11
    assert campaign.world_state.last_verified == (
        "Turn 10 · Final operational snapshot (deterministic)"
    )


def test_aftermath_uses_player_facing_variable_names():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert "Information Integrity" in result.aftermath_summary
    assert "information_integrity" not in result.aftermath_summary
    immediate = " ".join(result.consequence_stack.immediate)
    assert "Information Integrity" in immediate
    assert "information_integrity" not in immediate


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
# NPC decider is the client on the current call, not a hardcoded office
# ---------------------------------------------------------------------------

def test_decider_is_the_current_caller_not_hardcoded():
    """The NPC that acts on the advice must be the caller of the current turn.

    Previously every decision was attributed to the Town Manager's Office; now
    the hospital (turn 3), the contractor (turn 4), and the state liaison
    (turn 6) each own their own decision.
    """
    campaign = _fresh_campaign()
    expected = {
        1: "Town Manager's Office",
        3: "Northbridge Hospital",
        4: "Utility Contractor",
        6: "State Emergency Management Liaison",
    }
    for advice_id in SURVIVAL_SEQUENCE:
        if campaign.is_terminal():
            break
        resolving_turn = campaign.turn_number
        call = campaign.client_calls[resolving_turn]
        result = turn.advance_turn(campaign, advice_id)
        # The decider always equals the caller on the line this turn.
        assert result.decision.decider == call.caller
        if resolving_turn in expected:
            assert result.decision.decider == expected[resolving_turn]
        # And it is threaded into the human-readable surfaces.
        assert call.caller in result.decision.rationale
        assert call.caller in result.aftermath_summary
        assert call.caller in result.canon_entry.source

    # Turns 3, 4, 6 must NOT all be attributed to the Town Manager anymore.
    non_manager = [
        t.decision.decider for t in campaign.turn_history
        if t.turn_number in (3, 4, 6)
    ]
    assert "Town Manager's Office" not in non_manager


# ---------------------------------------------------------------------------
# Independence from web frameworks
# ---------------------------------------------------------------------------

def _engine_imports():
    """Yield ``(filename, imported_module, imported_name)`` for every import in
    the engine package. Uses AST so prose/comments never count and the check is
    independent of what other test modules have imported into ``sys.modules``
    in the same session (mirrors the AI-boundary test pattern).
    """
    import os
    engine_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "engine")
    assert os.path.isdir(engine_dir), "engine package should exist"
    import ast
    for name in sorted(os.listdir(engine_dir)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(engine_dir, name), "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    yield name, alias.name, None
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    yield name, module, alias.name


def test_engine_does_not_import_fastapi():
    """The deterministic engine must not import any web framework.

    Checked by AST scan of ``engine/*.py`` so the result depends only on the
    engine source, not on pytest collection order or what other tests imported.
    """
    forbidden_prefixes = ("fastapi", "uvicorn", "starlette", "pydantic")
    for fname, module, _name in _engine_imports():
        for prefix in forbidden_prefixes:
            assert not module == prefix and not module.startswith(prefix + "."), (
                f"engine/{fname} must not import {prefix} (imported {module})"
            )


def test_engine_imports_only_stdlib_and_itself():
    """Engine modules may import only the stdlib and the engine package itself."""
    # Top-level packages reachable via the engine source. ``__future__`` and
    # ``typing`` etc. are stdlib; ``engine`` is self-import. Anything else is a
    # boundary leak. This is the stricter, structural form of the independence
    # guarantee.
    allowed_first_party = {"engine"}
    for fname, module, _name in _engine_imports():
        top = module.split(".")[0]
        if top in allowed_first_party:
            continue
        # Stdlib modules are importable without the backend installed.
        import importlib.util
        assert importlib.util.find_spec(top) is not None or top in {
            "__future__",
        }, f"engine/{fname} imports non-stdlib, non-engine package '{top}'"


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
