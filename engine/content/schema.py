"""Content schema: version, controlled vocabularies, and entity field specs.

This module is the single source of truth for *what valid Northbridge content
looks like*. It deliberately imports only from the engine package (models,
state, rules) so the deterministic-engine import boundary is preserved
(``tests/test_engine_turns.py::test_engine_imports_only_stdlib_and_itself``).

Field sets are derived from the engine dataclasses via ``dataclasses.fields`` so
the content contract cannot silently drift from the runtime objects the loader
constructs. Enum vocabularies for urgency / public-status / reliability are read
off the model constant classes for the same reason; the coarser type
vocabularies (faction / advice / document / crisis type) are the authored lists
from ``docs/state-schema.md``.
"""

from __future__ import annotations

from dataclasses import MISSING, fields
from typing import Dict, Set

from engine import rules
from engine.models import (
    AdviceOption,
    ClientCall,
    Crisis,
    Document,
    Faction,
    OpenThread,
    PublicStatus,
    Reliability,
    Urgency,
)
from engine.state import STATE_VARIABLE_LABELS

# ---------------------------------------------------------------------------
# Schema version. Bump ``CURRENT_SCHEMA_VERSION`` only alongside a migration in
# ``engine/content/loader.py`` (see MIGRATIONS) or an intentional break.
# ``SUPPORTED_SCHEMA_VERSIONS`` is every version the loader can read directly.
# ---------------------------------------------------------------------------

CURRENT_SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS: Set[int] = {1}


# ---------------------------------------------------------------------------
# Known WorldState variables. The engine's label map is the canonical set.
# ---------------------------------------------------------------------------

KNOWN_VARIABLES: Set[str] = set(STATE_VARIABLE_LABELS)

# Deltas are bounded so a fat-fingered effect (e.g. 500 instead of 5) is caught.
MIN_EFFECT_DELTA = -100
MAX_EFFECT_DELTA = 100


def _string_values(cls) -> Set[str]:
    return {
        v
        for k, v in vars(cls).items()
        if not k.startswith("_") and isinstance(v, str)
    }


URGENCY_VALUES: Set[str] = _string_values(Urgency)
PUBLIC_STATUS_VALUES: Set[str] = _string_values(PublicStatus)
RELIABILITY_VALUES: Set[str] = _string_values(Reliability)

# Coarser controlled vocabularies (authored in docs/state-schema.md).
FACTION_ALIGNMENTS: Set[str] = {"authority", "opposition", "neutral", "service"}

FACTION_TYPES: Set[str] = {
    "EXECUTIVE", "LEGISLATIVE", "AGENCY", "UTILITY", "HOSPITAL", "SCHOOL",
    "BUSINESS", "RESIDENT_GROUP", "MEDIA", "CONTRACTOR", "STATE_ACTOR",
    "LEGAL_ACTOR", "PUBLIC_SAFETY", "LABOR", "ACTIVIST",
}

ADVICE_TYPES: Set[str] = {
    "FULL_DISCLOSURE", "CONTROLLED_DISCLOSURE", "DELAY", "EMERGENCY_ORDER",
    "RESOURCE_TRIAGE", "STATE_AID_REQUEST", "MUTUAL_AID", "PROCUREMENT_STRATEGY",
    "CONTRACTOR_PRESSURE", "PUBLIC_STATEMENT", "NEGOTIATION_PLAN", "LEGAL_MEMO",
    "INDEPENDENT_REVIEW", "BACKCHANNEL",
    # As-built per-turn advice types (see engine content).
    "SCHOOL_CLOSURE_PROTOCOL", "HOSPITAL_PRIORITY", "BUSINESS_COMPENSATION",
}

DOCUMENT_TYPES: Set[str] = {
    "LAB_REPORT", "EMAIL", "MEMO", "INVOICE", "CONTRACT", "MEETING_MINUTES",
    "PRESS_RELEASE", "NEWS_ARTICLE", "SOCIAL_MEDIA_THREAD", "LEGAL_NOTICE",
    "COURT_FILING", "AGENCY_LETTER", "EMERGENCY_ORDER", "CALL_TRANSCRIPT",
    "PUBLIC_FAQ", "AFTER_ACTION_REPORT",
}

CRISIS_TYPES: Set[str] = {
    "WATER_FAILURE", "POWER_FAILURE", "PUBLIC_HEALTH", "BUDGET", "PROCUREMENT",
    "LEGAL", "MEDIA_RUMOR", "SCHOOL", "HOSPITAL", "PUBLIC_ORDER",
    "STATE_OVERSIGHT", "CONTRACTOR",
}

# Advice tags the deterministic rules know how to resolve. An advice option
# whose tags contain none of these would silently fall through to the generic
# partial handler -- a typo that changes gameplay -- so the validator requires
# at least one recognized decision tag per option.
KNOWN_DECISION_TAGS: Set[str] = set(rules._ADVICE_TAG_DISPATCH)

# Variables the deterministic rules read as failure thresholds or drift each
# turn. The authored starting state must cover every one of them.
THRESHOLD_VARIABLES: Set[str] = {var for var, _op, _th in rules.FAILURE_THRESHOLDS}
AMBIENT_VARIABLES: Set[str] = set(rules.AMBIENT_DRIFT)


# ---------------------------------------------------------------------------
# Entity field specs, derived from the dataclasses the loader reconstructs.
# ---------------------------------------------------------------------------

class FieldSpec:
    """Allowed and required JSON keys for one engine dataclass."""

    __slots__ = ("cls", "allowed", "required")

    def __init__(self, cls) -> None:
        self.cls = cls
        self.allowed: Set[str] = {f.name for f in fields(cls)}
        self.required: Set[str] = {
            f.name
            for f in fields(cls)
            if f.default is MISSING and f.default_factory is MISSING  # type: ignore[misc]
        }


FIELD_SPECS: Dict[str, FieldSpec] = {
    "faction": FieldSpec(Faction),
    "advice": FieldSpec(AdviceOption),
    "call": FieldSpec(ClientCall),
    "document": FieldSpec(Document),
    "thread": FieldSpec(OpenThread),
    "crisis": FieldSpec(Crisis),
}

# Scenario metadata is not a dataclass; its contract is spelled out directly.
SCENARIO_REQUIRED_KEYS: Set[str] = {
    "schema_version", "scenario_id", "name", "max_turns",
    "starting_variables", "crisis",
}
SCENARIO_ALLOWED_KEYS: Set[str] = SCENARIO_REQUIRED_KEYS | {"description"}
