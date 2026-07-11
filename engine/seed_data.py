"""Northbridge Water Failure seed scenario (compatibility facade).

The authored Northbridge content -- starting state, factions, advice, calls,
documents, threads, and crisis -- now lives as versioned, validated JSON under
``engine/content/scenarios/northbridge_water_failure/`` and is constructed by
``engine.content``. This module preserves the historical public surface
(``create_northbridge_campaign``, ``SCENARIO_ID``, ``MAX_TURNS``,
``STARTING_VARIABLES``) so existing engine and backend callers are unchanged.

Content describes inputs; the engine rules (``engine/rules.py``, ``engine/turn.py``)
decide outcomes. Nothing here is generated -- it is hand-authored canon, now
validated before a campaign can start.
"""

from __future__ import annotations

from typing import Dict

from engine.content import NORTHBRIDGE_SCENARIO_ID, load_campaign, scenario_metadata
from engine.models import Campaign

SCENARIO_ID = NORTHBRIDGE_SCENARIO_ID

# Scenario metadata is validated on first access; a typo in content therefore
# surfaces here rather than silently seeding a broken campaign.
_META = scenario_metadata(SCENARIO_ID)
MAX_TURNS: int = _META["max_turns"]
STARTING_VARIABLES: Dict[str, int] = dict(_META["starting_variables"])


def create_northbridge_campaign(
    campaign_id: str = "", name: str = "", variant_id: str = ""
) -> Campaign:
    """Construct a fresh, validated Northbridge campaign.

    Delegates to the content factory, which validates the complete scenario
    before any authoritative state is created. ``variant_id`` selects an
    authored starting-state perturbation ("" = baseline).
    """
    return load_campaign(
        SCENARIO_ID, campaign_id=campaign_id, name=name, variant_id=variant_id
    )
