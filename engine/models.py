"""Typed dataclass models for the Northbridge deterministic engine.

These models are plain dataclasses (no web/Pydantic dependency) so the engine
can be imported and unit-tested in complete isolation from FastAPI. The backend
maps these into Pydantic response models at the API boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Controlled vocabularies (kept as plain string constants for trivial JSON).
# ---------------------------------------------------------------------------

class CampaignStatus:
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DecisionType:
    FOLLOWED = "FOLLOWED"
    PARTIALLY_FOLLOWED = "PARTIALLY_FOLLOWED"
    MODIFIED = "MODIFIED"
    DELAYED = "DELAYED"
    REJECTED = "REJECTED"


class SourceType:
    ADVICE = "advice"
    NPC_MODIFICATION = "npc_modification"
    AMBIENT = "ambient"
    DECISION = "decision"


class FactClassification:
    """Classification of a generated/known fact (design rule #4)."""
    CANON = "canon"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    RUMOR = "rumor"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------

@dataclass
class Faction:
    id: str
    name: str
    description: str
    posture: str            # current posture label, e.g. "anxious", "cooperative"
    influence: int          # 0-100, how much weight they carry this turn
    alignment: str          # "authority" / "opposition" / "neutral" / "service"


@dataclass
class Crisis:
    id: str
    name: str
    description: str
    severity: int           # 0-100
    active: bool = True


@dataclass
class AdviceOption:
    id: str
    label: str
    summary: str            # one-line description shown to the player
    rationale: str          # why one might choose it
    tags: List[str]         # e.g. ["disclosure"], ["state_support"]
    effects: Dict[str, int] # variable -> delta when FOLLOWED (adherence == 1.0)


@dataclass
class ClientCall:
    id: str
    turn: int
    caller: str
    caller_faction_id: str
    summary: str
    known_facts: List[str]
    ask: str
    crisis_id: Optional[str] = None


@dataclass
class AppliedDiff:
    variable: str
    old_value: int
    new_value: int
    delta: int
    reason: str
    source_type: str        # one of SourceType.*


@dataclass
class NpcDecision:
    advice_id: str
    decision_type: str      # one of DecisionType.*
    decider: str            # faction name that acted on the advice
    rationale: str
    adherence: float        # 0.0-1.0 multiplier applied to advice effects
    modifications: Dict[str, int] = field(default_factory=dict)


@dataclass
class CanonEntry:
    id: str
    turn_number: int
    category: str           # "decision" / "memo" / "statement" / "event"
    title: str
    body: str
    source: str             # who/what produced it
    classification: str = FactClassification.CANON


@dataclass
class WorldState:
    turn_number: int
    variables: Dict[str, int]
    factions: List[Faction]
    active_crisis: Optional[Crisis]
    last_verified: str      # diegetic freshness label


@dataclass
class TurnResult:
    turn_number: int
    advice_id: str
    advice_label: str
    decision: NpcDecision
    diffs: List[AppliedDiff]
    aftermath_summary: str
    canon_entry: CanonEntry
    status_after: str
    failure_reason: Optional[str] = None


@dataclass
class Campaign:
    id: str
    name: str
    scenario_id: str
    status: str
    turn_number: int
    max_turns: int
    world_state: WorldState
    advice_options: List[AdviceOption]
    client_calls: Dict[int, ClientCall]    # turn -> call
    turn_history: List[TurnResult] = field(default_factory=list)
    canon: List[CanonEntry] = field(default_factory=list)
    failure_reason: Optional[str] = None
    created_at: str = ""

    def is_terminal(self) -> bool:
        return self.status in (CampaignStatus.COMPLETED, CampaignStatus.FAILED)

    def current_call(self) -> Optional[ClientCall]:
        return self.client_calls.get(self.turn_number)

    def available_advice(self) -> List[AdviceOption]:
        return list(self.advice_options)
