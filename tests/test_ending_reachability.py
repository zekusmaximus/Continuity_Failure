"""Ending reachability: every completed-campaign verdict has a witness.

The adversarial review found that only two of the five completed-campaign
verdicts ever appeared across 4,212 systematic strategies; the other three
were dead content. The structural blocker was that ``contractor_dependency``
was a pure ratchet -- nothing in the game could lower it, so the independence
axis could not be held and every stabilizing route ended "on someone else's
terms" (or worse). The turn-4 ``competitive_procurement`` option is the
authored counterplay that unlocks the rest of the verdict space.

Each test below pins one legal, completing advice sequence (found by
deterministic search, re-verified on every run) whose terminal assessment
produces the named verdict. If a balance change silently kills a verdict,
its witness fails here -- a verdict without a witness is not live content.
"""

from __future__ import annotations

import pytest

from engine import degradation, endings, seed_data, turn
from engine.models import CampaignStatus


def _play(sequence, variant_id=""):
    campaign = seed_data.create_northbridge_campaign(
        name="ending-witness", variant_id=variant_id
    )
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        kwargs = {}
        if degradation.assess_degradation(campaign).requires_power_allocation:
            kwargs["powered_subsystem"] = "COMMUNICATIONS"
        turn.advance_turn(campaign, advice_id, **kwargs)
    return campaign


def _assessment(campaign):
    assessment = endings.build_outcome_assessment(campaign)
    return assessment, {axis.id: axis for axis in assessment.axes}


# ---------------------------------------------------------------------------
# The five completed-campaign verdicts, each with a pinned witness sequence.
# ---------------------------------------------------------------------------

WITNESSES = {
    # Stabilize everything, hold independence via the turn-4 competitive
    # procurement, keep the record clean. The intended "clean" ending.
    "A defensible stabilization": [
        "full_disclosure", "mutual_aid", "mutual_aid",
        "competitive_procurement", "mutual_aid", "full_disclosure",
        "delay_disclosure", "controlled_disclosure",
        "contractor_pressure", "contractor_pressure",
    ],
    # Stabilize operationally and stay independent, but burn trust and the
    # information record doing it: the water flowed, consent did not survive.
    "The water flowed; consent drained away": [
        "delay_disclosure", "contractor_pressure", "delay_disclosure",
        "competitive_procurement", "mutual_aid", "mutual_aid",
        "business_compensation_framework", "mutual_aid",
        "delay_disclosure", "full_disclosure",
    ],
    # Stabilize with legitimacy intact but a legal record that will not
    # survive discovery (delay timing + sole-source precedents).
    "Stabilized, and discoverable": [
        "mutual_aid", "delay_disclosure", "contractor_pressure",
        "competitive_procurement", "mutual_aid", "controlled_disclosure",
        "business_compensation_framework", "controlled_disclosure",
        "controlled_disclosure", "contractor_pressure",
    ],
    # Survive ten turns of process while the essential systems keep failing.
    "The clock ran out before the water was safe": [
        "full_disclosure", "full_disclosure", "full_disclosure",
        "full_disclosure", "load_shedding_protocol", "full_disclosure",
        "full_disclosure", "full_disclosure", "full_disclosure",
        "delay_disclosure",
    ],
    # The canonical survival line: the water holds, but dependency and
    # oversight now own the town.
    "Stabilized — on someone else's terms": [
        "controlled_disclosure", "contractor_pressure", "mutual_aid",
        "controlled_disclosure", "state_support", "controlled_disclosure",
        "mutual_aid", "contractor_pressure", "controlled_disclosure",
        "mutual_aid",
    ],
}


@pytest.mark.parametrize("verdict", sorted(WITNESSES), ids=lambda v: v[:32])
def test_every_completed_verdict_has_a_witness(verdict):
    campaign = _play(WITNESSES[verdict])
    assert campaign.status == CampaignStatus.COMPLETED, verdict
    assessment, _ = _assessment(campaign)
    assert assessment.verdict_title == verdict


def test_defensible_stabilization_holds_every_verdict_axis():
    campaign = _play(WITNESSES["A defensible stabilization"])
    _, axes = _assessment(campaign)
    for axis_id in ("stabilization", "independence", "legitimacy", "legal_record"):
        assert axes[axis_id].score >= 50, (
            f"{axis_id} fell below the holding band; the 'defensible' witness "
            "no longer earns its verdict"
        )


def test_competitive_procurement_is_the_dependency_counterplay():
    """The one lever that lowers structural dependency: the same route with
    the turn-4 competitive procurement swapped out loses independence."""
    with_lever = _play(WITNESSES["A defensible stabilization"])
    swapped = list(WITNESSES["A defensible stabilization"])
    swapped[3] = "mutual_aid"
    without_lever = _play(swapped)
    _, axes_with = _assessment(with_lever)
    _, axes_without = _assessment(without_lever)
    assert axes_with["independence"].score >= 50
    assert axes_without["independence"].score < axes_with["independence"].score


def test_failed_campaigns_keep_the_collapse_verdict():
    campaign = _play(["delay_disclosure"] * 10)
    assert campaign.status == CampaignStatus.FAILED
    assessment, _ = _assessment(campaign)
    assert assessment.verdict_title == "The engagement collapsed"
