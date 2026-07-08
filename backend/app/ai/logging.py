"""Model-run logging.

Every model invocation — success, validation failure, or deterministic fallback —
produces exactly one :class:`ModelRun` record. The field set mirrors the logging
contract in ``prompts/README.md`` so that AI-assisted turns stay inspectable and
replayable. Storage is process-local and in-memory, mirroring
``memory.persistence.CampaignStore``; the API exposes it read-only.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from pydantic import BaseModel


class ValidationStatus:
    """Outcome of a single logged run (from the runner's perspective)."""

    OK = "ok"            # provider succeeded and output validated
    INVALID = "invalid"  # provider succeeded but output failed validation
    FALLBACK = "fallback"  # deterministic fallback used (AI off, or exhausted retries)
    ERROR = "error"      # provider errored (network/transport)


class ModelRun(BaseModel):
    """One logged model invocation. See ``prompts/README.md`` § Logging."""

    prompt_name: str
    prompt_version: str
    model_name: str
    validation_status: str
    input_summary: str = ""
    raw_output: str = ""
    parsed_output: Optional[dict] = None
    retry_count: int = 0
    latency_ms: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
    estimated_cost: Optional[float] = None
    # Optional provenance so runs can be filtered per campaign/turn.
    campaign_id: Optional[str] = None
    turn_number: Optional[int] = None


class ModelRunStore:
    """Append-only, thread-safe, in-memory log of :class:`ModelRun` records.

    Process-local and cleared on restart, matching the rest of the skeleton's
    persistence. Never mutates game state; it only records what happened.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runs: List[ModelRun] = []

    def add(self, run: ModelRun) -> None:
        with self._lock:
            self._runs.append(run)

    def all(self) -> List[ModelRun]:
        with self._lock:
            return list(self._runs)

    def for_campaign(self, campaign_id: str) -> List[ModelRun]:
        with self._lock:
            return [r for r in self._runs if r.campaign_id == campaign_id]

    def clear(self) -> None:
        with self._lock:
            self._runs.clear()


# Module-level store, mirroring campaign_service._STORE.
_STORE = ModelRunStore()


def get_run_store() -> ModelRunStore:
    return _STORE
