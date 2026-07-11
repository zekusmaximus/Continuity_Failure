"""Deterministic client-call resolution: the base call or an authored variant.

A turn's call slot may carry authored ``CallVariant`` entries (branchable /
faction-gated calls). Selection is a pure read of the campaign state: the
first variant in authored order whose conditions ALL hold replaces the base
call entirely, so everything downstream -- presentation, the caller's
decision profile, red lines, primary options, the NPC decision seam -- sees
one coherent call with no duplicated logic.

World state only mutates inside ``advance_turn``, so a selection made when the
call is presented and a selection made when the turn resolves always agree --
PROVIDED the turn resolver selects once at entry, before applying any diffs,
and passes the resolved call down (mid-turn re-selection against half-mutated
state could flip the variant; ``engine/turn.py`` is written to make that
impossible).
"""

from __future__ import annotations

from typing import Optional, Tuple

from engine import conditions
from engine.models import Campaign, ClientCall


def resolve_call_with_variant(
    campaign: Campaign, turn: int
) -> Tuple[Optional[ClientCall], Optional[str]]:
    """The call on the line for ``turn``, plus the variant id when one fired.

    Returns ``(base_call, None)`` when no variant's conditions hold, and
    ``(None, None)`` when the turn has no call at all. Deterministic:
    authored order is the tiebreak, first full match wins.
    """
    base = campaign.client_calls.get(turn)
    if base is None:
        return None, None
    variants = campaign.call_variants.get(turn, [])
    if not variants:
        return base, None
    variables = campaign.world_state.variables
    factions_by_id = {f.id: f for f in campaign.world_state.factions}
    for variant in variants:
        # The validator requires at least one condition; the guard keeps an
        # unconditioned variant from shadowing the base call regardless.
        if variant.conditions and conditions.all_hold(
            variant.conditions, variables, factions_by_id
        ):
            return variant.call, variant.id
    return base, None


def resolve_call(campaign: Campaign, turn: int) -> Optional[ClientCall]:
    """The call on the line for ``turn`` (variant-aware)."""
    return resolve_call_with_variant(campaign, turn)[0]
