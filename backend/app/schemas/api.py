"""Pydantic API schemas.

These mirror the engine dataclasses so the API layer never leaks engine
internals to clients. Conversion happens via ``dataclasses.asdict`` in the
service layer, so field names here must match the engine models exactly.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


MAX_TURN_NUMBER = 1000

PUBLIC_STATUS_PATTERN = r"^(public|private|leaked|sealed|disputed|unknown)$"
RELIABILITY_PATTERN = r"^(high|medium|low|unknown|contested)$"
CAMPAIGN_STATUS_PATTERN = r"^(ACTIVE|COMPLETED|FAILED)$"
DECISION_TYPE_PATTERN = r"^(FOLLOWED|PARTIALLY_FOLLOWED|MODIFIED|DELAYED|REJECTED)$"
SOURCE_TYPE_PATTERN = r"^(advice|npc_modification|ambient|decision)$"
FACT_CLASSIFICATION_PATTERN = r"^(canon|proposed|rejected|rumor|unverified|contradicted)$"


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactionModel(BaseModel):
    id: str
    name: str
    description: str
    posture: str
    influence: int = Field(ge=0, le=100)
    alignment: str = Field(pattern=r"^(authority|opposition|neutral|service)$")
    type: str = "AGENCY"
    public_position: str = ""
    private_incentive: str = ""
    trust_in_player: int = Field(default=50, ge=0, le=100)
    risk_tolerance: int = Field(default=40, ge=0, le=100)
    current_pressure: int = Field(default=30, ge=0, le=100)
    red_lines: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class CrisisModel(BaseModel):
    id: str
    name: str
    description: str
    severity: int = Field(ge=0, le=100)
    active: bool
    type: str = "WATER_FAILURE"


class AdviceOptionModel(BaseModel):
    id: str
    label: str
    summary: str
    rationale: str
    tags: List[str]
    effects: Dict[str, int]
    type: str = "CONTROLLED_DISCLOSURE"
    title: str = ""
    recommendation: str = ""
    expected_benefits: List[str] = Field(default_factory=list)
    expected_harms: List[str] = Field(default_factory=list)
    operational_steps: List[str] = Field(default_factory=list)
    legal_risk: int = Field(default=30, ge=0, le=100)
    political_risk: int = Field(default=30, ge=0, le=100)
    operational_risk: int = Field(default=30, ge=0, le=100)
    affected_factions: List[str] = Field(default_factory=list)

    @field_validator("effects")
    @classmethod
    def validate_effect_ranges(cls, effects: Dict[str, int]) -> Dict[str, int]:
        if any(delta < -100 or delta > 100 for delta in effects.values()):
            raise ValueError("advice effects must stay within -100..100")
        return effects


class ClientCallModel(BaseModel):
    id: str
    turn: int = Field(ge=1)
    caller: str
    caller_faction_id: str
    summary: str
    known_facts: List[str]
    ask: str
    crisis_id: Optional[str] = None
    caller_role: str = ""
    urgency: str = Field(default="high", pattern=r"^(low|elevated|high|critical)$")
    time_horizon: str = ""
    unknown_facts: List[str] = Field(default_factory=list)
    immediate_risks: List[str] = Field(default_factory=list)
    public_exposure: str = Field(default="private", pattern=PUBLIC_STATUS_PATTERN)
    private_pressure: str = ""
    attached_document_ids: List[str] = Field(default_factory=list)


class DocumentModel(BaseModel):
    id: str
    title: str
    type: str
    source: str
    turn_number: int = Field(ge=1)
    public_status: str = Field(default="private", pattern=PUBLIC_STATUS_PATTERN)
    reliability: str = Field(default="medium", pattern=RELIABILITY_PATTERN)
    summary: str = ""
    content: str = ""
    tags: List[str] = Field(default_factory=list)


class OpenThreadModel(BaseModel):
    id: str
    title: str
    summary: str
    turn_opened: int = Field(ge=1)
    status: str = Field(default="open", pattern=r"^(open|escalating|stabilizing|resolved)$")
    tags: List[str] = Field(default_factory=list)


class WorldStateModel(BaseModel):
    turn_number: int = Field(ge=1)
    variables: Dict[str, int]
    factions: List[FactionModel]
    active_crisis: Optional[CrisisModel] = None
    last_verified: str

    @field_validator("variables")
    @classmethod
    def validate_variable_ranges(cls, variables: Dict[str, int]) -> Dict[str, int]:
        if any(value < 0 or value > 100 for value in variables.values()):
            raise ValueError("world-state variables must stay within 0..100")
        return variables


class CampaignSummaryModel(BaseModel):
    id: str
    name: str
    scenario_id: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    turn_number: int = Field(ge=1)
    max_turns: int = Field(ge=1)
    failure_reason: Optional[str] = None
    created_at: str


class CampaignModel(BaseModel):
    """Full campaign summary plus the live world state."""
    summary: CampaignSummaryModel
    world_state: WorldStateModel


class RecentCampaignModel(BaseModel):
    """Minimal metadata projection for the resume screen."""
    id: str
    name: str
    scenario_id: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    turn_number: int = Field(ge=1)
    max_turns: int = Field(ge=1)
    failure_reason: Optional[str] = None
    created_at: str
    updated_at: str


class AdviceRequest(StrictRequestModel):
    """Advisory, non-mutating requests (memo drafting)."""

    advice_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )


class AdviceSubmissionRequest(StrictRequestModel):
    """A turn-resolution request: what to do, to which revision, exactly once.

    ``expected_turn`` is the campaign revision the client believes is current;
    resolving against any other revision is a conflict rather than an overwrite.
    ``idempotency_key`` is minted once per deliberate submission and reused for
    transport retries, so a retried request never resolves a second turn.
    """

    advice_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )
    expected_turn: int = Field(ge=1, le=MAX_TURN_NUMBER)
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )


class ApiErrorDetail(BaseModel):
    """Stable, internals-free error body: ``{"detail": ApiErrorDetail}``.

    ``error`` is a machine-readable code the frontend switches on; ``message``
    is player-safe prose. No stack traces, SQL, paths, or model output.
    """

    error: str
    message: str
    request_id: Optional[str] = None
    campaign_id: Optional[str] = None
    expected_turn: Optional[int] = None
    current_turn: Optional[int] = None


class ApiErrorModel(BaseModel):
    detail: ApiErrorDetail


class CreateCampaignRequest(StrictRequestModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^.*\S.*$",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: Optional[str]) -> Optional[str]:
        return name.strip() if name is not None else None


class NpcDecisionModel(BaseModel):
    advice_id: str
    decision_type: str = Field(pattern=DECISION_TYPE_PATTERN)
    decider: str
    rationale: str
    adherence: float = Field(ge=0.0, le=1.0)
    modifications: Dict[str, int] = Field(default_factory=dict)
    deviation: str = ""
    public_explanation: str = ""
    private_motive: str = ""
    resulting_risk: str = ""

    @field_validator("modifications")
    @classmethod
    def validate_modification_ranges(
        cls, modifications: Dict[str, int]
    ) -> Dict[str, int]:
        if any(delta < -100 or delta > 100 for delta in modifications.values()):
            raise ValueError("NPC modifications must stay within -100..100")
        return modifications


class AppliedDiffModel(BaseModel):
    variable: str
    old_value: int = Field(ge=0, le=100)
    new_value: int = Field(ge=0, le=100)
    delta: int = Field(ge=-100, le=100)
    reason: str
    source_type: str = Field(pattern=SOURCE_TYPE_PATTERN)


class CanonEntryModel(BaseModel):
    id: str
    turn_number: int = Field(ge=1)
    category: str
    title: str
    body: str
    source: str
    classification: str = Field(pattern=FACT_CLASSIFICATION_PATTERN)
    public_status: str = Field(default="public", pattern=PUBLIC_STATUS_PATTERN)
    involved_factions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class FactionReactionModel(BaseModel):
    faction_id: str
    faction_name: str
    reaction: str


class ConsequenceStackModel(BaseModel):
    immediate: List[str] = Field(default_factory=list)
    second_order: List[str] = Field(default_factory=list)
    faction_reactions: List[FactionReactionModel] = Field(default_factory=list)
    media_framing: List[str] = Field(default_factory=list)
    legal_fallout: List[str] = Field(default_factory=list)
    canonized_events: List[str] = Field(default_factory=list)
    opened_threads: List[str] = Field(default_factory=list)


class TurnResultModel(BaseModel):
    turn_number: int = Field(ge=1)
    advice_id: str
    advice_label: str
    decision: NpcDecisionModel
    diffs: List[AppliedDiffModel]
    aftermath_summary: str
    canon_entry: CanonEntryModel
    status_after: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    consequence_stack: ConsequenceStackModel = Field(default_factory=ConsequenceStackModel)
    failure_reason: Optional[str] = None


class SystemStatusModel(BaseModel):
    """Diegetic system/infrastructure status read off world state.

    The infrastructure metrics (power/comms/data_freshness/staff) are derived
    deterministically from world state. ``ai_available`` reflects whether a live
    model provider is actually configured (``settings.ai_live``): the AI-assist
    layer is present and reachable either way, but when AI is off (the default)
    the memo drafter returns a deterministic fallback and ``ai_available`` is
    False so the workstation indicator stays honest.
    """
    power: int = Field(ge=0, le=100)
    comms: int = Field(ge=0, le=100)
    data_freshness: int = Field(ge=0, le=100)
    staff_capacity: int = Field(ge=0, le=100)
    ai_available: bool = False
    model_status: str = "AI assist present — off by default (returns system drafts)"


class CurrentTurnModel(BaseModel):
    """The package the client needs to render the current turn."""
    summary: CampaignSummaryModel
    world_state: WorldStateModel
    client_call: Optional[ClientCallModel] = None
    advice_options: List[AdviceOptionModel]
    documents: List[DocumentModel] = Field(default_factory=list)
    open_threads: List[OpenThreadModel] = Field(default_factory=list)
    system_status: SystemStatusModel
    last_turn: Optional[TurnResultModel] = None


class TurnHistoryModel(BaseModel):
    summary: CampaignSummaryModel
    turns: List[TurnResultModel]
    canon: List[CanonEntryModel]
    open_threads: List[OpenThreadModel] = Field(default_factory=list)


class CampaignCreatedModel(BaseModel):
    id: str
    name: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    turn_number: int = Field(ge=1)
    max_turns: int = Field(ge=1)


class DossierModel(BaseModel):
    campaign_id: str
    name: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    filename: str
    markdown: str


class HealthModel(BaseModel):
    status: str
    service: str
    scenario: str


# --- AI-assist layer (advisory only; never mutates game state) ---


class MemoContentModel(BaseModel):
    recommendation: str
    rationale: str
    operational_steps: List[str]
    communications: str
    likely_opposition: List[str]
    second_order_risks: List[str]
    fallback_plan: str


class MemoDraftModel(BaseModel):
    # ``status``: "ok" (model produced it) or "fallback" (deterministic builder).
    # ``source``: "ai" or "system" — for honest UI labeling.
    status: str = Field(pattern=r"^(ok|fallback)$")
    source: str = Field(pattern=r"^(ai|system)$")
    draft: MemoContentModel


class ModelRunModel(BaseModel):
    """Read-only projection of a logged ModelRun for the inspector endpoint."""

    prompt_name: str
    prompt_version: str
    model_name: str
    validation_status: str = Field(pattern=r"^(ok|invalid|fallback|error)$")
    input_summary: str
    retry_count: int = Field(ge=0)
    latency_ms: Optional[int] = Field(default=None, ge=0)
    turn_number: Optional[int] = Field(default=None, ge=1)
