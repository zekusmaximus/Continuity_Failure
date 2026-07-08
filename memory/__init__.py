"""Memory / persistence layer.

For the first slice this is an in-process store. It is kept as its own package
(per the repository structure) so that a durable canon store (SQLite/Postgres)
can be slotted in later without touching engine or API code.
"""

from memory.persistence import CampaignStore, MemoryStore

__all__ = ["CampaignStore", "MemoryStore"]
