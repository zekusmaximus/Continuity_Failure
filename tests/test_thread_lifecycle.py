"""Open-thread lifecycle: scheduled escalation, resolution, and determinism.

Threads are no longer narrative bookkeeping: a thread with a ``due_turn``
applies its ``escalation_effects`` as an authoritative diff batch (source
``thread``) when it comes due unresolved, re-arms via ``repeat_every``, and
resolves either through matching advice the client acted on or through
explicit world-state conditions.
"""

from __future__ import annotations

import pytest

from engine import seed_data, turn
from engine.models import (
    Campaign,
    CampaignStatus,
    DecisionType,
    OpenThread,
    SourceType,
    ThreadCondition,
    ThreadStatus,
)
from engine.threads import process_threads


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


def _bare_thread(**overrides) -> OpenThread:
    base = dict(
        id="thread_test",
        title="Test thread",
        summary="A scheduled test risk.",
        turn_opened=1,
    )
    base.update(overrides)
    return OpenThread(**base)


def _find_advice(campaign, advice_id):
    return turn.find_advice(campaign, advice_id)


# ---------------------------------------------------------------------------
# Escalation schedule
# ---------------------------------------------------------------------------

def test_thread_escalates_exactly_at_due_turn():
    campaign = _fresh_campaign()
    campaign.open_threads = [
        _bare_thread(
            due_turn=3,
            escalation_effects={"legal_exposure": 5},
            escalation_note="The clock ran out.",
        )
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()

    diffs, events = process_threads(campaign, advice, decision, resolving_turn=2)
    assert diffs == [] and events == []
    assert campaign.open_threads[0].status == ThreadStatus.OPEN

    diffs, events = process_threads(campaign, advice, decision, resolving_turn=3)
    assert len(diffs) == 1
    assert diffs[0].variable == "legal_exposure"
    assert diffs[0].delta == 5
    assert diffs[0].source_type == SourceType.THREAD
    assert "Test thread" in diffs[0].reason
    assert events[0].kind == "escalated"
    assert events[0].note == "The clock ran out."
    thread = campaign.open_threads[0]
    assert thread.status == ThreadStatus.ESCALATING
    assert thread.escalation_count == 1
    assert thread.due_turn is None  # repeat_every=0 -> fires once


def test_thread_rearms_with_repeat_every():
    campaign = _fresh_campaign()
    campaign.open_threads = [
        _bare_thread(
            due_turn=2, repeat_every=2,
            escalation_effects={"media_pressure": 3},
            escalation_note="Still unresolved.",
        )
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()

    process_threads(campaign, advice, decision, resolving_turn=2)
    assert campaign.open_threads[0].due_turn == 4
    process_threads(campaign, advice, decision, resolving_turn=4)
    thread = campaign.open_threads[0]
    assert thread.due_turn == 6
    assert thread.escalation_count == 2


def test_escalation_diffs_are_clamped():
    campaign = _fresh_campaign()
    campaign.world_state.variables["legal_exposure"] = 99
    campaign.open_threads = [
        _bare_thread(
            due_turn=1,
            escalation_effects={"legal_exposure": 10},
            escalation_note="Over the top.",
        )
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()
    diffs, _ = process_threads(campaign, advice, decision, resolving_turn=1)
    assert campaign.world_state.variables["legal_exposure"] == 100
    assert diffs[0].new_value == 100


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def test_thread_resolves_via_advice_tag_when_client_acted():
    campaign = _fresh_campaign()
    campaign.open_threads = [
        _bare_thread(
            due_turn=5,
            escalation_effects={"legal_exposure": 5},
            escalation_note="n",
            resolve_tags=["disclosure"],
            resolution_note="Closed by the public record.",
        )
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.PARTIALLY_FOLLOWED})()
    diffs, events = process_threads(campaign, advice, decision, resolving_turn=2)
    assert diffs == []
    assert events[0].kind == "resolved"
    thread = campaign.open_threads[0]
    assert thread.status == ThreadStatus.RESOLVED
    assert thread.turn_resolved == 2
    assert thread.due_turn is None


def test_thread_does_not_resolve_when_client_rejected_the_advice():
    campaign = _fresh_campaign()
    campaign.open_threads = [
        _bare_thread(resolve_tags=["disclosure"])
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()
    _, events = process_threads(campaign, advice, decision, resolving_turn=2)
    assert events == []
    assert campaign.open_threads[0].status == ThreadStatus.OPEN


def test_thread_resolves_via_conditions():
    campaign = _fresh_campaign()
    campaign.world_state.variables["contractor_dependency"] = 25
    campaign.open_threads = [
        _bare_thread(
            due_turn=2,
            escalation_effects={"budget_capacity": -5},
            escalation_note="n",
            resolve_conditions=[ThreadCondition("contractor_dependency", "<=", 30)],
            resolution_note="Dependency broke.",
        )
    ]
    advice = _find_advice(campaign, "mutual_aid")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()
    diffs, events = process_threads(campaign, advice, decision, resolving_turn=2)
    # Resolution wins over a same-turn escalation.
    assert diffs == []
    assert events[0].kind == "resolved"
    assert campaign.open_threads[0].status == ThreadStatus.RESOLVED


def test_resolved_thread_never_escalates_again():
    campaign = _fresh_campaign()
    campaign.open_threads = [
        _bare_thread(
            status=ThreadStatus.RESOLVED, turn_resolved=1,
            due_turn=2, escalation_effects={"legal_exposure": 5},
            escalation_note="n",
        )
    ]
    advice = _find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()
    diffs, events = process_threads(campaign, advice, decision, resolving_turn=3)
    assert diffs == [] and events == []


# ---------------------------------------------------------------------------
# Integration with advance_turn
# ---------------------------------------------------------------------------

def test_disclosure_clock_resolves_on_disclosure_play():
    campaign = _fresh_campaign()
    turn.advance_turn(campaign, "controlled_disclosure")
    clock = next(
        t for t in campaign.open_threads if t.id == "thread_disclosure_clock"
    )
    assert clock.status == ThreadStatus.RESOLVED
    assert clock.turn_resolved == 1
    result = campaign.turn_history[0]
    assert any(
        clock.title in line for line in result.consequence_stack.resolved_threads
    )


def test_disclosure_clock_escalates_when_ignored():
    campaign = _fresh_campaign()
    # Play turns that never carry the disclosure tag; the clock (due turn 4)
    # must fire on schedule with a thread-sourced, legible diff.
    for advice_id in ["mutual_aid", "contractor_pressure", "mutual_aid", "contractor_pressure"]:
        if campaign.is_terminal():
            break
        result = turn.advance_turn(campaign, advice_id)

    clock = next(
        t for t in campaign.open_threads if t.id == "thread_disclosure_clock"
    )
    assert clock.status == ThreadStatus.ESCALATING
    assert clock.escalation_count >= 1
    escalation_turn = campaign.turn_history[3]  # turn 4 resolved
    thread_diffs = [
        d for d in escalation_turn.diffs if d.source_type == SourceType.THREAD
    ]
    assert any(d.variable == "legal_exposure" for d in thread_diffs)
    assert all("Open thread escalated" in d.reason for d in thread_diffs)
    assert escalation_turn.consequence_stack.escalated_threads


def test_thread_escalation_can_fail_the_campaign():
    campaign = _fresh_campaign()
    campaign.world_state.variables["legal_exposure"] = 92
    campaign.open_threads = [
        _bare_thread(
            due_turn=1,
            escalation_effects={"legal_exposure": 10},
            escalation_note="The filing landed.",
        )
    ]
    result = turn.advance_turn(campaign, "mutual_aid")
    assert campaign.status == CampaignStatus.FAILED
    assert "Legal Exposure" in (campaign.failure_reason or "")
    assert result.status_after == CampaignStatus.FAILED


def test_new_thread_does_not_escalate_on_its_opening_turn():
    campaign = _fresh_campaign()
    # Force high dependency so contractor advice opens the precedent thread.
    campaign.world_state.variables["contractor_dependency"] = 75
    result = turn.advance_turn(campaign, "contractor_pressure")
    precedent = next(
        (t for t in campaign.open_threads if t.id == "thread_contractor_precedent"),
        None,
    )
    assert precedent is not None
    assert precedent.escalation_count == 0
    assert precedent.due_turn == result.turn_number + 2


# ---------------------------------------------------------------------------
# Determinism with the lifecycle active
# ---------------------------------------------------------------------------

NEGLECT_SEQUENCE = [
    "mutual_aid", "contractor_pressure", "mutual_aid", "contractor_pressure",
    "mutual_aid", "contractor_pressure", "mutual_aid", "contractor_pressure",
    "mutual_aid", "contractor_pressure",
]


def test_thread_lifecycle_is_bit_for_bit_repeatable():
    def play():
        campaign = _fresh_campaign()
        results = []
        for advice_id in NEGLECT_SEQUENCE:
            if campaign.is_terminal():
                break
            results.append(turn.advance_turn(campaign, advice_id))
        return campaign, results

    campaign_a, results_a = play()
    campaign_b, results_b = play()

    assert campaign_a.status == campaign_b.status
    assert campaign_a.world_state.variables == campaign_b.world_state.variables
    for ta, tb in zip(campaign_a.open_threads, campaign_b.open_threads):
        assert (ta.id, ta.status, ta.due_turn, ta.escalation_count, ta.turn_resolved) == (
            tb.id, tb.status, tb.due_turn, tb.escalation_count, tb.turn_resolved
        )
    for ra, rb in zip(results_a, results_b):
        assert [(d.variable, d.new_value, d.delta, d.source_type) for d in ra.diffs] == [
            (d.variable, d.new_value, d.delta, d.source_type) for d in rb.diffs
        ]
        assert ra.consequence_stack.escalated_threads == rb.consequence_stack.escalated_threads
        assert ra.consequence_stack.resolved_threads == rb.consequence_stack.resolved_threads
