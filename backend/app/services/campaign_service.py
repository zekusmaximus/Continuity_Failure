"""Campaign service.

This is the only place the FastAPI layer touches engine + memory. It owns the
in-memory campaign store and converts engine dataclasses into Pydantic API
models. No game logic lives here -- all state transitions delegate to the
engine so the deterministic core stays framework-free.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from engine import dossier as dossier_engine
from engine import seed_data, turn as turn_engine
from engine.models import Campaign
from memory.persistence import CampaignStore

from app.schemas import api as schemas


# Module-level in-memory store. Reset on process restart, which is acceptable
# for the skeleton slice (see AGENTS.md: "over-engineer persistence" avoided).
_STORE = CampaignStore()


def get_store() -> CampaignStore:
    return _STORE


def _require_campaign(campaign_id: str) -> Campaign:
    campaign = _STORE.get(campaign_id)
    if campaign is None:
        raise KeyError(campaign_id)
    return campaign


def _summary(campaign: Campaign) -> schemas.CampaignSummaryModel:
    return schemas.CampaignSummaryModel(
        id=campaign.id,
        name=campaign.name,
        scenario_id=campaign.scenario_id,
        status=campaign.status,
        turn_number=campaign.turn_number,
        max_turns=campaign.max_turns,
        failure_reason=campaign.failure_reason,
        created_at=campaign.created_at,
    )


def _world_state(campaign: Campaign) -> schemas.WorldStateModel:
    return schemas.WorldStateModel.model_validate(asdict(campaign.world_state))


def _documents(campaign: Campaign) -> list[schemas.DocumentModel]:
    return [
        schemas.DocumentModel.model_validate(asdict(d))
        for d in campaign.available_documents()
    ]


def _open_threads(campaign: Campaign) -> list[schemas.OpenThreadModel]:
    return [
        schemas.OpenThreadModel.model_validate(asdict(t))
        for t in campaign.open_threads
    ]


def _system_status(campaign: Campaign) -> schemas.SystemStatusModel:
    """Derive diegetic infrastructure status from world state (deterministic)."""
    v = campaign.world_state.variables
    power = v.get("power_stability", 50)
    staff = v.get("staff_capacity", 50)
    info = v.get("information_integrity", 50)
    # Data freshness degrades as staff/information capacity drops -- a strained
    # operations floor stops keeping feeds current. Kept as a simple blend.
    data_freshness = (info + staff) // 2
    comms = min(power, info + 10)
    return schemas.SystemStatusModel(
        power=power,
        comms=comms,
        data_freshness=data_freshness,
        staff_capacity=staff,
        ai_available=False,
        model_status="AI systems unavailable in current build",
    )


def create_campaign(name: Optional[str] = None) -> schemas.CampaignCreatedModel:
    campaign = seed_data.create_northbridge_campaign(name=name or "")
    _STORE.put(campaign)
    return schemas.CampaignCreatedModel(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        turn_number=campaign.turn_number,
        max_turns=campaign.max_turns,
    )


def get_campaign(campaign_id: str) -> Optional[schemas.CampaignModel]:
    campaign = _STORE.get(campaign_id)
    if campaign is None:
        return None
    return schemas.CampaignModel(
        summary=_summary(campaign),
        world_state=_world_state(campaign),
    )


def get_current(campaign_id: str) -> Optional[schemas.CurrentTurnModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None

    call = campaign.current_call()
    client_call = schemas.ClientCallModel.model_validate(asdict(call)) if call else None
    advice_options = [
        schemas.AdviceOptionModel.model_validate(asdict(o)) for o in campaign.advice_options
    ]
    last_turn = None
    if campaign.turn_history:
        last_turn = schemas.TurnResultModel.model_validate(
            asdict(campaign.turn_history[-1])
        )

    return schemas.CurrentTurnModel(
        summary=_summary(campaign),
        world_state=_world_state(campaign),
        client_call=client_call,
        advice_options=advice_options,
        documents=_documents(campaign),
        open_threads=_open_threads(campaign),
        system_status=_system_status(campaign),
        last_turn=last_turn,
    )


def submit_advice(
    campaign_id: str, advice_id: str
) -> Optional[schemas.TurnResultModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None

    result = turn_engine.advance_turn(campaign, advice_id)
    # The campaign object is mutated in place and already referenced by the
    # store, so no explicit re-put is required.
    return schemas.TurnResultModel.model_validate(asdict(result))


def get_turns(campaign_id: str) -> Optional[schemas.TurnHistoryModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    turns = [
        schemas.TurnResultModel.model_validate(asdict(t)) for t in campaign.turn_history
    ]
    canon = [
        schemas.CanonEntryModel.model_validate(asdict(c)) for c in campaign.canon
    ]
    return schemas.TurnHistoryModel(
        summary=_summary(campaign),
        turns=turns,
        canon=canon,
        open_threads=_open_threads(campaign),
    )


def get_dossier(campaign_id: str) -> Optional[schemas.DossierModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    return schemas.DossierModel(
        campaign_id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        filename=dossier_engine.dossier_filename(campaign),
        markdown=dossier_engine.render_dossier_markdown(campaign),
    )


def _require_campaign_or_none(campaign_id: str) -> Optional[Campaign]:
    return _STORE.get(campaign_id)
