"""Versioned, validated scenario content layer.

Authored Northbridge content lives as domain-grouped JSON under
``engine/content/scenarios/<scenario_id>/`` and is loaded through a single
factory so engine callers do not care where the data lives:

    from engine.content import load_campaign
    campaign = load_campaign("northbridge_water_failure")

All content is validated (``engine/content/validator.py``) before a campaign is
constructed, so malformed content fails early with file/field context instead of
silently seeding wrong or missing gameplay. Run the validator standalone with::

    python -m engine.content validate

The layer imports only the standard library and the engine package, preserving
the deterministic-engine import boundary.
"""

from engine.content.loader import (
    IncompatibleSchemaVersion,
    RawContent,
    build_campaign,
    load_campaign,
    load_raw,
    scenario_metadata,
    validate_scenario,
)
from engine.content.schema import CURRENT_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS
from engine.content.validator import ContentError, ContentValidationError, validate_bundle

# The MVP scenario id. Kept here so callers import one canonical constant.
NORTHBRIDGE_SCENARIO_ID = "northbridge_water_failure"

__all__ = [
    "NORTHBRIDGE_SCENARIO_ID",
    "CURRENT_SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "RawContent",
    "ContentError",
    "ContentValidationError",
    "IncompatibleSchemaVersion",
    "load_campaign",
    "build_campaign",
    "load_raw",
    "validate_scenario",
    "validate_bundle",
    "scenario_metadata",
]
