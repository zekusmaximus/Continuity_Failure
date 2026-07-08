"""Pydantic API schemas.

These mirror the engine dataclasses so the API layer never leaks engine
internals to clients. Conversion happens via ``dataclasses.asdict`` in the
service layer, so field names here must match the engine models exactly.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FactionModel(BaseModel):
    id: str
    name: str
    description: str
    posture: str
    influence: int
    alignment: str
    type: str = "AGENCY"
    public_position: str = ""
    private_incentive: str = ""
    trust_in_player: int = 50
    risk_tolerance: int = 40
    current_pressure: int = 30
    red_lines: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class CrisisModel(BaseModel):
    id: str
    name: str
    description: str
    severity: int
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
    legal_risk: int = 30
    political_risk: int = 30
    operational_risk: int = 30
    affected_factions: List[str] = Field(default_factory=list)


class ClientCallModel(BaseModel):
    id: str
    turn: int
    caller: str
    caller_faction_id: str
    summary: str
    known_facts: List[str]
    ask: str
    crisis_id: Optional[str] = None
    caller_role: str = ""
    urgency: str = "high"
    time_horizon: str = ""
    unknown_facts: List[str] = Field(default_factory=list)
    immediate_risks: List[str] = Field(default_factory=list)
    public_exposure: str = "private"
    private_pressure: str = ""
    attached_document_ids: List[str] = Field(default_factory=list)


class DocumentModel(BaseModel):
    id: str
    title: str
    type: str
    source: str
    turn_number: int
    public_status: str = "private"
    reliability: str = "medium"
    summary: str = ""
    content: str = ""
    tags: List[str] = Field(default_factory=list)


class OpenThreadModel(BaseModel):
    id: str
    title: str
    summary: str
    turn_opened: int
    status: str = "open"
    tags: List[str] = Field(default_factory=list)


class WorldStateModel(BaseModel):
    turn_number: int
    variables: Dict[str, int]
    factions: List[FactionModel]
    active_crisis: Optional[CrisisModel] = None
    last_verified: str


class CampaignSummaryModel(BaseModel):
    id: str
    name: str
    scenario_id: str
    status: str
    turn_number: int
    max_turns: int
    failure_reason: Optional[str] = None
    created_at: str


class CampaignModel(BaseModel):
    """Full campaign summary plus the live world state."""
    summary: CampaignSummaryModel
    world_state: WorldStateModel


class AdviceRequest(BaseModel):
    advice_id: str


class CreateCampaignRequest(BaseModel):
    name: Optional[str] = None


class NpcDecisionModel(BaseModel):
    advice_id: str
    decision_type: str
    decider: str
    rationale: str
    adherence: float
    modifications: Dict[str, int] = Field(default_factory=dict)
    deviation: str = ""
    public_explanation: str = ""
    private_motive: str = ""
    resulting_risk: str = ""


class AppliedDiffModel(BaseModel):
    variable: str
    old_value: int
    new_value: int
    delta: int
    reason: str
    source_type: str


class CanonEntryModel(BaseModel):
    id: str
    turn_number: int
    category: str
    title: str
    body: str
    source: str
    classification: str
    public_status: str = "public"
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
    turn_number: int
    advice_id: str
    advice_label: str
    decision: NpcDecisionModel
    diffs: List[AppliedDiffModel]
    aftermath_summary: str
    canon_entry: CanonEntryModel
    status_after: str
    consequence_stack: ConsequenceStackModel = Field(default_factory=ConsequenceStackModel)
    failure_reason: Optional[str] = None


class SystemStatusModel(BaseModel):
    """Diegetic system/infrastructure status read off world state.

    Deterministic only. ``ai_available`` is always False in this build -- the
    indicator exists for the workstation visual direction, not to fake output.
    """
    power: int
    comms: int
    data_freshness: int
    staff_capacity: int
    ai_available: bool = False
    model_status: str = "AI systems unavailable in current build"


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
    status: str
    turn_number: int
    max_turns: int


class DossierModel(BaseModel):
    campaign_id: str
    name: str
    status: str
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
    status: str
    source: str
    draft: MemoContentModel


class ModelRunModel(BaseModel):
    """Read-only projection of a logged ModelRun for the inspector endpoint."""

    prompt_name: str
    prompt_version: str
    model_name: str
    validation_status: str
    input_summary: str
    retry_count: int
    latency_ms: Optional[int]
    turn_number: Optional[int]
