"""Durable persistence boundary, kept separate from the deterministic engine."""

from memory.persistence import (
    CampaignRepository,
    CorruptRecordError,
    ImmutableSnapshotError,
    SQLiteRepository,
)

__all__ = [
    "CampaignRepository",
    "CorruptRecordError",
    "ImmutableSnapshotError",
    "SQLiteRepository",
]
