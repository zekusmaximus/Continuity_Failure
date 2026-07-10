"""Campaign service.

This is the only place the FastAPI layer touches engine + persistence. It loads
detached typed campaigns from SQLite, delegates state transitions to the
engine, then durably saves the result. No game logic lives here.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Optional

from engine import dossier as dossier_engine
from engine import seed_data, turn as turn_engine
from engine.models import Campaign
from app.ai import fallbacks
from app.ai.logging import get_run_store
from app.ai.provider import get_provider
from app.ai.runner import run_artifact
from app.ai.schemas import MemoDraft
from app.config import get_settings
from app.repository import configure_repository, get_repository
from app.schemas import api as schemas


def get_store():
    """Backward-compatible name for callers that only need the repository."""
    return get_repository()


def _require_campaign(campaign_id: str) -> Campaign:
    campaign = get_repository().get(campaign_id)
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
    """Derive diegetic infrastructure status from world state (deterministic).

    ``ai_available`` reflects whether a live model provider is actually
    configured, so the workstation indicator stays honest: when AI is off (the
    default), the memo drafter still works but returns a deterministic fallback.
    """
    settings = get_settings()
    v = campaign.world_state.variables
    power = v.get("power_stability", 50)
    staff = v.get("staff_capacity", 50)
    info = v.get("information_integrity", 50)
    # Data freshness degrades as staff/information capacity drops -- a strained
    # operations floor stops keeping feeds current. Kept as a simple blend.
    data_freshness = (info + staff) // 2
    comms = min(power, info + 10)
    # AI assist is present and reachable; it is "available" only when a live
    # provider is configured. Otherwise the layer stays dormant and the memo
    # drafter returns a deterministic fallback.
    ai_live = settings.ai_live
    provider = get_provider(settings) if ai_live else None
    model_status = (
        f"Live AI assist active ({getattr(provider, 'name', 'unknown')} provider)"
        if ai_live and provider is not None
        else "AI assist present — off by default (returns system drafts)"
    )
    return schemas.SystemStatusModel(
        power=power,
        comms=comms,
        data_freshness=data_freshness,
        staff_capacity=staff,
        ai_available=ai_live,
        model_status=model_status,
    )


def create_campaign(name: Optional[str] = None) -> schemas.CampaignCreatedModel:
    campaign = seed_data.create_northbridge_campaign(name=name or "")
    get_repository().put(campaign)
    return schemas.CampaignCreatedModel(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        turn_number=campaign.turn_number,
        max_turns=campaign.max_turns,
    )


def get_campaign(campaign_id: str) -> Optional[schemas.CampaignModel]:
    campaign = get_repository().get(campaign_id)
    if campaign is None:
        return None
    return schemas.CampaignModel(
        summary=_summary(campaign),
        world_state=_world_state(campaign),
    )


def list_recent_campaigns(limit: int = 5) -> list[schemas.RecentCampaignModel]:
    """Return only resume-screen metadata, never campaign/model payloads."""
    return [
        schemas.RecentCampaignModel.model_validate(row)
        for row in get_repository().list_recent(limit=limit)
    ]


def get_current(campaign_id: str) -> Optional[schemas.CurrentTurnModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None

    call = campaign.current_call()
    client_call = schemas.ClientCallModel.model_validate(asdict(call)) if call else None
    advice_options = [
        schemas.AdviceOptionModel.model_validate(asdict(o))
        for o in campaign.available_advice()
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
    # Save the authoritative document and immutable end-of-turn snapshot in
    # one SQLite transaction.
    get_repository().put(campaign, snapshot_turn=result.turn_number)
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


def draft_memo(
    campaign_id: str, advice_id: str
) -> Optional[schemas.MemoDraftModel]:
    """Draft a consultant memo for a selected advice option.

    This is **advisory only** — it reads campaign state and produces prose; it
    never calls ``advance_turn`` or mutates ``WorldState``. With AI disabled (the
    default), the runner returns a deterministic fallback memo. Raises
    ``UnknownAdviceOption`` if the advice id isn't available this turn.
    """
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None

    option = next(
        (o for o in campaign.available_advice() if o.id == advice_id), None
    )
    if option is None:
        raise turn_engine.UnknownAdviceOption(advice_id)

    payload = fallbacks.build_memo_input(
        option,
        campaign.current_call(),
        campaign.world_state.factions,
    )
    artifact = run_artifact(
        prompt_name="memo_drafter",
        prompt_version="v1",
        input_payload=payload,
        schema=MemoDraft,
        fallback=fallbacks.memo_fallback,
        input_summary=f"turn {campaign.turn_number}: {option.label}",
        campaign_id=campaign.id,
        turn_number=campaign.turn_number,
    )
    return schemas.MemoDraftModel(
        status=artifact.status,
        source="ai" if artifact.from_model else "system",
        draft=schemas.MemoContentModel(**artifact.content.model_dump()),
    )


def get_model_runs(campaign_id: str) -> Optional[list[schemas.ModelRunModel]]:
    """Read-only log of AI model runs recorded for this campaign."""
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    return [
        schemas.ModelRunModel(
            prompt_name=r.prompt_name,
            prompt_version=r.prompt_version,
            model_name=r.model_name,
            validation_status=r.validation_status,
            input_summary=r.input_summary,
            retry_count=r.retry_count,
            latency_ms=r.latency_ms,
            turn_number=r.turn_number,
        )
        for r in get_run_store().for_campaign(campaign_id)
    ]


def _require_campaign_or_none(campaign_id: str) -> Optional[Campaign]:
    return get_repository().get(campaign_id)
