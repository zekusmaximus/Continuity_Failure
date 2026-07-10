"""Application-level construction of the durable repository.

This neutral provider is shared by campaign orchestration and advisory AI
logging. It does not import the engine or expose any state-transition method.
"""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Optional

from app.config import get_settings
from memory.persistence import CampaignRepository, SQLiteRepository


_REPOSITORY: Optional[CampaignRepository] = None
_REPOSITORY_PATH: Optional[Path] = None
_REPOSITORY_LOCK = threading.RLock()


def configure_repository(repository: Optional[CampaignRepository] = None) -> None:
    """Override/reset the repository (primarily for isolated test databases)."""
    global _REPOSITORY, _REPOSITORY_PATH
    with _REPOSITORY_LOCK:
        _REPOSITORY = repository
        _REPOSITORY_PATH = (
            Path(repository.path).resolve()
            if repository is not None and hasattr(repository, "path")
            else None
        )


def get_repository() -> CampaignRepository:
    global _REPOSITORY, _REPOSITORY_PATH
    configured_path = Path(get_settings().database_path).expanduser().resolve()
    with _REPOSITORY_LOCK:
        if _REPOSITORY is None or (
            _REPOSITORY_PATH is not None and _REPOSITORY_PATH != configured_path
        ):
            _REPOSITORY = SQLiteRepository(configured_path)
            _REPOSITORY_PATH = configured_path
        return _REPOSITORY
