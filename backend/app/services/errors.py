"""Typed turn-resolution failures.

Each carries a stable machine-readable ``code`` and a player-safe ``message``.
Nothing here exposes stack traces, SQL, file paths, or model internals; the API
layer renders these directly into the response body.
"""

from __future__ import annotations

from typing import Optional


class TurnResolutionError(Exception):
    """Base class for a rejected turn-resolution request."""

    code = "turn_resolution_error"
    status_code = 409

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class CampaignNotFound(TurnResolutionError):
    code = "campaign_not_found"
    status_code = 404

    def __init__(self, campaign_id: str) -> None:
        super().__init__(f"Campaign not found: {campaign_id}")


class CampaignTerminal(TurnResolutionError):
    """The campaign already completed or failed; no further turns resolve."""

    code = "campaign_terminal"
    status_code = 409

    def __init__(self, status: str, failure_reason: Optional[str] = None) -> None:
        detail = f" ({failure_reason})" if failure_reason else ""
        super().__init__(
            f"This engagement is {status.lower()}{detail}. No further turns can be advanced."
        )
        self.status = status
        self.failure_reason = failure_reason


class StaleTurn(TurnResolutionError):
    """The client's expected turn no longer matches the authoritative campaign."""

    code = "stale_turn"
    status_code = 409

    def __init__(self, expected_turn: int, current_turn: int) -> None:
        super().__init__(
            f"This submission expected turn {expected_turn}, but the engagement "
            f"is on turn {current_turn}. Reload the current turn and resubmit."
        )
        self.expected_turn = expected_turn
        self.current_turn = current_turn


class IdempotencyKeyConflict(TurnResolutionError):
    """The key was already used for a materially different submission."""

    code = "idempotency_key_conflict"
    status_code = 409

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f"Idempotency key {idempotency_key} was already used for a different "
            "submission. Use a new key for a new submission."
        )
        self.idempotency_key = idempotency_key


class UnknownVariant(TurnResolutionError):
    """The requested seed variant is not authored for this scenario."""

    code = "unknown_variant"
    status_code = 422

    def __init__(self, variant_id: str, known: list) -> None:
        authored = ", ".join(known) if known else "none"
        super().__init__(
            f"Unknown scenario variant: {variant_id}. Authored variants: {authored}."
        )
        self.variant_id = variant_id


class PowerAllocationRequired(TurnResolutionError):
    """The desk is CRITICAL: the turn needs an auxiliary-power allocation."""

    code = "power_allocation_required"
    status_code = 409

    def __init__(self) -> None:
        super().__init__(
            "The workstation is critical: auxiliary power supports one "
            "subsystem per turn. Allocate it (MODEL_ACCESS, COMMUNICATIONS, "
            "or LIVE_DATA) and resubmit."
        )


class PowerAllocationUnavailable(TurnResolutionError):
    """An allocation was sent while the desk is not CRITICAL."""

    code = "power_allocation_not_available"
    status_code = 409

    def __init__(self, band: str) -> None:
        super().__init__(
            f"No auxiliary-power constraint applies at workstation band {band}. "
            "Omit powered_subsystem and resubmit."
        )
        self.band = band


class UnknownPowerAllocation(TurnResolutionError):
    """The named subsystem is not one auxiliary power can support."""

    code = "unknown_power_allocation"
    status_code = 422

    def __init__(self, allocation: str) -> None:
        super().__init__(
            f"Unknown auxiliary-power subsystem: {allocation}. Auxiliary "
            "power supports MODEL_ACCESS, COMMUNICATIONS, or LIVE_DATA."
        )
        self.allocation = allocation


class PowerAllocationConflict(TurnResolutionError):
    """The turn's auxiliary power is already committed to another subsystem."""

    code = "power_allocation_conflict"
    status_code = 409

    def __init__(self, committed: str, requested: Optional[str]) -> None:
        super().__init__(
            f"Auxiliary power is already committed to {committed} this turn "
            "(a drafting request energized that circuit). Auxiliary power "
            f"supports one subsystem per turn; resubmit with {committed} or "
            "wait for the next cycle."
        )
        self.committed = committed
        self.requested = requested


class RulesetIncompatible(TurnResolutionError):
    """The stored campaign was created under a different deterministic ruleset.

    Continuing it under the current rules would silently produce a hybrid
    record mislabeled with the old version, so continuation is refused. The
    campaign stays readable: history, canon, and the dossier remain available.
    """

    code = "ruleset_incompatible"
    status_code = 409

    def __init__(self, campaign_version: str, current_version: str) -> None:
        super().__init__(
            f"This engagement was resolved under ruleset {campaign_version}, "
            f"but this build executes ruleset {current_version}. Its record "
            "remains readable and the dossier can be exported, but further "
            "turns cannot be resolved under rules that did not produce it. "
            "Start a new engagement to play on the current ruleset."
        )
        self.campaign_version = campaign_version
        self.current_version = current_version


class EvidenceUnverifiable(TurnResolutionError):
    """Citations were submitted without the live-data circuit powered."""

    code = "evidence_unverifiable"
    status_code = 409

    def __init__(self, powered_subsystem: str) -> None:
        super().__init__(
            "Cited evidence cannot be verified: auxiliary power is allocated "
            f"to {powered_subsystem}, not LIVE_DATA. Drop the citations or "
            "change the allocation."
        )
        self.powered_subsystem = powered_subsystem


class UnknownAdvice(TurnResolutionError):
    code = "unknown_advice_option"
    status_code = 400

    def __init__(self, advice_id: str) -> None:
        super().__init__(f"Unknown advice option: {advice_id}")
        self.advice_id = advice_id


class UnknownDocument(TurnResolutionError):
    code = "unknown_document"
    status_code = 400

    def __init__(self, document_id: str) -> None:
        super().__init__(
            f"Cited document is unknown or not yet on the board: {document_id}"
        )
        self.document_id = document_id


class MemoNotFound(TurnResolutionError):
    code = "memo_not_found"
    status_code = 404

    def __init__(self, memo_id: str) -> None:
        super().__init__(f"Advice memo not found: {memo_id}")
        self.memo_id = memo_id


class StaleMemoRevision(TurnResolutionError):
    code = "stale_memo_revision"
    status_code = 409

    def __init__(self, expected_revision: int, current_revision: int) -> None:
        super().__init__(
            f"This request expected memo revision {expected_revision}, but the "
            f"draft is revision {current_revision}. Reload the memo before continuing."
        )
        self.expected_revision = expected_revision
        self.current_revision = current_revision


class ImmutableMemo(TurnResolutionError):
    code = "memo_immutable"
    status_code = 409

    def __init__(self, memo_id: str) -> None:
        super().__init__(
            f"Advice memo {memo_id} has been sent and is part of the historical record."
        )


class MemoAdviceMismatch(TurnResolutionError):
    code = "memo_advice_mismatch"
    status_code = 409

    def __init__(self) -> None:
        super().__init__(
            "The attached memo was drafted for a different advice option. "
            "Create or select a memo for this recommendation."
        )


class PresentationNotFound(TurnResolutionError):
    code = "turn_presentation_not_found"
    status_code = 409

    def __init__(self, turn_number: int) -> None:
        super().__init__(
            f"Resolved turn {turn_number} is not awaiting Next Call acknowledgement."
        )
        self.turn_number = turn_number
