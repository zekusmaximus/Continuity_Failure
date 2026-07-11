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
    THREAD = "thread"


class FactClassification:
    """Classification of a generated/known fact (design rule #4)."""
    CANON = "canon"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    RUMOR = "rumor"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


class MemoStatus:
    DRAFT = "draft"
    SENT = "sent"


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
    operational_steps: List[str] = field(default_factory=list)
    legal_risk: int = 30                   # 0-100 descriptive risk estimate
    political_risk: int = 30
    operational_risk: int = 30
    affected_factions: List[str] = field(default_factory=list)


@dataclass
class CallDecisionProfile:
    """Structured, call-specific incentive context for the NPC on the line.

    This is the legible input the deterministic decision logic reads to explain
    *why* a caller weighs advice the way it does on this particular call. It is
    authored content (not model output): ``mandate`` is the institutional charge
    the caller is under, ``priorities`` are the WorldState variables they care
    most about, ``red_line_tags`` are advice decision-tags that cross a stated
    red line (so proposing one is rejected outright), and ``off_brief_tolerance``
    is how willing the caller is to entertain advice they did not ask for.
    """
    mandate: str = ""
    priorities: List[str] = field(default_factory=list)     # WorldState variable names
    red_line_tags: List[str] = field(default_factory=list)  # advice decision-tags
    off_brief_tolerance: int = 50                           # 0-100


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
    # --- Call-specific decision space (Batch 6) ---
    # The 3-4 on-brief advice options this call is really asking about. Any other
    # known option is a "strategic alternative" the caller did not request, and
    # carries a visible, deterministic off-brief tradeoff at resolution.
    primary_advice_ids: List[str] = field(default_factory=list)
    decision_profile: Optional[CallDecisionProfile] = None


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
class ThreadCondition:
    """A legible resolution threshold, mirroring the FAILURE_THRESHOLDS shape."""
    variable: str
    op: str                 # "<=" / ">="
    threshold: int


@dataclass
class OpenThread:
    """An unresolved risk, promise, or storyline tracked across turns.

    A thread with a ``due_turn`` is a scheduled deterministic consequence: if it
    is still unresolved when that turn resolves, ``escalation_effects`` are
    applied as their own diff batch (source ``thread``) and, when
    ``repeat_every`` is set, the deadline re-arms. Threads resolve either when
    the player's advice carries one of ``resolve_tags`` and the client acted on
    it, or when every ``resolve_conditions`` threshold holds.
    """
    id: str
    title: str
    summary: str
    turn_opened: int
    status: str = ThreadStatus.OPEN
    tags: List[str] = field(default_factory=list)
    # --- Deterministic schedule (all optional; a bare thread is just a note) ---
    due_turn: Optional[int] = None
    escalation_effects: Dict[str, int] = field(default_factory=dict)
    escalation_note: str = ""
    repeat_every: int = 0                   # 0 = fire once; N = re-arm at +N turns
    resolve_conditions: List[ThreadCondition] = field(default_factory=list)
    resolve_tags: List[str] = field(default_factory=list)
    resolution_note: str = ""
    # --- Runtime lifecycle record (never authored in content) ---
    turn_resolved: Optional[int] = None
    escalation_count: int = 0


@dataclass
class AppliedDiff:
    variable: str
    old_value: int
    new_value: int
    delta: int
    reason: str
    source_type: str        # one of SourceType.*


class AdviceEffectOutcome:
    """How the caller's mediation left one proposed advice effect."""
    APPLIED = "applied"     # landed at the full proposed size
    REDUCED = "reduced"     # partially adopted (adherence scaling and/or clamp)
    DELAYED = "delayed"     # deferred by the client; nothing landed this turn
    REJECTED = "rejected"   # refused outright; nothing landed


@dataclass
class AdviceMediation:
    """Proposed-versus-applied record for ONE variable the advice targeted.

    ``proposed_delta`` is what the advice option would do at full adherence;
    ``expected_delta`` is the deterministic post-adherence request; and
    ``applied_delta`` is what actually landed after the 0-100 clamp. When the
    three disagree, the aftermath can say exactly where the effect was lost.
    """
    proposed_delta: int
    adherence: float
    expected_delta: int     # int(round(proposed_delta * adherence)), pre-clamp
    applied_delta: int      # the authoritative advice-sourced diff total
    outcome: str            # one of AdviceEffectOutcome.*
    clamped: bool = False   # applied differs from expected due to 0-100 bounds


@dataclass
class ConsequenceDelta:
    """One attributed step in a variable's start -> final reconciliation."""
    source_type: str        # one of SourceType.*
    delta: int              # effective (post-clamp) change, never zero
    reason: str
    value_before: int
    value_after: int


@dataclass
class VariableConsequence:
    """The causal story of one variable across one resolved turn.

    ``start_value`` + the ordered ``deltas`` reconcile exactly to
    ``final_value``; a variable the advice targeted but that never moved keeps
    an empty delta list and carries the rejection in ``advice``.
    """
    variable: str
    label: str              # humanized, player-facing
    direction: str          # "higher_is_better" / "higher_is_worse"
    start_value: int
    final_value: int
    net_delta: int
    deltas: List["ConsequenceDelta"] = field(default_factory=list)
    advice: Optional[AdviceMediation] = None


@dataclass
class ConsequenceReport:
    """Authoritative per-variable causal decomposition of one resolved turn.

    Built by the deterministic engine from the applied diffs plus the advice
    option and NPC decision -- never recomputed client-side. Ordered by the
    size of the net move so the largest consequences read first.
    """
    variables: List[VariableConsequence] = field(default_factory=list)


@dataclass
class AdherenceFactor:
    """One human-labeled input into how the NPC weighed the advice.

    Deliberately not an opaque score: ``label`` names the factor, ``detail``
    explains it in plain civic language, and ``direction`` says whether it
    pushed the caller toward or away from adopting the advice.
    """
    label: str
    detail: str
    direction: str          # "increase" / "decrease" / "neutral"


@dataclass
class DecisionExplanation:
    """Aftermath-facing account of why the NPC decided as it did.

    Surfaces the caller's incentives, any conflicts the advice raised, the
    human-labeled adherence factors, and whether the advice was on- or off-brief
    for this call -- so the consultant can read the mediation without seeing raw
    internal scoring.
    """
    caller: str
    institutional_mandate: str = ""
    incentives: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    adherence_factors: List[AdherenceFactor] = field(default_factory=list)
    off_brief: bool = False
    off_brief_note: str = ""
    outcome_reason: str = ""
    on_brief_options: List[str] = field(default_factory=list)   # labels the caller asked for
    # Deterministic client memory: what this decider remembers of the prior
    # engagement record (advice given, how it was used, red lines crossed).
    memory: List[str] = field(default_factory=list)


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
    # --- Off-brief mediation (Batch 6) ---
    off_brief: bool = False        # advice was not among the call's primary options
    off_brief_adjustments: Dict[str, int] = field(default_factory=dict)  # deterministic cost deltas
    cost_reason: str = ""          # AppliedDiff reason for the off-brief/red-line cost
    # --- Institutional-debt mediation ---
    # When this decision repeats an emergency precedent already on the ledger,
    # the repetition carries its own deterministic cost, applied as a diff
    # batch with ``precedent_reason`` as the legible AppliedDiff reason.
    precedent_adjustments: Dict[str, int] = field(default_factory=dict)
    precedent_reason: str = ""
    # --- Evidence citation mediation ---
    # Documents the consultant staked the memo on. Relevant, reliable, public
    # evidence strengthens adherence; contested evidence carries its own
    # deterministic cost, applied with ``citation_reason`` as the diff reason.
    cited_document_ids: List[str] = field(default_factory=list)
    citation_adjustments: Dict[str, int] = field(default_factory=dict)
    citation_reason: str = ""
    explanation: Optional["DecisionExplanation"] = None
    memo_id: Optional[str] = None
    memo_revision: Optional[int] = None


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
    memo_id: Optional[str] = None


@dataclass
class MemoProvenance:
    """Audit metadata for advisory prose; never an input to engine effects."""
    workflow: str                 # manual / deterministic_template / ai_assisted / deterministic_fallback
    model_run_id: Optional[str] = None
    prompt_version: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    validation_status: Optional[str] = None
    fallback_used: bool = False


@dataclass
class MemoRevision:
    revision: int
    name: str
    content: str
    author: str
    source: str                  # player / ai / system
    created_at: str
    content_digest: str


@dataclass
class SentMemoSnapshot:
    """Exact advisory artifact attached to one resolved turn."""
    memo_id: str
    revision: int
    name: str
    content: str
    content_digest: str
    sent_at: str
    author: str
    source: str
    classification: str
    provenance: MemoProvenance


@dataclass
class AdviceMemo:
    """Persistent advisory artifact. Draft revisions are append-only."""
    id: str
    campaign_id: str
    status: str
    name: str
    content: str
    revision: int
    created_at: str
    updated_at: str
    author: str
    source: str
    classification: str
    provenance: MemoProvenance
    turn_number: Optional[int] = None
    call_id: Optional[str] = None
    advice_id: Optional[str] = None
    revisions: List[MemoRevision] = field(default_factory=list)
    sent_snapshot: Optional[SentMemoSnapshot] = None


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
    escalated_threads: List[str] = field(default_factory=list)
    resolved_threads: List[str] = field(default_factory=list)


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
    sent_memo: Optional[SentMemoSnapshot] = None
    # Defaulted so pre-existing persisted turns rebuild cleanly with an empty
    # report; every newly resolved turn carries the full causal decomposition.
    consequence_report: ConsequenceReport = field(default_factory=ConsequenceReport)


@dataclass
class PrecedentEntry:
    """One emergency precedent on the institutional debt ledger.

    Precedents are the durable cost of expedient decisions: sole-source
    procurement, informal hospital priority, delayed public notice. Each entry
    links back to the canon entry that recorded the turn, and repeating a kind
    already on the ledger carries a deterministic cost and lowers the client's
    resistance to doing it again.
    """
    id: str
    kind: str               # PrecedentKind vocabulary (engine/ledger.py)
    label: str
    turn_recorded: int
    detail: str             # one legible sentence for the UI and dossier
    canon_id: str


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
    # Advice options that only make sense on a specific turn's call (e.g. a
    # school-closure protocol on the school turn). Global options above are
    # always available; these are appended for their turn only.
    per_turn_advice: Dict[int, List[AdviceOption]] = field(default_factory=dict)
    turn_history: List[TurnResult] = field(default_factory=list)
    canon: List[CanonEntry] = field(default_factory=list)
    documents: List[Document] = field(default_factory=list)
    open_threads: List[OpenThread] = field(default_factory=list)
    failure_reason: Optional[str] = None
    created_at: str = ""
    advice_memos: List[AdviceMemo] = field(default_factory=list)
    debt_ledger: List[PrecedentEntry] = field(default_factory=list)

    def is_terminal(self) -> bool:
        return self.status in (CampaignStatus.COMPLETED, CampaignStatus.FAILED)

    def current_call(self) -> Optional[ClientCall]:
        return self.client_calls.get(self.turn_number)

    def available_advice(self) -> List[AdviceOption]:
        """Global options plus any advice specific to the current turn's call."""
        return list(self.advice_options) + list(
            self.per_turn_advice.get(self.turn_number, [])
        )

    def available_documents(self) -> List[Document]:
        """Documents visible at the current turn (available-on-or-before now)."""
        return [d for d in self.documents if d.turn_number <= self.turn_number]
