"""Institutional debt ledger and deterministic client memory.

Emergency precedents (sole-source procurement, delayed notice, informal
hospital priority, compensation frameworks, red-line crossings) accumulate on
``campaign.debt_ledger``. The first instance is recorded free; repetition
carries a deterministic priced diff batch and lowers the client's resistance
to matching advice. Clients quote the engagement record back (pure canon /
turn-history reads, no model call).
"""

from __future__ import annotations

from engine import ledger, rules, seed_data, turn
from engine.models import (
    Campaign,
    DecisionType,
    NpcDecision,
    PrecedentEntry,
    SourceType,
)


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


def _decision(decision_type: str, cost_reason: str = "") -> NpcDecision:
    return NpcDecision(
        advice_id="x", decision_type=decision_type, decider="d",
        rationale="r", adherence=0.5, cost_reason=cost_reason,
    )


# ---------------------------------------------------------------------------
# Recording rules
# ---------------------------------------------------------------------------

def test_delay_advice_records_delayed_notice_precedent():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert len(campaign.debt_ledger) == 1
    entry = campaign.debt_ledger[0]
    assert entry.kind == ledger.PrecedentKind.DELAYED_NOTICE
    assert entry.turn_recorded == 1
    assert entry.canon_id == "canon_turn_1"
    assert any(
        "Precedent recorded" in line
        for line in result.consequence_stack.legal_fallout
    )


def test_conceded_contractor_terms_record_sole_source_precedent():
    campaign = _fresh_campaign()
    campaign.world_state.variables["contractor_dependency"] = 75
    turn.advance_turn(campaign, "contractor_pressure")  # dep >= 70 -> MODIFIED
    kinds = [e.kind for e in campaign.debt_ledger]
    assert ledger.PrecedentKind.SOLE_SOURCE_PROCUREMENT in kinds


def test_followed_contractor_squeeze_records_no_precedent():
    campaign = _fresh_campaign()
    campaign.world_state.variables["contractor_dependency"] = 40
    campaign.world_state.variables["budget_capacity"] = 60
    turn.advance_turn(campaign, "contractor_pressure")  # FOLLOWED branch
    assert campaign.debt_ledger == []


# ---------------------------------------------------------------------------
# Repetition pricing
# ---------------------------------------------------------------------------

def test_repeating_a_precedent_applies_a_priced_diff_batch():
    campaign = _fresh_campaign()
    turn.advance_turn(campaign, "delay_disclosure")
    assert len(campaign.debt_ledger) == 1

    # Turns 2-3 red-line delay; turn 4 (contractor call) does not, so the
    # second delayed-notice precedent lands there.
    turn.advance_turn(campaign, "mutual_aid")
    turn.advance_turn(campaign, "mutual_aid")
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert len(campaign.debt_ledger) == 2
    assert "(instance 2 on the ledger)" in campaign.debt_ledger[1].detail

    precedent_diffs = [
        d for d in result.diffs if "Precedent repeated" in d.reason
    ]
    assert precedent_diffs, "repetition must be priced as its own diff batch"
    assert {d.variable for d in precedent_diffs} == set(
        ledger.REPEAT_COSTS[ledger.PrecedentKind.DELAYED_NOTICE]
    )
    assert all(d.source_type == SourceType.DECISION for d in precedent_diffs)


def test_first_instance_is_recorded_free():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert result.decision.precedent_adjustments == {}
    assert result.decision.precedent_reason == ""


# ---------------------------------------------------------------------------
# Familiarity: standing precedent lowers off-brief resistance
# ---------------------------------------------------------------------------

def test_standing_precedent_relieves_off_brief_discomfort():
    campaign = _fresh_campaign()
    advice = turn.find_advice(campaign, "delay_disclosure")
    baseline = ledger.evaluate_repeat(campaign, advice, _decision(DecisionType.DELAYED))
    assert baseline == ({}, "")

    # Construct two otherwise-identical campaigns; one carries the precedent.
    def resolve(with_precedent: bool):
        c = _fresh_campaign()
        if with_precedent:
            c.debt_ledger.append(
                PrecedentEntry(
                    id="precedent_delayed_notice_t0",
                    kind=ledger.PrecedentKind.DELAYED_NOTICE,
                    label="Delayed public notice",
                    turn_recorded=1,
                    detail="d",
                    canon_id="canon_turn_0",
                )
            )
        return rules.decide(c, turn.find_advice(c, "delay_disclosure"))

    without = resolve(False)
    with_prec = resolve(True)
    factors_with = [f.label for f in with_prec.explanation.adherence_factors]
    assert "Standing precedent" in factors_with
    factors_without = [f.label for f in without.explanation.adherence_factors]
    assert "Standing precedent" not in factors_without


# ---------------------------------------------------------------------------
# Client memory
# ---------------------------------------------------------------------------

def test_client_memory_quotes_the_prior_turn_from_the_same_decider():
    campaign = _fresh_campaign()
    first = turn.advance_turn(campaign, "controlled_disclosure")
    decider = first.decision.decider

    # Find the next turn with the same caller so memory applies.
    while not campaign.is_terminal():
        call = campaign.current_call()
        if call is not None and call.caller == decider:
            break
        turn.advance_turn(campaign, "mutual_aid")
    if campaign.is_terminal():
        return  # scenario never repeats the caller; nothing to assert

    result = turn.advance_turn(campaign, "mutual_aid")
    memory = result.decision.explanation.memory
    assert memory, "a repeat caller must remember the prior engagement"
    assert any(f"Turn {first.turn_number}" in line for line in memory)
    assert any(first.advice_label in line for line in memory)


def test_client_memory_is_empty_on_first_contact():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert result.decision.explanation.memory == []


# ---------------------------------------------------------------------------
# Determinism and persistence
# ---------------------------------------------------------------------------

def test_ledger_and_memory_are_deterministic():
    def play():
        c = _fresh_campaign()
        seq = ["delay_disclosure", "mutual_aid", "mutual_aid",
               "delay_disclosure", "contractor_pressure"]
        results = []
        for advice_id in seq:
            if c.is_terminal():
                break
            results.append(turn.advance_turn(c, advice_id))
        return c, results

    a, results_a = play()
    b, results_b = play()
    assert [(e.id, e.kind, e.turn_recorded) for e in a.debt_ledger] == [
        (e.id, e.kind, e.turn_recorded) for e in b.debt_ledger
    ]
    for ra, rb in zip(results_a, results_b):
        assert ra.decision.explanation.memory == rb.decision.explanation.memory
        assert ra.decision.precedent_adjustments == rb.decision.precedent_adjustments


def test_debt_ledger_survives_persistence_round_trip(tmp_path):
    from memory.persistence import SQLiteRepository

    repository = SQLiteRepository(tmp_path / "ledger.sqlite3")
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "delay_disclosure")
    repository.put(campaign, snapshot_turn=result.turn_number)

    reopened = SQLiteRepository(repository.path).get(campaign.id)
    assert len(reopened.debt_ledger) == 1
    entry = reopened.debt_ledger[0]
    assert entry.kind == ledger.PrecedentKind.DELAYED_NOTICE
    assert entry.canon_id == "canon_turn_1"
