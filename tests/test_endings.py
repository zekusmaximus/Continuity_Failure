"""Multi-axis outcome assessment: completion is graded, not binary.

The assessment is a pure, deterministic function of campaign state — final
variables, the debt ledger, and the thread record — and its verdict preserves
ambiguity: a campaign can stabilize the water while hollowing out legitimacy
or independence. The contractor-dependency exploit regression lives here.
"""

from __future__ import annotations

from engine import seed_data, turn
from engine.endings import OutcomeBand, build_outcome_assessment
from engine.models import Campaign, CampaignStatus


SURVIVAL_SEQUENCE = [
    "controlled_disclosure", "contractor_pressure", "mutual_aid",
    "controlled_disclosure", "state_support", "controlled_disclosure",
    "mutual_aid", "contractor_pressure", "controlled_disclosure", "mutual_aid",
]

AXIS_IDS = [
    "stabilization", "legitimacy", "legal_record", "independence",
    "harm_avoided", "consultant_standing", "shadow_authority",
]


def _play(sequence) -> Campaign:
    campaign = seed_data.create_northbridge_campaign(name="test")
    for advice_id in sequence:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    return campaign


def test_assessment_covers_all_seven_axes_with_bounded_scores():
    campaign = _play(SURVIVAL_SEQUENCE)
    assessment = build_outcome_assessment(campaign)
    assert [a.id for a in assessment.axes] == AXIS_IDS
    for axis in assessment.axes:
        assert 0 <= axis.score <= 100
        assert axis.band in ("strong", "holding", "compromised", "failed")
        assert axis.factors, f"axis {axis.id} must explain itself"
    assert assessment.verdict_title
    assert assessment.verdict_body
    assert assessment.campaign_status == campaign.status


def test_axis_arithmetic_reconciles_from_final_state():
    campaign = _play(SURVIVAL_SEQUENCE)
    v = campaign.world_state.variables
    assessment = build_outcome_assessment(campaign)
    by_id = {a.id: a for a in assessment.axes}

    expected_stabilization = round(
        (v["water_security"] + v["hospital_stability"] + v["public_order"]) / 3
    )
    assert by_id["stabilization"].score == max(0, min(100, expected_stabilization))

    expected_independence = 100 - round(
        (v["contractor_dependency"] + v["state_oversight_risk"]) / 2
    )
    assert by_id["independence"].score == max(0, min(100, expected_independence))

    assert by_id["shadow_authority"].score == 100 - v["player_shadow_authority"]


def test_high_dependency_completion_is_a_damning_verdict_not_a_win():
    """The review's balance exploit, end-graded: completing at contractor
    dependency 100 must read as capture, never as a clean success."""
    campaign = _play(SURVIVAL_SEQUENCE)
    assert campaign.status == CampaignStatus.COMPLETED
    campaign.world_state.variables["contractor_dependency"] = 100
    campaign.world_state.variables["state_oversight_risk"] = 60

    assessment = build_outcome_assessment(campaign)
    independence = next(a for a in assessment.axes if a.id == "independence")
    assert independence.band in (OutcomeBand.COMPROMISED, OutcomeBand.FAILED)
    assert assessment.verdict_title == "Stabilized — on someone else's terms"


def test_contractor_spam_now_fails_in_loop():
    """The exploit's in-loop fix: spamming contractor advice compounds
    sole-source precedents into a legal-exposure failure before turn 10."""
    campaign = _play(["contractor_pressure"] * 10)
    assert campaign.status == CampaignStatus.FAILED
    assert "Legal Exposure" in (campaign.failure_reason or "")
    sole_source = [
        e for e in campaign.debt_ledger if e.kind == "sole_source_procurement"
    ]
    assert len(sole_source) >= 2


def test_failed_campaigns_render_a_verdict_and_dossier_section():
    campaign = _play(["delay_disclosure"] * 10)
    assert campaign.status == CampaignStatus.FAILED

    assessment = build_outcome_assessment(campaign)
    assert assessment.verdict_title == "The engagement collapsed"
    assert any(
        (campaign.failure_reason or "") in line for line in assessment.verdict_body
    )

    from engine.dossier import render_dossier_markdown
    markdown = render_dossier_markdown(campaign)
    assert "## Outcome Assessment" in markdown
    assert assessment.verdict_title in markdown


def test_active_campaigns_carry_no_dossier_assessment_section():
    campaign = seed_data.create_northbridge_campaign(name="test")
    turn.advance_turn(campaign, "controlled_disclosure")
    assert campaign.status == CampaignStatus.ACTIVE
    from engine.dossier import render_dossier_markdown
    assert "## Outcome Assessment" not in render_dossier_markdown(campaign)


def test_assessment_is_deterministic_and_never_persisted():
    a = build_outcome_assessment(_play(SURVIVAL_SEQUENCE))
    b = build_outcome_assessment(_play(SURVIVAL_SEQUENCE))
    assert a == b

    # Recompute-on-demand: the Campaign dataclass has no assessment field.
    from dataclasses import fields
    assert "assessment" not in {f.name for f in fields(Campaign)}
