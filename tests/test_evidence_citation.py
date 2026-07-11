"""Evidence citation: staking the memo on documents has deterministic weight.

The player may cite up to three Evidence Board documents with a submission.
Relevant (tag-overlap or call-attached) high-reliability material relieves
off-brief discomfort and firms up adherence; already-public records add a
little more; contested material costs the consultant credibility as its own
legible diff batch. Citations are part of the idempotency fingerprint.
"""

from __future__ import annotations

import pytest

from engine import rules, seed_data, turn
from engine.models import Campaign, DecisionType


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


def _doc(campaign: Campaign, doc_id: str):
    return next(d for d in campaign.documents if d.id == doc_id)


# ---------------------------------------------------------------------------
# Decision weighting
# ---------------------------------------------------------------------------

def test_relevant_high_reliability_citation_firms_up_adherence():
    campaign = _fresh_campaign()
    advice = turn.find_advice(campaign, "controlled_disclosure")
    without = rules.decide(campaign, advice)
    with_citation = rules.decide(
        campaign, advice, [_doc(campaign, "doc_town_manager_transcript")]
    )
    assert with_citation.adherence > without.adherence
    assert with_citation.adherence <= 1.0
    labels = [f.label for f in with_citation.explanation.adherence_factors]
    assert "Evidence cited" in labels


def test_contested_citation_carries_a_recorded_cost():
    campaign = _fresh_campaign()
    advice = turn.find_advice(campaign, "controlled_disclosure")
    decision = rules.decide(
        campaign, advice, [_doc(campaign, "doc_preliminary_lab_report")]
    )
    assert decision.citation_adjustments == {
        "information_integrity": -1, "player_reputation": -1,
    }
    assert "doc" not in decision.citation_reason  # human title, not the id
    assert "Preliminary" in decision.citation_reason
    assert any("contested" in c.lower() for c in decision.explanation.conflicts)


def test_irrelevant_citation_is_neutral():
    campaign = _fresh_campaign()
    # The council excerpt is attached to turn 1's call, so use a later doc id
    # on a fresh campaign to construct irrelevance: cite the transcript against
    # advice whose tags it does not share, on a turn where it is not attached.
    campaign.turn_number = 4
    campaign.world_state.turn_number = 4
    advice = turn.find_advice(campaign, "mutual_aid")
    decision = rules.decide(
        campaign, advice, [_doc(campaign, "doc_town_manager_transcript")]
    )
    assert decision.citation_adjustments == {}
    factors = [
        f for f in decision.explanation.adherence_factors
        if f.label == "Evidence cited"
    ]
    assert len(factors) == 1
    assert factors[0].direction == "neutral"


def test_citation_never_rescues_a_red_line_rejection():
    campaign = _fresh_campaign()
    campaign.turn_number = 2  # schools call red-lines "delay"
    campaign.world_state.turn_number = 2
    advice = turn.find_advice(campaign, "delay_disclosure")
    decision = rules.decide(
        campaign, advice, [_doc(campaign, "doc_town_manager_transcript")]
    )
    assert decision.decision_type == DecisionType.REJECTED
    assert decision.adherence == 0.0


# ---------------------------------------------------------------------------
# Turn integration
# ---------------------------------------------------------------------------

def test_contested_citation_cost_is_applied_as_its_own_diff_batch():
    campaign = _fresh_campaign()
    result = turn.advance_turn(
        campaign, "controlled_disclosure",
        cited_document_ids=["doc_preliminary_lab_report"],
    )
    citation_diffs = [
        d for d in result.diffs if "Cited contested evidence" in d.reason
    ]
    assert {d.variable for d in citation_diffs} == {
        "information_integrity", "player_reputation",
    }
    assert result.decision.cited_document_ids == ["doc_preliminary_lab_report"]
    assert "evidence_cited" in result.canon_entry.tags


def test_unknown_or_future_document_is_rejected():
    campaign = _fresh_campaign()
    with pytest.raises(turn.UnknownDocument):
        turn.advance_turn(campaign, "mutual_aid", cited_document_ids=["nope"])
    with pytest.raises(turn.UnknownDocument):
        turn.advance_turn(
            campaign, "mutual_aid",
            cited_document_ids=["doc_school_closure_request"],  # turn 2 doc
        )
    # Neither attempt may have advanced the campaign.
    assert campaign.turn_number == 1
    assert campaign.turn_history == []


def test_citations_are_deterministic():
    def play():
        c = _fresh_campaign()
        results = [
            turn.advance_turn(
                c, "controlled_disclosure",
                cited_document_ids=["doc_town_manager_transcript",
                                    "doc_preliminary_lab_report"],
            )
        ]
        results.append(turn.advance_turn(c, "mutual_aid"))
        return c, results

    a, ra = play()
    b, rb = play()
    assert a.world_state.variables == b.world_state.variables
    for x, y in zip(ra, rb):
        assert x.decision.adherence == y.decision.adherence
        assert x.decision.citation_adjustments == y.decision.citation_adjustments
        assert [(d.variable, d.delta) for d in x.diffs] == [
            (d.variable, d.delta) for d in y.diffs
        ]
