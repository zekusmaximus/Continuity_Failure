"""Deterministic drivers for power_stability (Wave 2b, Batch B1).

Three drivers, all through ``apply_diffs`` with legible reasons: the authored
heat-event ambient window (scenario.json ``ambient_windows``), the grid-stress
thread spec (opens when power <= 55, escalates -4 every 2 turns), and the
turn-5 load-shedding advice (a real counterplay, priced like every other
option). None touches a failure-threshold variable -- that invariant is pinned
in tests/test_ruleset_version.py.
"""

from __future__ import annotations

from engine import seed_data, turn
from engine.models import AmbientWindow, CampaignStatus, SourceType


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

# The documented power counterplay: publish the load-shedding protocol on
# turn 5 (off-brief -- nobody called about the grid) and lean on the state on
# turn 7 to cover the budget the baseline line got there. Completes with the
# grid thread never opening. Pinned below like the survival sequence itself.
POWER_AWARE_SEQUENCE = [
    "controlled_disclosure",
    "contractor_pressure",
    "mutual_aid",
    "controlled_disclosure",
    "load_shedding_protocol",
    "controlled_disclosure",
    "state_support",
    "contractor_pressure",
    "controlled_disclosure",
    "mutual_aid",
]


def _fresh_campaign(variant_id=""):
    return seed_data.create_northbridge_campaign(name="power", variant_id=variant_id)


def _play(sequence, variant_id=""):
    campaign = _fresh_campaign(variant_id)
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    return campaign


def _grid_thread(campaign):
    return next(
        (t for t in campaign.open_threads if t.id == "thread_grid_stress"), None
    )


# ---------------------------------------------------------------------------
# Ambient windows
# ---------------------------------------------------------------------------

def test_heat_window_is_loaded_from_content():
    campaign = _fresh_campaign()
    assert [w.id for w in campaign.ambient_windows] == ["regional_heat_event"]
    window = campaign.ambient_windows[0]
    assert (window.from_turn, window.to_turn) == (3, 6)
    assert window.effects == {"power_stability": -6}


def test_window_applies_only_inside_its_turn_span_with_its_authored_reason():
    campaign = _fresh_campaign()

    def window_diffs(result):
        return [d for d in result.diffs
                if d.source_type == SourceType.AMBIENT and "heat event" in d.reason]

    r1 = turn.advance_turn(campaign, "controlled_disclosure")   # turn 1
    r2 = turn.advance_turn(campaign, "contractor_pressure")     # turn 2
    r3 = turn.advance_turn(campaign, "mutual_aid")              # turn 3
    assert window_diffs(r1) == [] and window_diffs(r2) == []
    diffs = window_diffs(r3)
    assert len(diffs) == 1
    assert diffs[0].variable == "power_stability" and diffs[0].delta == -6
    assert diffs[0].reason.startswith("Grid stress")


def test_window_effects_are_clamped_like_any_diff():
    campaign = _fresh_campaign()
    campaign.ambient_windows = [AmbientWindow(
        id="test_surge", from_turn=1, to_turn=1,
        effects={"power_stability": -100}, reason="Test surge",
    )]
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert campaign.world_state.variables["power_stability"] == 0
    surge = [d for d in result.diffs if d.reason == "Test surge"]
    assert surge[0].new_value == 0


# ---------------------------------------------------------------------------
# The grid-stress thread (neglect consequence)
# ---------------------------------------------------------------------------

def test_ignoring_power_opens_and_escalates_the_grid_thread():
    campaign = _play(SURVIVAL_SEQUENCE)
    assert campaign.status == CampaignStatus.COMPLETED
    thread = _grid_thread(campaign)
    assert thread is not None
    assert thread.escalation_count == 2
    assert campaign.world_state.variables["power_stability"] == 40
    escalations = [
        d for result in campaign.turn_history for d in result.diffs
        if d.source_type == SourceType.THREAD and d.variable == "power_stability"
    ]
    assert [d.delta for d in escalations] == [-4, -4]


def test_prompt_load_shedding_keeps_the_grid_thread_from_opening():
    campaign = _play(POWER_AWARE_SEQUENCE)
    assert campaign.status == CampaignStatus.COMPLETED
    assert _grid_thread(campaign) is None
    assert campaign.world_state.variables["power_stability"] == 58


def test_load_shedding_resolves_an_already_open_grid_thread():
    """On hot_summer the grid dips below 55 before turn 5; the protocol then
    resolves the open thread through the ordinary resolve_tags path."""
    campaign = _play(POWER_AWARE_SEQUENCE, variant_id="hot_summer")
    assert campaign.status == CampaignStatus.COMPLETED
    thread = _grid_thread(campaign)
    assert thread is not None
    assert thread.status == "resolved"
    assert thread.turn_resolved == 5


# ---------------------------------------------------------------------------
# The load-shedding decision handler
# ---------------------------------------------------------------------------

def test_load_shedding_decision_thresholds():
    from engine.rules import _decide_load_shedding
    from engine.models import DecisionType

    campaign = _fresh_campaign()
    v = campaign.world_state.variables

    v["power_stability"], v["public_order"] = 30, 60
    draft = _decide_load_shedding(campaign)
    assert (draft.decision_type, draft.adherence) == (DecisionType.FOLLOWED, 0.9)

    v["power_stability"], v["public_order"] = 50, 40
    draft = _decide_load_shedding(campaign)
    assert (draft.decision_type, draft.adherence) == (
        DecisionType.PARTIALLY_FOLLOWED, 0.6,
    )
    assert draft.modifications == {"media_pressure": 2}

    v["power_stability"], v["public_order"] = 50, 60
    draft = _decide_load_shedding(campaign)
    assert (draft.decision_type, draft.adherence) == (DecisionType.FOLLOWED, 0.8)


def test_load_shedding_consequence_text_is_its_own_not_disclosures():
    campaign = _fresh_campaign()
    for advice_id in SURVIVAL_SEQUENCE[:4]:
        turn.advance_turn(campaign, advice_id)
    result = turn.advance_turn(campaign, "load_shedding_protocol")
    immediate = " ".join(result.consequence_stack.immediate)
    assert "load" in immediate.lower()
    assert "public record" not in immediate  # the disclosure pool's line
