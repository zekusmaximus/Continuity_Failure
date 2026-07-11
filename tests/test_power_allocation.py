"""The low-power choice (Wave 2b, Batch B4 — HO#8).

At CRITICAL the desk runs on auxiliary power that supports exactly ONE
subsystem per turn. The allocation is a per-turn constraint submitted with the
advice: it joins the idempotency fingerprint, is recorded on the resolved
turn, and its effects are capability gates only — never diffs, so balance is
untouched by construction (asserted below by resolving the same turn under
all three allocations and comparing the records bit for bit).
"""

from __future__ import annotations

import copy
import os
import sys

import pytest

from engine import seed_data, turn
from engine.models import PowerAllocation

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.ai.logging import get_run_store  # noqa: E402
from app.services import campaign_service, errors  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "allocation.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


def _critical_campaign():
    campaign = seed_data.create_northbridge_campaign(name="critical")
    campaign.world_state.variables["power_stability"] = 10
    return campaign


def _stored_campaign_with_power(power: int) -> str:
    created = campaign_service.create_campaign(name="Allocation Test")
    repository = campaign_service.get_repository()
    campaign = repository.get(created.id)
    campaign.world_state.variables["power_stability"] = power
    repository.put(campaign)
    return created.id


# ---------------------------------------------------------------------------
# Engine: the constraint itself
# ---------------------------------------------------------------------------

def test_critical_turn_requires_an_allocation():
    campaign = _critical_campaign()
    with pytest.raises(turn.PowerAllocationRequired):
        turn.advance_turn(campaign, "controlled_disclosure")
    # Nothing resolved, nothing mutated.
    assert campaign.turn_number == 1
    assert campaign.turn_history == []


def test_allocation_outside_critical_is_rejected():
    campaign = seed_data.create_northbridge_campaign(name="nominal")
    with pytest.raises(turn.PowerAllocationUnavailable):
        turn.advance_turn(
            campaign, "controlled_disclosure",
            powered_subsystem=PowerAllocation.LIVE_DATA,
        )


def test_unknown_allocation_is_rejected():
    campaign = _critical_campaign()
    with pytest.raises(turn.UnknownPowerAllocation):
        turn.advance_turn(
            campaign, "controlled_disclosure", powered_subsystem="FLUX_CAPACITOR"
        )


def test_citations_require_the_live_data_circuit():
    campaign = _critical_campaign()
    with pytest.raises(turn.EvidenceUnverifiable):
        turn.advance_turn(
            campaign, "controlled_disclosure",
            cited_document_ids=["doc_preliminary_lab_report"],
            powered_subsystem=PowerAllocation.MODEL_ACCESS,
        )
    result = turn.advance_turn(
        campaign, "controlled_disclosure",
        cited_document_ids=["doc_preliminary_lab_report"],
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    assert result.decision.cited_document_ids == ["doc_preliminary_lab_report"]
    assert result.powered_subsystem == PowerAllocation.LIVE_DATA


def test_allocation_gates_capability_but_never_moves_state():
    """The B4 invariant: all three allocations resolve the same turn to the
    exact same authoritative record — the choice costs capability, not
    numbers."""
    base = _critical_campaign()
    records = {}
    for allocation in PowerAllocation.ALL:
        campaign = copy.deepcopy(base)
        result = turn.advance_turn(
            campaign, "controlled_disclosure", powered_subsystem=allocation
        )
        records[allocation] = (
            [(d.variable, d.new_value, d.delta) for d in result.diffs],
            dict(campaign.world_state.variables),
            result.decision.decision_type,
            result.decision.adherence,
        )
    assert records[PowerAllocation.MODEL_ACCESS] == records[
        PowerAllocation.COMMUNICATIONS
    ] == records[PowerAllocation.LIVE_DATA]


def test_comms_unpowered_keeps_the_record_truthful_and_masks_at_presentation():
    """The caller remembers whether or not the desk could hear it: the
    AUTHORITATIVE record keeps the true memory under every allocation; the
    dark line is a presentation mask applied by the service projection
    (asserted in tests/test_wave2_balance.py). The engine never falsifies
    the explanation to match a blackout."""
    base = _critical_campaign()

    dark = copy.deepcopy(base)
    result = turn.advance_turn(
        dark, "controlled_disclosure",
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    assert result.powered_subsystem == PowerAllocation.LIVE_DATA
    # Turn 1 has no prior history with this caller: the true (empty) memory
    # stays on the record, NOT a fabricated dark line.
    assert result.decision.explanation.memory == []

    heard = copy.deepcopy(base)
    result = turn.advance_turn(
        heard, "controlled_disclosure",
        powered_subsystem=PowerAllocation.COMMUNICATIONS,
    )
    assert result.decision.explanation.memory == []


def test_allocated_turn_is_bit_for_bit_repeatable():
    def play():
        campaign = _critical_campaign()
        return turn.advance_turn(
            campaign, "controlled_disclosure",
            powered_subsystem=PowerAllocation.MODEL_ACCESS,
        ), campaign

    result_a, campaign_a = play()
    result_b, campaign_b = play()
    assert result_a.powered_subsystem == result_b.powered_subsystem
    assert [(d.variable, d.new_value) for d in result_a.diffs] == [
        (d.variable, d.new_value) for d in result_b.diffs
    ]
    assert campaign_a.world_state.variables == campaign_b.world_state.variables


# ---------------------------------------------------------------------------
# Service/API: typed errors, fingerprint, presentation
# ---------------------------------------------------------------------------

def test_submitting_without_an_allocation_at_critical_is_typed():
    campaign_id = _stored_campaign_with_power(10)
    with pytest.raises(errors.PowerAllocationRequired) as excinfo:
        campaign_service.submit_advice(
            campaign_id, "controlled_disclosure",
            expected_turn=1, idempotency_key="alloc-required-1",
        )
    assert excinfo.value.code == "power_allocation_required"
    assert excinfo.value.status_code == 409


def test_submitting_an_allocation_outside_critical_is_typed():
    campaign_id = _stored_campaign_with_power(72)
    with pytest.raises(errors.PowerAllocationUnavailable) as excinfo:
        campaign_service.submit_advice(
            campaign_id, "controlled_disclosure",
            expected_turn=1, idempotency_key="alloc-unavail-1",
            powered_subsystem=PowerAllocation.LIVE_DATA,
        )
    assert excinfo.value.code == "power_allocation_not_available"
    assert "NOMINAL" in excinfo.value.message


def test_citations_without_live_data_are_typed_as_unverifiable():
    campaign_id = _stored_campaign_with_power(10)
    with pytest.raises(errors.EvidenceUnverifiable) as excinfo:
        campaign_service.submit_advice(
            campaign_id, "controlled_disclosure",
            expected_turn=1, idempotency_key="alloc-evidence-1",
            cited_document_ids=["doc_preliminary_lab_report"],
            powered_subsystem=PowerAllocation.MODEL_ACCESS,
        )
    assert excinfo.value.code == "evidence_unverifiable"


def test_allocation_joins_the_idempotency_fingerprint():
    campaign_id = _stored_campaign_with_power(10)
    key = "alloc-fingerprint-1"
    first = campaign_service.submit_advice(
        campaign_id, "controlled_disclosure",
        expected_turn=1, idempotency_key=key,
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    assert first.replayed is False
    assert first.result.powered_subsystem == "LIVE_DATA"

    # Same key + different allocation = a materially different submission.
    with pytest.raises(errors.IdempotencyKeyConflict):
        campaign_service.submit_advice(
            campaign_id, "controlled_disclosure",
            expected_turn=1, idempotency_key=key,
            powered_subsystem=PowerAllocation.MODEL_ACCESS,
        )

    # Byte-identical retry replays the original resolution.
    replay = campaign_service.submit_advice(
        campaign_id, "controlled_disclosure",
        expected_turn=1, idempotency_key=key,
        powered_subsystem=PowerAllocation.LIVE_DATA,
    )
    assert replay.replayed is True
    assert replay.result.powered_subsystem == "LIVE_DATA"


def test_caller_disposition_is_dark_at_critical():
    campaign_id = _stored_campaign_with_power(10)
    current = campaign_service.get_current(campaign_id)
    assert current.system_status.requires_power_allocation is True
    assert "Communications dark" in current.caller_disposition


def test_provisional_model_access_lifts_the_drafting_gate(monkeypatch):
    """At CRITICAL, routing auxiliary power to MODEL_ACCESS for a drafting
    request lifts the diegetic gate; any other routing stays offline."""
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    campaign_id = _stored_campaign_with_power(10)

    campaign_service.draft_memo(campaign_id, "controlled_disclosure")
    ungated_runs = get_run_store().for_campaign(campaign_id)
    assert ungated_runs[-1].provider == "offline"

    campaign_service.draft_memo(
        campaign_id, "controlled_disclosure",
        powered_subsystem=PowerAllocation.MODEL_ACCESS,
    )
    runs = get_run_store().for_campaign(campaign_id)
    assert runs[-1].provider != "offline"  # the gate lifted; fallback may
    # still occur for provider reasons, but not the power gate.
