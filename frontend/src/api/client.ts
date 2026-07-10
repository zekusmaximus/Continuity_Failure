// Minimal typed client for the Continuity Failure FastAPI backend.
// All requests use same-origin relative URLs; in dev the Vite proxy forwards
// them to the FastAPI server at http://localhost:8000.

export interface Faction {
  id: string;
  name: string;
  description: string;
  posture: string;
  influence: number;
  alignment: string;
  type: string;
  public_position: string;
  private_incentive: string;
  trust_in_player: number;
  risk_tolerance: number;
  current_pressure: number;
  red_lines: string[];
  tags: string[];
}

export interface Crisis {
  id: string;
  name: string;
  description: string;
  severity: number;
  active: boolean;
  type: string;
}

export interface AdviceOption {
  id: string;
  label: string;
  summary: string;
  rationale: string;
  tags: string[];
  effects: Record<string, number>;
  type: string;
  title: string;
  recommendation: string;
  expected_benefits: string[];
  expected_harms: string[];
  operational_steps: string[];
  legal_risk: number;
  political_risk: number;
  operational_risk: number;
  affected_factions: string[];
}

export interface ClientCall {
  id: string;
  turn: number;
  caller: string;
  caller_faction_id: string;
  summary: string;
  known_facts: string[];
  ask: string;
  crisis_id: string | null;
  caller_role: string;
  urgency: string;
  time_horizon: string;
  unknown_facts: string[];
  immediate_risks: string[];
  public_exposure: string;
  private_pressure: string;
  attached_document_ids: string[];
}

export interface DocumentRecord {
  id: string;
  title: string;
  type: string;
  source: string;
  turn_number: number;
  public_status: string;
  reliability: string;
  summary: string;
  content: string;
  tags: string[];
}

export interface OpenThread {
  id: string;
  title: string;
  summary: string;
  turn_opened: number;
  status: string;
  tags: string[];
}

export interface WorldState {
  turn_number: number;
  variables: Record<string, number>;
  factions: Faction[];
  active_crisis: Crisis | null;
  last_verified: string;
}

export interface CampaignSummary {
  id: string;
  name: string;
  scenario_id: string;
  status: "ACTIVE" | "COMPLETED" | "FAILED";
  turn_number: number;
  max_turns: number;
  failure_reason: string | null;
  created_at: string;
}

export interface NpcDecision {
  advice_id: string;
  decision_type: string;
  decider: string;
  rationale: string;
  adherence: number;
  modifications: Record<string, number>;
  deviation: string;
  public_explanation: string;
  private_motive: string;
  resulting_risk: string;
}

export interface AppliedDiff {
  variable: string;
  old_value: number;
  new_value: number;
  delta: number;
  reason: string;
  source_type: string;
}

export interface CanonEntry {
  id: string;
  turn_number: number;
  category: string;
  title: string;
  body: string;
  source: string;
  classification: string;
  public_status: string;
  involved_factions: string[];
  tags: string[];
}

export interface FactionReaction {
  faction_id: string;
  faction_name: string;
  reaction: string;
}

export interface ConsequenceStack {
  immediate: string[];
  second_order: string[];
  faction_reactions: FactionReaction[];
  media_framing: string[];
  legal_fallout: string[];
  canonized_events: string[];
  opened_threads: string[];
}

export interface TurnResult {
  turn_number: number;
  advice_id: string;
  advice_label: string;
  decision: NpcDecision;
  diffs: AppliedDiff[];
  aftermath_summary: string;
  canon_entry: CanonEntry;
  status_after: "ACTIVE" | "COMPLETED" | "FAILED";
  consequence_stack: ConsequenceStack;
  failure_reason: string | null;
}

export interface SystemStatus {
  power: number;
  comms: number;
  data_freshness: number;
  staff_capacity: number;
  ai_available: boolean;
  model_status: string;
}

export interface CurrentTurn {
  summary: CampaignSummary;
  world_state: WorldState;
  client_call: ClientCall | null;
  advice_options: AdviceOption[];
  documents: DocumentRecord[];
  open_threads: OpenThread[];
  system_status: SystemStatus;
  last_turn: TurnResult | null;
}

export interface TurnHistory {
  summary: CampaignSummary;
  turns: TurnResult[];
  canon: CanonEntry[];
  open_threads: OpenThread[];
}

export interface CampaignCreated {
  id: string;
  name: string;
  status: string;
  turn_number: number;
  max_turns: number;
}

export interface Dossier {
  campaign_id: string;
  name: string;
  status: string;
  filename: string;
  markdown: string;
}

export interface Health {
  status: string;
  service: string;
  scenario: string;
}

// --- AI-assist layer (advisory only; never mutates game state) ---
// Mirrors backend/app/schemas/api.py MemoContentModel / MemoDraftModel /
// ModelRunModel. ``status`` is "ok" (model output) or "fallback" (deterministic
// builder); ``source`` is "ai" or "system" — for honest UI labeling.
export interface MemoContent {
  recommendation: string;
  rationale: string;
  operational_steps: string[];
  communications: string;
  likely_opposition: string[];
  second_order_risks: string[];
  fallback_plan: string;
}

export interface MemoDraft {
  status: "ok" | "fallback";
  source: "ai" | "system";
  draft: MemoContent;
}

export interface ModelRun {
  prompt_name: string;
  prompt_version: string;
  model_name: string;
  validation_status: string;
  input_summary: string;
  retry_count: number;
  latency_ms: number | null;
  turn_number: number | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/health"),
  createCampaign: (name?: string) =>
    request<CampaignCreated>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(name ? { name } : {}),
    }),
  getCampaign: (id: string) =>
    request<{ summary: CampaignSummary; world_state: WorldState }>(
      `/api/campaigns/${id}`,
    ),
  getCurrent: (id: string) =>
    request<CurrentTurn>(`/api/campaigns/${id}/current`),
  submitAdvice: (id: string, adviceId: string) =>
    request<TurnResult>(`/api/campaigns/${id}/advice`, {
      method: "POST",
      body: JSON.stringify({ advice_id: adviceId }),
    }),
  getTurns: (id: string) =>
    request<TurnHistory>(`/api/campaigns/${id}/turns`),
  getDossier: (id: string) =>
    request<Dossier>(`/api/campaigns/${id}/dossier`),
  // Advisory only: drafts a memo without advancing the turn or changing state.
  // With AI off (the default) this returns a deterministic fallback memo.
  draftMemo: (id: string, adviceId: string) =>
    request<MemoDraft>(`/api/campaigns/${id}/memo`, {
      method: "POST",
      body: JSON.stringify({ advice_id: adviceId }),
    }),
  // Read-only log of AI model runs recorded for this campaign.
  getModelRuns: (id: string) =>
    request<ModelRun[]>(`/api/campaigns/${id}/model-runs`),
};
