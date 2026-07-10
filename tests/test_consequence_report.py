"""Batch 8: the causal consequence report.

Every resolved turn carries a ``ConsequenceReport`` -- the authoritative
per-variable decomposition of how the starting snapshot became the resolved
snapshot (start -> attributed deltas -> final). These tests pin:

* exact grouping/reconciliation math against the applied diffs;
* the proposed-versus-applied advice mediation (rejected / delayed / reduced /
  clamped effects are recorded explicitly, never implied);
* ambient drift attribution and no-change variables;
* clamp boundaries;
* humanized labels and direction semantics;
* determinism, API-schema round-tripping, persistence backward-compatibility,
  and the dossier export of the same provenance.

Unit tests drive ``build_consequence_report`` directly with synthetic diffs for
exact control; integration tests go through ``advance_turn`` on the real
Northbridge content.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from engine import seed_data, turn
from engine.consequences import build_consequence_report
from engine.diffs import apply_diffs
from engine.dossier import render_dossier_markdown
from engine.models import (
    AdviceEffectOutcome,
    AdviceOption,
    DecisionType,
    NpcDecision,
    SourceType,
)
from engine.state import humanize_variable, variable_direction
from memory.persistence import decode_campaign, encode_campaign


def _fresh():
    return seed_data.create_northbridge_campaign(name="report-test")


def _advance_to(campaign, target_turn):
    safe = [
        "controlled_disclosure",
        "school_staged_closure",
        "hospital_priority_allocation",
        "contractor_pressure",
        "controlled_disclosure",
        "state_support",
        "controlled_disclosure",
        "controlled_disclosure",
        "contractor_pressure",
        "state_support",
    ]
    while campaign.turn_number < target_turn and not campaign.is_terminal():
        turn.advance_turn(campaign, safe[campaign.turn_number - 1])
    return campaign


def _advice(effects, label="Test advice"):
    return AdviceOption(
        id="test_advice",
        label=label,
        summary="s",
        rationale="r",
        tags=["disclosure"],
        effects=effects,
    )


def _decision(decision_type=DecisionType.FOLLOWED, adherence=1.0):
    return NpcDecision(
        advice_id="test_advice",
        decision_type=decision_type,
        decider="Test Faction",
        rationale="because",
        adherence=adherence,
    )


# ---------------------------------------------------------------------------
# Exact grouping and reconciliation math (synthetic)
# ---------------------------------------------------------------------------

def test_report_groups_ordered_deltas_and_reconciles_exactly():
    variables = {"public_trust": 50, "media_pressure": 40}
    start = dict(variables)
    advice = _advice({"public_trust": 6, "media_pressure": -4})
    decision = _decision(adherence=1.0)

    diffs = []
    diffs += apply_diffs(variables, {"public_trust": 6, "media_pressure": -4},
                         reason="Advice — Test advice", source_type=SourceType.ADVICE)
    diffs += apply_diffs(variables, {"public_trust": -2},
                         reason="NPC modification (MODIFIED)",
                         source_type=SourceType.NPC_MODIFICATION)
    diffs += apply_diffs(variables, {"media_pressure": 3},
                         reason="Ambient crisis pressure", source_type=SourceType.AMBIENT)

    report = build_consequence_report(start, diffs, advice, decision)
    by_var = {e.variable: e for e in report.variables}
    assert set(by_var) == {"public_trust", "media_pressure"}

    trust = by_var["public_trust"]
    assert (trust.start_value, trust.final_value, trust.net_delta) == (50, 54, 4)
    assert [(d.source_type, d.delta) for d in trust.deltas] == [
        (SourceType.ADVICE, 6),
        (SourceType.NPC_MODIFICATION, -2),
    ]
    # Each step chains: value_after of one step is value_before of the next.
    assert trust.deltas[0].value_after == trust.deltas[1].value_before

    media = by_var["media_pressure"]
    assert (media.start_value, media.final_value, media.net_delta) == (40, 39, -1)
    assert [(d.source_type, d.delta) for d in media.deltas] == [
        (SourceType.ADVICE, -4),
        (SourceType.AMBIENT, 3),
    ]

    # The invariant: start + sum(deltas) == final, exactly, for every entry.
    for entry in report.variables:
        assert entry.start_value + sum(d.delta for d in entry.deltas) == entry.final_value
        assert entry.net_delta == entry.final_value - entry.start_value


def test_report_is_sorted_by_net_move_then_variable():
    variables = {"public_trust": 50, "media_pressure": 40, "public_order": 60}
    start = dict(variables)
    diffs = apply_diffs(
        variables,
        {"public_trust": 1, "media_pressure": -7, "public_order": -1},
        reason="Ambient crisis pressure",
        source_type=SourceType.AMBIENT,
    )
    report = build_consequence_report(start, diffs, _advice({}), _decision())
    assert [e.variable for e in report.variables] == [
        "media_pressure",   # |net| 7
        "public_order",     # |net| 1, alphabetical before public_trust
        "public_trust",
    ]


# ---------------------------------------------------------------------------
# Advice mediation: rejected / delayed / reduced / clamped, never implied
# ---------------------------------------------------------------------------

def test_rejected_advice_is_recorded_as_proposed_but_not_applied():
    variables = {"public_trust": 50}
    start = dict(variables)
    advice = _advice({"public_trust": 8})
    decision = _decision(DecisionType.REJECTED, adherence=0.0)
    # Rejection means no advice diff exists at all -- only the report can say
    # the proposal happened.
    report = build_consequence_report(start, [], advice, decision)
    assert len(report.variables) == 1
    entry = report.variables[0]
    assert entry.variable == "public_trust"
    assert entry.start_value == entry.final_value == 50
    assert entry.net_delta == 0
    assert entry.deltas == []
    med = entry.advice
    assert med is not None
    assert med.proposed_delta == 8
    assert med.applied_delta == 0
    assert med.outcome == AdviceEffectOutcome.REJECTED


def test_delayed_advice_with_no_applied_effect_is_marked_delayed():
    variables = {"public_trust": 50}
    report = build_consequence_report(
        dict(variables), [], _advice({"public_trust": 8}),
        _decision(DecisionType.DELAYED, adherence=0.0),
    )
    assert report.variables[0].advice.outcome == AdviceEffectOutcome.DELAYED


def test_reduced_adherence_shows_proposed_versus_applied():
    variables = {"public_trust": 50}
    start = dict(variables)
    advice = _advice({"public_trust": 8})
    decision = _decision(DecisionType.MODIFIED, adherence=0.6)
    scaled = int(round(8 * 0.6))  # 5 — what the engine actually requests
    diffs = apply_diffs(variables, {"public_trust": scaled},
                        reason="Advice — Test advice", source_type=SourceType.ADVICE)
    report = build_consequence_report(start, diffs, advice, decision)
    med = report.variables[0].advice
    assert med.proposed_delta == 8
    assert med.expected_delta == 5
    assert med.applied_delta == 5
    assert med.outcome == AdviceEffectOutcome.REDUCED
    assert med.clamped is False


def test_clamped_advice_effect_is_flagged_and_still_reconciles():
    variables = {"public_trust": 98}
    start = dict(variables)
    advice = _advice({"public_trust": 8})
    decision = _decision(adherence=1.0)
    diffs = apply_diffs(variables, {"public_trust": 8},
                        reason="Advice — Test advice", source_type=SourceType.ADVICE)
    report = build_consequence_report(start, diffs, advice, decision)
    entry = report.variables[0]
    assert entry.final_value == 100
    assert entry.net_delta == 2
    med = entry.advice
    assert med.proposed_delta == 8
    assert med.expected_delta == 8
    assert med.applied_delta == 2      # the effective, post-clamp truth
    assert med.clamped is True
    assert med.outcome == AdviceEffectOutcome.REDUCED
    assert entry.start_value + sum(d.delta for d in entry.deltas) == entry.final_value


def test_fully_applied_advice_is_marked_applied():
    variables = {"public_trust": 50}
    start = dict(variables)
    diffs = apply_diffs(variables, {"public_trust": 8},
                        reason="Advice — Test advice", source_type=SourceType.ADVICE)
    report = build_consequence_report(
        start, diffs, _advice({"public_trust": 8}), _decision(adherence=1.0)
    )
    med = report.variables[0].advice
    assert med.outcome == AdviceEffectOutcome.APPLIED
    assert med.clamped is False


# ---------------------------------------------------------------------------
# Ambient drift and no-change variables
# ---------------------------------------------------------------------------

def test_ambient_only_variable_is_attributed_to_ambient_without_mediation():
    variables = {"legal_exposure": 30}
    start = dict(variables)
    diffs = apply_diffs(variables, {"legal_exposure": 2},
                        reason="Ambient crisis pressure", source_type=SourceType.AMBIENT)
    report = build_consequence_report(start, diffs, _advice({"public_trust": 4}), _decision())
    by_var = {e.variable: e for e in report.variables}
    legal = by_var["legal_exposure"]
    assert [d.source_type for d in legal.deltas] == [SourceType.AMBIENT]
    assert legal.advice is None


def test_untouched_unproposed_variables_are_absent_from_the_report():
    variables = {"public_trust": 50, "staff_capacity": 60}
    start = dict(variables)
    diffs = apply_diffs(variables, {"public_trust": 3},
                        reason="Advice — Test advice", source_type=SourceType.ADVICE)
    report = build_consequence_report(start, diffs, _advice({"public_trust": 3}), _decision())
    assert {e.variable for e in report.variables} == {"public_trust"}


def test_zero_proposed_effect_does_not_create_an_entry():
    variables = {"public_trust": 50}
    report = build_consequence_report(
        dict(variables), [], _advice({"public_trust": 0}), _decision()
    )
    assert report.variables == []


# ---------------------------------------------------------------------------
# Human labels and direction semantics
# ---------------------------------------------------------------------------

def test_labels_are_humanized_and_directions_semantically_correct():
    variables = {"water_security": 60, "legal_exposure": 30}
    start = dict(variables)
    diffs = apply_diffs(variables, {"water_security": -3, "legal_exposure": 2},
                        reason="Ambient crisis pressure", source_type=SourceType.AMBIENT)
    report = build_consequence_report(start, diffs, _advice({}), _decision())
    by_var = {e.variable: e for e in report.variables}
    assert by_var["water_security"].label == "Water Security"
    assert by_var["water_security"].direction == "higher_is_better"
    assert by_var["legal_exposure"].label == "Legal Exposure"
    assert by_var["legal_exposure"].direction == "higher_is_worse"


def test_direction_vocabulary_covers_every_scenario_variable():
    campaign = _fresh()
    for variable in campaign.world_state.variables:
        assert variable_direction(variable) in {"higher_is_better", "higher_is_worse"}
        assert humanize_variable(variable) != variable


# ---------------------------------------------------------------------------
# Integration through advance_turn on real Northbridge content
# ---------------------------------------------------------------------------

def test_resolved_turn_report_matches_authoritative_state_and_diffs():
    campaign = _fresh()
    before = dict(campaign.world_state.variables)
    result = turn.advance_turn(campaign, "controlled_disclosure")
    after = campaign.world_state.variables
    report = result.consequence_report

    assert report.variables, "a resolved turn must carry a populated report"
    by_var = {e.variable: e for e in report.variables}

    # Every changed variable is in the report; the report never invents change.
    changed = {k for k in after if after[k] != before[k]}
    assert changed.issubset(set(by_var))
    for entry in report.variables:
        assert entry.start_value == before[entry.variable]
        assert entry.final_value == after[entry.variable]
        assert entry.start_value + sum(d.delta for d in entry.deltas) == entry.final_value

    # The report's deltas are exactly the applied diffs, grouped and ordered.
    flattened = [
        (e.variable, d.source_type, d.delta, d.value_before, d.value_after)
        for e in report.variables
        for d in e.deltas
    ]
    from_diffs = [
        (d.variable, d.source_type, d.delta, d.old_value, d.new_value)
        for d in result.diffs
    ]
    assert sorted(flattened) == sorted(from_diffs)


def test_red_line_rejection_report_shows_every_proposed_effect_as_rejected():
    campaign = _advance_to(_fresh(), 3)
    advice = turn.find_advice(campaign, "delay_disclosure")
    result = turn.advance_turn(campaign, "delay_disclosure")
    assert result.decision.decision_type == DecisionType.REJECTED
    by_var = {e.variable: e for e in result.consequence_report.variables}
    for variable, proposed in advice.effects.items():
        if proposed == 0:
            continue
        entry = by_var[variable]
        assert entry.advice is not None
        assert entry.advice.proposed_delta == proposed
        assert entry.advice.applied_delta == 0
        assert entry.advice.outcome == AdviceEffectOutcome.REJECTED
        # Rejected advice contributed no delta -- any movement is drift/cost.
        assert all(d.source_type != SourceType.ADVICE for d in entry.deltas)


def test_report_is_deterministic_across_replays():
    def play():
        c = _fresh()
        r1 = turn.advance_turn(c, "controlled_disclosure")
        r2 = turn.advance_turn(c, "school_staged_closure")
        return [asdict(r1.consequence_report), asdict(r2.consequence_report)]

    assert play() == play()


def test_report_survives_the_api_schema_boundary():
    import os
    import sys
    backend = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.schemas import api as schemas

    result = turn.advance_turn(_fresh(), "controlled_disclosure")
    model = schemas.TurnResultModel.model_validate(asdict(result))
    assert model.consequence_report.variables
    assert asdict(result.consequence_report) == model.consequence_report.model_dump()


# ---------------------------------------------------------------------------
# Persistence backward-compatibility and dossier export
# ---------------------------------------------------------------------------

def test_persisted_turn_without_report_rebuilds_with_empty_report():
    campaign = _fresh()
    turn.advance_turn(campaign, "controlled_disclosure")
    raw = json.loads(encode_campaign(campaign))
    for stored_turn in raw["data"]["turn_history"]:
        del stored_turn["consequence_report"]
    revived = decode_campaign(json.dumps(raw))
    assert revived.turn_history[0].consequence_report.variables == []


def test_persistence_round_trips_the_report_exactly():
    campaign = _fresh()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    revived = decode_campaign(encode_campaign(campaign))
    assert asdict(revived.turn_history[0].consequence_report) == asdict(
        result.consequence_report
    )


def test_dossier_exports_the_state_reconciliation_from_stable_provenance():
    campaign = _fresh()
    result = turn.advance_turn(campaign, "controlled_disclosure")
    markdown = render_dossier_markdown(campaign)
    assert "State reconciliation" in markdown
    top = result.consequence_report.variables[0]
    sign = "+" if top.net_delta > 0 else ""
    assert (
        f"{top.label}: {top.start_value} → {top.final_value} "
        f"(net {sign}{top.net_delta})"
    ) in markdown


def test_dossier_reports_rejected_advice_explicitly():
    campaign = _advance_to(_fresh(), 3)
    turn.advance_turn(campaign, "delay_disclosure")
    markdown = render_dossier_markdown(campaign)
    assert "rejected — not applied" in markdown
