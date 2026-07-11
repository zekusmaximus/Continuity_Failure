"""Deterministic workstation degradation and capability gating (Wave 2b, B2).

engine/degradation.py derives the desk's condition from the campaign record --
computed on demand, never persisted (the endings contract). The backend
consumes it at three seams: the system-status package (band + honest
``ai_available``), the world-state freshness label (stale stamp when live
feeds are lost), and the memo drafter (deterministic system drafts below the
degraded threshold, regardless of deployment configuration).
"""

from __future__ import annotations

import dataclasses
import os
import sys

import pytest

from engine import seed_data, turn
from engine.degradation import (
    DegradationBand,
    assess_degradation,
    band_for_power,
)
from engine.models import Campaign

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.services import campaign_service  # noqa: E402
from app.ai.logging import get_run_store  # noqa: E402


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


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "degradation.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


def _campaign_with_power(power: int) -> str:
    """Create a stored campaign and set its live power level."""
    created = campaign_service.create_campaign(name="Degradation Test")
    repository = campaign_service.get_repository()
    campaign = repository.get(created.id)
    campaign.world_state.variables["power_stability"] = power
    repository.put(campaign)
    return created.id


# ---------------------------------------------------------------------------
# Bands (engine)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("power,band", [
    (100, DegradationBand.NOMINAL),
    (55, DegradationBand.NOMINAL),
    (54, DegradationBand.STRAINED),
    (35, DegradationBand.STRAINED),
    (34, DegradationBand.DEGRADED),
    (15, DegradationBand.DEGRADED),
    (14, DegradationBand.CRITICAL),
    (0, DegradationBand.CRITICAL),
])
def test_band_boundaries(power, band):
    assert band_for_power(power) == band


def test_gates_accumulate_down_the_bands():
    campaign = seed_data.create_northbridge_campaign(name="gates")
    v = campaign.world_state.variables

    v["power_stability"] = 72
    status = assess_degradation(campaign)
    assert (status.live_feeds, status.ai_operational,
            status.requires_power_allocation) == (True, True, False)

    v["power_stability"] = 40
    status = assess_degradation(campaign)
    assert (status.live_feeds, status.ai_operational,
            status.requires_power_allocation) == (False, True, False)

    v["power_stability"] = 30
    status = assess_degradation(campaign)
    assert (status.live_feeds, status.ai_operational,
            status.requires_power_allocation) == (False, False, False)

    v["power_stability"] = 10
    status = assess_degradation(campaign)
    assert (status.live_feeds, status.ai_operational,
            status.requires_power_allocation) == (False, False, True)
    assert "auxiliary power" in status.reason


def test_degradation_is_derived_and_never_persisted():
    assert "degradation" not in {f.name for f in dataclasses.fields(Campaign)}
    campaign = seed_data.create_northbridge_campaign(name="pure")
    assert assess_degradation(campaign) == assess_degradation(campaign)


# ---------------------------------------------------------------------------
# last_live_turn reconstruction from the diff record
# ---------------------------------------------------------------------------

def test_last_live_turn_is_the_latest_turn_that_closed_with_live_feeds():
    campaign = seed_data.create_northbridge_campaign(name="trace")
    for advice_id in SURVIVAL_SEQUENCE:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    # End-of-turn power under ruleset 3: 72,72,66,60,54,48,42,36,30,24 --
    # the last close-out at or above the nominal floor (55) is turn 4.
    status = assess_degradation(campaign)
    assert status.band == DegradationBand.DEGRADED
    assert status.power == 24
    assert status.last_live_turn == 4


def test_last_live_turn_is_current_while_feeds_are_live():
    campaign = seed_data.create_northbridge_campaign(name="live")
    turn.advance_turn(campaign, "controlled_disclosure")
    turn.advance_turn(campaign, "contractor_pressure")
    status = assess_degradation(campaign)
    assert status.live_feeds is True
    assert status.last_live_turn == campaign.turn_number == 3


def test_last_live_turn_is_zero_when_power_started_low():
    campaign = seed_data.create_northbridge_campaign(name="cold-open")
    campaign.world_state.variables["power_stability"] = 40
    status = assess_degradation(campaign)
    assert status.live_feeds is False
    assert status.last_live_turn == 0  # the intake picture is the last live one


# ---------------------------------------------------------------------------
# Backend: the system-status package and the stale freshness stamp
# ---------------------------------------------------------------------------

def test_system_status_carries_the_band_and_stale_stamp():
    campaign_id = _campaign_with_power(40)
    current = campaign_service.get_current(campaign_id)
    status = current.system_status
    assert status.degradation_band == "STRAINED"
    assert status.live_feeds is False
    assert status.requires_power_allocation is False
    assert current.world_state.last_verified.startswith("LAST VERIFIED")
    assert "engagement intake" in current.world_state.last_verified


def test_nominal_campaign_keeps_the_ordinary_freshness_label():
    campaign_id = _campaign_with_power(72)
    current = campaign_service.get_current(campaign_id)
    assert current.system_status.degradation_band == "NOMINAL"
    assert current.system_status.live_feeds is True
    assert current.world_state.last_verified == (
        "Turn 1 · Operational snapshot (deterministic)"
    )


def test_diegetic_gate_outranks_deployment_configuration(monkeypatch):
    """Even with a live provider configured, DEGRADED power forces
    ai_available False and the diegetic model_status."""
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    campaign_id = _campaign_with_power(30)
    status = campaign_service.get_current(campaign_id).system_status
    assert status.ai_available is False
    assert "Model access offline" in status.model_status
    assert status.degradation_band == "DEGRADED"


def test_strained_power_does_not_gate_the_model_stack(monkeypatch):
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    campaign_id = _campaign_with_power(40)
    status = campaign_service.get_current(campaign_id).system_status
    assert status.ai_available is True  # STRAINED loses feeds, not the model


# ---------------------------------------------------------------------------
# Backend: the memo drafter falls back deterministically when gated
# ---------------------------------------------------------------------------

def test_ai_memo_creation_falls_back_when_the_grid_cannot_sustain_it(monkeypatch):
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    campaign_id = _campaign_with_power(30)

    memo = campaign_service.create_memo(
        campaign_id,
        creation_mode="ai",
        advice_id="controlled_disclosure",
        name="Gated draft",
    )
    assert memo.provenance.workflow == "deterministic_fallback"
    assert memo.provenance.fallback_used is True
    assert memo.provenance.provider == "offline"
    assert memo.content  # the deterministic draft is still a real memo

    runs = get_run_store().for_campaign(campaign_id)
    assert runs[-1].provider == "offline"
    assert "grid power 30 below sustaining threshold" in runs[-1].input_summary


def test_draft_memo_reports_the_gated_fallback(monkeypatch):
    monkeypatch.setenv("CF_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    campaign_id = _campaign_with_power(20)
    draft = campaign_service.draft_memo(campaign_id, "controlled_disclosure")
    assert draft.fallback_used is True
    assert draft.source == "system"
    assert draft.provider == "offline"
