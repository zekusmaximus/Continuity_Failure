"""In-memory persistence for the skeleton.

``CampaignStore`` holds live ``Campaign`` objects keyed by id. It is the single
mutable container the FastAPI service talks to. A thin JSON snapshot helper is
included for future durability; live play does not depend on it.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, Iterator, List, Optional


class MemoryStore:
    """Generic thread-safe key/value store for arbitrary in-memory data.

    Used today for campaign objects and reserved for future canon snapshots.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: str, default: Optional[object] = None) -> Optional[object]:
        with self._lock:
            return self._data.get(key, default)

    def has(self, key: str) -> bool:
        with self._lock:
            return key in self._data

    def remove(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def all(self) -> List[object]:
        with self._lock:
            return list(self._data.values())

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def save_json(self, path: str) -> None:
        """Dump the store to JSON. Values must be JSON-serializable dicts."""
        with self._lock:
            Path(path).write_text(json.dumps(self._data, indent=2, default=str))

    def load_json(self, path: str) -> None:
        text = Path(path).read_text()
        with self._lock:
            self._data = json.loads(text) if text.strip() else {}


class CampaignStore:
    """Convenience wrapper around ``MemoryStore`` for live campaign objects."""

    def __init__(self) -> None:
        self._store = MemoryStore()

    def put(self, campaign) -> None:
        self._store.set(campaign.id, campaign)

    def get(self, campaign_id: str):
        return self._store.get(campaign_id)

    def has(self, campaign_id: str) -> bool:
        return self._store.has(campaign_id)

    def list(self) -> Iterator:
        for value in self._store.all():
            yield value

    def clear(self) -> None:
        self._store.clear()
