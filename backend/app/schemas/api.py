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


class CrisisModel(BaseModel):
    id: str
    name: str
    description: str
    severity: int
    active: bool


class AdviceOptionModel(BaseModel):
    id: str
    label: str
    summary: str
    rationale: str
    tags: List[str]
    effects: Dict[str, int]


class ClientCallModel(BaseModel):
    id: str
    turn: int
    caller: str
    caller_faction_id: str
    summary: str
    known_facts: List[str]
    ask: str
    crisis_id: Optional[str] = None


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


class TurnResultModel(BaseModel):
    turn_number: int
    advice_id: str
    advice_label: str
    decision: NpcDecisionModel
    diffs: List[AppliedDiffModel]
    aftermath_summary: str
    canon_entry: CanonEntryModel
    status_after: str
    failure_reason: Optional[str] = None


class CurrentTurnModel(BaseModel):
    """The package the client needs to render the current turn."""
    summary: CampaignSummaryModel
    world_state: WorldStateModel
    client_call: Optional[ClientCallModel] = None
    advice_options: List[AdviceOptionModel]
    last_turn: Optional[TurnResultModel] = None


class TurnHistoryModel(BaseModel):
    summary: CampaignSummaryModel
    turns: List[TurnResultModel]
    canon: List[CanonEntryModel]


class CampaignCreatedModel(BaseModel):
    id: str
    name: str
    status: str
    turn_number: int
    max_turns: int


class HealthModel(BaseModel):
    status: str
    service: str
    scenario: str
