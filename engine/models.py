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


class PublicStatus:
    """Visibility of a fact, document, or canon entry within the world."""
    PUBLIC = "public"
    PRIVATE = "private"
    LEAKED = "leaked"
    SEALED = "sealed"
    DISPUTED = "disputed"
    UNKNOWN = "unknown"


class Reliability:
    """Source reliability of a document (state-schema.md)."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"
    CONTESTED = "contested"


class Urgency:
    LOW = "low"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


class ThreadStatus:
    OPEN = "open"
    ESCALATING = "escalating"
    STABILIZING = "stabilizing"
    RESOLVED = "resolved"


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
    # --- Richer faction texture (deterministic, hand-authored seed values) ---
    type: str = "AGENCY"                  # faction type vocabulary (state-schema.md)
    public_position: str = ""             # what they say publicly
    private_incentive: str = ""           # what actually drives them
    trust_in_player: int = 50             # 0-100
    risk_tolerance: int = 40              # 0-100 appetite for escalation
    current_pressure: int = 30            # 0-100 pressure they are applying now
    red_lines: List[str] = field(default_factory=list)   # things they will not accept
    tags: List[str] = field(default_factory=list)


@dataclass
class Crisis:
    id: str
    name: str
    description: str
    severity: int           # 0-100
    active: bool = True
    type: str = "WATER_FAILURE"


@dataclass
class AdviceOption:
    """A player-selectable recommendation.

    ``effects`` are the deltas applied when the advice is FOLLOWED at full
    adherence; the engine scales them by the NPC's ``adherence``. The tradeoff
    fields (``expected_benefits`` / ``expected_harms`` / ``*_risk``) are
    descriptive, not authoritative -- they exist so the UI can show the player
    the cost of each path before they commit.
    """
    id: str
    label: str
    summary: str            # one-line description shown to the player
    rationale: str          # why one might choose it
    tags: List[str]         # e.g. ["disclosure"], ["state_support"]
    effects: Dict[str, int] # variable -> delta when FOLLOWED (adherence == 1.0)
    # --- Tradeoff surface (deterministic, descriptive only) ---
    type: str = "CONTROLLED_DISCLOSURE"   # advice-type vocabulary (state-schema.md)
    title: str = ""                        # display title (defaults to label)
    recommendation: str = ""               # the specific recommended action
    expected_benefits: List[str] = field(default_factory=list)
    expected_harms: List[str] = field(default_factory=list)
    legal_risk: int = 30                   # 0-100 descriptive risk estimate
    political_risk: int = 30
    operational_risk: int = 30
    affected_factions: List[str] = field(default_factory=list)


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
    # --- Richer call package ---
    caller_role: str = ""                  # title of the person on the line
    urgency: str = Urgency.HIGH
    time_horizon: str = ""                 # e.g. "72 hours"
    unknown_facts: List[str] = field(default_factory=list)
    immediate_risks: List[str] = field(default_factory=list)
    public_exposure: str = PublicStatus.PRIVATE
    private_pressure: str = ""
    attached_document_ids: List[str] = field(default_factory=list)


@dataclass
class Document:
    """An in-world artifact on the Evidence Board.

    Documents are hand-authored canon in seed data (no model output). Each is
    classified so the UI can render reliability / public-status labels. A
    document with ``turn_number`` N is available from turn N onward, so the
    evidence board accumulates as the engagement progresses.
    """
    id: str
    title: str
    type: str               # LAB_REPORT / EMAIL / MEMO / ... (state-schema.md)
    source: str
    turn_number: int        # turn from which the document is available
    public_status: str = PublicStatus.PRIVATE
    reliability: str = Reliability.MEDIUM
    summary: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class OpenThread:
    """An unresolved risk, promise, or storyline tracked across turns."""
    id: str
    title: str
    summary: str
    turn_opened: int
    status: str = ThreadStatus.OPEN
    tags: List[str] = field(default_factory=list)


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
    # --- Visible mediation of the player's advice ---
    deviation: str = ""            # how the action departed from the advice
    public_explanation: str = ""   # what the client said publicly
    private_motive: str = ""       # what actually drove the deviation
    resulting_risk: str = ""       # the new exposure created by the deviation


@dataclass
class CanonEntry:
    id: str
    turn_number: int
    category: str           # "decision" / "memo" / "statement" / "event"
    title: str
    body: str
    source: str             # who/what produced it
    classification: str = FactClassification.CANON
    # --- Richer canon metadata ---
    public_status: str = PublicStatus.PUBLIC
    involved_factions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class FactionReaction:
    faction_id: str
    faction_name: str
    reaction: str


@dataclass
class ConsequenceStack:
    """A human-readable decomposition of a turn's aftermath.

    The applied diffs remain the authoritative record; this stack translates
    them (plus the decision and prior state) into the categories a consultant
    would brief: immediate effects, second-order fallout, faction/media/legal
    reactions, and the canon/threads the turn leaves behind.
    """
    immediate: List[str] = field(default_factory=list)
    second_order: List[str] = field(default_factory=list)
    faction_reactions: List[FactionReaction] = field(default_factory=list)
    media_framing: List[str] = field(default_factory=list)
    legal_fallout: List[str] = field(default_factory=list)
    canonized_events: List[str] = field(default_factory=list)
    opened_threads: List[str] = field(default_factory=list)


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
    consequence_stack: ConsequenceStack = field(default_factory=ConsequenceStack)
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
    documents: List[Document] = field(default_factory=list)
    open_threads: List[OpenThread] = field(default_factory=list)
    failure_reason: Optional[str] = None
    created_at: str = ""

    def is_terminal(self) -> bool:
        return self.status in (CampaignStatus.COMPLETED, CampaignStatus.FAILED)

    def current_call(self) -> Optional[ClientCall]:
        return self.client_calls.get(self.turn_number)

    def available_advice(self) -> List[AdviceOption]:
        return list(self.advice_options)

    def available_documents(self) -> List[Document]:
        """Documents visible at the current turn (available-on-or-before now)."""
        return [d for d in self.documents if d.turn_number <= self.turn_number]
