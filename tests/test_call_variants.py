"""Branchable / faction-gated client calls (Wave 2a, Batch A3).

A call slot may carry authored variants selected by deterministic conditions
over world state and faction fields. Selection happens once per turn, before
the NPC decision seam, so a variant's ask, primary options, and decision
profile flow into the mediation unchanged -- and the record always shows which
opening was on the line (``TurnResult.call_variant_id``).
"""

from __future__ import annotations

from engine import calls, seed_data, turn
from engine.conditions import condition_holds
from engine.models import (
    CallVariant,
    DecisionType,
    OpenThread,
    ThreadCondition,
)
from engine.threads import process_threads
from memory.persistence import SQLiteRepository


SURVIVAL_PREFIX = ["controlled_disclosure", "contractor_pressure", "mutual_aid"]

CONTRACTOR_VARIANT_ID = "call_04_terms_ultimatum"
STATE_VARIANT_ID = "call_06_oversight_footing"


def _fresh_campaign():
    return seed_data.create_northbridge_campaign(name="variants")


def _faction(campaign, faction_id):
    return next(f for f in campaign.world_state.factions if f.id == faction_id)


def _play_to_turn_four(campaign):
    for advice_id in SURVIVAL_PREFIX:
        turn.advance_turn(campaign, advice_id)
    assert campaign.turn_number == 4


# ---------------------------------------------------------------------------
# Faction-scoped conditions (the ThreadCondition extension itself)
# ---------------------------------------------------------------------------

def test_faction_scoped_condition_evaluates_against_the_named_faction():
    campaign = _fresh_campaign()
    factions_by_id = {f.id: f for f in campaign.world_state.factions}
    cond = ThreadCondition(
        "trust_in_player", "<=", 25, faction_id="utility_contractor"
    )
    assert not condition_holds(cond, campaign.world_state.variables, factions_by_id)
    _faction(campaign, "utility_contractor").trust_in_player = 25
    assert condition_holds(cond, campaign.world_state.variables, factions_by_id)


def test_faction_scoped_condition_against_unknown_subject_never_holds():
    variables = {"public_trust": 50}
    unknown_faction = ThreadCondition("trust_in_player", "<=", 100, faction_id="ghost")
    assert not condition_holds(unknown_faction, variables, {})
    # An unknown FIELD on a real faction must not hold either.
    campaign = _fresh_campaign()
    factions_by_id = {f.id: f for f in campaign.world_state.factions}
    bad_field = ThreadCondition("posture", "<=", 100, faction_id="utility_contractor")
    assert not condition_holds(bad_field, variables, factions_by_id)


def test_threads_can_resolve_on_faction_scoped_conditions():
    """The shared evaluator gives threads faction-conditioned resolution."""
    campaign = _fresh_campaign()
    campaign.open_threads = [OpenThread(
        id="thread_trust_repair",
        title="Contractor working trust",
        summary="Repairs relations with the sole-source firm.",
        turn_opened=1,
        resolve_conditions=[ThreadCondition(
            "trust_in_player", ">=", 60, faction_id="utility_contractor"
        )],
        resolution_note="The firm re-engaged through the consultant.",
    )]
    advice = turn.find_advice(campaign, "controlled_disclosure")
    decision = type("D", (), {"decision_type": DecisionType.REJECTED})()

    _, events = process_threads(campaign, advice, decision, resolving_turn=1)
    assert events == []
    _faction(campaign, "utility_contractor").trust_in_player = 60
    _, events = process_threads(campaign, advice, decision, resolving_turn=2)
    assert [e.kind for e in events] == ["resolved"]


# ---------------------------------------------------------------------------
# Variant selection
# ---------------------------------------------------------------------------

def test_base_call_is_presented_when_no_variant_condition_holds():
    campaign = _fresh_campaign()
    _play_to_turn_four(campaign)
    call = campaign.current_call()
    assert call.id == "call_04"
    _, variant_id = calls.resolve_call_with_variant(campaign, 4)
    assert variant_id is None


def test_variant_is_selected_when_its_faction_condition_holds():
    campaign = _fresh_campaign()
    _play_to_turn_four(campaign)
    _faction(campaign, "utility_contractor").trust_in_player = 20

    call, variant_id = calls.resolve_call_with_variant(campaign, 4)
    assert variant_id == CONTRACTOR_VARIANT_ID
    assert call.id == CONTRACTOR_VARIANT_ID
    assert campaign.current_call().id == CONTRACTOR_VARIANT_ID
    # The variant is a complete call: its own ask and decision profile.
    assert "ultimatum" in call.summary.lower() or "ultimatum" in call.ask.lower()
    assert call.decision_profile.off_brief_tolerance == 30


def test_first_matching_variant_wins_in_authored_order():
    campaign = _fresh_campaign()
    base = campaign.client_calls[1]
    always = ThreadCondition("public_trust", ">=", 0)
    first = CallVariant(id="v_first", conditions=[always], call=base)
    second = CallVariant(id="v_second", conditions=[always], call=base)
    campaign.call_variants[1] = [first, second]
    _, variant_id = calls.resolve_call_with_variant(campaign, 1)
    assert variant_id == "v_first"


# ---------------------------------------------------------------------------
# The variant drives the decision seam and the record
# ---------------------------------------------------------------------------

def test_variant_profile_reaches_the_decision_and_the_record():
    campaign = _fresh_campaign()
    _play_to_turn_four(campaign)
    _faction(campaign, "utility_contractor").trust_in_player = 20

    result = turn.advance_turn(campaign, "state_support")

    # Selection happened BEFORE the mediation seam: the explanation carries
    # the variant's mandate, and the decider is the variant's caller.
    assert result.call_variant_id == CONTRACTOR_VARIANT_ID
    assert result.decision.decider == "Utility Contractor"
    assert "assurances no longer count" in (
        result.decision.explanation.institutional_mandate
    )


def test_base_call_turn_records_no_variant_id():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert result.call_variant_id is None


def test_variant_turn_is_bit_for_bit_repeatable():
    def play():
        campaign = _fresh_campaign()
        _play_to_turn_four(campaign)
        _faction(campaign, "utility_contractor").trust_in_player = 20
        result = turn.advance_turn(campaign, "state_support")
        return campaign, result

    campaign_a, result_a = play()
    campaign_b, result_b = play()
    assert result_a.call_variant_id == result_b.call_variant_id
    assert [(d.variable, d.new_value, d.delta) for d in result_a.diffs] == [
        (d.variable, d.new_value, d.delta) for d in result_b.diffs
    ]
    assert campaign_a.world_state.variables == campaign_b.world_state.variables


# ---------------------------------------------------------------------------
# Loader + persistence
# ---------------------------------------------------------------------------

def test_loader_builds_the_authored_variant_table():
    campaign = _fresh_campaign()
    assert set(campaign.call_variants) == {4, 6}
    assert campaign.call_variants[4][0].id == CONTRACTOR_VARIANT_ID
    assert campaign.call_variants[4][0].conditions[0].faction_id == "utility_contractor"
    assert campaign.call_variants[6][0].id == STATE_VARIANT_ID
    assert campaign.call_variants[6][0].conditions[0].faction_id is None


def test_variant_table_and_recorded_variant_id_survive_persistence(tmp_path):
    repository = SQLiteRepository(tmp_path / "variants.sqlite3")
    campaign = _fresh_campaign()
    _play_to_turn_four(campaign)
    _faction(campaign, "utility_contractor").trust_in_player = 20
    result = turn.advance_turn(campaign, "state_support")
    repository.put(campaign, snapshot_turn=result.turn_number)

    restored = SQLiteRepository(repository.path).get(campaign.id)
    assert set(restored.call_variants) == {4, 6}
    variant = restored.call_variants[4][0]
    assert variant.id == CONTRACTOR_VARIANT_ID
    assert variant.call.decision_profile.off_brief_tolerance == 30
    assert restored.turn_history[-1].call_variant_id == CONTRACTOR_VARIANT_ID
