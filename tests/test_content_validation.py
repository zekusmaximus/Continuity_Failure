"""Scenario content-layer validation tests.

These exercise the versioned/validated content layer added in the content-split
batch: they confirm the shipped Northbridge content is valid, that the loader
reproduces the pre-extraction campaign, and that a focused defect in any content
domain fails with a precise, file/field-anchored error *before* a campaign is
seeded. They import only the ``engine`` package (framework-free).

Each ``test_reject_*`` is a focused invalid fixture: it starts from the real,
valid content bundle and injects exactly one defect, so the assertions describe
the single thing that should fail.
"""

from __future__ import annotations

import copy

import pytest

from engine.content import (
    NORTHBRIDGE_SCENARIO_ID,
    build_campaign,
    load_campaign,
    loader,
    validate_scenario,
)
from engine.content.loader import IncompatibleSchemaVersion
from engine.content.validator import ContentValidationError, validate_bundle


def valid_bundle():
    """A deep copy of the real content bundle, safe to mutate per test."""
    return copy.deepcopy(loader.load_raw(NORTHBRIDGE_SCENARIO_ID))


def _messages(exc: ContentValidationError):
    return [str(e) for e in exc.errors]


def _expect_invalid(bundle):
    with pytest.raises(ContentValidationError) as excinfo:
        validate_bundle(bundle)
    return excinfo.value


# ---------------------------------------------------------------------------
# 1. The shipped content is valid and reproduces the campaign
# ---------------------------------------------------------------------------

def test_shipped_northbridge_content_is_valid():
    # Both the pure validation entry point and the whole-bundle validator pass.
    validate_scenario(NORTHBRIDGE_SCENARIO_ID)
    validate_bundle(valid_bundle())


def test_loader_builds_expected_campaign_shape():
    campaign = load_campaign(NORTHBRIDGE_SCENARIO_ID, campaign_id="fixed", name="Test")
    assert campaign.scenario_id == NORTHBRIDGE_SCENARIO_ID
    assert campaign.max_turns == 10
    assert campaign.turn_number == 1
    assert len(campaign.world_state.factions) == 10
    assert len(campaign.advice_options) == 6
    assert set(campaign.per_turn_advice) == {2, 3, 7}
    assert set(campaign.client_calls) == set(range(1, 11))
    assert len(campaign.documents) == 12
    assert len(campaign.thread_specs) == 5
    assert campaign.world_state.active_crisis.id == "northbridge_water_crisis"
    assert len(campaign.world_state.variables) == 16


# ---------------------------------------------------------------------------
# 2. Unique IDs
# ---------------------------------------------------------------------------

def test_reject_duplicate_faction_id():
    bundle = valid_bundle()
    bundle.factions[1]["id"] = bundle.factions[0]["id"]
    exc = _expect_invalid(bundle)
    assert any("duplicate faction id" in m for m in _messages(exc))
    assert any(e.file == "factions.json" for e in exc.errors)


def test_reject_duplicate_advice_id_across_global_and_per_turn():
    bundle = valid_bundle()
    # Collide a per-turn advice id with a global advice id.
    bundle.per_turn_advice["2"][0]["id"] = bundle.advice[0]["id"]
    exc = _expect_invalid(bundle)
    assert any("duplicate advice id" in m for m in _messages(exc))


def test_reject_duplicate_document_id():
    bundle = valid_bundle()
    bundle.documents[2]["id"] = bundle.documents[0]["id"]
    exc = _expect_invalid(bundle)
    assert any("duplicate document id" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 3. Known cross-references
# ---------------------------------------------------------------------------

def test_reject_unknown_caller_faction():
    bundle = valid_bundle()
    bundle.calls[0]["caller_faction_id"] = "ministry_of_typos"
    exc = _expect_invalid(bundle)
    assert any("references unknown faction 'ministry_of_typos'" in m for m in _messages(exc))


def test_reject_unknown_attached_document():
    bundle = valid_bundle()
    bundle.calls[0]["attached_document_ids"][0] = "doc_missing"
    exc = _expect_invalid(bundle)
    assert any("references unknown document 'doc_missing'" in m for m in _messages(exc))


def test_reject_unknown_affected_faction_in_advice():
    bundle = valid_bundle()
    bundle.advice[0]["affected_factions"][0] = "nobody"
    exc = _expect_invalid(bundle)
    assert any("references unknown faction 'nobody'" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 4. Known WorldState variables and effect maps
# ---------------------------------------------------------------------------

def test_reject_unknown_starting_variable():
    bundle = valid_bundle()
    bundle.scenario["starting_variables"]["watr_security"] = 40
    exc = _expect_invalid(bundle)
    assert any("unknown WorldState variable 'watr_security'" in m for m in _messages(exc))


def test_reject_missing_starting_variable():
    bundle = valid_bundle()
    del bundle.scenario["starting_variables"]["water_security"]
    exc = _expect_invalid(bundle)
    assert any("missing known WorldState variable 'water_security'" in m for m in _messages(exc))
    # A missing threshold variable is also independently reported.
    assert any("failure-threshold variable 'water_security'" in m for m in _messages(exc))


def test_reject_unknown_effect_variable():
    bundle = valid_bundle()
    bundle.advice[0]["effects"]["public_trst"] = 5
    exc = _expect_invalid(bundle)
    assert any("public_trst" in m and "effect map" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 5. Enums and ranges
# ---------------------------------------------------------------------------

def test_reject_out_of_range_faction_influence():
    bundle = valid_bundle()
    bundle.factions[0]["influence"] = 150
    exc = _expect_invalid(bundle)
    assert any("within [0, 100]" in m for m in _messages(exc))


def test_reject_out_of_range_effect_delta():
    bundle = valid_bundle()
    bundle.advice[0]["effects"]["public_trust"] = 999
    exc = _expect_invalid(bundle)
    assert any("within [-100, 100]" in m for m in _messages(exc))


def test_reject_unknown_document_reliability_enum():
    bundle = valid_bundle()
    bundle.documents[0]["reliability"] = "super-solid"
    exc = _expect_invalid(bundle)
    assert any("unknown reliability 'super-solid'" in m for m in _messages(exc))


def test_reject_unknown_call_urgency_enum():
    bundle = valid_bundle()
    bundle.calls[0]["urgency"] = "SUPER_URGENT"
    exc = _expect_invalid(bundle)
    assert any("unknown urgency 'SUPER_URGENT'" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 6. Advice tags (decision routing)
# ---------------------------------------------------------------------------

def test_reject_advice_without_recognized_decision_tag():
    bundle = valid_bundle()
    bundle.advice[0]["tags"] = ["disclsure"]  # typo of "disclosure"
    exc = _expect_invalid(bundle)
    assert any("no recognized decision tag" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 7. operational_steps structure
# ---------------------------------------------------------------------------

def test_reject_empty_operational_steps():
    bundle = valid_bundle()
    bundle.advice[0]["operational_steps"] = []
    exc = _expect_invalid(bundle)
    assert any("operational_steps must not be empty" in m for m in _messages(exc))


def test_reject_malformed_operational_steps_entries():
    bundle = valid_bundle()
    bundle.advice[0]["operational_steps"] = ["do the thing", "   "]
    exc = _expect_invalid(bundle)
    assert any("operational_steps entries must be non-empty strings" in m for m in _messages(exc))


def test_reject_operational_steps_not_a_list():
    bundle = valid_bundle()
    bundle.advice[0]["operational_steps"] = "just wing it"
    exc = _expect_invalid(bundle)
    assert any("operational_steps must be a list" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 8. Unknown / missing fields
# ---------------------------------------------------------------------------

def test_reject_unknown_field_on_faction():
    bundle = valid_bundle()
    bundle.factions[0]["colour"] = "blue"
    exc = _expect_invalid(bundle)
    assert any("unknown field 'colour'" in m for m in _messages(exc))
    assert any(e.path.endswith(".colour") for e in exc.errors)


def test_reject_missing_required_field_on_document():
    bundle = valid_bundle()
    del bundle.documents[0]["title"]
    exc = _expect_invalid(bundle)
    assert any("missing required field 'title'" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 9. Turn ordering / coverage
# ---------------------------------------------------------------------------

def test_reject_missing_turn_coverage():
    bundle = valid_bundle()
    bundle.calls = [c for c in bundle.calls if c["turn"] != 5]
    exc = _expect_invalid(bundle)
    assert any("no client call defined for turn 5" in m for m in _messages(exc))


def test_reject_duplicate_turn_coverage():
    bundle = valid_bundle()
    bundle.calls[1]["turn"] = bundle.calls[0]["turn"]
    exc = _expect_invalid(bundle)
    assert any("already has a call" in m for m in _messages(exc))


def test_reject_per_turn_advice_out_of_range_key():
    bundle = valid_bundle()
    bundle.per_turn_advice["99"] = bundle.per_turn_advice["2"]
    exc = _expect_invalid(bundle)
    assert any("outside 1..10" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 9b. Call-specific advice space (Batch 6)
# ---------------------------------------------------------------------------

def test_reject_call_missing_primary_advice():
    bundle = valid_bundle()
    del bundle.calls[0]["primary_advice_ids"]
    exc = _expect_invalid(bundle)
    assert any("must declare primary_advice_ids" in m for m in _messages(exc))


def test_reject_primary_advice_unknown_option():
    bundle = valid_bundle()
    bundle.calls[0]["primary_advice_ids"][0] = "not_a_real_option"
    exc = _expect_invalid(bundle)
    assert any("not an option available on turn 1" in m for m in _messages(exc))


def test_reject_primary_advice_out_of_count_range():
    bundle = valid_bundle()
    bundle.calls[0]["primary_advice_ids"] = ["controlled_disclosure"]
    exc = _expect_invalid(bundle)
    assert any("primary advice options, got 1" in m for m in _messages(exc))


def test_reject_primary_option_crossing_a_red_line():
    bundle = valid_bundle()
    # Turn 3 (hospital) red-lines "delay"; listing the delay option as on-brief
    # must be caught.
    hospital_call = next(c for c in bundle.calls if c["turn"] == 3)
    hospital_call["primary_advice_ids"][0] = "delay_disclosure"
    exc = _expect_invalid(bundle)
    assert any("carries a red-line tag" in m for m in _messages(exc))


def test_reject_unknown_decision_priority_variable():
    bundle = valid_bundle()
    bundle.calls[0]["decision_profile"]["priorities"] = ["watr_security"]
    exc = _expect_invalid(bundle)
    assert any("unknown WorldState variable 'watr_security'" in m for m in _messages(exc))


def test_reject_unknown_red_line_tag():
    bundle = valid_bundle()
    bundle.calls[2]["decision_profile"]["red_line_tags"] = ["dilly_dally"]
    exc = _expect_invalid(bundle)
    assert any("unknown decision tag 'dilly_dally'" in m for m in _messages(exc))


def test_reject_out_of_range_off_brief_tolerance():
    bundle = valid_bundle()
    bundle.calls[0]["decision_profile"]["off_brief_tolerance"] = 250
    exc = _expect_invalid(bundle)
    assert any("within [0, 100]" in m for m in _messages(exc))


def test_reject_unknown_field_on_decision_profile():
    bundle = valid_bundle()
    bundle.calls[0]["decision_profile"]["mood"] = "grumpy"
    exc = _expect_invalid(bundle)
    assert any("unknown field 'mood'" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# 10. Schema version incompatibility
# ---------------------------------------------------------------------------

def test_reject_unsupported_schema_version_via_build():
    bundle = valid_bundle()
    bundle.scenario["schema_version"] = 999
    with pytest.raises(IncompatibleSchemaVersion) as excinfo:
        build_campaign(bundle)
    assert "999" in str(excinfo.value)


def test_apply_schema_version_passes_current():
    bundle = valid_bundle()
    # Current version returns the bundle unchanged (no raise).
    assert loader._apply_schema_version(bundle) is bundle


# ---------------------------------------------------------------------------
# 11. Error collection and anchoring
# ---------------------------------------------------------------------------

def test_multiple_errors_are_collected_in_one_pass():
    bundle = valid_bundle()
    bundle.factions[0]["influence"] = 150            # range error
    bundle.advice[0]["effects"]["nope"] = 3          # unknown-variable error
    bundle.calls[0]["caller_faction_id"] = "ghost"   # cross-ref error
    exc = _expect_invalid(bundle)
    assert len(exc.errors) >= 3
    files = {e.file for e in exc.errors}
    assert {"factions.json", "advice.json", "calls.json"}.issubset(files)


def test_errors_carry_file_and_path_context():
    bundle = valid_bundle()
    bundle.advice[2]["effects"]["bogus"] = 4
    exc = _expect_invalid(bundle)
    hit = [e for e in exc.errors if e.file == "advice.json" and "bogus" in e.path]
    assert hit, "expected an advice.json error anchored at the bogus effect path"
    assert "[2].effects.bogus" == hit[0].path


# ---------------------------------------------------------------------------
# 12. Loader edge cases (on-disk paths)
# ---------------------------------------------------------------------------

def test_missing_scenario_directory_is_a_validation_error():
    with pytest.raises(ContentValidationError) as excinfo:
        loader.load_raw("no_such_scenario")
    assert any("directory not found" in m for m in _messages(excinfo.value))


def test_invalid_json_reports_the_offending_file(tmp_path, monkeypatch):
    scenario_dir = tmp_path / "broken_scenario"
    scenario_dir.mkdir()
    (scenario_dir / "scenario.json").write_text("{ not valid json ", encoding="utf-8")
    monkeypatch.setattr(loader, "_CONTENT_ROOT", str(tmp_path))
    with pytest.raises(ContentValidationError) as excinfo:
        loader.load_raw("broken_scenario")
    errors = excinfo.value.errors
    assert errors[0].file == "scenario.json"
    assert "invalid JSON" in errors[0].message


def test_validate_module_scans_shipped_scenarios():
    # The developer command entry point validates the real content directory.
    import engine.content.__main__ as cli
    assert cli.main(["validate"]) == 0


# ---------------------------------------------------------------------------
# Thread lifecycle schedule fields
# ---------------------------------------------------------------------------

def test_reject_thread_due_turn_out_of_range():
    bundle = valid_bundle()
    bundle.threads[0]["due_turn"] = 99
    exc = _expect_invalid(bundle)
    assert any("due_turn" in m for m in _messages(exc))


def test_reject_unknown_variable_in_escalation_effects():
    bundle = valid_bundle()
    bundle.threads[0]["escalation_effects"] = {"not_a_variable": 5}
    exc = _expect_invalid(bundle)
    assert any("unknown WorldState variable 'not_a_variable'" in m for m in _messages(exc))


def test_reject_escalation_effects_without_note():
    bundle = valid_bundle()
    bundle.threads[0]["escalation_effects"] = {"legal_exposure": 4}
    bundle.threads[0]["escalation_note"] = ""
    exc = _expect_invalid(bundle)
    assert any("escalation_note" in m for m in _messages(exc))


def test_reject_unknown_resolve_tag():
    bundle = valid_bundle()
    bundle.threads[0]["resolve_tags"] = ["not_a_tag"]
    exc = _expect_invalid(bundle)
    assert any("resolve tag 'not_a_tag'" in m for m in _messages(exc))


def test_reject_bad_resolve_condition():
    bundle = valid_bundle()
    bundle.threads[0]["resolve_conditions"] = [
        {"variable": "nope", "op": "==", "threshold": 500}
    ]
    exc = _expect_invalid(bundle)
    messages = _messages(exc)
    assert any("unknown WorldState variable 'nope'" in m for m in messages)
    assert any("op must be one of" in m for m in messages)
    assert any("threshold" in m for m in messages)


def test_reject_authored_runtime_thread_fields():
    bundle = valid_bundle()
    bundle.threads[0]["escalation_count"] = 2
    bundle.threads[0]["turn_resolved"] = 3
    bundle.threads[0]["status"] = "escalating"
    exc = _expect_invalid(bundle)
    messages = _messages(exc)
    assert sum("engine-owned runtime state" in m for m in messages) == 3


def test_reject_negative_repeat_every():
    bundle = valid_bundle()
    bundle.threads[0]["repeat_every"] = -1
    exc = _expect_invalid(bundle)
    assert any("repeat_every" in m for m in _messages(exc))


# ---------------------------------------------------------------------------
# Thread specs (dynamic-thread opening rules, thread_specs.json)
# ---------------------------------------------------------------------------

def test_loader_builds_thread_specs():
    campaign = load_campaign(NORTHBRIDGE_SCENARIO_ID, campaign_id="fixed")
    assert [s.id for s in campaign.thread_specs] == [
        "thread_concealment_narrative",
        "thread_oversight_designation",
        "thread_contractor_precedent",
        "thread_school_standoff",
        "thread_trust_collapse",
    ]
    concealment = campaign.thread_specs[0]
    assert concealment.open_advice_tags == ["delay"]
    assert concealment.open_decision_types == ["DELAYED"]
    assert concealment.open_conditions_all[0].variable == "media_pressure"
    assert concealment.due_in == 2 and concealment.repeat_every == 2


def test_reject_thread_spec_without_any_opening_trigger():
    bundle = valid_bundle()
    for key in ("open_conditions_all", "open_conditions_any",
                "open_advice_tags", "open_decision_types"):
        bundle.thread_specs[0].pop(key, None)
    exc = _expect_invalid(bundle)
    assert any("no opening trigger" in m for m in _messages(exc))


def test_reject_thread_spec_with_unknown_open_condition_variable():
    bundle = valid_bundle()
    bundle.thread_specs[0]["open_conditions_all"] = [
        {"variable": "not_a_variable", "op": ">=", "threshold": 45}
    ]
    exc = _expect_invalid(bundle)
    assert any("unknown WorldState variable 'not_a_variable'" in m
               for m in _messages(exc))


def test_reject_thread_spec_with_unknown_advice_tag_or_decision_type():
    bundle = valid_bundle()
    bundle.thread_specs[0]["open_advice_tags"] = ["not_a_tag"]
    bundle.thread_specs[0]["open_decision_types"] = ["SHRUGGED"]
    exc = _expect_invalid(bundle)
    messages = _messages(exc)
    assert any("open advice tag 'not_a_tag'" in m for m in messages)
    assert any("unknown decision type 'SHRUGGED'" in m for m in messages)


def test_reject_thread_spec_escalation_without_note():
    bundle = valid_bundle()
    bundle.thread_specs[0]["escalation_note"] = ""
    exc = _expect_invalid(bundle)
    assert any("escalation_note" in m for m in _messages(exc))


def test_reject_thread_spec_with_bad_due_in():
    bundle = valid_bundle()
    bundle.thread_specs[0]["due_in"] = 0
    exc = _expect_invalid(bundle)
    assert any("due_in" in m for m in _messages(exc))


def test_reject_thread_spec_id_colliding_with_seeded_thread():
    bundle = valid_bundle()
    bundle.thread_specs[0]["id"] = bundle.threads[0]["id"]
    exc = _expect_invalid(bundle)
    assert any("collides with a seeded thread" in m for m in _messages(exc))


def test_reject_duplicate_thread_spec_ids():
    bundle = valid_bundle()
    bundle.thread_specs[1]["id"] = bundle.thread_specs[0]["id"]
    exc = _expect_invalid(bundle)
    assert any("duplicate thread spec id" in m for m in _messages(exc))


def test_reject_unknown_thread_spec_field():
    bundle = valid_bundle()
    bundle.thread_specs[0]["opens_when"] = "media is high"
    exc = _expect_invalid(bundle)
    assert any("unknown field 'opens_when'" in m for m in _messages(exc))
