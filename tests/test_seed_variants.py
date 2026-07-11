"""Deterministic seed variants (Wave 2a, Batch A4).

A campaign-creation ``variant`` id selects an authored starting-state
perturbation from ``variants.json`` -- replayability without randomness. The
variant id is persisted on the campaign so an exact replay is scenario +
variant + advice sequence.
"""

from __future__ import annotations

import pytest

from engine import seed_data, turn
from engine.content import (
    NORTHBRIDGE_SCENARIO_ID,
    UnknownVariant,
    load_campaign,
    scenario_variants,
)
from engine.models import CampaignStatus
from memory.persistence import SQLiteRepository


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

# The documented survival line for strained_finances: the baseline playbook is
# one mutual-aid activation too rich there, so the closeout leans on the state
# instead. Pinned like SURVIVAL_SEQUENCE so the variant's completability is a
# test, not a hope.
STRAINED_FINANCES_SURVIVAL = SURVIVAL_SEQUENCE[:9] + ["state_support"]


def _play(sequence, variant_id=""):
    campaign = seed_data.create_northbridge_campaign(
        name="variant-test", variant_id=variant_id
    )
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    return campaign


# ---------------------------------------------------------------------------
# Loading and metadata
# ---------------------------------------------------------------------------

def test_authored_variants_are_listed_with_presentation_metadata():
    variants = scenario_variants(NORTHBRIDGE_SCENARIO_ID)
    assert [v["id"] for v in variants] == ["hot_summer", "strained_finances"]
    for variant in variants:
        assert set(variant) == {"id", "name", "description"}
        assert variant["name"] and variant["description"]


def test_variant_overrides_apply_and_the_id_is_stamped():
    baseline = seed_data.create_northbridge_campaign(name="base")
    hot = seed_data.create_northbridge_campaign(name="hot", variant_id="hot_summer")
    assert baseline.variant_id == ""
    assert hot.variant_id == "hot_summer"
    assert hot.world_state.variables["water_security"] == 40
    assert hot.world_state.variables["power_stability"] == 64
    # Non-overridden variables keep the baseline starting state.
    assert (
        hot.world_state.variables["budget_capacity"]
        == baseline.world_state.variables["budget_capacity"]
    )


def test_unknown_variant_is_rejected_before_any_state_is_created():
    with pytest.raises(UnknownVariant) as excinfo:
        load_campaign(NORTHBRIDGE_SCENARIO_ID, variant_id="mild_spring")
    assert "mild_spring" in str(excinfo.value)
    assert "hot_summer" in str(excinfo.value)  # the message names the options


# ---------------------------------------------------------------------------
# Determinism and balance obligations
# ---------------------------------------------------------------------------

def test_same_variant_and_sequence_is_bit_for_bit_repeatable():
    a = _play(SURVIVAL_SEQUENCE, "hot_summer")
    b = _play(SURVIVAL_SEQUENCE, "hot_summer")
    assert a.world_state.variables == b.world_state.variables
    assert a.status == b.status
    for ra, rb in zip(a.turn_history, b.turn_history):
        assert [(d.variable, d.new_value, d.delta) for d in ra.diffs] == [
            (d.variable, d.new_value, d.delta) for d in rb.diffs
        ]


def test_hot_summer_completes_on_the_canonical_sequence():
    campaign = _play(SURVIVAL_SEQUENCE, "hot_summer")
    assert campaign.status == CampaignStatus.COMPLETED


def test_strained_finances_breaks_the_canonical_playbook_but_is_survivable():
    """The variant's point: the baseline line fails on budget, and a documented
    alternate closeout completes. Both facts are pinned."""
    canonical = _play(SURVIVAL_SEQUENCE, "strained_finances")
    assert canonical.status == CampaignStatus.FAILED
    assert "Budget Capacity" in canonical.failure_reason

    adapted = _play(STRAINED_FINANCES_SURVIVAL, "strained_finances")
    assert adapted.status == CampaignStatus.COMPLETED


@pytest.mark.parametrize("variant_id", ["hot_summer", "strained_finances"])
def test_spam_strategies_still_fail_on_every_variant(variant_id):
    contractor = _play(["contractor_pressure"] * 10, variant_id)
    assert contractor.status == CampaignStatus.FAILED
    assert "Legal Exposure" in contractor.failure_reason
    delay = _play(["delay_disclosure"] * 10, variant_id)
    assert delay.status == CampaignStatus.FAILED


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def test_variant_id_survives_persistence(tmp_path):
    repository = SQLiteRepository(tmp_path / "variant.sqlite3")
    campaign = seed_data.create_northbridge_campaign(
        name="persisted", variant_id="hot_summer"
    )
    repository.put(campaign)
    restored = SQLiteRepository(repository.path).get(campaign.id)
    assert restored.variant_id == "hot_summer"
    assert restored.world_state.variables["power_stability"] == 64
