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

export interface CallDecisionProfile {
  mandate: string;
  priorities: string[];
  red_line_tags: string[];
  off_brief_tolerance: number;
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
  // Batch 6: the 3-4 on-brief options this call is really asking about; any
  // other known option is a strategic alternative with an off-brief tradeoff.
  primary_advice_ids: string[];
  decision_profile: CallDecisionProfile | null;
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

export interface RecentCampaign extends CampaignSummary {
  updated_at: string;
}

export interface AdherenceFactor {
  label: string;
  detail: string;
  direction: "increase" | "decrease" | "neutral" | string;
}

export interface DecisionExplanation {
  caller: string;
  institutional_mandate: string;
  incentives: string[];
  conflicts: string[];
  adherence_factors: AdherenceFactor[];
  off_brief: boolean;
  off_brief_note: string;
  outcome_reason: string;
  on_brief_options: string[];
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
  off_brief: boolean;
  off_brief_adjustments: Record<string, number>;
  cost_reason: string;
  explanation: DecisionExplanation | null;
  memo_id: string | null;
  memo_revision: number | null;
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
  memo_id: string | null;
}

export interface MemoProvenance {
  workflow: "manual" | "ai_assisted" | "deterministic_fallback";
  model_run_id: string | null;
  prompt_version: string | null;
  model_name: string | null;
  provider: string | null;
  validation_status: string | null;
  fallback_used: boolean;
}

export interface MemoRevision {
  revision: number;
  name: string;
  content: string;
  author: string;
  source: "player" | "ai" | "system";
  created_at: string;
  content_digest: string;
}

export interface SentMemoSnapshot {
  memo_id: string;
  revision: number;
  name: string;
  content: string;
  content_digest: string;
  sent_at: string;
  author: string;
  source: "player" | "ai" | "system";
  classification: string;
  provenance: MemoProvenance;
}

export interface AdviceMemo {
  id: string;
  campaign_id: string;
  status: "draft" | "sent";
  name: string;
  content: string;
  revision: number;
  created_at: string;
  updated_at: string;
  author: string;
  source: "player" | "ai" | "system";
  classification: string;
  provenance: MemoProvenance;
  turn_number: number | null;
  call_id: string | null;
  advice_id: string | null;
  revisions: MemoRevision[];
  sent_snapshot: SentMemoSnapshot | null;
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
  sent_memo: SentMemoSnapshot | null;
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
  model_run_id: string | null;
  prompt_version: string;
  model_name: string | null;
  provider: string | null;
  validation_status: string | null;
  fallback_used: boolean;
}

export interface ModelRun {
  id: string;
  prompt_name: string;
  prompt_version: string;
  model_name: string;
  validation_status: string;
  input_summary: string;
  retry_count: number;
  latency_ms: number | null;
  turn_number: number | null;
  provider: string | null;
}

// --- Errors -----------------------------------------------------------------
// The backend returns `{"detail": {error, message, request_id, ...}}` for every
// failure. `code` is the stable machine-readable discriminator; `message` is
// already player-safe prose and never contains internals.

export type ApiErrorCode =
  | "campaign_not_found"
  | "campaign_terminal"
  | "stale_turn"
  | "idempotency_key_conflict"
  | "unknown_advice_option"
  | "memo_not_found"
  | "stale_memo_revision"
  | "memo_immutable"
  | "memo_advice_mismatch"
  | "corrupt_record"
  | "network_error"
  | "unexpected_error";

export class ApiError extends Error {
  readonly code: ApiErrorCode | string;
  readonly status: number;
  readonly requestId: string | null;
  readonly expectedTurn: number | null;
  readonly currentTurn: number | null;

  constructor(init: {
    code: string;
    message: string;
    status: number;
    requestId?: string | null;
    expectedTurn?: number | null;
    currentTurn?: number | null;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.code = init.code;
    this.status = init.status;
    this.requestId = init.requestId ?? null;
    this.expectedTurn = init.expectedTurn ?? null;
    this.currentTurn = init.currentTurn ?? null;
  }
}

// `status === 0` marks a transport failure: the request may or may not have
// reached the backend, which is exactly why retries must reuse the same key.
const NETWORK_STATUS = 0;
const RETRY_DELAYS_MS = [250, 750];

function isRetriable(error: ApiError): boolean {
  return (
    error.status === NETWORK_STATUS ||
    error.status === 408 ||
    error.status === 429 ||
    error.status >= 500
  );
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Distinguishes keys minted in the same millisecond when the last-resort branch
// below is the only one available. Two submissions must never share a key.
let keyCounter = 0;

/**
 * Mint one idempotency key per deliberate user submission.
 *
 * Reuse it for every transport retry of that submission so a lost response can
 * never resolve a second turn. A new submission must call this again.
 *
 * `randomUUID` needs a secure context; `getRandomValues` does not, so it covers
 * plain-HTTP dev. The final branch runs only without Web Crypto entirely, and
 * still cannot collide: the counter makes it unique within a page session.
 */
export function newIdempotencyKey(): string {
  const source = globalThis.crypto;
  if (typeof source?.randomUUID === "function") return source.randomUUID();
  if (typeof source?.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    source.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  keyCounter += 1;
  const drift = Math.random().toString(36).slice(2).padEnd(8, "0").slice(0, 8);
  return `k-${Date.now().toString(36)}-${keyCounter.toString(36)}-${drift}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError({
      code: "network_error",
      message:
        "The workstation could not reach the backend. Check the connection and retry.",
      status: NETWORK_STATUS,
    });
  }

  if (!res.ok) {
    const requestId = res.headers.get("X-Request-ID");
    let detail: Record<string, unknown> | null = null;
    try {
      const body = await res.json();
      if (body?.detail && typeof body.detail === "object") detail = body.detail;
      else if (typeof body?.detail === "string") detail = { message: body.detail };
    } catch {
      /* fall through to the status-line default */
    }
    throw new ApiError({
      code: (detail?.error as string) ?? "unexpected_error",
      message:
        (detail?.message as string) ?? `${res.status} ${res.statusText}`,
      status: res.status,
      requestId: (detail?.request_id as string) ?? requestId,
      expectedTurn: (detail?.expected_turn as number) ?? null,
      currentTurn: (detail?.current_turn as number) ?? null,
    });
  }

  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}

/**
 * Retry only transport-level failures, never a decided answer.
 *
 * A 4xx is the backend's verdict on this exact request and must not be
 * retried. The request body is byte-identical across attempts, so the
 * idempotency key is reused and the backend replays rather than re-resolves.
 */
async function requestWithRetry<T>(path: string, init: RequestInit): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      return await request<T>(path, init);
    } catch (error) {
      const exhausted = attempt >= RETRY_DELAYS_MS.length;
      if (!(error instanceof ApiError) || !isRetriable(error) || exhausted) throw error;
      await sleep(RETRY_DELAYS_MS[attempt]);
    }
  }
}

export const api = {
  health: () => request<Health>("/health"),
  createCampaign: (name?: string) =>
    request<CampaignCreated>("/api/campaigns", {
      method: "POST",
      body: JSON.stringify(name ? { name } : {}),
    }),
  listRecentCampaigns: (limit = 5) =>
    request<RecentCampaign[]>(`/api/campaigns?limit=${limit}`),
  getCampaign: (id: string) =>
    request<{ summary: CampaignSummary; world_state: WorldState }>(
      `/api/campaigns/${id}`,
    ),
  getCurrent: (id: string) =>
    request<CurrentTurn>(`/api/campaigns/${id}/current`),
  /**
   * Resolve one turn. `expectedTurn` is the revision this submission was
   * composed against; `idempotencyKey` must come from `newIdempotencyKey()`
   * once per deliberate submission and is reused across transport retries.
   */
  submitAdvice: (
    id: string,
    adviceId: string,
    expectedTurn: number,
    idempotencyKey: string,
    memoId: string,
    memoRevision: number,
  ) =>
    requestWithRetry<TurnResult>(`/api/campaigns/${id}/advice`, {
      method: "POST",
      body: JSON.stringify({
        advice_id: adviceId,
        expected_turn: expectedTurn,
        idempotency_key: idempotencyKey,
        memo_id: memoId,
        memo_revision: memoRevision,
      }),
    }),
  getTurns: (id: string) =>
    request<TurnHistory>(`/api/campaigns/${id}/turns`),
  getDossier: (id: string) =>
    request<Dossier>(`/api/campaigns/${id}/dossier`),
  getMemos: (id: string) =>
    request<AdviceMemo[]>(`/api/campaigns/${id}/memos`),
  createMemo: (
    id: string,
    payload: {
      creation_mode: "manual" | "ai";
      advice_id: string;
      name: string;
      content?: string;
    },
  ) =>
    request<AdviceMemo>(`/api/campaigns/${id}/memos`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateMemo: (
    id: string,
    memoId: string,
    payload: { expected_revision: number; name: string; content: string },
  ) =>
    request<AdviceMemo>(`/api/campaigns/${id}/memos/${memoId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
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
