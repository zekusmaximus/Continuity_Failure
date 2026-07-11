"""Pydantic API schemas.

These mirror the engine dataclasses so the API layer never leaks engine
internals to clients. Conversion happens via ``dataclasses.asdict`` in the
service layer, so field names here must match the engine models exactly.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_TURN_NUMBER = 1000

PUBLIC_STATUS_PATTERN = r"^(public|private|leaked|sealed|disputed|unknown)$"
RELIABILITY_PATTERN = r"^(high|medium|low|unknown|contested)$"
CAMPAIGN_STATUS_PATTERN = r"^(ACTIVE|COMPLETED|FAILED)$"
DECISION_TYPE_PATTERN = r"^(FOLLOWED|PARTIALLY_FOLLOWED|MODIFIED|DELAYED|REJECTED)$"
SOURCE_TYPE_PATTERN = r"^(advice|npc_modification|ambient|decision|thread|leak)$"
FACT_CLASSIFICATION_PATTERN = r"^(canon|proposed|rejected|rumor|unverified|contradicted)$"
MEMO_ID_PATTERN = r"^memo_[a-f0-9]{32}$"


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FactionAdviceTrustCostModel(BaseModel):
    """Authored trust reaction to advice targeting this faction off the line."""
    advice_tag: str
    delta: int = Field(ge=-20, le=20)
    reason: str


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
    advice_trust_costs: List[FactionAdviceTrustCostModel] = Field(default_factory=list)


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


class CallDecisionProfileModel(BaseModel):
    mandate: str = ""
    priorities: List[str] = Field(default_factory=list)
    red_line_tags: List[str] = Field(default_factory=list)
    off_brief_tolerance: int = Field(default=50, ge=0, le=100)


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
    primary_advice_ids: List[str] = Field(default_factory=list)
    decision_profile: Optional[CallDecisionProfileModel] = None


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
    # True when live feeds are down and this document became available after
    # the last live turn: it did not arrive over a verified feed, so the board
    # labels it instead of contradicting its own last-verified stamp.
    # Presentation-only; authored reliability is untouched.
    unverified_offline: bool = False


class ThreadConditionModel(BaseModel):
    variable: str
    op: str = Field(pattern=r"^(<=|>=)$")
    threshold: int = Field(ge=0, le=100)
    # When set, the condition is faction-scoped: ``variable`` names a numeric
    # faction field evaluated against this faction (engine/conditions.py).
    faction_id: Optional[str] = None


class OpenThreadModel(BaseModel):
    id: str
    title: str
    summary: str
    turn_opened: int = Field(ge=1)
    status: str = Field(default="open", pattern=r"^(open|escalating|stabilizing|resolved)$")
    tags: List[str] = Field(default_factory=list)
    due_turn: Optional[int] = Field(default=None, ge=1)
    escalation_effects: Dict[str, int] = Field(default_factory=dict)
    escalation_note: str = ""
    repeat_every: int = Field(default=0, ge=0)
    resolve_conditions: List[ThreadConditionModel] = Field(default_factory=list)
    resolve_tags: List[str] = Field(default_factory=list)
    resolution_note: str = ""
    turn_resolved: Optional[int] = Field(default=None, ge=1)
    escalation_count: int = Field(default=0, ge=0)


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
    ruleset_version: str
    variant_id: str = ""


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


POWER_ALLOCATION_PATTERN = r"^(MODEL_ACCESS|COMMUNICATIONS|LIVE_DATA)$"


class AdviceRequest(StrictRequestModel):
    """Advisory, non-mutating requests (memo drafting)."""

    advice_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )
    # Provisional auxiliary-power routing for this drafting request (CRITICAL
    # band only). Advisory: the binding allocation ships with the advice.
    powered_subsystem: Optional[str] = Field(
        default=None, pattern=POWER_ALLOCATION_PATTERN
    )


class PowerAllocationRequest(StrictRequestModel):
    """Commit the turn's auxiliary-power allocation (CRITICAL band only).

    This is the pre-decision action: committing COMMUNICATIONS makes the
    caller's disposition readable before advice is composed; committing
    MODEL_ACCESS lifts the drafting gate. Binding for the turn -- any later
    gated action or the advice submission must carry the same subsystem.
    ``expected_turn`` pins the campaign revision the allocation was chosen
    against, exactly like an advice submission.
    """

    allocation: str = Field(pattern=POWER_ALLOCATION_PATTERN)
    expected_turn: int = Field(ge=1, le=MAX_TURN_NUMBER, strict=True)


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
    memo_id: str = Field(pattern=MEMO_ID_PATTERN)
    memo_revision: int = Field(ge=1, le=1000, strict=True)
    # Documents the consultant stakes the memo on (Evidence Board ids). Bounded
    # and validated server-side against the campaign's available documents.
    cited_document_ids: List[str] = Field(
        default_factory=list,
        max_length=3,
    )
    # The binding auxiliary-power allocation for this turn. Required by the
    # service when the desk is CRITICAL, rejected otherwise; joins the
    # idempotency request fingerprint like cited_document_ids.
    powered_subsystem: Optional[str] = Field(
        default=None, pattern=POWER_ALLOCATION_PATTERN
    )

    @field_validator("cited_document_ids")
    @classmethod
    def validate_cited_document_ids(cls, ids: List[str]) -> List[str]:
        import re
        for doc_id in ids:
            if not re.fullmatch(r"[a-z0-9_]{1,64}", doc_id):
                raise ValueError(f"invalid document id: {doc_id!r}")
        if len(set(ids)) != len(ids):
            raise ValueError("cited_document_ids must not repeat")
        return ids


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


class ScenarioVariantModel(BaseModel):
    """One authored seed variant, as presented on the intake screen.

    ``variable_overrides`` stays content-internal: the client picks a variant
    by id; only the engine applies its perturbation.
    """
    id: str
    name: str
    description: str


class CreateCampaignRequest(StrictRequestModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=80,
        pattern=r"^.*\S.*$",
    )
    # An authored seed-variant id ("" / omitted = the baseline starting state).
    variant: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: Optional[str]) -> Optional[str]:
        return name.strip() if name is not None else None


class AdherenceFactorModel(BaseModel):
    label: str
    detail: str
    direction: str = Field(pattern=r"^(increase|decrease|neutral)$")


class DecisionExplanationModel(BaseModel):
    caller: str
    institutional_mandate: str = ""
    incentives: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    adherence_factors: List[AdherenceFactorModel] = Field(default_factory=list)
    off_brief: bool = False
    off_brief_note: str = ""
    outcome_reason: str = ""
    on_brief_options: List[str] = Field(default_factory=list)
    memory: List[str] = Field(default_factory=list)


class FactionShiftModel(BaseModel):
    """One faction-relationship move: which faction, which field, old -> new, why."""
    faction_id: str
    faction_name: str
    field: str = Field(pattern=r"^(trust_in_player|influence|current_pressure)$")
    old_value: int = Field(ge=0, le=100)
    new_value: int = Field(ge=0, le=100)
    delta: int
    reason: str


class PrecedentEntryModel(BaseModel):
    """One emergency precedent on the institutional debt ledger."""
    id: str
    kind: str
    label: str
    turn_recorded: int = Field(ge=1)
    detail: str
    canon_id: str


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
    off_brief: bool = False
    off_brief_adjustments: Dict[str, int] = Field(default_factory=dict)
    cost_reason: str = ""
    precedent_adjustments: Dict[str, int] = Field(default_factory=dict)
    precedent_reason: str = ""
    cited_document_ids: List[str] = Field(default_factory=list)
    citation_adjustments: Dict[str, int] = Field(default_factory=dict)
    citation_reason: str = ""
    explanation: Optional[DecisionExplanationModel] = None
    memo_id: Optional[str] = Field(default=None, pattern=MEMO_ID_PATTERN)
    memo_revision: Optional[int] = Field(default=None, ge=1)

    @field_validator("modifications", "off_brief_adjustments", "precedent_adjustments")
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
    memo_id: Optional[str] = Field(default=None, pattern=MEMO_ID_PATTERN)


class MemoProvenanceModel(BaseModel):
    workflow: str = Field(
        pattern=r"^(manual|deterministic_template|ai_assisted|deterministic_fallback)$"
    )
    model_run_id: Optional[str] = None
    prompt_version: Optional[str] = None
    model_name: Optional[str] = None
    provider: Optional[str] = None
    validation_status: Optional[str] = Field(
        default=None, pattern=r"^(ok|invalid|fallback|error)$"
    )
    fallback_used: bool = False


class MemoRevisionModel(BaseModel):
    revision: int = Field(ge=1)
    name: str
    content: str
    author: str
    source: str = Field(pattern=r"^(player|ai|system)$")
    created_at: str
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class SentMemoSnapshotModel(BaseModel):
    memo_id: str = Field(pattern=MEMO_ID_PATTERN)
    revision: int = Field(ge=1)
    name: str
    content: str
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    sent_at: str
    author: str
    source: str = Field(pattern=r"^(player|ai|system)$")
    classification: str = Field(pattern=FACT_CLASSIFICATION_PATTERN)
    provenance: MemoProvenanceModel


class AdviceMemoModel(BaseModel):
    id: str = Field(pattern=MEMO_ID_PATTERN)
    campaign_id: str
    status: str = Field(pattern=r"^(draft|sent)$")
    name: str
    content: str
    revision: int = Field(ge=1)
    created_at: str
    updated_at: str
    author: str
    source: str = Field(pattern=r"^(player|ai|system)$")
    classification: str = Field(pattern=FACT_CLASSIFICATION_PATTERN)
    provenance: MemoProvenanceModel
    turn_number: Optional[int] = Field(default=None, ge=1)
    call_id: Optional[str] = None
    advice_id: Optional[str] = None
    revisions: List[MemoRevisionModel] = Field(default_factory=list)
    sent_snapshot: Optional[SentMemoSnapshotModel] = None


class CreateMemoRequest(StrictRequestModel):
    creation_mode: Literal["manual", "template", "ai"]
    advice_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=120, pattern=r"^.*\S.*$")
    content: Optional[str] = Field(default=None, min_length=1, max_length=12000)
    # Provisional auxiliary-power routing for an "ai" drafting request
    # (CRITICAL band only). See AdviceRequest.powered_subsystem.
    powered_subsystem: Optional[str] = Field(
        default=None, pattern=POWER_ALLOCATION_PATTERN
    )

    @field_validator("name")
    @classmethod
    def normalize_memo_name(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_creation_mode(self):
        if self.creation_mode == "manual" and not (self.content and self.content.strip()):
            raise ValueError("manual memos require non-blank content")
        if self.creation_mode in ("template", "ai") and self.content is not None:
            raise ValueError("template and AI-assisted memos do not accept supplied content")
        if self.content is not None:
            self.content = self.content.strip()
        return self


class UpdateMemoRequest(StrictRequestModel):
    expected_revision: int = Field(ge=1, le=1000, strict=True)
    name: str = Field(min_length=1, max_length=120, pattern=r"^.*\S.*$")
    content: str = Field(min_length=1, max_length=12000, pattern=r"(?s)^.*\S.*$")

    @field_validator("name", "content")
    @classmethod
    def normalize_memo_text(cls, value: str) -> str:
        return value.strip()


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
    escalated_threads: List[str] = Field(default_factory=list)
    resolved_threads: List[str] = Field(default_factory=list)


class ConsequenceDeltaModel(BaseModel):
    source_type: str = Field(pattern=SOURCE_TYPE_PATTERN)
    delta: int = Field(ge=-100, le=100)
    reason: str
    value_before: int = Field(ge=0, le=100)
    value_after: int = Field(ge=0, le=100)


class AdviceMediationModel(BaseModel):
    proposed_delta: int = Field(ge=-100, le=100)
    adherence: float = Field(ge=0.0, le=1.0)
    expected_delta: int = Field(ge=-100, le=100)
    applied_delta: int = Field(ge=-100, le=100)
    outcome: str = Field(pattern=r"^(applied|reduced|delayed|rejected)$")
    clamped: bool = False


class VariableConsequenceModel(BaseModel):
    variable: str
    label: str
    direction: str = Field(pattern=r"^(higher_is_better|higher_is_worse)$")
    start_value: int = Field(ge=0, le=100)
    final_value: int = Field(ge=0, le=100)
    net_delta: int = Field(ge=-100, le=100)
    deltas: List[ConsequenceDeltaModel] = Field(default_factory=list)
    advice: Optional[AdviceMediationModel] = None


class ConsequenceReportModel(BaseModel):
    variables: List[VariableConsequenceModel] = Field(default_factory=list)


class ConsequenceReferenceModel(BaseModel):
    kind: str = Field(pattern=r"^(diff|thread|precedent|failure|decision)$")
    id: str
    label: str


class ConsequenceLeadModel(BaseModel):
    """Deterministic causal headline + future hook (Wave 3 B1).

    Defaulted empty so idempotent replays and presentations recorded before
    the field existed still validate; freshly resolved turns populate it.
    """
    headline: str = ""
    future_hook: str = ""
    references: List[ConsequenceReferenceModel] = Field(default_factory=list)


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
    sent_memo: Optional[SentMemoSnapshotModel] = None
    # Defaulted so idempotent replays recorded before this field existed still
    # validate; every freshly resolved turn carries the populated report.
    consequence_report: ConsequenceReportModel = Field(default_factory=ConsequenceReportModel)
    faction_shifts: List[FactionShiftModel] = Field(default_factory=list)
    # The authored call variant that was on the line this turn, when one fired
    # (None = the base call). Defaulted so pre-variant replays still validate.
    call_variant_id: Optional[str] = None
    # The auxiliary-power allocation the turn resolved under (CRITICAL band
    # only; None otherwise). Defaulted so earlier replays still validate.
    powered_subsystem: Optional[str] = None
    # Causal headline + future hook (Wave 3 B1). Defaulted so earlier replays
    # and stored presentations still validate with an empty lead.
    consequence_lead: ConsequenceLeadModel = Field(default_factory=ConsequenceLeadModel)


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
    # --- Deterministic degradation (engine/degradation.py) ---
    degradation_band: str = Field(
        default="NOMINAL", pattern=r"^(NOMINAL|STRAINED|DEGRADED|CRITICAL)$"
    )
    live_feeds: bool = True
    last_live_turn: int = Field(default=0, ge=0)
    requires_power_allocation: bool = False
    # The turn's bound auxiliary allocation, when a gated drafting action has
    # already committed it (CRITICAL band only). The submission must match.
    power_commitment: Optional[str] = Field(
        default=None, pattern=r"^(MODEL_ACCESS|COMMUNICATIONS|LIVE_DATA)$"
    )


class CurrentTurnModel(BaseModel):
    """The package the client needs to render the current turn."""
    summary: CampaignSummaryModel
    world_state: WorldStateModel
    client_call: Optional[ClientCallModel] = None
    advice_options: List[AdviceOptionModel]
    documents: List[DocumentModel] = Field(default_factory=list)
    open_threads: List[OpenThreadModel] = Field(default_factory=list)
    debt_ledger: List[PrecedentEntryModel] = Field(default_factory=list)
    system_status: SystemStatusModel
    last_turn: Optional[TurnResultModel] = None
    # Computed presentation line: how the caller opens, from live faction trust.
    caller_disposition: str = ""


class TurnPresentationModel(BaseModel):
    """Unacknowledged resolved turn, frozen until explicit Next Call."""
    campaign_id: str
    turn_number: int = Field(ge=1)
    current_turn: CurrentTurnModel
    result: TurnResultModel


class AcknowledgePresentationRequest(StrictRequestModel):
    turn_number: int = Field(ge=1, le=MAX_TURN_NUMBER, strict=True)


class PresentationAcknowledgedModel(BaseModel):
    campaign_id: str
    turn_number: int = Field(ge=1)
    acknowledged: Literal[True] = True


class TurnHistoryModel(BaseModel):
    summary: CampaignSummaryModel
    turns: List[TurnResultModel]
    canon: List[CanonEntryModel]
    open_threads: List[OpenThreadModel] = Field(default_factory=list)
    debt_ledger: List[PrecedentEntryModel] = Field(default_factory=list)


class CampaignCreatedModel(BaseModel):
    id: str
    name: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    turn_number: int = Field(ge=1)
    max_turns: int = Field(ge=1)


class OutcomeFactorModel(BaseModel):
    label: str
    detail: str
    direction: str = Field(pattern=r"^(increase|decrease|neutral)$")


class OutcomeAxisModel(BaseModel):
    id: str
    label: str
    score: int = Field(ge=0, le=100)
    band: str = Field(pattern=r"^(strong|holding|compromised|failed)$")
    factors: List[OutcomeFactorModel] = Field(default_factory=list)


class OutcomeAssessmentModel(BaseModel):
    axes: List[OutcomeAxisModel]
    verdict_title: str
    verdict_body: List[str] = Field(default_factory=list)
    campaign_status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)


class DossierModel(BaseModel):
    campaign_id: str
    name: str
    status: str = Field(pattern=CAMPAIGN_STATUS_PATTERN)
    filename: str
    markdown: str
    # Structured multi-axis verdict; populated for terminal campaigns only.
    assessment: Optional[OutcomeAssessmentModel] = None


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
    model_run_id: Optional[str] = None
    prompt_version: str = "v1"
    model_name: Optional[str] = None
    provider: Optional[str] = None
    validation_status: Optional[str] = None
    fallback_used: bool = False


class ModelRunModel(BaseModel):
    """Read-only projection of a logged ModelRun for the inspector endpoint."""

    id: str
    prompt_name: str
    prompt_version: str
    model_name: str
    validation_status: str = Field(pattern=r"^(ok|invalid|fallback|error)$")
    input_summary: str
    retry_count: int = Field(ge=0)
    latency_ms: Optional[int] = Field(default=None, ge=0)
    turn_number: Optional[int] = Field(default=None, ge=1)
    provider: Optional[str] = None
