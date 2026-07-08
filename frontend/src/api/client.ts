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
}

export interface Crisis {
  id: string;
  name: string;
  description: string;
  severity: number;
  active: boolean;
}

export interface AdviceOption {
  id: string;
  label: string;
  summary: string;
  rationale: string;
  tags: string[];
  effects: Record<string, number>;
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
  failure_reason: string | null;
}

export interface CurrentTurn {
  summary: CampaignSummary;
  world_state: WorldState;
  client_call: ClientCall | null;
  advice_options: AdviceOption[];
  last_turn: TurnResult | null;
}

export interface TurnHistory {
  summary: CampaignSummary;
  turns: TurnResult[];
  canon: CanonEntry[];
}

export interface CampaignCreated {
  id: string;
  name: string;
  status: string;
  turn_number: number;
  max_turns: number;
}

export interface Health {
  status: string;
  service: string;
  scenario: string;
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
};
