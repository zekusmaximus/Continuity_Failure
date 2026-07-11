"""Content loader / campaign factory.

Reads the versioned JSON content for a scenario, validates it, and constructs
the deterministic engine dataclasses. Engine callers use the single factory
``load_campaign`` (re-exported by ``engine.content`` and by the backward-compatible
``engine.seed_data``) and never touch file paths or JSON directly.

Import boundary: this module uses only the standard library plus the engine
package, so ``engine`` stays framework-free.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from engine import rules
from engine.content import schema
from engine.content.validator import (
    ContentError,
    ContentValidationError,
    validate_bundle,
)
from engine.models import (
    AdviceOption,
    CallDecisionProfile,
    Campaign,
    CampaignStatus,
    ClientCall,
    Crisis,
    Document,
    Faction,
    OpenThread,
    ThreadCondition,
    ThreadSpec,
    WorldState,
)

_CONTENT_ROOT = os.path.join(os.path.dirname(__file__), "scenarios")

# The domain -> filename layout. One coherent file per authored domain.
_FILES: Dict[str, str] = {
    "scenario": "scenario.json",
    "factions": "factions.json",
    "advice": "advice.json",
    "per_turn_advice": "per_turn_advice.json",
    "calls": "calls.json",
    "documents": "documents.json",
    "threads": "threads.json",
    "thread_specs": "thread_specs.json",
}


class IncompatibleSchemaVersion(Exception):
    """Raised when content declares a schema version the loader cannot read."""


@dataclass
class RawContent:
    """A parsed-but-unvalidated content bundle for one scenario."""

    root: str                       # scenario id (used in messages)
    files: Dict[str, str]           # domain -> relative filename (for error anchoring)
    scenario: Any = None
    factions: Any = field(default_factory=list)
    advice: Any = field(default_factory=list)
    per_turn_advice: Any = field(default_factory=dict)
    calls: Any = field(default_factory=list)
    documents: Any = field(default_factory=list)
    threads: Any = field(default_factory=list)
    thread_specs: Any = field(default_factory=list)


# ---------------------------------------------------------------------------
# Schema migrations. A migration maps a bundle authored at version N to the
# shape version N+1 expects. The chain is applied in order until the bundle is
# at CURRENT_SCHEMA_VERSION. There are no migrations yet (only v1 exists); the
# registry documents the mechanism and gives a clean home for the first one.
# ---------------------------------------------------------------------------

MIGRATIONS: Dict[int, Callable[[RawContent], RawContent]] = {}


def _scenario_dir(scenario_id: str) -> str:
    return os.path.join(_CONTENT_ROOT, scenario_id)


def _read_json(path: str, rel: str, scenario_id: str) -> Any:
    if not os.path.exists(path):
        raise ContentValidationError(
            scenario_id, [ContentError(rel, "", "content file is missing")]
        )
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ContentValidationError(
            scenario_id,
            [ContentError(rel, f"line {exc.lineno}", f"invalid JSON: {exc.msg}")],
        ) from exc


def load_raw(scenario_id: str) -> RawContent:
    """Read and JSON-parse every content file for ``scenario_id``."""
    scenario_dir = _scenario_dir(scenario_id)
    if not os.path.isdir(scenario_dir):
        raise ContentValidationError(
            scenario_id,
            [ContentError(scenario_id, "", "scenario content directory not found")],
        )
    parsed: Dict[str, Any] = {}
    for domain, filename in _FILES.items():
        parsed[domain] = _read_json(
            os.path.join(scenario_dir, filename), filename, scenario_id
        )
    return RawContent(root=scenario_id, files=dict(_FILES), **parsed)


def _apply_schema_version(bundle: RawContent) -> RawContent:
    """Gate and, if needed, migrate the bundle to the current schema version."""
    scenario = bundle.scenario
    version = scenario.get("schema_version") if isinstance(scenario, dict) else None
    if not isinstance(version, int) or isinstance(version, bool):
        # A malformed/absent version is a validation error, surfaced with full
        # field context by the validator rather than here.
        return bundle
    if version in schema.SUPPORTED_SCHEMA_VERSIONS:
        return bundle

    # Try to migrate an older version forward.
    migrated = bundle
    current = version
    while current < schema.CURRENT_SCHEMA_VERSION and current in MIGRATIONS:
        migrated = MIGRATIONS[current](migrated)
        current += 1
    if current in schema.SUPPORTED_SCHEMA_VERSIONS:
        return migrated

    raise IncompatibleSchemaVersion(
        f"scenario '{bundle.root}' declares schema_version {version}, but this "
        f"build supports {sorted(schema.SUPPORTED_SCHEMA_VERSIONS)} and has no "
        f"migration path from {version}. Update the content or add a migration "
        f"in engine/content/loader.py."
    )


def validate_scenario(scenario_id: str) -> None:
    """Load and validate a scenario's content without building a campaign.

    Raises ``ContentValidationError`` or ``IncompatibleSchemaVersion`` on any
    problem. Used by tests and the developer CLI.
    """
    bundle = load_raw(scenario_id)
    bundle = _apply_schema_version(bundle)
    validate_bundle(bundle)


# ---------------------------------------------------------------------------
# Dataclass construction (only reached after validation passes)
# ---------------------------------------------------------------------------

def _build_factions(raw: List[dict]) -> List[Faction]:
    return [Faction(**f) for f in raw]


def _build_advice(raw: List[dict]) -> List[AdviceOption]:
    return [AdviceOption(**a) for a in raw]


def _build_per_turn_advice(raw: Dict[str, list]) -> Dict[int, List[AdviceOption]]:
    return {int(turn): _build_advice(options) for turn, options in raw.items()}


def _build_calls(raw: List[dict]) -> Dict[int, ClientCall]:
    calls = []
    for c in raw:
        data = dict(c)
        profile = data.get("decision_profile")
        if isinstance(profile, dict):
            data["decision_profile"] = CallDecisionProfile(**profile)
        calls.append(ClientCall(**data))
    return {call.turn: call for call in calls}


def _build_documents(raw: List[dict]) -> List[Document]:
    return [Document(**d) for d in raw]


def _build_threads(raw: List[dict]) -> List[OpenThread]:
    threads = []
    for t in raw:
        data = dict(t)
        conditions = data.get("resolve_conditions")
        if isinstance(conditions, list):
            data["resolve_conditions"] = [
                ThreadCondition(**cond) for cond in conditions
            ]
        threads.append(OpenThread(**data))
    return threads


def _build_thread_specs(raw: List[dict]) -> List[ThreadSpec]:
    specs = []
    for s in raw:
        data = dict(s)
        for key in ("open_conditions_all", "open_conditions_any", "resolve_conditions"):
            conditions = data.get(key)
            if isinstance(conditions, list):
                data[key] = [ThreadCondition(**cond) for cond in conditions]
        specs.append(ThreadSpec(**data))
    return specs


def _last_verified(turn: int) -> str:
    return f"Turn {turn} · Operational snapshot (deterministic)"


def build_campaign(bundle: RawContent, campaign_id: str = "", name: str = "") -> Campaign:
    """Construct a campaign from an already-loaded bundle (validates first)."""
    bundle = _apply_schema_version(bundle)
    validate_bundle(bundle)

    scenario = bundle.scenario
    campaign_id = campaign_id or uuid.uuid4().hex[:8]
    name = name or scenario["name"]

    crisis_raw = scenario["crisis"]
    world_state = WorldState(
        turn_number=1,
        variables=dict(scenario["starting_variables"]),
        factions=_build_factions(bundle.factions),
        active_crisis=Crisis(**crisis_raw),
        last_verified=_last_verified(1),
    )
    return Campaign(
        id=campaign_id,
        name=name,
        scenario_id=scenario["scenario_id"],
        status=CampaignStatus.ACTIVE,
        turn_number=1,
        max_turns=scenario["max_turns"],
        world_state=world_state,
        advice_options=_build_advice(bundle.advice),
        per_turn_advice=_build_per_turn_advice(bundle.per_turn_advice),
        client_calls=_build_calls(bundle.calls),
        documents=_build_documents(bundle.documents),
        open_threads=_build_threads(bundle.threads),
        thread_specs=_build_thread_specs(bundle.thread_specs),
        created_at=datetime.now(timezone.utc).isoformat(),
        ruleset_version=rules.CURRENT_RULESET_VERSION,
    )


def load_campaign(
    scenario_id: str, campaign_id: str = "", name: str = ""
) -> Campaign:
    """The single content factory: validate ``scenario_id`` and build a campaign.

    Malformed content raises before any authoritative state is created, so a
    campaign is never partially seeded from invalid content.
    """
    bundle = load_raw(scenario_id)
    return build_campaign(bundle, campaign_id=campaign_id, name=name)


def scenario_metadata(scenario_id: str) -> Dict[str, Any]:
    """Return validated scenario metadata (id, name, max_turns, ...)."""
    bundle = load_raw(scenario_id)
    bundle = _apply_schema_version(bundle)
    validate_bundle(bundle)
    return dict(bundle.scenario)
