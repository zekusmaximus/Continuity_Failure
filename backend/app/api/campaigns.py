"""Campaign API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from engine.turn import UnknownAdviceOption

from app.observability import bind_log_fields, get_request_id
from app.services import campaign_service
from app.services import errors
from app.schemas import api as schemas

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

# Read-only scenario metadata (seed variants for the intake screen).
scenarios_router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@scenarios_router.get(
    "/{scenario_id}/variants",
    summary="List the authored seed variants for a scenario",
)
def list_scenario_variants(
    scenario_id: str = Path(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$"),
) -> list[schemas.ScenarioVariantModel]:
    try:
        return campaign_service.list_scenario_variants(scenario_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error_body(
                "scenario_not_found", f"Scenario not found: {scenario_id}"
            ),
        )


def _error_body(
    code: str,
    message: str,
    *,
    campaign_id: Optional[str] = None,
    expected_turn: Optional[int] = None,
    current_turn: Optional[int] = None,
) -> dict:
    """Build the one error shape every route returns. Never leaks internals."""
    return schemas.ApiErrorDetail(
        error=code,
        message=message,
        request_id=get_request_id(),
        campaign_id=campaign_id,
        expected_turn=expected_turn,
        current_turn=current_turn,
    ).model_dump()


def _not_found(campaign_id: str):
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_error_body(
            "campaign_not_found",
            f"Campaign not found: {campaign_id}",
            campaign_id=campaign_id,
        ),
    )


def _turn_error(campaign_id: str, exc: errors.TurnResolutionError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail=_error_body(
            exc.code,
            exc.message,
            campaign_id=campaign_id,
            expected_turn=getattr(exc, "expected_turn", None),
            current_turn=getattr(exc, "current_turn", None),
        ),
    )


@router.post(
    "",
    response_model=schemas.CampaignCreatedModel,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new Northbridge campaign",
)
def create_campaign(payload: schemas.CreateCampaignRequest | None = None):
    name = payload.name if payload and payload.name else None
    variant = payload.variant if payload and payload.variant else None
    try:
        return campaign_service.create_campaign(name=name, variant=variant)
    except errors.TurnResolutionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=_error_body(exc.code, exc.message),
        )


@router.get(
    "",
    response_model=list[schemas.RecentCampaignModel],
    summary="List recent campaigns for the resume screen",
)
def list_recent_campaigns(limit: int = Query(default=5, ge=1, le=20)):
    return campaign_service.list_recent_campaigns(limit=limit)


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
    responses={
        400: {"model": schemas.ApiErrorModel},
        404: {"model": schemas.ApiErrorModel},
        409: {"model": schemas.ApiErrorModel},
    },
    summary="Submit advice, resolve the NPC decision, and advance the turn",
)
def submit_advice(
    campaign_id: str,
    payload: schemas.AdviceSubmissionRequest,
    response: Response,
):
    """Resolve exactly one turn, atomically and at most once per key.

    * same key + same payload → the original response, no turn advanced
      (``Idempotent-Replay: true``);
    * same key + different payload → 409 ``idempotency_key_conflict``;
    * ``expected_turn`` behind the campaign → 409 ``stale_turn``;
    * terminal campaign → 409 ``campaign_terminal``.
    """
    bind_log_fields(campaign_id=campaign_id, expected_turn=payload.expected_turn)
    try:
        resolved = campaign_service.submit_advice(
            campaign_id,
            payload.advice_id,
            expected_turn=payload.expected_turn,
            idempotency_key=payload.idempotency_key,
            memo_id=payload.memo_id,
            memo_revision=payload.memo_revision,
            cited_document_ids=payload.cited_document_ids,
        )
    except errors.TurnResolutionError as exc:
        raise _turn_error(campaign_id, exc) from None
    response.headers["Idempotent-Replay"] = "true" if resolved.replayed else "false"
    return resolved.result


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


@router.get(
    "/{campaign_id}/presentation",
    response_model=schemas.TurnPresentationModel | None,
    summary="Get the resolved turn awaiting explicit Next Call acknowledgement",
)
def get_turn_presentation(campaign_id: str):
    bind_log_fields(campaign_id=campaign_id)
    try:
        return campaign_service.get_pending_presentation(campaign_id)
    except errors.TurnResolutionError as exc:
        raise _turn_error(campaign_id, exc) from None


@router.post(
    "/{campaign_id}/presentation/acknowledge",
    response_model=schemas.PresentationAcknowledgedModel,
    responses={404: {"model": schemas.ApiErrorModel}, 409: {"model": schemas.ApiErrorModel}},
    summary="Acknowledge a resolved turn before loading the next call",
)
def acknowledge_turn_presentation(
    campaign_id: str, payload: schemas.AcknowledgePresentationRequest
):
    bind_log_fields(campaign_id=campaign_id, turn_number=payload.turn_number)
    try:
        return campaign_service.acknowledge_presentation(
            campaign_id, payload.turn_number
        )
    except errors.TurnResolutionError as exc:
        raise _turn_error(campaign_id, exc) from None


@router.get(
    "/{campaign_id}/memos",
    response_model=list[schemas.AdviceMemoModel],
    summary="List persistent advice memos for a campaign",
)
def list_memos(campaign_id: str):
    result = campaign_service.list_memos(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result


@router.post(
    "/{campaign_id}/memos",
    response_model=schemas.AdviceMemoModel,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": schemas.ApiErrorModel}, 404: {"model": schemas.ApiErrorModel}},
    summary="Create a manual or AI-assisted memo draft",
)
def create_memo(campaign_id: str, payload: schemas.CreateMemoRequest):
    bind_log_fields(campaign_id=campaign_id)
    try:
        return campaign_service.create_memo(
            campaign_id,
            creation_mode=payload.creation_mode,
            advice_id=payload.advice_id,
            name=payload.name,
            content=payload.content,
        )
    except errors.TurnResolutionError as exc:
        raise _turn_error(campaign_id, exc) from None


@router.patch(
    "/{campaign_id}/memos/{memo_id}",
    response_model=schemas.AdviceMemoModel,
    responses={404: {"model": schemas.ApiErrorModel}, 409: {"model": schemas.ApiErrorModel}},
    summary="Save a new player-authored memo revision",
)
def update_memo(
    campaign_id: str,
    payload: schemas.UpdateMemoRequest,
    memo_id: str = Path(pattern=schemas.MEMO_ID_PATTERN),
):
    bind_log_fields(campaign_id=campaign_id)
    try:
        return campaign_service.update_memo(
            campaign_id,
            memo_id,
            expected_revision=payload.expected_revision,
            name=payload.name,
            content=payload.content,
        )
    except errors.TurnResolutionError as exc:
        raise _turn_error(campaign_id, exc) from None


@router.get(
    "/{campaign_id}/dossier",
    response_model=schemas.DossierModel,
    summary="Get the campaign dossier as Markdown",
)
def get_dossier(campaign_id: str):
    result = campaign_service.get_dossier(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result


@router.post(
    "/{campaign_id}/memo",
    response_model=schemas.MemoDraftModel,
    summary="Draft a consultant memo for an advice option (advisory only)",
)
def draft_memo(campaign_id: str, payload: schemas.AdviceRequest):
    """Advisory only: drafts a memo without advancing the turn or changing state.

    With AI disabled (the default) this returns a deterministic fallback memo.
    """
    bind_log_fields(campaign_id=campaign_id)
    if campaign_service.get_campaign(campaign_id) is None:
        _not_found(campaign_id)
    try:
        result = campaign_service.draft_memo(campaign_id, payload.advice_id)
    except UnknownAdviceOption as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error_body(
                "unknown_advice_option",
                f"Unknown advice option: {exc}",
                campaign_id=campaign_id,
            ),
        ) from None
    if result is None:
        _not_found(campaign_id)
    return result


@router.get(
    "/{campaign_id}/model-runs",
    response_model=list[schemas.ModelRunModel],
    summary="Read-only log of AI model runs for this campaign",
)
def get_model_runs(campaign_id: str):
    result = campaign_service.get_model_runs(campaign_id)
    if result is None:
        _not_found(campaign_id)
    return result
