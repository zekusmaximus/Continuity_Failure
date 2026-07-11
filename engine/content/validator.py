"""Scenario content validator.

Validates a fully-parsed Northbridge content bundle *before* a campaign is
seeded, so malformed content fails early with a precise, actionable error
instead of silently changing or omitting gameplay. The validator never mutates
state and never constructs a campaign; it only inspects raw JSON-parsed data.

Design notes
------------
* Errors are collected, not raised one at a time, so an author sees every
  problem in one pass. Each error carries the source ``file`` and a ``path``
  (dotted/indexed pointer into that file) plus a human-readable message.
* Collection is bounded by safety: a check that structurally cannot proceed
  (e.g. ``factions.json`` is not a list) records one error and skips the
  dependent checks rather than raising.
* The engine dataclasses and rules are the source of truth for the contract
  (see ``engine/content/schema.py``); this module only enforces it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from engine.content import schema
from engine.content.schema import FieldSpec


class ContentError:
    """A single validation problem, anchored to a file and a field path."""

    __slots__ = ("file", "path", "message")

    def __init__(self, file: str, path: str, message: str) -> None:
        self.file = file
        self.path = path
        self.message = message

    def __str__(self) -> str:
        where = f"{self.file}:{self.path}" if self.path else self.file
        return f"{where}: {self.message}"


class ContentValidationError(Exception):
    """Raised when scenario content fails validation. Aggregates all errors."""

    def __init__(self, scenario_root: str, errors: List[ContentError]) -> None:
        self.scenario_root = scenario_root
        self.errors = errors
        lines = "\n".join(f"  - {e}" for e in errors)
        super().__init__(
            f"{len(errors)} content validation error(s) in '{scenario_root}':\n{lines}"
        )


class _Collector:
    def __init__(self) -> None:
        self.errors: List[ContentError] = []

    def add(self, file: str, path: str, message: str) -> None:
        self.errors.append(ContentError(file, path, message))

    # -- structural helpers -------------------------------------------------

    def is_mapping(self, file: str, path: str, obj: Any, label: str) -> bool:
        if not isinstance(obj, dict):
            self.add(file, path, f"{label} must be an object, got {type(obj).__name__}")
            return False
        return True

    def is_list(self, file: str, path: str, obj: Any, label: str) -> bool:
        if not isinstance(obj, list):
            self.add(file, path, f"{label} must be a list, got {type(obj).__name__}")
            return False
        return True

    def check_fields(
        self, file: str, path: str, obj: Dict[str, Any], spec: FieldSpec, label: str
    ) -> None:
        """Reject unknown keys and require the dataclass's mandatory keys."""
        for key in obj:
            if key not in spec.allowed:
                self.add(
                    file, f"{path}.{key}",
                    f"unknown field '{key}' on {label} (silently accepting a "
                    f"typo here would change or omit gameplay)",
                )
        for key in sorted(spec.required):
            if key not in obj:
                self.add(file, path, f"{label} is missing required field '{key}'")

    def check_int_range(
        self, file: str, path: str, value: Any, lo: int, hi: int
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            self.add(file, path, f"must be an integer, got {type(value).__name__}")
            return
        if not (lo <= value <= hi):
            self.add(file, path, f"must be within [{lo}, {hi}], got {value}")

    def check_enum(
        self, file: str, path: str, value: Any, allowed: Set[str], label: str
    ) -> None:
        if not isinstance(value, str):
            self.add(file, path, f"{label} must be a string, got {type(value).__name__}")
            return
        if value not in allowed:
            self.add(
                file, path,
                f"unknown {label} '{value}' (allowed: {', '.join(sorted(allowed))})",
            )

    def check_nonempty_str(self, file: str, path: str, value: Any, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            self.add(file, path, f"{label} must be a non-empty string")

    def check_str_list(
        self, file: str, path: str, value: Any, label: str, *, require_nonempty: bool
    ) -> None:
        if not isinstance(value, list):
            self.add(file, path, f"{label} must be a list")
            return
        if require_nonempty and not value:
            self.add(file, path, f"{label} must not be empty")
        for i, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                self.add(file, f"{path}[{i}]", f"{label} entries must be non-empty strings")


def _collect_ids(
    c: _Collector, file: str, entries: List[Any], label: str
) -> Set[str]:
    """Return the set of ``id`` values, recording duplicates as errors."""
    seen: Set[str] = set()
    dupes: Set[str] = set()
    for i, entry in enumerate(entries):
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            eid = entry["id"]
            if eid in seen and eid not in dupes:
                c.add(file, f"[{i}].id", f"duplicate {label} id '{eid}'")
                dupes.add(eid)
            seen.add(eid)
    return seen


# ---------------------------------------------------------------------------
# Per-domain validation
# ---------------------------------------------------------------------------

def _validate_scenario(c: _Collector, file: str, scenario: Any) -> Optional[int]:
    """Validate scenario metadata; return ``max_turns`` when usable."""
    if not c.is_mapping(file, "", scenario, "scenario metadata"):
        return None

    for key in scenario:
        if key not in schema.SCENARIO_ALLOWED_KEYS:
            c.add(file, key, f"unknown scenario metadata field '{key}'")
    for key in sorted(schema.SCENARIO_REQUIRED_KEYS):
        if key not in scenario:
            c.add(file, "", f"scenario metadata missing required field '{key}'")

    if not isinstance(scenario.get("schema_version"), int) or isinstance(
        scenario.get("schema_version"), bool
    ):
        c.add(file, "schema_version", "schema_version must be an integer")

    for key in ("scenario_id", "name"):
        if key in scenario:
            c.check_nonempty_str(file, key, scenario[key], key)

    max_turns = scenario.get("max_turns")
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns < 1:
        c.add(file, "max_turns", "max_turns must be an integer >= 1")
        max_turns = None

    _validate_starting_variables(c, file, scenario.get("starting_variables"))

    crisis = scenario.get("crisis")
    if crisis is not None and c.is_mapping(file, "crisis", crisis, "crisis"):
        c.check_fields(file, "crisis", crisis, schema.FIELD_SPECS["crisis"], "crisis")
        if "id" in crisis:
            c.check_nonempty_str(file, "crisis.id", crisis["id"], "crisis id")
        if "severity" in crisis:
            c.check_int_range(file, "crisis.severity", crisis["severity"], 0, 100)
        if "type" in crisis:
            c.check_enum(file, "crisis.type", crisis["type"], schema.CRISIS_TYPES, "crisis type")

    return max_turns


def _validate_starting_variables(c: _Collector, file: str, variables: Any) -> None:
    if not c.is_mapping(file, "starting_variables", variables, "starting_variables"):
        return
    present = set(variables)
    for missing in sorted(schema.KNOWN_VARIABLES - present):
        c.add(file, "starting_variables", f"missing known WorldState variable '{missing}'")
    for unknown in sorted(present - schema.KNOWN_VARIABLES):
        c.add(
            file, f"starting_variables.{unknown}",
            f"unknown WorldState variable '{unknown}' (not in the engine variable set)",
        )
    for name, value in variables.items():
        if name in schema.KNOWN_VARIABLES:
            c.check_int_range(file, f"starting_variables.{name}", value, 0, 100)

    # Threshold / drift coverage: every variable the rules act on must exist.
    for missing in sorted(schema.THRESHOLD_VARIABLES - present):
        c.add(file, "starting_variables",
              f"failure-threshold variable '{missing}' has no starting value")
    for missing in sorted(schema.AMBIENT_VARIABLES - present):
        c.add(file, "starting_variables",
              f"ambient-drift variable '{missing}' has no starting value")


def _validate_faction(c: _Collector, file: str, path: str, faction: Dict[str, Any]) -> None:
    c.check_fields(file, path, faction, schema.FIELD_SPECS["faction"], "faction")
    if "id" in faction:
        c.check_nonempty_str(file, f"{path}.id", faction["id"], "faction id")
    for key in ("name", "description", "posture"):
        if key in faction:
            c.check_nonempty_str(file, f"{path}.{key}", faction[key], key)
    if "alignment" in faction:
        c.check_enum(file, f"{path}.alignment", faction["alignment"],
                     schema.FACTION_ALIGNMENTS, "faction alignment")
    if "type" in faction:
        c.check_enum(file, f"{path}.type", faction["type"], schema.FACTION_TYPES, "faction type")
    for key in ("influence", "trust_in_player", "risk_tolerance", "current_pressure"):
        if key in faction:
            c.check_int_range(file, f"{path}.{key}", faction[key], 0, 100)
    for key in ("red_lines", "tags"):
        if key in faction:
            c.check_str_list(file, f"{path}.{key}", faction[key], key, require_nonempty=False)


def _validate_advice(
    c: _Collector, file: str, path: str, advice: Dict[str, Any], faction_ids: Set[str]
) -> None:
    c.check_fields(file, path, advice, schema.FIELD_SPECS["advice"], "advice option")
    if "id" in advice:
        c.check_nonempty_str(file, f"{path}.id", advice["id"], "advice id")
    for key in ("label", "summary", "rationale"):
        if key in advice:
            c.check_nonempty_str(file, f"{path}.{key}", advice[key], key)

    tags = advice.get("tags")
    if not isinstance(tags, list) or not tags:
        c.add(file, f"{path}.tags", "advice tags must be a non-empty list")
    else:
        c.check_str_list(file, f"{path}.tags", tags, "tags", require_nonempty=True)
        if not any(isinstance(t, str) and t in schema.KNOWN_DECISION_TAGS for t in tags):
            c.add(
                file, f"{path}.tags",
                "advice option has no recognized decision tag "
                f"(one of {', '.join(sorted(schema.KNOWN_DECISION_TAGS))}); it would "
                "fall through to the generic handler and resolve incorrectly",
            )

    effects = advice.get("effects")
    if not c.is_mapping(file, f"{path}.effects", effects, "effects"):
        pass
    elif not effects:
        c.add(file, f"{path}.effects", "effects must not be empty")
    else:
        for var, delta in effects.items():
            if var not in schema.KNOWN_VARIABLES:
                c.add(file, f"{path}.effects.{var}",
                      f"unknown WorldState variable '{var}' in effect map")
                continue
            c.check_int_range(file, f"{path}.effects.{var}", delta,
                              schema.MIN_EFFECT_DELTA, schema.MAX_EFFECT_DELTA)

    if "type" in advice:
        c.check_enum(file, f"{path}.type", advice["type"], schema.ADVICE_TYPES, "advice type")
    for key in ("legal_risk", "political_risk", "operational_risk"):
        if key in advice:
            c.check_int_range(file, f"{path}.{key}", advice[key], 0, 100)
    for key in ("expected_benefits", "expected_harms", "operational_steps"):
        c.check_str_list(file, f"{path}.{key}", advice.get(key, []), key, require_nonempty=True)

    for i, fid in enumerate(advice.get("affected_factions", []) or []):
        if isinstance(fid, str) and fid not in faction_ids:
            c.add(file, f"{path}.affected_factions[{i}]",
                  f"references unknown faction '{fid}'")


def _validate_call(
    c: _Collector, file: str, path: str, call: Dict[str, Any],
    faction_ids: Set[str], document_ids: Set[str], crisis_id: Optional[str],
    max_turns: Optional[int], global_advice_ids: Set[str],
    per_turn_advice_ids: Dict[int, Set[str]], advice_tags_by_id: Dict[str, Set[str]],
    all_call_ids: Optional[Set[str]] = None, allow_variants: bool = True,
) -> None:
    # ``variants`` is authored alongside the call but is not a ClientCall
    # field; extract it before the field check. A nested variant call may not
    # carry variants of its own -- there, the key is simply unknown.
    body = dict(call)
    raw_variants = body.pop("variants", None) if allow_variants else None
    c.check_fields(file, path, body, schema.FIELD_SPECS["call"], "client call")
    if "id" in call:
        c.check_nonempty_str(file, f"{path}.id", call["id"], "call id")
    if "caller" in call:
        c.check_nonempty_str(file, f"{path}.caller", call["caller"], "caller")
    if "ask" in call:
        c.check_nonempty_str(file, f"{path}.ask", call["ask"], "ask")

    turn = call.get("turn")
    if isinstance(turn, bool) or not isinstance(turn, int):
        c.add(file, f"{path}.turn", "call turn must be an integer")
    elif max_turns is not None and not (1 <= turn <= max_turns):
        c.add(file, f"{path}.turn", f"call turn {turn} is outside 1..{max_turns}")

    if "caller_faction_id" in call:
        fid = call["caller_faction_id"]
        if isinstance(fid, str) and fid not in faction_ids:
            c.add(file, f"{path}.caller_faction_id",
                  f"references unknown faction '{fid}'")
    if "crisis_id" in call and call["crisis_id"] is not None:
        if call["crisis_id"] != crisis_id:
            c.add(file, f"{path}.crisis_id",
                  f"references unknown crisis '{call['crisis_id']}'")
    if "urgency" in call:
        c.check_enum(file, f"{path}.urgency", call["urgency"], schema.URGENCY_VALUES, "urgency")
    if "public_exposure" in call:
        c.check_enum(file, f"{path}.public_exposure", call["public_exposure"],
                     schema.PUBLIC_STATUS_VALUES, "public_exposure")
    for key in ("known_facts", "unknown_facts", "immediate_risks"):
        if key in call:
            c.check_str_list(file, f"{path}.{key}", call[key], key, require_nonempty=False)

    for i, doc_id in enumerate(call.get("attached_document_ids", []) or []):
        if isinstance(doc_id, str) and doc_id not in document_ids:
            c.add(file, f"{path}.attached_document_ids[{i}]",
                  f"references unknown document '{doc_id}'")

    # --- Call-specific decision space (Batch 6) ---
    # Advice available on this call's turn = global options + that turn's options.
    available = set(global_advice_ids)
    if isinstance(turn, int) and not isinstance(turn, bool):
        available |= per_turn_advice_ids.get(turn, set())

    # The caller's red-line tags gate the on-brief invariant below.
    red_line_tags: Set[str] = set()
    profile = call.get("decision_profile")
    if isinstance(profile, dict):
        rlt = profile.get("red_line_tags")
        if isinstance(rlt, list):
            red_line_tags = {t for t in rlt if isinstance(t, str)}

    _validate_primary_advice(
        c, file, path, call, turn, available, advice_tags_by_id, red_line_tags
    )
    _validate_decision_profile(c, file, path, profile)

    if raw_variants is not None:
        _validate_call_variants(
            c, file, path, raw_variants, call, faction_ids, document_ids,
            crisis_id, max_turns, global_advice_ids, per_turn_advice_ids,
            advice_tags_by_id, all_call_ids,
        )


def _validate_call_variants(
    c: _Collector, file: str, path: str, variants: Any, parent_call: Dict[str, Any],
    faction_ids: Set[str], document_ids: Set[str], crisis_id: Optional[str],
    max_turns: Optional[int], global_advice_ids: Set[str],
    per_turn_advice_ids: Dict[int, Set[str]], advice_tags_by_id: Dict[str, Set[str]],
    all_call_ids: Optional[Set[str]],
) -> None:
    vroot = f"{path}.variants"
    if not c.is_list(file, vroot, variants, "call variants"):
        return
    parent_turn = parent_call.get("turn")
    for i, variant in enumerate(variants):
        vpath = f"{vroot}[{i}]"
        if not c.is_mapping(file, vpath, variant, "call variant"):
            continue
        c.check_fields(file, vpath, variant,
                       schema.FIELD_SPECS["call_variant"], "call variant")
        vid = variant.get("id")
        if "id" in variant:
            c.check_nonempty_str(file, f"{vpath}.id", vid, "variant id")
        if isinstance(vid, str) and vid.strip() and all_call_ids is not None:
            if vid in all_call_ids:
                c.add(file, f"{vpath}.id",
                      f"duplicate call/variant id '{vid}' (call and variant "
                      "ids share one namespace so the record stays unambiguous)")
            all_call_ids.add(vid)

        conditions = variant.get("conditions")
        if isinstance(conditions, list) and not conditions:
            c.add(file, f"{vpath}.conditions",
                  "a call variant must declare at least one condition; an "
                  "unconditioned variant would always shadow the base call")
        elif conditions is not None:
            _validate_conditions(c, file, f"{vpath}.conditions", conditions,
                                 "variant condition", faction_ids)

        vcall = variant.get("call")
        if vcall is not None and c.is_mapping(file, f"{vpath}.call", vcall, "variant call"):
            _validate_call(
                c, file, f"{vpath}.call", vcall, faction_ids, document_ids,
                crisis_id, max_turns, global_advice_ids, per_turn_advice_ids,
                advice_tags_by_id, all_call_ids=None, allow_variants=False,
            )
            if parent_turn is not None and vcall.get("turn") != parent_turn:
                c.add(file, f"{vpath}.call.turn",
                      f"variant call turn {vcall.get('turn')} must equal the "
                      f"base call's turn {parent_turn}")
            if isinstance(vid, str) and vid.strip() and vcall.get("id") != vid:
                c.add(file, f"{vpath}.call.id",
                      f"variant call id '{vcall.get('id')}' must equal the "
                      f"variant id '{vid}' (one name for the thing on the record)")


def _validate_primary_advice(
    c: _Collector, file: str, path: str, call: Dict[str, Any], turn: Any,
    available: Set[str], advice_tags_by_id: Dict[str, Set[str]],
    red_line_tags: Set[str],
) -> None:
    primary = call.get("primary_advice_ids")
    if primary is None or (isinstance(primary, list) and not primary):
        c.add(file, f"{path}.primary_advice_ids",
              "client call must declare primary_advice_ids (the 3-4 on-brief options)")
        return
    if not c.is_list(file, f"{path}.primary_advice_ids", primary, "primary_advice_ids"):
        return
    lo, hi = schema.MIN_PRIMARY_ADVICE_OPTIONS, schema.MAX_PRIMARY_ADVICE_OPTIONS
    if not (lo <= len(primary) <= hi):
        c.add(file, f"{path}.primary_advice_ids",
              f"a call should present {lo}-{hi} primary advice options, got {len(primary)}")
    seen: Set[str] = set()
    for i, aid in enumerate(primary):
        if not isinstance(aid, str) or not aid.strip():
            c.add(file, f"{path}.primary_advice_ids[{i}]",
                  "primary advice entries must be non-empty advice-id strings")
            continue
        if aid in seen:
            c.add(file, f"{path}.primary_advice_ids[{i}]",
                  f"duplicate primary advice id '{aid}'")
        seen.add(aid)
        if aid not in available:
            c.add(file, f"{path}.primary_advice_ids[{i}]",
                  f"primary advice '{aid}' is not an option available on turn {turn}")
            continue
        crossed = advice_tags_by_id.get(aid, set()) & red_line_tags
        if crossed:
            c.add(file, f"{path}.primary_advice_ids[{i}]",
                  f"primary advice '{aid}' carries a red-line tag "
                  f"({', '.join(sorted(crossed))}); a red-line option cannot be on-brief")


def _validate_decision_profile(
    c: _Collector, file: str, path: str, profile: Any
) -> None:
    if profile is None:
        c.add(file, path, "client call must include a decision_profile (caller incentives)")
        return
    p = f"{path}.decision_profile"
    if not c.is_mapping(file, p, profile, "decision_profile"):
        return
    c.check_fields(file, p, profile,
                   schema.FIELD_SPECS["call_decision_profile"], "decision profile")
    if "mandate" in profile:
        c.check_nonempty_str(file, f"{p}.mandate", profile["mandate"], "mandate")
    if "off_brief_tolerance" in profile:
        c.check_int_range(file, f"{p}.off_brief_tolerance",
                          profile["off_brief_tolerance"], 0, 100)
    prio = profile.get("priorities")
    if prio is not None:
        c.check_str_list(file, f"{p}.priorities", prio, "priorities", require_nonempty=False)
        if isinstance(prio, list):
            for j, var in enumerate(prio):
                if isinstance(var, str) and var not in schema.KNOWN_VARIABLES:
                    c.add(file, f"{p}.priorities[{j}]",
                          f"unknown WorldState variable '{var}' in decision priorities")
    rlt = profile.get("red_line_tags")
    if rlt is not None:
        c.check_str_list(file, f"{p}.red_line_tags", rlt, "red_line_tags", require_nonempty=False)
        if isinstance(rlt, list):
            for j, tag in enumerate(rlt):
                if isinstance(tag, str) and tag not in schema.KNOWN_DECISION_TAGS:
                    c.add(file, f"{p}.red_line_tags[{j}]",
                          f"unknown decision tag '{tag}' in red_line_tags "
                          f"(allowed: {', '.join(sorted(schema.KNOWN_DECISION_TAGS))})")


def _validate_document(
    c: _Collector, file: str, path: str, doc: Dict[str, Any], max_turns: Optional[int]
) -> None:
    c.check_fields(file, path, doc, schema.FIELD_SPECS["document"], "document")
    for key in ("id", "title", "source"):
        if key in doc:
            c.check_nonempty_str(file, f"{path}.{key}", doc[key], key)
    if "type" in doc:
        c.check_enum(file, f"{path}.type", doc["type"], schema.DOCUMENT_TYPES, "document type")
    if "public_status" in doc:
        c.check_enum(file, f"{path}.public_status", doc["public_status"],
                     schema.PUBLIC_STATUS_VALUES, "public_status")
    if "reliability" in doc:
        c.check_enum(file, f"{path}.reliability", doc["reliability"],
                     schema.RELIABILITY_VALUES, "reliability")
    turn = doc.get("turn_number")
    if isinstance(turn, bool) or not isinstance(turn, int):
        c.add(file, f"{path}.turn_number", "document turn_number must be an integer")
    elif max_turns is not None and not (1 <= turn <= max_turns):
        c.add(file, f"{path}.turn_number",
              f"document turn_number {turn} (freshness) is outside 1..{max_turns}")
    if "tags" in doc:
        c.check_str_list(file, f"{path}.tags", doc["tags"], "tags", require_nonempty=True)


def _validate_conditions(
    c: _Collector, file: str, path: str, conditions: Any, label: str,
    faction_ids: Set[str],
) -> None:
    """Validate a list of ThreadCondition-shaped mappings.

    A condition is world-scoped by default; with ``faction_id`` set it is
    faction-scoped and ``variable`` must name an allowed faction field.
    """
    if not c.is_list(file, path, conditions, label):
        return
    for i, cond in enumerate(conditions):
        cpath = f"{path}[{i}]"
        if not c.is_mapping(file, cpath, cond, label):
            continue
        c.check_fields(file, cpath, cond,
                       schema.FIELD_SPECS["thread_condition"], label)
        variable = cond.get("variable")
        faction_id = cond.get("faction_id")
        if faction_id is not None:
            if not isinstance(faction_id, str) or faction_id not in faction_ids:
                c.add(file, f"{cpath}.faction_id",
                      f"references unknown faction '{faction_id}'")
            if variable is not None and variable not in schema.FACTION_CONDITION_FIELDS:
                c.add(file, f"{cpath}.variable",
                      f"'{variable}' is not a faction condition field "
                      f"(allowed: {', '.join(sorted(schema.FACTION_CONDITION_FIELDS))})")
        elif variable is not None and variable not in schema.KNOWN_VARIABLES:
            c.add(file, f"{cpath}.variable",
                  f"unknown WorldState variable '{variable}' in {label}")
        op = cond.get("op")
        if op is not None and op not in schema.THREAD_CONDITION_OPS:
            c.add(file, f"{cpath}.op",
                  f"{label} op must be one of "
                  f"{', '.join(sorted(schema.THREAD_CONDITION_OPS))}")
        if "threshold" in cond:
            c.check_int_range(file, f"{cpath}.threshold", cond["threshold"], 0, 100)


def _validate_thread_spec(
    c: _Collector, file: str, path: str, spec: Dict[str, Any],
    faction_ids: Set[str],
) -> None:
    c.check_fields(file, path, spec, schema.FIELD_SPECS["thread_spec"], "thread spec")
    for key in ("id", "title", "summary"):
        if key in spec:
            c.check_nonempty_str(file, f"{path}.{key}", spec[key], key)
    if "tags" in spec:
        c.check_str_list(file, f"{path}.tags", spec["tags"], "tags", require_nonempty=False)

    # --- Opening trigger: at least one criterion, every part legible ---
    trigger_keys = ("open_conditions_all", "open_conditions_any",
                    "open_advice_tags", "open_decision_types")
    if not any(spec.get(key) for key in trigger_keys):
        c.add(file, path,
              "thread spec has no opening trigger (one of "
              f"{', '.join(trigger_keys)}); it would open unconditionally on "
              "the first resolved turn")
    for key in ("open_conditions_all", "open_conditions_any"):
        if key in spec:
            _validate_conditions(c, file, f"{path}.{key}", spec[key],
                                 "open condition", faction_ids)
    for i, tag in enumerate(spec.get("open_advice_tags", []) or []):
        if not isinstance(tag, str) or tag not in schema.KNOWN_DECISION_TAGS:
            c.add(file, f"{path}.open_advice_tags[{i}]",
                  f"open advice tag '{tag}' is not a recognized decision tag "
                  f"(one of {', '.join(sorted(schema.KNOWN_DECISION_TAGS))})")
    for i, dtype in enumerate(spec.get("open_decision_types", []) or []):
        if not isinstance(dtype, str) or dtype not in schema.DECISION_TYPE_VALUES:
            c.add(file, f"{path}.open_decision_types[{i}]",
                  f"unknown decision type '{dtype}' "
                  f"(allowed: {', '.join(sorted(schema.DECISION_TYPE_VALUES))})")

    # --- Schedule carried by the thread the spec opens ---
    due_in = spec.get("due_in")
    if due_in is not None:
        if isinstance(due_in, bool) or not isinstance(due_in, int) or due_in < 1:
            c.add(file, f"{path}.due_in",
                  "thread spec due_in must be an integer >= 1 (turns until "
                  "first escalation)")
    repeat = spec.get("repeat_every")
    if repeat is not None:
        if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 0:
            c.add(file, f"{path}.repeat_every",
                  "thread spec repeat_every must be a non-negative integer")

    effects = spec.get("escalation_effects")
    if effects is not None and c.is_mapping(
        file, f"{path}.escalation_effects", effects, "escalation_effects"
    ):
        for var, delta in effects.items():
            if var not in schema.KNOWN_VARIABLES:
                c.add(file, f"{path}.escalation_effects.{var}",
                      f"unknown WorldState variable '{var}' in escalation map")
                continue
            c.check_int_range(file, f"{path}.escalation_effects.{var}", delta,
                              schema.MIN_EFFECT_DELTA, schema.MAX_EFFECT_DELTA)
        if effects and not (
            isinstance(spec.get("escalation_note"), str)
            and spec.get("escalation_note", "").strip()
        ):
            c.add(file, f"{path}.escalation_note",
                  "a thread spec with escalation_effects must carry a non-empty "
                  "escalation_note so the applied diff stays legible")

    if "resolve_conditions" in spec:
        _validate_conditions(c, file, f"{path}.resolve_conditions",
                             spec["resolve_conditions"], "resolve condition",
                             faction_ids)
    for i, rtag in enumerate(spec.get("resolve_tags", []) or []):
        if not isinstance(rtag, str) or rtag not in schema.KNOWN_DECISION_TAGS:
            c.add(file, f"{path}.resolve_tags[{i}]",
                  f"resolve tag '{rtag}' is not a recognized decision tag "
                  f"(one of {', '.join(sorted(schema.KNOWN_DECISION_TAGS))})")


def _validate_thread(
    c: _Collector, file: str, path: str, thread: Dict[str, Any],
    max_turns: Optional[int], faction_ids: Set[str],
) -> None:
    c.check_fields(file, path, thread, schema.FIELD_SPECS["thread"], "open thread")
    for key in ("id", "title", "summary"):
        if key in thread:
            c.check_nonempty_str(file, f"{path}.{key}", thread[key], key)
    turn = thread.get("turn_opened")
    if isinstance(turn, bool) or not isinstance(turn, int):
        c.add(file, f"{path}.turn_opened", "thread turn_opened must be an integer")
    elif max_turns is not None and not (1 <= turn <= max_turns):
        c.add(file, f"{path}.turn_opened",
              f"thread turn_opened {turn} is outside 1..{max_turns}")
    if "tags" in thread:
        c.check_str_list(file, f"{path}.tags", thread["tags"], "tags", require_nonempty=False)

    # --- Deterministic schedule fields ---
    for key in sorted(schema.THREAD_RUNTIME_ONLY_FIELDS & set(thread)):
        c.add(file, f"{path}.{key}",
              f"thread field '{key}' is engine-owned runtime state and must not be authored")

    due_turn = thread.get("due_turn")
    if due_turn is not None:
        if isinstance(due_turn, bool) or not isinstance(due_turn, int):
            c.add(file, f"{path}.due_turn", "thread due_turn must be an integer")
        elif max_turns is not None and not (1 <= due_turn <= max_turns):
            c.add(file, f"{path}.due_turn",
                  f"thread due_turn {due_turn} is outside 1..{max_turns}")

    effects = thread.get("escalation_effects")
    if effects is not None and c.is_mapping(
        file, f"{path}.escalation_effects", effects, "escalation_effects"
    ):
        for var, delta in effects.items():
            if var not in schema.KNOWN_VARIABLES:
                c.add(file, f"{path}.escalation_effects.{var}",
                      f"unknown WorldState variable '{var}' in escalation map")
                continue
            c.check_int_range(file, f"{path}.escalation_effects.{var}", delta,
                              schema.MIN_EFFECT_DELTA, schema.MAX_EFFECT_DELTA)
        # An escalation that moves state must say why, on the record.
        if effects and not (
            isinstance(thread.get("escalation_note"), str)
            and thread.get("escalation_note", "").strip()
        ):
            c.add(file, f"{path}.escalation_note",
                  "a thread with escalation_effects must carry a non-empty "
                  "escalation_note so the applied diff stays legible")

    repeat = thread.get("repeat_every")
    if repeat is not None:
        if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 0:
            c.add(file, f"{path}.repeat_every",
                  "thread repeat_every must be a non-negative integer")

    conditions = thread.get("resolve_conditions")
    if conditions is not None:
        _validate_conditions(c, file, f"{path}.resolve_conditions", conditions,
                             "resolve condition", faction_ids)

    resolve_tags = thread.get("resolve_tags")
    if resolve_tags is not None and c.is_list(
        file, f"{path}.resolve_tags", resolve_tags, "resolve_tags"
    ):
        for i, rtag in enumerate(resolve_tags):
            if not isinstance(rtag, str) or rtag not in schema.KNOWN_DECISION_TAGS:
                c.add(file, f"{path}.resolve_tags[{i}]",
                      f"resolve tag '{rtag}' is not a recognized decision tag "
                      f"(one of {', '.join(sorted(schema.KNOWN_DECISION_TAGS))})")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_bundle(bundle) -> None:
    """Validate a parsed content bundle. Raises ``ContentValidationError``.

    ``bundle`` is a :class:`engine.content.loader.RawContent`. This function is
    the single validation contract used by both the loader (before seeding a
    campaign) and the developer CLI / tests.
    """
    c = _Collector()
    f = bundle.files

    max_turns = _validate_scenario(c, f["scenario"], bundle.scenario)
    crisis = bundle.scenario.get("crisis") if isinstance(bundle.scenario, dict) else None
    crisis_id = crisis.get("id") if isinstance(crisis, dict) else None

    # --- factions ---
    faction_ids: Set[str] = set()
    if c.is_list(f["factions"], "", bundle.factions, "factions"):
        faction_ids = _collect_ids(c, f["factions"], bundle.factions, "faction")
        for i, faction in enumerate(bundle.factions):
            if c.is_mapping(f["factions"], f"[{i}]", faction, "faction"):
                _validate_faction(c, f["factions"], f"[{i}]", faction)

    # --- documents (needed before calls, which reference them) ---
    document_ids: Set[str] = set()
    if c.is_list(f["documents"], "", bundle.documents, "documents"):
        document_ids = _collect_ids(c, f["documents"], bundle.documents, "document")
        for i, doc in enumerate(bundle.documents):
            if c.is_mapping(f["documents"], f"[{i}]", doc, "document"):
                _validate_document(c, f["documents"], f"[{i}]", doc, max_turns)

    # --- advice (global) + per-turn advice share one id namespace ---
    advice_ids: Set[str] = set()
    global_advice_ids: Set[str] = set()
    per_turn_advice_ids: Dict[int, Set[str]] = {}
    advice_tags_by_id: Dict[str, Set[str]] = {}

    def register_advice_id(
        file: str, path: str, advice: Any, bucket: Optional[Set[str]] = None
    ) -> None:
        if isinstance(advice, dict) and isinstance(advice.get("id"), str):
            aid = advice["id"]
            if aid in advice_ids:
                c.add(file, f"{path}.id", f"duplicate advice id '{aid}'")
            advice_ids.add(aid)
            if bucket is not None:
                bucket.add(aid)
            tags = advice.get("tags")
            if isinstance(tags, list):
                advice_tags_by_id[aid] = {t for t in tags if isinstance(t, str)}

    if c.is_list(f["advice"], "", bundle.advice, "advice"):
        for i, advice in enumerate(bundle.advice):
            if c.is_mapping(f["advice"], f"[{i}]", advice, "advice option"):
                register_advice_id(f["advice"], f"[{i}]", advice, global_advice_ids)
                _validate_advice(c, f["advice"], f"[{i}]", advice, faction_ids)

    if c.is_mapping(f["per_turn_advice"], "", bundle.per_turn_advice, "per_turn_advice"):
        for turn_key, options in bundle.per_turn_advice.items():
            try:
                turn_no = int(turn_key)
            except (TypeError, ValueError):
                c.add(f["per_turn_advice"], turn_key,
                      f"per-turn advice key '{turn_key}' is not an integer turn number")
                continue
            if max_turns is not None and not (1 <= turn_no <= max_turns):
                c.add(f["per_turn_advice"], turn_key,
                      f"per-turn advice key {turn_no} is outside 1..{max_turns}")
            if not c.is_list(f["per_turn_advice"], turn_key, options, "per-turn advice list"):
                continue
            bucket = per_turn_advice_ids.setdefault(turn_no, set())
            for i, advice in enumerate(options):
                path = f"{turn_key}[{i}]"
                if c.is_mapping(f["per_turn_advice"], path, advice, "advice option"):
                    register_advice_id(f["per_turn_advice"], path, advice, bucket)
                    _validate_advice(c, f["per_turn_advice"], path, advice, faction_ids)

    # --- calls (coverage + references) ---
    if c.is_list(f["calls"], "", bundle.calls, "calls"):
        # Base call ids and variant ids share one namespace: the record must
        # never show two different calls under the same id.
        all_call_ids = _collect_ids(c, f["calls"], bundle.calls, "call")
        turns_seen: Dict[int, int] = {}
        for i, call in enumerate(bundle.calls):
            if not c.is_mapping(f["calls"], f"[{i}]", call, "client call"):
                continue
            _validate_call(c, f["calls"], f"[{i}]", call, faction_ids,
                           document_ids, crisis_id, max_turns,
                           global_advice_ids, per_turn_advice_ids,
                           advice_tags_by_id, all_call_ids=all_call_ids)
            turn = call.get("turn")
            if isinstance(turn, int) and not isinstance(turn, bool):
                if turn in turns_seen:
                    c.add(f["calls"], f"[{i}].turn",
                          f"turn {turn} already has a call at index {turns_seen[turn]}")
                else:
                    turns_seen[turn] = i
        if max_turns is not None:
            for turn in range(1, max_turns + 1):
                if turn not in turns_seen:
                    c.add(f["calls"], "", f"no client call defined for turn {turn}")

    # --- threads ---
    thread_ids: Set[str] = set()
    if c.is_list(f["threads"], "", bundle.threads, "threads"):
        thread_ids = _collect_ids(c, f["threads"], bundle.threads, "thread")
        for i, thread in enumerate(bundle.threads):
            if c.is_mapping(f["threads"], f"[{i}]", thread, "open thread"):
                _validate_thread(c, f["threads"], f"[{i}]", thread, max_turns,
                                 faction_ids)

    # --- thread specs (dynamic-thread opening rules) ---
    if c.is_list(f["thread_specs"], "", bundle.thread_specs, "thread_specs"):
        spec_ids = _collect_ids(c, f["thread_specs"], bundle.thread_specs, "thread spec")
        # A spec never re-opens an id already on the record, so a spec that
        # shares an id with a seeded thread could never fire.
        for shared in sorted(spec_ids & thread_ids):
            c.add(f["thread_specs"], "",
                  f"thread spec id '{shared}' collides with a seeded thread in "
                  "threads.json; the spec could never open")
        for i, spec in enumerate(bundle.thread_specs):
            if c.is_mapping(f["thread_specs"], f"[{i}]", spec, "thread spec"):
                _validate_thread_spec(c, f["thread_specs"], f"[{i}]", spec,
                                      faction_ids)

    if c.errors:
        raise ContentValidationError(bundle.root, c.errors)
