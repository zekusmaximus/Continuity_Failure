"""Content, consequence-stack, and dossier tests.

These exercise the richer Northbridge content added in the content/ui-polish
branch: documents/evidence, advice tradeoff fields, the deterministic
consequence stack, open threads, and the campaign dossier export. They import
only the ``engine`` package (framework-free) and require no web server.
"""

from __future__ import annotations

import pytest

from engine import dossier as dossier_engine
from engine import seed_data, turn
from engine.models import Campaign, DecisionType


def _fresh_campaign() -> Campaign:
    return seed_data.create_northbridge_campaign(name="test")


# ---------------------------------------------------------------------------
# 1. Documents / evidence in the current turn package
# ---------------------------------------------------------------------------

def test_campaign_seed_has_documents():
    campaign = _fresh_campaign()
    assert len(campaign.documents) >= 6, "scenario should ship a document set"
    # Every document carries the presentation fields the Evidence Board needs.
    for doc in campaign.documents:
        assert doc.id and doc.title and doc.type and doc.source
        assert 1 <= doc.turn_number <= campaign.max_turns
        assert doc.reliability
        assert doc.public_status
        assert doc.summary


def test_available_documents_grow_as_turns_advance():
    """A document with turn_number N must appear from turn N onward only."""
    campaign = _fresh_campaign()
    by_turn = {d.turn_number for d in campaign.documents}
    first_turn_docs = {d.id for d in campaign.available_documents()}
    # Turn 1 should expose exactly the turn-1 documents (and any turn<=1).
    assert by_turn.intersection({1})  # at least one turn-1 document exists
    assert first_turn_docs == {d.id for d in campaign.documents if d.turn_number <= 1}

    # Resolve several turns; the available set must only grow, never shrink.
    seen = set(first_turn_docs)
    for advice_id in ("controlled_disclosure", "contractor_pressure", "mutual_aid"):
        turn.advance_turn(campaign, advice_id)
        now = {d.id for d in campaign.available_documents()}
        assert seen.issubset(now), "documents disappeared after advancing turns"
        seen = now
    # By turn 4, strictly more documents should be visible than at turn 1.
    assert len(seen) > len(first_turn_docs)


def test_client_calls_attach_documents():
    """Each turn's client call references at least one evidence document."""
    campaign = _fresh_campaign()
    for t in range(1, campaign.max_turns + 1):
        call = campaign.client_calls[t]
        assert call.attached_document_ids, f"turn {t} call has no attached documents"
        known = {d.id for d in campaign.documents}
        for doc_id in call.attached_document_ids:
            assert doc_id in known, f"turn {t} references unknown doc {doc_id}"


# ---------------------------------------------------------------------------
# 2. Advice options carry tradeoff fields
# ---------------------------------------------------------------------------

TRADEOFF_FIELDS = (
    "type", "title", "recommendation",
    "expected_benefits", "expected_harms",
    "legal_risk", "political_risk", "operational_risk",
    "affected_factions",
)


def test_advice_options_have_tradeoff_fields():
    campaign = _fresh_campaign()
    assert len(campaign.advice_options) >= 3
    for opt in campaign.advice_options:
        for field in TRADEOFF_FIELDS:
            assert hasattr(opt, field), f"{opt.id} missing tradeoff field {field}"
        # Tradeoffs must be non-vacuous: at least one benefit and one harm.
        assert opt.expected_benefits, f"{opt.id} has no expected benefits"
        assert opt.expected_harms, f"{opt.id} has no expected harms"
        for risk in (opt.legal_risk, opt.political_risk, opt.operational_risk):
            assert 0 <= risk <= 100
        # Effects (authoritative) must remain intact for the engine to resolve.
        assert opt.effects


def test_no_advice_option_is_purely_optimal():
    """Every option must carry at least one stated harm (no free lunch)."""
    campaign = _fresh_campaign()
    for opt in campaign.advice_options:
        assert opt.expected_harms, f"{opt.id} appears risk-free, which violates the design"


def test_client_calls_carry_rich_situation_fields():
    campaign = _fresh_campaign()
    for t in range(1, campaign.max_turns + 1):
        call = campaign.client_calls[t]
        assert call.urgency
        assert call.time_horizon
        assert call.unknown_facts, f"turn {t} call has no unknowns"
        assert call.immediate_risks, f"turn {t} call has no immediate risks"
        assert call.caller_role
        assert call.public_exposure  # non-empty public-status label


# ---------------------------------------------------------------------------
# 3. Consequence stack is generated after advice resolution
# ---------------------------------------------------------------------------

def test_consequence_stack_generated_after_turn():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    stack = result.consequence_stack
    assert stack.immediate, "immediate consequences must be populated"
    assert stack.second_order, "second-order consequences must be populated"
    assert stack.faction_reactions, "faction reactions must be populated"
    assert stack.media_framing
    assert stack.legal_fallout
    # Canonized events reference the canon entry produced this turn.
    assert result.canon_entry.title in stack.canonized_events


def test_consequence_stack_is_deterministic():
    def play():
        c = _fresh_campaign()
        return turn.advance_turn(c, "controlled_disclosure").consequence_stack

    a, b = play(), play()
    assert a.immediate == b.immediate
    assert a.second_order == b.second_order
    assert [r.reaction for r in a.faction_reactions] == [r.reaction for r in b.faction_reactions]
    assert a.media_framing == b.media_framing
    assert a.legal_fallout == b.legal_fallout


def test_delay_path_opens_concealment_thread():
    """Repeated delay under rising media pressure opens the concealment thread."""
    campaign = _fresh_campaign()
    opened = False
    for _ in range(4):
        if campaign.is_terminal():
            break
        result = turn.advance_turn(campaign, "delay_disclosure")
        if "concealment" in " ".join(result.consequence_stack.opened_threads).lower():
            opened = True
            break
    assert opened, "delaying under media pressure should open a concealment thread"
    assert any("concealment" in t.title.lower() for t in campaign.open_threads)


def test_npc_decision_carries_mediation_fields():
    campaign = _fresh_campaign()
    result = turn.advance_turn(campaign, "delay_disclosure")
    d = result.decision
    # The client visibly mediates the advice.
    assert d.decision_type in {
        DecisionType.FOLLOWED, DecisionType.PARTIALLY_FOLLOWED,
        DecisionType.MODIFIED, DecisionType.DELAYED, DecisionType.REJECTED,
    }
    assert d.deviation
    assert d.public_explanation
    assert d.private_motive
    assert d.resulting_risk


def test_factions_have_red_lines_and_pressure():
    campaign = _fresh_campaign()
    assert len(campaign.world_state.factions) >= 6
    for f in campaign.world_state.factions:
        assert f.red_lines, f"{f.id} has no red lines"
        assert f.public_position and f.private_incentive
        assert 0 <= f.current_pressure <= 100
        assert 0 <= f.trust_in_player <= 100


# ---------------------------------------------------------------------------
# 4. Campaign dossier can be produced after at least one turn
# ---------------------------------------------------------------------------

def test_dossier_produced_after_one_turn():
    campaign = _fresh_campaign()
    turn.advance_turn(campaign, "controlled_disclosure")
    md = dossier_engine.render_dossier_markdown(campaign)
    assert md
    assert campaign.name in md
    assert "Turn-by-Turn Timeline" in md
    assert "Turn 1" in md
    # The dossier reflects the single resolved turn.
    assert md.count("### Turn ") == 1


def test_dossier_after_full_campaign_has_all_sections():
    campaign = _fresh_campaign()
    seq = [
        "controlled_disclosure", "contractor_pressure", "mutual_aid",
        "controlled_disclosure", "state_support", "controlled_disclosure",
        "mutual_aid", "contractor_pressure", "controlled_disclosure", "mutual_aid",
    ]
    for advice_id in seq:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    md = dossier_engine.render_dossier_markdown(campaign)
    for section in (
        "Final World State", "Faction Summary", "Turn-by-Turn Timeline",
        "Canon Archive", "Open Threads",
    ):
        assert section in md
    assert md.count("### Turn ") == len(campaign.turn_history)
    fname = dossier_engine.dossier_filename(campaign)
    assert fname.endswith(".md") and campaign.name.split()[0] in fname


def test_dossier_is_pure_read_only():
    """Rendering the dossier must not mutate campaign state."""
    campaign = _fresh_campaign()
    turn.advance_turn(campaign, "controlled_disclosure")
    snapshot = (campaign.status, dict(campaign.world_state.variables),
                len(campaign.canon), len(campaign.open_threads))
    _ = dossier_engine.render_dossier_markdown(campaign)
    after = (campaign.status, dict(campaign.world_state.variables),
             len(campaign.canon), len(campaign.open_threads))
    assert snapshot == after


# ---------------------------------------------------------------------------
# 5. Backward-compat: the survival sequence still completes (regression)
# ---------------------------------------------------------------------------

SURVIVAL_SEQUENCE = [
    "controlled_disclosure", "contractor_pressure", "mutual_aid",
    "controlled_disclosure", "state_support", "controlled_disclosure",
    "mutual_aid", "contractor_pressure", "controlled_disclosure", "mutual_aid",
]


def test_survival_sequence_still_completes_with_new_fields():
    campaign = _fresh_campaign()
    for advice_id in SURVIVAL_SEQUENCE:
        if campaign.is_terminal():
            break
        turn.advance_turn(campaign, advice_id)
    assert campaign.status == "COMPLETED"
    assert len(campaign.turn_history) == campaign.max_turns
    # Every turn produced a consequence stack.
    assert all(t.consequence_stack.immediate for t in campaign.turn_history)
