"""Campaign API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from engine.turn import UnknownAdviceOption

from app.services import campaign_service
from app.schemas import api as schemas

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _not_found(campaign_id: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Campaign not found: {campaign_id}",
    )


@router.post(
    "",
    response_model=schemas.CampaignCreatedModel,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new Northbridge campaign",
)
def create_campaign(payload: schemas.CreateCampaignRequest | None = None):
    name = payload.name if payload and payload.name else None
    return campaign_service.create_campaign(name=name)


@router.get(
    "/{campaign_id}",
    response_model=schemas.CampaignModel,
    summary="Get a campaign summary and current world state",
)
def get_campaign(campaign_id: str):
    result = campaign_service.get_campaign(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result


@router.get(
    "/{campaign_id}/current",
    response_model=schemas.CurrentTurnModel,
    summary="Get the current turn package",
)
def get_current(campaign_id: str):
    result = campaign_service.get_current(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result


@router.post(
    "/{campaign_id}/advice",
    response_model=schemas.TurnResultModel,
    summary="Submit advice, resolve the NPC decision, and advance the turn",
)
def submit_advice(campaign_id: str, payload: schemas.AdviceRequest):
    if campaign_service.get_campaign(campaign_id) is None:
        _not_found(campaign_id)
    try:
        result = campaign_service.submit_advice(campaign_id, payload.advice_id)
    except UnknownAdviceOption as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown advice option: {exc}",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if result is None:
        _not_found(campaign_id)
    return result


@router.get(
    "/{campaign_id}/turns",
    response_model=schemas.TurnHistoryModel,
    summary="Get the full turn history and canon for a campaign",
)
def get_turns(campaign_id: str):
    result = campaign_service.get_turns(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result
