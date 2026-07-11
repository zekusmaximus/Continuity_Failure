"""Wave 3 B1: the deterministic causal lead and future hook.

``build_consequence_lead`` derives a one-glance orientation from values the
resolution has already produced. These tests pin the plan's guarantees:

* stable tie-breaking for the largest applied movement;
* truthful followed/modified/delayed/rejected attribution;
* ambient/thread/leak movement is never called player action;
* terminal failure wins headline priority;
* future-hook priority and references;
* old snapshot/default replay compatibility (persistence + Pydantic);
* the lead never becomes canon and canonical records stay bit-identical.

Unit tests drive the builder directly with synthetic inputs; integration
tests go through ``advance_turn`` on the real Northbridge content.
"""

from __future__ import annotations

import copy
from dataclasses import asdict

from engine import seed_data, turn
from engine.diffs import apply_diffs
from engine.experience import build_consequence_lead
from engine.models import (
    AdviceOption,
    CampaignStatus,
    ConsequenceLead,
    ConsequenceStack,
    DecisionType,
    NpcDecision,
    OpenThread,
    PrecedentEntry,
    SourceType,
)
from engine.threads import ThreadEvent


def _advice(effects=None, label="Controlled disclosure", advice_id="test_advice"):
    return AdviceOption(
        id=advice_id,
        label=label,
        summary="s",
        rationale="r",
        tags=["disclosure"],
        effects=effects or {},
    )


def _decision(decision_type=DecisionType.FOLLOWED, adherence=1.0):
    return NpcDecision(
        advice_id="test_advice",
        decision_type=decision_type,
        decider="Town Manager's Office",
        rationale="because",
        adherence=adherence,
    )


def _lead(**overrides):
    defaults = dict(
        resolving_turn=3,
        advice=_advice(),
        decision=_decision(),
        diffs=[],
        thread_events=[],
        new_threads=[],
        new_precedents=[],
        consequence_stack=ConsequenceStack(),
        status_after=CampaignStatus.ACTIVE,
        failure_reason=None,
    )
    defaults.update(overrides)
    return build_consequence_lead(**defaults)


def _diffs(variables, batches):
    """Apply (effects, source_type) batches; returns the applied diffs."""
    out = []
    for effects, source_type in batches:
        out += apply_diffs(variables, effects, reason=f"why {source_type}", source_type=source_type)
    return out


# ---------------------------------------------------------------------------
# Headline: decision attribution
# ---------------------------------------------------------------------------

def test_followed_headline_names_advice_decider_and_largest_move():
    variables = {"public_trust": 50, "media_pressure": 40}
    diffs = _diffs(variables, [({"public_trust": 4, "media_pressure": -2}, SourceType.ADVICE)])
    lead = _lead(diffs=diffs)
    assert "You advised Controlled disclosure" in lead.headline
    assert "Town Manager's Office carried it out as advised" in lead.headline
    assert "Public Trust rose 4 under the recorded decision" in lead.headline
    kinds = [(r.kind, r.id) for r in lead.references]
    assert ("decision", "test_advice") in kinds
    assert ("diff", "public_trust") in kinds


def test_delayed_and_rejected_never_imply_the_effect_landed():
    for decision_type in (DecisionType.DELAYED, DecisionType.REJECTED):
        lead = _lead(decision=_decision(decision_type))
        assert "none of its proposed effects landed this turn" in lead.headline
        assert "under the recorded decision" not in lead.headline


def test_modified_and_partial_attribution_language():
    assert "adopted part of it" in _lead(
        decision=_decision(DecisionType.PARTIALLY_FOLLOWED)
    ).headline
    assert "changed the terms" in _lead(
        decision=_decision(DecisionType.MODIFIED)
    ).headline


def test_display_title_wins_over_internal_label():
    advice = _advice()
    advice.title = "Full disclosure and emergency conservation order"
    lead = _lead(advice=advice)
    assert "You advised Full disclosure and emergency conservation order" in lead.headline
    assert lead.references[0].label == advice.title


# ---------------------------------------------------------------------------
# Headline: movement selection and source truthfulness
# ---------------------------------------------------------------------------

def test_largest_absolute_movement_wins():
    variables = {"public_trust": 50, "legal_exposure": 40}
    diffs = _diffs(
        variables,
        [
            ({"public_trust": 2}, SourceType.ADVICE),
            ({"legal_exposure": -5}, SourceType.ADVICE),
        ],
    )
    lead = _lead(diffs=diffs)
    assert "Legal Exposure fell 5" in lead.headline


def test_tie_breaks_by_humanized_name_then_diff_order():
    variables = {"water_security": 50, "public_trust": 50}
    # Both move by +3: "Public Trust" < "Water Security" alphabetically, even
    # though water_security appears first in diff order.
    diffs = _diffs(
        variables,
        [({"water_security": 3, "public_trust": 3}, SourceType.ADVICE)],
    )
    lead = _lead(diffs=diffs)
    assert "Public Trust rose 3" in lead.headline


def test_net_movement_spans_batches_not_single_diffs():
    variables = {"public_trust": 50, "media_pressure": 40}
    # public_trust nets to +1 (+4 - 3); media_pressure moves -3 in one batch.
    diffs = _diffs(
        variables,
        [
            ({"public_trust": 4}, SourceType.ADVICE),
            ({"public_trust": -3}, SourceType.NPC_MODIFICATION),
            ({"media_pressure": -3}, SourceType.ADVICE),
        ],
    )
    lead = _lead(diffs=diffs)
    assert "Media Pressure fell 3" in lead.headline


def test_ambient_thread_and_leak_movement_is_not_called_player_action():
    cases = [
        (SourceType.AMBIENT, "ambient crisis pressure — not the decision — moved"),
        (SourceType.THREAD, "an open thread's escalation moved"),
        (SourceType.LEAK, "a faction leak moved"),
    ]
    for source_type, expected in cases:
        variables = {"public_order": 50}
        diffs = _diffs(variables, [({"public_order": -6}, source_type)])
        lead = _lead(diffs=diffs, decision=_decision(DecisionType.DELAYED))
        assert expected in lead.headline, source_type
        assert "under the recorded decision" not in lead.headline


def test_client_own_action_is_attributed_to_the_client():
    variables = {"public_trust": 50}
    diffs = _diffs(variables, [({"public_trust": -4}, SourceType.NPC_MODIFICATION)])
    lead = _lead(diffs=diffs, decision=_decision(DecisionType.MODIFIED))
    assert "Town Manager's Office's own action moved Public Trust -4" in lead.headline


def test_no_movement_is_stated_not_invented():
    lead = _lead(diffs=[])
    assert "No tracked variable moved this turn." in lead.headline
    assert [r.kind for r in lead.references] == ["decision"]


# ---------------------------------------------------------------------------
# Headline: terminal priority
# ---------------------------------------------------------------------------

def test_terminal_failure_wins_headline_priority():
    variables = {"water_security": 12}
    diffs = _diffs(variables, [({"water_security": -8}, SourceType.AMBIENT)])
    reason = "Water security collapsed below the failure threshold."
    lead = _lead(
        diffs=diffs, status_after=CampaignStatus.FAILED, failure_reason=reason
    )
    assert lead.headline.startswith(f"The engagement ended this turn: {reason}")
    # The decision context still appears, after the terminal fact.
    assert "You advised Controlled disclosure" in lead.headline
    assert lead.references[0].kind == "failure"
    assert lead.references[0].id == "turn_3_failed"


def test_completion_leads_with_the_closed_engagement():
    lead = _lead(status_after=CampaignStatus.COMPLETED)
    assert lead.headline.startswith("The engagement reached its final turn and closed.")
    assert lead.references[0] .kind == "failure"
    assert lead.references[0].id == "turn_3_completed"


# ---------------------------------------------------------------------------
# Future hook: pinned priority and references
# ---------------------------------------------------------------------------

def _thread(thread_id="th_contractor", title="Contractor warning", due=None):
    return OpenThread(
        id=thread_id, title=title, summary="s", turn_opened=2, due_turn=due
    )


def _escalation(thread_id="th_contractor", title="Contractor warning"):
    return ThreadEvent(thread_id=thread_id, title=title, kind="escalated", note="n")


def _precedent():
    return PrecedentEntry(
        id="prec_1",
        kind="sole_source_procurement",
        label="Sole-source procurement",
        turn_recorded=3,
        detail="d",
        canon_id="canon_turn_3",
    )


def test_escalated_thread_wins_the_future_hook():
    stack = ConsequenceStack(second_order=["Costs compound next cycle."])
    lead = _lead(
        thread_events=[_escalation(), ThreadEvent("th_x", "Other", "resolved", "")],
        new_threads=[_thread("th_new", "New thread")],
        new_precedents=[_precedent()],
        consequence_stack=stack,
    )
    assert "Contractor warning escalated this turn" in lead.future_hook
    hook_refs = [r for r in lead.references if r.kind == "thread"]
    assert [(r.id, r.label) for r in hook_refs] == [
        ("th_contractor", "Contractor warning")
    ]


def test_newly_opened_thread_is_second_priority_and_names_its_deadline():
    lead = _lead(
        new_threads=[_thread(due=6)],
        new_precedents=[_precedent()],
        consequence_stack=ConsequenceStack(second_order=["Risk line."]),
    )
    assert lead.future_hook == (
        "Contractor warning is now open on the record. It is due on turn 6."
    )


def test_precedent_is_third_priority():
    lead = _lead(new_precedents=[_precedent()])
    assert "Sole-source procurement is now a recorded precedent" in lead.future_hook
    assert any(r.kind == "precedent" and r.id == "prec_1" for r in lead.references)


def test_stack_risk_is_fourth_priority_and_none_is_last():
    lead = _lead(consequence_stack=ConsequenceStack(second_order=["Budget strain deepens."]))
    assert lead.future_hook == "Budget strain deepens."
    assert any(
        r.kind == "decision" and r.id == "turn_3_second_order_0"
        for r in lead.references
    )
    assert _lead().future_hook == ""


def test_resolved_thread_events_do_not_hook():
    lead = _lead(thread_events=[ThreadEvent("th_x", "Other", "resolved", "")])
    assert lead.future_hook == ""


# ---------------------------------------------------------------------------
# Integration: the real turn pipeline
# ---------------------------------------------------------------------------

def test_advance_turn_populates_the_lead_deterministically():
    campaign_a = seed_data.create_northbridge_campaign(name="lead-a")
    campaign_b = seed_data.create_northbridge_campaign(name="lead-b")
    result_a = turn.advance_turn(campaign_a, "controlled_disclosure")
    result_b = turn.advance_turn(campaign_b, "controlled_disclosure")

    assert result_a.consequence_lead.headline
    assert result_a.consequence_lead.references
    assert asdict(result_a.consequence_lead) == asdict(result_b.consequence_lead)

    # Every reference points back at a record: kind is in-vocabulary and both
    # id and label are non-empty record values.
    for reference in result_a.consequence_lead.references:
        assert reference.kind in {"diff", "thread", "precedent", "failure", "decision"}
        assert reference.id
        assert reference.label


def test_lead_is_derived_not_canon_and_leaves_records_bit_identical():
    campaign = seed_data.create_northbridge_campaign(name="lead-canon")
    result = turn.advance_turn(campaign, "controlled_disclosure")

    baseline = seed_data.create_northbridge_campaign(name="lead-canon")
    expected = turn.advance_turn(baseline, "controlled_disclosure")

    # The lead is not a CanonEntry and adds nothing to canon.
    assert len(campaign.canon) == len(baseline.canon)
    for entry in campaign.canon:
        assert entry.title != result.consequence_lead.headline

    # State, diffs, decision, faction, and stack records are bit-identical to
    # a resolution of the same seed: the lead reads the record, never writes it.
    assert campaign.world_state.variables == baseline.world_state.variables
    assert asdict(result.decision) == asdict(expected.decision)
    assert [asdict(d) for d in result.diffs] == [asdict(d) for d in expected.diffs]
    assert [asdict(s) for s in result.faction_shifts] == [
        asdict(s) for s in expected.faction_shifts
    ]
    assert asdict(result.consequence_stack) == asdict(expected.consequence_stack)


def test_terminal_campaign_lead_states_the_failure():
    campaign = seed_data.create_northbridge_campaign(name="lead-fail")
    # Force the next resolution over a failure threshold via ambient state.
    campaign.world_state.variables["water_security"] = 11
    campaign.world_state.variables["public_trust"] = 8
    result = None
    for advice_id in ("delay_disclosure", "contractor_pressure", "delay_disclosure"):
        result = turn.advance_turn(campaign, advice_id)
        if campaign.is_terminal():
            break
    assert campaign.status == CampaignStatus.FAILED
    assert result is not None
    assert result.consequence_lead.headline.startswith("The engagement ended this turn:")
    assert result.failure_reason in result.consequence_lead.headline
    assert result.consequence_lead.references[0].kind == "failure"


# ---------------------------------------------------------------------------
# Compatibility: old snapshots and replays decode to the default lead
# ---------------------------------------------------------------------------

def test_turn_result_without_lead_decodes_to_default():
    from memory.persistence import decode_campaign, encode_campaign

    campaign = seed_data.create_northbridge_campaign(name="lead-compat")
    turn.advance_turn(campaign, "controlled_disclosure")
    raw = encode_campaign(campaign)

    # Simulate a snapshot written before the field existed.
    import json

    document = json.loads(raw)
    stored_result = document["data"]["turn_history"][-1]
    assert stored_result.pop("consequence_lead") is not None
    revived = decode_campaign(json.dumps(document))

    lead = revived.turn_history[-1].consequence_lead
    assert isinstance(lead, ConsequenceLead)
    assert asdict(lead) == {"headline": "", "future_hook": "", "references": []}


def test_pydantic_model_defaults_the_lead_for_old_payloads():
    import os
    import sys

    backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.schemas import api as schemas

    campaign = seed_data.create_northbridge_campaign(name="lead-pydantic")
    result = turn.advance_turn(campaign, "controlled_disclosure")
    data = asdict(result)

    # Round-trip parity: the populated lead validates and dumps identically.
    model = schemas.TurnResultModel.model_validate(copy.deepcopy(data))
    assert model.model_dump()["consequence_lead"] == data["consequence_lead"]

    # An old replay payload without the field validates to the empty default.
    data.pop("consequence_lead")
    old = schemas.TurnResultModel.model_validate(data)
    assert old.consequence_lead.headline == ""
    assert old.consequence_lead.references == []


# ---------------------------------------------------------------------------
# Wave 3 B2: the dossier timeline carries the lead, before reconciliation
# ---------------------------------------------------------------------------

def test_dossier_places_causal_lead_before_reconciliation():
    from engine.dossier import render_dossier_markdown

    campaign = seed_data.create_northbridge_campaign(name="lead-dossier")
    result = turn.advance_turn(campaign, "controlled_disclosure")
    markdown = render_dossier_markdown(campaign)

    assert f"- **Causal lead:** {result.consequence_lead.headline}" in markdown
    if result.consequence_lead.future_hook:
        assert (
            f"- **On the record next:** {result.consequence_lead.future_hook}"
            in markdown
        )
    # The lead supplements the audit immediately before the reconciliation it
    # summarizes — and replaces none of the existing Wave-2 facts.
    assert markdown.index("**Causal lead:**") < markdown.index("**State reconciliation")
    assert "**NPC decision:**" in markdown
    assert "**Aftermath:**" in markdown


def test_dossier_omits_the_lead_for_pre_lead_turns():
    from engine.dossier import render_dossier_markdown
    from engine.models import ConsequenceLead

    campaign = seed_data.create_northbridge_campaign(name="lead-dossier-old")
    turn.advance_turn(campaign, "controlled_disclosure")
    # Simulate a turn persisted before the field existed.
    campaign.turn_history[-1].consequence_lead = ConsequenceLead()
    markdown = render_dossier_markdown(campaign)
    assert "**Causal lead:**" not in markdown
    assert "**On the record next:**" not in markdown
    assert "**State reconciliation" in markdown
