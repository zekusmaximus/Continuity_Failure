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
