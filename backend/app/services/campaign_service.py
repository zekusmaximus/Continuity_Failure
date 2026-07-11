"""Campaign service.

This is the only place the FastAPI layer touches engine + persistence. It loads
detached typed campaigns from SQLite, delegates state transitions to the
engine, then durably saves the result. No game logic lives here.

Turn resolution is the one operation that must be atomic. ``submit_advice``
opens a single repository transaction and, inside it, checks the idempotency
record, validates the campaign revision, runs the deterministic engine, saves
the authoritative campaign, appends the immutable snapshot, and records the
idempotency result. Any failure rolls the whole thing back, so a partially
resolved turn is never observable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional
import uuid

from engine import dossier as dossier_engine
from engine import endings as endings_engine
from engine import seed_data, turn as turn_engine
from engine.models import (
    AdviceMemo,
    Campaign,
    FactClassification,
    MemoProvenance,
    MemoRevision,
    MemoStatus,
    SentMemoSnapshot,
)
from app.ai import fallbacks
from app.ai.logging import get_run_store
from app.ai.provider import get_provider
from app.ai.runner import run_artifact
from app.ai.schemas import MemoDraft
from app.config import get_settings
from app.observability import IdempotencyOutcome, bind_log_fields
from app.repository import configure_repository, get_repository
from app.schemas import api as schemas
from app.services import errors


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


def _debt_ledger(campaign: Campaign) -> list[schemas.PrecedentEntryModel]:
    return [
        schemas.PrecedentEntryModel.model_validate(asdict(entry))
        for entry in campaign.debt_ledger
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


def _caller_disposition(campaign: Campaign) -> str:
    """How the caller opens the line, from live trust. Presentation-only."""
    call = campaign.current_call()
    if call is None:
        return ""
    faction = next(
        (f for f in campaign.world_state.factions if f.id == call.caller_faction_id),
        None,
    )
    if faction is None:
        return ""
    trust = faction.trust_in_player
    if trust <= 30:
        band = "opens guarded — working trust is close to exhausted"
    elif trust <= 45:
        band = "opens wary — earlier turns are remembered"
    elif trust >= 70:
        band = "opens direct — the desk's record has earned the benefit of the doubt"
    else:
        band = "opens professionally"
    return f"The {faction.name} {band} (trust {trust}/100)."


def _current_model(campaign: Campaign) -> schemas.CurrentTurnModel:
    """Map one campaign revision to the exact turn package shown by the desk."""
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
        debt_ledger=_debt_ledger(campaign),
        system_status=_system_status(campaign),
        last_turn=last_turn,
        caller_disposition=_caller_disposition(campaign),
    )


def get_current(campaign_id: str) -> Optional[schemas.CurrentTurnModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    return _current_model(campaign)


def get_pending_presentation(
    campaign_id: str,
) -> Optional[schemas.TurnPresentationModel]:
    """Return the oldest resolved turn not yet acknowledged by Next Call."""
    if get_repository().get(campaign_id) is None:
        raise errors.CampaignNotFound(campaign_id)
    payload = get_repository().pending_turn_presentation(campaign_id)
    if payload is None:
        return None
    return schemas.TurnPresentationModel.model_validate(payload)


def acknowledge_presentation(
    campaign_id: str, turn_number: int
) -> schemas.PresentationAcknowledgedModel:
    """Idempotently record the player's explicit transition beyond a resolved turn."""
    if get_repository().get(campaign_id) is None:
        raise errors.CampaignNotFound(campaign_id)
    if not get_repository().acknowledge_turn_presentation(campaign_id, turn_number):
        raise errors.PresentationNotFound(turn_number)
    return schemas.PresentationAcknowledgedModel(
        campaign_id=campaign_id, turn_number=turn_number
    )


def request_fingerprint(
    advice_id: str,
    expected_turn: int,
    memo_id: Optional[str] = None,
    memo_revision: Optional[int] = None,
    cited_document_ids: Optional[list[str]] = None,
) -> str:
    """Stable digest of everything a submission asks the engine to do.

    Reusing an idempotency key with a different fingerprint is a client bug, so
    it must be a conflict rather than a silent replay of the wrong turn.
    """
    canonical = json.dumps(
        {
            "advice_id": advice_id,
            "expected_turn": expected_turn,
            "memo_id": memo_id,
            "memo_revision": memo_revision,
            "cited_document_ids": sorted(cited_document_ids or []),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _content_digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _memo_content_text(draft: MemoDraft) -> str:
    """Render validated structured output into the editable plain-text record."""
    sections = [
        ("Recommendation", [draft.recommendation]),
        ("Rationale", [draft.rationale]),
        ("Operational steps", draft.operational_steps),
        ("Communications", [draft.communications]),
        ("Likely opposition", draft.likely_opposition),
        ("Second-order risks", draft.second_order_risks),
        ("Fallback plan", [draft.fallback_plan]),
    ]
    lines: list[str] = []
    for heading, items in sections:
        lines.append(heading.upper())
        lines.extend(
            item if len(items) == 1 else f"- {item}"
            for item in items
        )
        lines.append("")
    return "\n".join(lines).strip()


def _memo_model(memo: AdviceMemo) -> schemas.AdviceMemoModel:
    return schemas.AdviceMemoModel.model_validate(asdict(memo))


def _find_memo(campaign: Campaign, memo_id: str) -> AdviceMemo:
    memo = next((item for item in campaign.advice_memos if item.id == memo_id), None)
    if memo is None or memo.campaign_id != campaign.id:
        raise errors.MemoNotFound(memo_id)
    return memo


def _new_memo(
    campaign: Campaign,
    *,
    name: str,
    content: str,
    advice_id: str,
    author: str,
    source: str,
    provenance: MemoProvenance,
) -> AdviceMemo:
    now = _utc_now()
    digest = _content_digest(content)
    memo = AdviceMemo(
        id=f"memo_{uuid.uuid4().hex}",
        campaign_id=campaign.id,
        status=MemoStatus.DRAFT,
        name=name,
        content=content,
        revision=1,
        created_at=now,
        updated_at=now,
        author=author,
        source=source,
        classification=FactClassification.PROPOSED,
        provenance=provenance,
        turn_number=campaign.turn_number,
        call_id=campaign.current_call().id if campaign.current_call() else None,
        advice_id=advice_id,
        revisions=[
            MemoRevision(
                revision=1,
                name=name,
                content=content,
                author=author,
                source=source,
                created_at=now,
                content_digest=digest,
            )
        ],
    )
    campaign.advice_memos.append(memo)
    return memo


class ResolvedTurn:
    """A turn-resolution outcome plus whether it replayed a prior submission."""

    __slots__ = ("result", "replayed")

    def __init__(self, result: schemas.TurnResultModel, replayed: bool) -> None:
        self.result = result
        self.replayed = replayed


def submit_advice(
    campaign_id: str,
    advice_id: str,
    *,
    expected_turn: int,
    idempotency_key: str,
    memo_id: Optional[str] = None,
    memo_revision: Optional[int] = None,
    cited_document_ids: Optional[list[str]] = None,
) -> ResolvedTurn:
    """Resolve one turn atomically, at most once per (campaign, key).

    Ordering is deliberate. The idempotency record is consulted first, so an
    honest retry of a turn that already committed replays its original response
    instead of tripping the now-stale revision check. Only a key that has never
    resolved reaches the terminal and revision guards.
    """
    fingerprint = request_fingerprint(
        advice_id, expected_turn, memo_id, memo_revision, cited_document_ids
    )

    with get_repository().transaction() as active:
        campaign = active.get_campaign(campaign_id)
        if campaign is None:
            bind_log_fields(idempotency=IdempotencyOutcome.REJECTED)
            raise errors.CampaignNotFound(campaign_id)

        recorded = active.get_idempotency_record(campaign_id, idempotency_key)
        if recorded is not None:
            if recorded["request_fingerprint"] != fingerprint:
                bind_log_fields(idempotency=IdempotencyOutcome.KEY_CONFLICT)
                raise errors.IdempotencyKeyConflict(idempotency_key)
            bind_log_fields(
                idempotency=IdempotencyOutcome.REPLAYED,
                turn_number=recorded["resulting_turn"],
            )
            return ResolvedTurn(
                schemas.TurnResultModel.model_validate(recorded["response"]),
                replayed=True,
            )

        if campaign.is_terminal():
            bind_log_fields(idempotency=IdempotencyOutcome.TERMINAL)
            raise errors.CampaignTerminal(campaign.status, campaign.failure_reason)

        if campaign.turn_number != expected_turn:
            bind_log_fields(idempotency=IdempotencyOutcome.STALE_TURN)
            raise errors.StaleTurn(expected_turn, campaign.turn_number)

        option = next(
            (item for item in campaign.available_advice() if item.id == advice_id),
            None,
        )
        if option is None:
            bind_log_fields(idempotency=IdempotencyOutcome.REJECTED)
            raise errors.UnknownAdvice(advice_id)

        # Cited evidence must exist and already be on the board this turn.
        available_docs = {
            doc.id for doc in campaign.documents
            if doc.turn_number <= campaign.turn_number
        }
        for doc_id in cited_document_ids or []:
            if doc_id not in available_docs:
                bind_log_fields(idempotency=IdempotencyOutcome.REJECTED)
                raise errors.UnknownDocument(doc_id)

        # Public API callers always attach an explicit memo. The optional
        # branch preserves direct service compatibility by materializing the
        # same deterministic system memo; every resolved turn still has an
        # exact sent artifact.
        if memo_id is None:
            payload = fallbacks.build_memo_input(
                option, campaign.current_call(), campaign.world_state.factions
            )
            generated = fallbacks.memo_fallback(payload)
            memo = _new_memo(
                campaign,
                name=f"Advice of record — {option.title or option.label}",
                content=_memo_content_text(generated),
                advice_id=advice_id,
                author="Continuity Desk",
                source="system",
                provenance=MemoProvenance(
                    workflow="deterministic_fallback",
                    model_name="disabled",
                    provider="disabled",
                    validation_status="fallback",
                    fallback_used=True,
                ),
            )
        else:
            memo = _find_memo(campaign, memo_id)
            if memo.status != MemoStatus.DRAFT:
                raise errors.ImmutableMemo(memo.id)
            if memo_revision != memo.revision:
                raise errors.StaleMemoRevision(memo_revision or 0, memo.revision)
            if memo.advice_id is not None and memo.advice_id != advice_id:
                raise errors.MemoAdviceMismatch()

        sent_at = _utc_now()
        current_before_resolution = _current_model(campaign)
        sent_snapshot = SentMemoSnapshot(
            memo_id=memo.id,
            revision=memo.revision,
            name=memo.name,
            content=memo.content,
            content_digest=_content_digest(memo.content),
            sent_at=sent_at,
            author=memo.author,
            source=memo.source,
            classification=memo.classification,
            provenance=memo.provenance,
        )

        try:
            result = turn_engine.advance_turn(
                campaign, advice_id, cited_document_ids
            )
        except turn_engine.UnknownAdviceOption as exc:
            bind_log_fields(idempotency=IdempotencyOutcome.REJECTED)
            raise errors.UnknownAdvice(advice_id) from exc
        except turn_engine.UnknownDocument as exc:
            bind_log_fields(idempotency=IdempotencyOutcome.REJECTED)
            raise errors.UnknownDocument(str(exc)) from exc

        # Attach audit references only after deterministic resolution. Memo
        # prose is never visible to rules, diffs, decision type, or canon text.
        result.sent_memo = sent_snapshot
        result.decision.memo_id = memo.id
        result.decision.memo_revision = memo.revision
        result.canon_entry.memo_id = memo.id

        memo.status = MemoStatus.SENT
        memo.turn_number = result.turn_number
        memo.call_id = memo.call_id or (
            campaign.client_calls.get(result.turn_number).id
            if campaign.client_calls.get(result.turn_number)
            else None
        )
        memo.advice_id = advice_id
        memo.updated_at = sent_at
        memo.sent_snapshot = sent_snapshot

        response = schemas.TurnResultModel.model_validate(asdict(result))
        active.save_campaign(campaign, snapshot_turn=result.turn_number)
        active.save_turn_presentation(
            campaign_id=campaign_id,
            turn_number=result.turn_number,
            current_turn=current_before_resolution.model_dump(mode="json"),
            result=response.model_dump(mode="json"),
        )
        active.save_idempotency_record(
            campaign_id=campaign_id,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            expected_turn=expected_turn,
            resulting_turn=result.turn_number,
            response=response.model_dump(mode="json"),
        )
        bind_log_fields(
            idempotency=IdempotencyOutcome.RESOLVED,
            turn_number=result.turn_number,
        )

    return ResolvedTurn(response, replayed=False)


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
        debt_ledger=_debt_ledger(campaign),
    )


def get_dossier(campaign_id: str) -> Optional[schemas.DossierModel]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    assessment = None
    if campaign.is_terminal():
        assessment = schemas.OutcomeAssessmentModel.model_validate(
            asdict(endings_engine.build_outcome_assessment(campaign))
        )
    return schemas.DossierModel(
        campaign_id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        filename=dossier_engine.dossier_filename(campaign),
        markdown=dossier_engine.render_dossier_markdown(campaign),
        assessment=assessment,
    )


def list_memos(campaign_id: str) -> Optional[list[schemas.AdviceMemoModel]]:
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    return [_memo_model(memo) for memo in campaign.advice_memos]


def create_memo(
    campaign_id: str,
    *,
    creation_mode: str,
    advice_id: str,
    name: str,
    content: Optional[str] = None,
) -> schemas.AdviceMemoModel:
    """Create a persistent proposed memo without touching WorldState."""
    artifact = None
    if creation_mode in ("template", "ai"):
        campaign = _require_campaign(campaign_id)
        option = next(
            (item for item in campaign.available_advice() if item.id == advice_id),
            None,
        )
        if option is None:
            raise errors.UnknownAdvice(advice_id)
        payload = fallbacks.build_memo_input(
            option, campaign.current_call(), campaign.world_state.factions
        )
        if creation_mode == "template":
            content = _memo_content_text(fallbacks.memo_fallback(payload))
        else:
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
            content = _memo_content_text(artifact.content)

    with get_repository().transaction() as active:
        campaign = active.get_campaign(campaign_id)
        if campaign is None:
            raise errors.CampaignNotFound(campaign_id)
        if not any(item.id == advice_id for item in campaign.available_advice()):
            raise errors.UnknownAdvice(advice_id)

        if creation_mode == "manual":
            provenance = MemoProvenance(workflow="manual", fallback_used=False)
            source = "player"
            author = "Player consultant"
        elif creation_mode == "template":
            provenance = MemoProvenance(
                workflow="deterministic_template", fallback_used=False
            )
            source = "system"
            author = "Continuity Desk"
        else:
            provenance = MemoProvenance(
                workflow=(
                    "ai_assisted" if artifact.from_model else "deterministic_fallback"
                ),
                model_run_id=artifact.run.id,
                prompt_version=artifact.run.prompt_version,
                model_name=artifact.run.model_name,
                provider=artifact.run.provider,
                validation_status=artifact.run.validation_status,
                fallback_used=not artifact.from_model,
            )
            source = "ai" if artifact.from_model else "system"
            author = "AI drafting assistant" if artifact.from_model else "Continuity Desk"

        memo = _new_memo(
            campaign,
            name=name,
            content=content or "",
            advice_id=advice_id,
            author=author,
            source=source,
            provenance=provenance,
        )
        active.save_campaign(campaign)
    return _memo_model(memo)


def update_memo(
    campaign_id: str,
    memo_id: str,
    *,
    expected_revision: int,
    name: str,
    content: str,
) -> schemas.AdviceMemoModel:
    """Append a player-authored revision to an editable draft."""
    with get_repository().transaction() as active:
        campaign = active.get_campaign(campaign_id)
        if campaign is None:
            raise errors.CampaignNotFound(campaign_id)
        memo = _find_memo(campaign, memo_id)
        if memo.status != MemoStatus.DRAFT:
            raise errors.ImmutableMemo(memo.id)
        if memo.revision != expected_revision:
            raise errors.StaleMemoRevision(expected_revision, memo.revision)
        now = _utc_now()
        memo.revision += 1
        memo.name = name
        memo.content = content
        memo.updated_at = now
        memo.author = "Player consultant"
        memo.source = "player"
        memo.revisions.append(
            MemoRevision(
                revision=memo.revision,
                name=name,
                content=content,
                author=memo.author,
                source=memo.source,
                created_at=now,
                content_digest=_content_digest(content),
            )
        )
        active.save_campaign(campaign)
    return _memo_model(memo)


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
        model_run_id=artifact.run.id,
        prompt_version=artifact.run.prompt_version,
        model_name=artifact.run.model_name,
        provider=artifact.run.provider,
        validation_status=artifact.run.validation_status,
        fallback_used=not artifact.from_model,
    )


def get_model_runs(campaign_id: str) -> Optional[list[schemas.ModelRunModel]]:
    """Read-only log of AI model runs recorded for this campaign."""
    campaign = _require_campaign_or_none(campaign_id)
    if campaign is None:
        return None
    return [
        schemas.ModelRunModel(
            id=r.id,
            prompt_name=r.prompt_name,
            prompt_version=r.prompt_version,
            model_name=r.model_name,
            validation_status=r.validation_status,
            input_summary=r.input_summary,
            retry_count=r.retry_count,
            latency_ms=r.latency_ms,
            turn_number=r.turn_number,
            provider=r.provider,
        )
        for r in get_run_store().for_campaign(campaign_id)
    ]


def _require_campaign_or_none(campaign_id: str) -> Optional[Campaign]:
    return get_repository().get(campaign_id)
