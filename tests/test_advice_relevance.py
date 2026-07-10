"""Batch 6: call-specific advice relevance and NPC decision reachability.

These tests pin the Batch 6 guarantees:

* Every client call declares a small primary (on-brief) advice set plus at least
  one strategic alternative.
* Off-brief advice is flagged and carries a deterministic, AppliedDiff-backed
  cost; on-brief advice does not.
* The same advice is received differently by different callers for an explicit,
  deterministic reason (a red line).
* FOLLOWED, MODIFIED, DELAYED, and REJECTED are all genuinely reachable.
* Resolution (including off-brief/red-line turns) is bit-for-bit replayable and
  never violates the 0-100 clamp or the "every mutation emits a diff" invariant.
* The decision carries a human-labeled explanation, not an opaque score.

They import only the ``engine`` package (framework-free).
"""

from __future__ import annotations

import pytest

from engine import seed_data, turn
from engine.models import DecisionType, SourceType
from engine.content import NORTHBRIDGE_SCENARIO_ID, load_campaign


# A safe, all on-brief prefix used to walk a fresh campaign to a given turn.
_SAFE_SEQ = [
    "controlled_disclosure",           # 1  Town Manager
    "school_staged_closure",           # 2  Schools
    "hospital_priority_allocation",    # 3  Hospital
    "contractor_pressure",             # 4  Contractor
    "controlled_disclosure",           # 5  Media
    "state_support",                   # 6  State liaison
    "controlled_disclosure",           # 7  Business
    "controlled_disclosure",           # 8  Opposition
    "contractor_pressure",             # 9  Water authority
    "state_support",                   # 10 Town Manager
]


def _fresh():
    return seed_data.create_northbridge_campaign(name="test")


def _advance_to(campaign, target_turn):
    """Resolve on-brief safe advice until the campaign reaches ``target_turn``."""
    while campaign.turn_number < target_turn and not campaign.is_terminal():
        turn.advance_turn(campaign, _SAFE_SEQ[campaign.turn_number - 1])
    return campaign


# ---------------------------------------------------------------------------
# 1. Content shape: primary set + alternatives on every call
# ---------------------------------------------------------------------------

def test_every_call_declares_primary_and_has_alternatives():
    campaign = load_campaign(NORTHBRIDGE_SCENARIO_ID, campaign_id="fixed")
    global_ids = {o.id for o in campaign.advice_options}
    for t in range(1, campaign.max_turns + 1):
        call = campaign.client_calls[t]
        primary = call.primary_advice_ids
        assert 3 <= len(primary) <= 5, f"turn {t} primary count {len(primary)}"
        assert call.decision_profile is not None, f"turn {t} has no decision profile"
        available = global_ids | {o.id for o in campaign.per_turn_advice.get(t, [])}
        assert set(primary).issubset(available), f"turn {t} primary not all available"
        alternatives = available - set(primary)
        assert alternatives, f"turn {t} offers no strategic alternative"
        # A red-line tag must never appear on an option the call calls on-brief.
        red = set(call.decision_profile.red_line_tags)
        by_id = {o.id: set(o.tags) for o in campaign.available_advice()}
        for aid in primary:
            assert not (by_id.get(aid, set()) & red), f"turn {t}: {aid} is on-brief but red-line"


# ---------------------------------------------------------------------------
# 2. Off-brief flagging + deterministic cost via AppliedDiff
# ---------------------------------------------------------------------------

def test_off_brief_pick_is_flagged_and_costs_through_applied_diff():
    campaign = _fresh()
    # On turn 1 the Town Manager did not ask about state support -> off-brief.
    assert "state_support" not in campaign.client_calls[1].primary_advice_ids
    result = turn.advance_turn(campaign, "state_support")

    d = result.decision
    assert d.off_brief is True
    assert d.off_brief_adjustments, "off-brief advice must carry a deterministic cost"
    assert d.cost_reason

    cost_diffs = [x for x in result.diffs if x.source_type == SourceType.DECISION]
    assert cost_diffs, "off-brief cost must be recorded as its own AppliedDiff batch"
    for diff in cost_diffs:
        assert diff.reason == d.cost_reason
        assert 0 <= diff.new_value <= 100
    touched = {x.variable for x in cost_diffs}
    assert "player_perceived_neutrality" in touched


def test_on_brief_pick_has_no_off_brief_cost():
    campaign = _fresh()
    assert "controlled_disclosure" in campaign.client_calls[1].primary_advice_ids
    result = turn.advance_turn(campaign, "controlled_disclosure")
    assert result.decision.off_brief is False
    assert result.decision.off_brief_adjustments == {}
    assert not [x for x in result.diffs if x.source_type == SourceType.DECISION]


# ---------------------------------------------------------------------------
# 3. Same advice, different callers -> different outcome (deterministic reason)
# ---------------------------------------------------------------------------

def test_same_advice_received_differently_by_factions():
    # Turn 1: delaying is on-brief for the Town Manager -> a real DELAYED outcome.
    c1 = _fresh()
    r1 = turn.advance_turn(c1, "delay_disclosure")
    assert r1.decision.decision_type == DecisionType.DELAYED
    assert r1.decision.off_brief is False

    # Turn 3: the Hospital has drawn a red line against delay -> REJECTED.
    c2 = _advance_to(_fresh(), 3)
    assert "delay" in c2.client_calls[3].decision_profile.red_line_tags
    r2 = turn.advance_turn(c2, "delay_disclosure")
    assert r2.decision.decision_type == DecisionType.REJECTED
    assert r2.decision.adherence == 0.0
    # The divergence is explained, not opaque.
    assert any("red line" in cf.lower() for cf in r2.decision.explanation.conflicts)


# ---------------------------------------------------------------------------
# 4. Rejection reachable without violating state invariants
# ---------------------------------------------------------------------------

def test_red_line_rejection_holds_state_invariants():
    campaign = _advance_to(_fresh(), 3)
    result = turn.advance_turn(campaign, "delay_disclosure")
    d = result.decision
    assert d.decision_type == DecisionType.REJECTED
    assert d.adherence == 0.0
    assert d.modifications == {}
    # Advice contributed nothing; the ambient + red-line cost still emit diffs.
    assert result.diffs
    assert all(0 <= v <= 100 for v in campaign.world_state.variables.values())
    # A rejected turn is a normal resolved turn: campaign advanced, not corrupt.
    assert campaign.turn_number == 4


# ---------------------------------------------------------------------------
# 5. Every decision branch is reachable under plausible tested conditions
# ---------------------------------------------------------------------------

def test_followed_is_reachable_on_brief():
    campaign = _advance_to(_fresh(), 4)
    # Contractor pressure is on-brief for the contractor; with dependency not yet
    # decisive and budget intact, the squeeze holds -> FOLLOWED.
    result = turn.advance_turn(campaign, "contractor_pressure")
    assert result.decision.decision_type == DecisionType.FOLLOWED


def test_modified_is_reachable():
    campaign = _advance_to(_fresh(), 4)
    # A contractor holding decisive leverage reworks the squeeze -> MODIFIED.
    campaign.world_state.variables["contractor_dependency"] = 75
    result = turn.advance_turn(campaign, "contractor_pressure")
    assert result.decision.decision_type == DecisionType.MODIFIED


def test_delayed_is_reachable_on_brief():
    campaign = _fresh()
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert result.decision.decision_type == DecisionType.DELAYED


def test_rejected_is_reachable_via_red_line():
    campaign = _advance_to(_fresh(), 3)
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert result.decision.decision_type == DecisionType.REJECTED


def test_all_four_required_branches_reachable_in_one_sweep():
    seen = set()
    # DELAYED
    seen.add(turn.advance_turn(_fresh(), "delay_disclosure").decision.decision_type)
    # FOLLOWED
    seen.add(turn.advance_turn(_advance_to(_fresh(), 4), "contractor_pressure").decision.decision_type)
    # MODIFIED
    c = _advance_to(_fresh(), 4)
    c.world_state.variables["contractor_dependency"] = 75
    seen.add(turn.advance_turn(c, "contractor_pressure").decision.decision_type)
    # REJECTED
    seen.add(turn.advance_turn(_advance_to(_fresh(), 3), "delay_disclosure").decision.decision_type)
    assert {
        DecisionType.FOLLOWED,
        DecisionType.MODIFIED,
        DecisionType.DELAYED,
        DecisionType.REJECTED,
    }.issubset(seen)


# ---------------------------------------------------------------------------
# 6. Relevance materially changes the outcome (on-brief vs off-brief)
# ---------------------------------------------------------------------------

def test_relevance_changes_reception_of_same_option():
    # mutual_aid is on-brief on the Hospital call (turn 3) but off-brief on the
    # Schools call (turn 2). Same option, materially different reception.
    on_brief = turn.advance_turn(_advance_to(_fresh(), 3), "mutual_aid").decision
    off_brief = turn.advance_turn(_advance_to(_fresh(), 2), "mutual_aid").decision

    assert on_brief.off_brief is False
    assert off_brief.off_brief is True
    assert off_brief.off_brief_adjustments and not on_brief.off_brief_adjustments
    # Off-brief conviction never exceeds the on-brief version of the same advice.
    assert off_brief.adherence <= on_brief.adherence


# ---------------------------------------------------------------------------
# 7. Determinism, including off-brief and red-line turns
# ---------------------------------------------------------------------------

def test_replay_is_deterministic_with_off_brief_and_red_line():
    # A sequence that deliberately mixes on-brief, off-brief, and a red-line pick.
    seq = [
        "controlled_disclosure",   # 1 on-brief
        "state_support",           # 2 off-brief
        "delay_disclosure",        # 3 red-line -> REJECTED
        "contractor_pressure",     # 4 on-brief
    ]

    def play():
        c = _fresh()
        out = []
        for aid in seq:
            r = turn.advance_turn(c, aid)
            out.append(r)
        return c, out

    ca, ra = play()
    cb, rb = play()
    assert ca.world_state.variables == cb.world_state.variables
    for a, b in zip(ra, rb):
        assert a.decision.decision_type == b.decision.decision_type
        assert a.decision.adherence == b.decision.adherence
        assert a.decision.off_brief == b.decision.off_brief
        assert a.decision.off_brief_adjustments == b.decision.off_brief_adjustments
        assert [(d.variable, d.new_value, d.delta, d.source_type) for d in a.diffs] == [
            (d.variable, d.new_value, d.delta, d.source_type) for d in b.diffs
        ]


# ---------------------------------------------------------------------------
# 8. Every mutation is diffed; the explanation is human-labeled
# ---------------------------------------------------------------------------

def test_off_brief_turn_diffs_account_for_every_change():
    campaign = _fresh()
    before = dict(campaign.world_state.variables)
    result = turn.advance_turn(campaign, "state_support")  # off-brief on turn 1
    after = campaign.world_state.variables

    changed = {k for k in after if after[k] != before[k]}
    diffed = {d.variable for d in result.diffs}
    assert changed.issubset(diffed), "every changed variable must have an AppliedDiff"


def test_decision_explanation_uses_human_labels_not_raw_scores():
    result = turn.advance_turn(_fresh(), "state_support")  # off-brief on turn 1
    ex = result.decision.explanation
    assert ex is not None
    assert ex.caller
    assert ex.outcome_reason
    assert ex.incentives, "explanation should surface caller incentives"
    assert ex.adherence_factors, "explanation should list labeled adherence factors"
    for factor in ex.adherence_factors:
        assert factor.label and factor.detail
        assert factor.direction in {"increase", "decrease", "neutral"}
    # Off-brief note is present precisely when off-brief (and not red-lined).
    assert ex.off_brief is True
    assert ex.off_brief_note


def test_engine_still_completes_and_can_fail_under_new_logic():
    # Sanity: the safe on-brief sweep completes; pure stalling collapses.
    good = _fresh()
    for aid in _SAFE_SEQ:
        if good.is_terminal():
            break
        turn.advance_turn(good, aid)
    assert good.status == "COMPLETED"

    bad = _fresh()
    while not bad.is_terminal():
        turn.advance_turn(bad, "delay_disclosure")
    assert bad.status == "FAILED"
