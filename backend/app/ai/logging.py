"""Model-run logging.

Every model invocation — success, validation failure, or deterministic fallback —
produces exactly one :class:`ModelRun` record. Production calls use the same
SQLite repository boundary as campaigns. ``ModelRunStore`` remains as a small
in-memory test double for isolated validation-boundary tests.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel


class ValidationStatus:
    """Outcome of a single logged run (from the runner's perspective)."""

    OK = "ok"            # provider succeeded and output validated
    INVALID = "invalid"  # provider succeeded but output failed validation
    FALLBACK = "fallback"  # deterministic fallback used (AI off, or exhausted retries)
    ERROR = "error"      # provider errored (network/transport)


class ModelRun(BaseModel):
    """One logged model invocation. See ``prompts/README.md`` § Logging."""

    id: str = ""
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
    provider: Optional[str] = None

    def model_post_init(self, __context) -> None:
        if not self.id:
            self.id = f"run_{uuid.uuid4().hex}"


class ModelRunStore:
    """Append-only in-memory test double for :class:`ModelRun` records."""

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


class RepositoryModelRunStore:
    """Typed adapter over repository JSON records; never touches game state."""

    def __init__(self, repository) -> None:
        self._repository = repository

    def add(self, run: ModelRun) -> None:
        self._repository.add_model_run(run.model_dump(mode="json"))

    def all(self) -> List[ModelRun]:
        return [ModelRun.model_validate(row) for row in self._repository.all_model_runs()]

    def for_campaign(self, campaign_id: str) -> List[ModelRun]:
        return [
            ModelRun.model_validate(row)
            for row in self._repository.model_runs_for_campaign(campaign_id)
        ]

    def clear(self) -> None:
        self._repository.clear_model_runs()


def get_run_store() -> RepositoryModelRunStore:
    # Imported lazily so standalone validation-boundary tests can continue to
    # use the in-memory test double without constructing a database.
    from app.repository import get_repository

    return RepositoryModelRunStore(get_repository())
