"""Wave 2 balance / truthfulness fixes (adversarial-review follow-up).

Four review findings, each pinned here by the behavior that was broken:

1. **Auxiliary power is bindable, not bypassable.** A CRITICAL-band drafting
   request that routes auxiliary power to MODEL_ACCESS commits the turn's
   single allocation; the advice submission must carry the same one. The
   hostile probe (draft under MODEL_ACCESS, then submit under LIVE_DATA with
   citations) is now a typed conflict instead of a two-subsystem turn.
2. **CRITICAL is reachable through authored play.** The hot-summer neglect
   route crosses into CRITICAL at the end of turn 8 and still completes
   (witnessed in tests/test_seed_variants.py); the engine-level route is
   pinned here turn by turn.
3. **The turn-4 contractor ultimatum is live content.** Cross-faction trust
   costs let three acted-on squeezes collapse contractor trust below the
   authored threshold (also pinned in tests/test_ruleset_version.py).
4. **Stored campaigns from another ruleset do not silently continue.**
   Continuation is a typed 409; the record stays readable and exportable.

Plus the presentation-truth fixes: offline documents are labeled instead of
contradicting the last-verified stamp, and the dossier renders the resolved
call variant and the turn's auxiliary allocation.
"""

from __future__ import annotations

import copy
import os
import sys

import pytest

from engine import calls, degradation, dossier, seed_data, turn
from engine.models import CampaignStatus, PowerAllocation
from engine.content import NORTHBRIDGE_SCENARIO_ID, loader
from engine.content.validator import ContentValidationError, validate_bundle

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.services import campaign_service, errors  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "wave2-balance.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


def _stored_campaign_with_power(power: int) -> str:
    created = campaign_service.create_campaign(name="Balance Test")
    repository = campaign_service.get_repository()
    campaign = repository.get(created.id)
    campaign.world_state.variables["power_stability"] = power
    repository.put(campaign)
    return created.id


def _ai_memo(campaign_id: str, powered_subsystem=None):
    return campaign_service.create_memo(
        campaign_id,
        creation_mode="ai",
        advice_id="controlled_disclosure",
        name="Advice of record — test",
        powered_subsystem=powered_subsystem,
    )


# ---------------------------------------------------------------------------
# 1. Auxiliary-power binding (the two-subsystem exploit is closed)
# ---------------------------------------------------------------------------

def test_model_access_drafting_binds_the_turn_allocation():
    campaign_id = _stored_campaign_with_power(10)
    _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.power_commitments == {1: PowerAllocation.MODEL_ACCESS}
    current = campaign_service.get_current(campaign_id)
    assert current.system_status.power_commitment == PowerAllocation.MODEL_ACCESS


def test_the_hostile_two_subsystem_probe_is_a_typed_conflict():
    """The exact exploit from the adversarial review: draft under a
    provisional MODEL_ACCESS, then switch to LIVE_DATA, cite evidence, and
    submit. That would power two subsystems in one CRITICAL turn."""
    campaign_id = _stored_campaign_with_power(10)
    memo = _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    with pytest.raises(errors.PowerAllocationConflict) as excinfo:
        campaign_service.submit_advice(
            campaign_id, "controlled_disclosure",
            expected_turn=1, idempotency_key="two-subsystem-probe",
            memo_id=memo.id, memo_revision=memo.revision,
            cited_document_ids=["doc_preliminary_lab_report"],
            powered_subsystem=PowerAllocation.LIVE_DATA,
        )
    assert excinfo.value.code == "power_allocation_conflict"
    assert excinfo.value.status_code == 409
    # Nothing resolved: the turn is still open.
    assert campaign_service.get_current(campaign_id).summary.turn_number == 1


def test_submission_matching_the_commitment_resolves():
    campaign_id = _stored_campaign_with_power(10)
    memo = _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    resolved = campaign_service.submit_advice(
        campaign_id, "controlled_disclosure",
        expected_turn=1, idempotency_key="matching-allocation",
        memo_id=memo.id, memo_revision=memo.revision,
        powered_subsystem=PowerAllocation.MODEL_ACCESS,
    )
    assert resolved.replayed is False
    assert resolved.result.powered_subsystem == PowerAllocation.MODEL_ACCESS


def test_repeated_model_access_drafting_is_consistent_not_a_conflict():
    campaign_id = _stored_campaign_with_power(10)
    _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.power_commitments == {1: PowerAllocation.MODEL_ACCESS}


def test_advisory_draft_memo_also_binds_the_allocation():
    campaign_id = _stored_campaign_with_power(10)
    campaign_service.draft_memo(
        campaign_id, "controlled_disclosure",
        powered_subsystem=PowerAllocation.MODEL_ACCESS,
    )
    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.power_commitments == {1: PowerAllocation.MODEL_ACCESS}


def test_drafting_outside_critical_commits_nothing():
    campaign_id = _stored_campaign_with_power(72)
    _ai_memo(campaign_id, powered_subsystem=PowerAllocation.MODEL_ACCESS)
    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.power_commitments == {}
    assert campaign_service.get_current(campaign_id).system_status.power_commitment is None


def test_non_model_routing_at_critical_commits_nothing():
    """Only energizing the model circuit is a gated action at drafting time;
    LIVE_DATA is consumed at submission (citations), never at drafting."""
    campaign_id = _stored_campaign_with_power(10)
    _ai_memo(campaign_id, powered_subsystem=PowerAllocation.LIVE_DATA)
    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.power_commitments == {}


def test_engine_enforces_the_commitment_as_defense_in_depth():
    campaign = seed_data.create_northbridge_campaign(name="engine-conflict")
    campaign.world_state.variables["power_stability"] = 10
    campaign.power_commitments[1] = PowerAllocation.MODEL_ACCESS
    with pytest.raises(turn.PowerAllocationConflict):
        turn.advance_turn(
            campaign, "controlled_disclosure",
            powered_subsystem=PowerAllocation.COMMUNICATIONS,
        )
    result = turn.advance_turn(
        campaign, "controlled_disclosure",
        powered_subsystem=PowerAllocation.MODEL_ACCESS,
    )
    assert result.powered_subsystem == PowerAllocation.MODEL_ACCESS


def test_commitment_is_per_turn_and_stale_entries_are_inert():
    campaign = seed_data.create_northbridge_campaign(name="stale-commitment")
    campaign.world_state.variables["power_stability"] = 10
    # A commitment recorded for a PAST turn never constrains the current one.
    campaign.power_commitments[0] = PowerAllocation.MODEL_ACCESS
    result = turn.advance_turn(
        campaign, "controlled_disclosure",
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    assert result.powered_subsystem == PowerAllocation.LIVE_DATA


# ---------------------------------------------------------------------------
# 2. CRITICAL reachability (the authored deterioration route, engine level)
# ---------------------------------------------------------------------------

def test_hot_summer_neglect_route_reaches_critical_with_turns_left_to_play():
    """Ignore the grid on hot_summer and the desk itself goes down: STRAINED
    from turn 3, DEGRADED from turn 6, CRITICAL from turn 8 -- with turns 9
    and 10 still to play under the auxiliary-power constraint."""
    campaign = seed_data.create_northbridge_campaign(
        name="neglect", variant_id="hot_summer"
    )
    bands = []
    for advice_id in [
        "controlled_disclosure", "contractor_pressure", "mutual_aid",
        "controlled_disclosure", "state_support", "controlled_disclosure",
        "mutual_aid", "contractor_pressure",
    ]:
        turn.advance_turn(campaign, advice_id)
        bands.append(degradation.assess_degradation(campaign).band)
    assert bands == [
        "NOMINAL", "NOMINAL", "STRAINED", "STRAINED", "STRAINED",
        "DEGRADED", "DEGRADED", "CRITICAL",
    ]
    # Turn 9 now genuinely requires the B4 choice.
    with pytest.raises(turn.PowerAllocationRequired):
        turn.advance_turn(campaign, "controlled_disclosure")
    for allocation in (PowerAllocation.COMMUNICATIONS, PowerAllocation.LIVE_DATA):
        step = copy.deepcopy(campaign)
        turn.advance_turn(step, "controlled_disclosure", powered_subsystem=allocation)
        turn.advance_turn(step, "mutual_aid", powered_subsystem=allocation)
        assert step.status == CampaignStatus.COMPLETED


def test_load_shedding_remains_the_effective_counterplay_on_hot_summer():
    campaign = seed_data.create_northbridge_campaign(
        name="counterplay", variant_id="hot_summer"
    )
    for advice_id in [
        "controlled_disclosure", "contractor_pressure", "mutual_aid",
        "controlled_disclosure", "load_shedding_protocol", "controlled_disclosure",
        "state_support", "contractor_pressure", "controlled_disclosure", "mutual_aid",
    ]:
        turn.advance_turn(campaign, advice_id)
    assert campaign.status == CampaignStatus.COMPLETED
    # The desk never falls below DEGRADED, and no turn needed an allocation.
    assert all(t.powered_subsystem is None for t in campaign.turn_history)
    assert campaign.world_state.variables["power_stability"] == 46


# ---------------------------------------------------------------------------
# 3. Contractor ultimatum reachability (cross-faction trust)
# ---------------------------------------------------------------------------

def test_three_squeezes_reach_the_turn_four_ultimatum():
    campaign = seed_data.create_northbridge_campaign(name="squeeze")
    trust = lambda: next(  # noqa: E731
        f for f in campaign.world_state.factions if f.id == "utility_contractor"
    ).trust_in_player
    assert trust() == 40
    for _ in range(3):
        result = turn.advance_turn(campaign, "contractor_pressure")
        assert result.decision.decision_type in (
            "FOLLOWED", "PARTIALLY_FOLLOWED", "MODIFIED"
        )
    assert trust() == 22
    resolved, variant_id = calls.resolve_call_with_variant(campaign, 4)
    assert variant_id == "call_04_terms_ultimatum"
    assert resolved.id == "call_04_terms_ultimatum"
    result = turn.advance_turn(campaign, "contractor_pressure")
    assert result.call_variant_id == "call_04_terms_ultimatum"


def test_cross_faction_trust_moves_are_on_the_record_as_shifts():
    campaign = seed_data.create_northbridge_campaign(name="shift-record")
    result = turn.advance_turn(campaign, "contractor_pressure")
    contractor_shifts = [
        s for s in result.faction_shifts
        if s.faction_id == "utility_contractor" and s.field == "trust_in_player"
    ]
    assert len(contractor_shifts) == 1
    shift = contractor_shifts[0]
    assert (shift.old_value, shift.new_value, shift.delta) == (40, 34, -6)
    assert shift.reason  # a legible reason ships with the move


def test_a_rejected_squeeze_costs_no_contractor_trust():
    """The cost applies only when the squeeze actually landed: force a
    REJECTED decision and the contractor's trust must not move."""
    campaign = seed_data.create_northbridge_campaign(name="rejected-squeeze")
    # Make contractor_pressure intolerably off-brief for the turn-1 caller.
    call = campaign.client_calls[1]
    call.decision_profile.off_brief_tolerance = 0
    contractor = next(
        f for f in campaign.world_state.factions if f.id == "utility_contractor"
    )
    contractor.risk_tolerance = 65
    town = next(
        f for f in campaign.world_state.factions if f.id == "town_managers_office"
    )
    town.risk_tolerance = 0
    town.trust_in_player = 10
    result = turn.advance_turn(campaign, "contractor_pressure")
    assert result.decision.decision_type == "REJECTED"
    assert contractor.trust_in_player == 40


def test_ordinary_play_does_not_fire_the_ultimatum():
    campaign = seed_data.create_northbridge_campaign(name="ordinary")
    for advice_id in ["controlled_disclosure", "mutual_aid", "state_support"]:
        turn.advance_turn(campaign, advice_id)
    assert calls.resolve_call_with_variant(campaign, 4)[1] is None


# ---------------------------------------------------------------------------
# 4. Executable ruleset compatibility
# ---------------------------------------------------------------------------

def test_stored_campaign_from_an_older_ruleset_cannot_continue():
    created = campaign_service.create_campaign(name="Old Ruleset")
    repository = campaign_service.get_repository()
    campaign = repository.get(created.id)
    campaign.ruleset_version = "2"
    repository.put(campaign)

    with pytest.raises(errors.RulesetIncompatible) as excinfo:
        campaign_service.submit_advice(
            created.id, "controlled_disclosure",
            expected_turn=1, idempotency_key="old-ruleset-1",
        )
    assert excinfo.value.code == "ruleset_incompatible"
    assert excinfo.value.status_code == 409
    assert "ruleset 2" in excinfo.value.message

    # The record stays readable: current turn, history, and dossier all work.
    assert campaign_service.get_current(created.id) is not None
    assert campaign_service.get_turns(created.id) is not None
    dossier_model = campaign_service.get_dossier(created.id)
    assert "`2`" in dossier_model.markdown


def test_current_ruleset_campaigns_continue_normally():
    created = campaign_service.create_campaign(name="Current Ruleset")
    resolved = campaign_service.submit_advice(
        created.id, "controlled_disclosure",
        expected_turn=1, idempotency_key="current-ruleset-1",
    )
    assert resolved.result.turn_number == 1


# ---------------------------------------------------------------------------
# 5. Stale evidence: offline documents are labeled, not silently verified
# ---------------------------------------------------------------------------

def test_documents_arriving_after_feed_loss_are_flagged_unverified():
    created = campaign_service.create_campaign(name="Stale Evidence")
    repository = campaign_service.get_repository()
    campaign = repository.get(created.id)
    # Simulate mid-campaign feed loss: the desk is on turn 6 and power has
    # been below the nominal floor since after turn 3.
    campaign.turn_number = 6
    campaign.world_state.turn_number = 6
    campaign.world_state.variables["power_stability"] = 40
    repository.put(campaign)

    current = campaign_service.get_current(created.id)
    assert current.system_status.live_feeds is False
    # Power never moved on the record, so the last live picture is intake (0):
    # every document on the board postdates the last verified feed.
    assert current.system_status.last_live_turn == 0
    docs = current.documents
    assert docs, "the board still shows documents"
    assert all(d.unverified_offline for d in docs)


def test_documents_before_feed_loss_keep_verified_provenance():
    created = campaign_service.create_campaign(name="Fresh Evidence")
    current = campaign_service.get_current(created.id)
    assert current.system_status.live_feeds is True
    assert all(not d.unverified_offline for d in current.documents)


# ---------------------------------------------------------------------------
# 6. The dossier tells the same truth as the record
# ---------------------------------------------------------------------------

def test_dossier_renders_call_variant_and_auxiliary_allocation():
    campaign = seed_data.create_northbridge_campaign(name="dossier-facts")
    for _ in range(3):
        turn.advance_turn(campaign, "contractor_pressure")
    turn.advance_turn(campaign, "contractor_pressure")  # ultimatum variant
    campaign.world_state.variables["power_stability"] = 10
    turn.advance_turn(
        campaign, "controlled_disclosure",
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    markdown = dossier.render_dossier_markdown(campaign)
    assert "variant `call_04_terms_ultimatum`" in markdown
    assert "Auxiliary power:" in markdown
    assert "LIVE_DATA" in markdown


# ---------------------------------------------------------------------------
# 7. Validator gaps
# ---------------------------------------------------------------------------

def _expect_invalid(bundle):
    with pytest.raises(ContentValidationError) as excinfo:
        validate_bundle(bundle)
    return [str(e) for e in excinfo.value.errors]


def _valid_bundle():
    return copy.deepcopy(loader.load_raw(NORTHBRIDGE_SCENARIO_ID))


def test_reject_variant_id_the_api_could_never_request():
    bundle = _valid_bundle()
    bundle.variants[0]["id"] = "hot-summer"
    messages = _expect_invalid(bundle)
    assert any("hot-summer" in m and "never be requested" in m for m in messages)


def test_reject_advice_id_the_api_could_never_request():
    bundle = _valid_bundle()
    bundle.advice[0]["id"] = "Full-Disclosure"
    messages = _expect_invalid(bundle)
    assert any("Full-Disclosure" in m and "never be requested" in m for m in messages)


def test_reject_document_id_the_api_could_never_cite():
    bundle = _valid_bundle()
    bundle.documents[0]["id"] = "doc.preliminary"
    messages = _expect_invalid(bundle)
    assert any("doc.preliminary" in m and "never be requested" in m for m in messages)


def test_reject_thread_spec_escalation_without_due_in():
    bundle = _valid_bundle()
    spec = bundle.thread_specs[0]
    spec.pop("due_in", None)
    messages = _expect_invalid(bundle)
    assert any("no due_in" in m and "never fire" in m for m in messages)


def test_reject_trust_cost_with_unknown_tag_or_zero_delta():
    bundle = _valid_bundle()
    contractor = next(
        f for f in bundle.factions if f["id"] == "utility_contractor"
    )
    contractor["advice_trust_costs"] = [
        {"advice_tag": "sabotage", "delta": 0, "reason": ""}
    ]
    messages = _expect_invalid(bundle)
    assert any("not a recognized decision tag" in m for m in messages)
    assert any("must not be zero" in m for m in messages)
    assert any("reason must be a non-empty string" in m for m in messages)


def test_reject_trust_cost_beyond_the_bounded_nudge():
    bundle = _valid_bundle()
    contractor = next(
        f for f in bundle.factions if f["id"] == "utility_contractor"
    )
    contractor["advice_trust_costs"][0]["delta"] = -40
    messages = _expect_invalid(bundle)
    assert any("within [-20, 20]" in m for m in messages)
