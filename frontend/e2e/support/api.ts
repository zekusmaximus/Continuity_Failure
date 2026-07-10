import type { APIRequestContext } from "@playwright/test";

import { BACKEND_URL } from "./env";

/**
 * Direct backend access for arranging scenarios and for asserting on server
 * truth rather than on what the UI happens to be rendering. These calls bypass
 * the Vite proxy and talk to FastAPI on its own port.
 */

export interface Summary {
  id: string;
  status: "ACTIVE" | "COMPLETED" | "FAILED";
  turn_number: number;
  max_turns: number;
  failure_reason: string | null;
}

/**
 * The advice option offered on every turn of the Northbridge scenario. Choosing
 * it repeatedly is a deterministic path to a terminal campaign — the engine
 * fails the run on collapsed public order well before the 10-turn window ends.
 */
export const RELENTLESS_OPTION = "full_disclosure";
const memosBySubmission = new Map<string, { id: string; revision: number }>();

export async function createCampaign(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${BACKEND_URL}/api/campaigns`, { data: {} });
  if (!res.ok()) throw new Error(`createCampaign failed: ${res.status()}`);
  return (await res.json()).id as string;
}

export async function getSummary(
  request: APIRequestContext,
  campaignId: string,
): Promise<Summary> {
  const res = await request.get(`${BACKEND_URL}/api/campaigns/${campaignId}/current`);
  if (!res.ok()) throw new Error(`getCurrent failed: ${res.status()}`);
  return (await res.json()).summary as Summary;
}

export async function countTurns(
  request: APIRequestContext,
  campaignId: string,
): Promise<number> {
  const res = await request.get(`${BACKEND_URL}/api/campaigns/${campaignId}/turns`);
  if (!res.ok()) throw new Error(`getTurns failed: ${res.status()}`);
  return ((await res.json()).turns as unknown[]).length;
}

/** Resolve one turn. Returns the HTTP status so callers can assert on refusals. */
export async function submitAdvice(
  request: APIRequestContext,
  campaignId: string,
  opts: { adviceId?: string; expectedTurn: number; idempotencyKey: string },
): Promise<{ status: number; body: Record<string, unknown> }> {
  const adviceId = opts.adviceId ?? RELENTLESS_OPTION;
  const submission = `${campaignId}:${opts.idempotencyKey}`;
  let memo = memosBySubmission.get(submission);
  if (!memo) {
    const created = await request.post(`${BACKEND_URL}/api/campaigns/${campaignId}/memos`, {
      data: {
        creation_mode: "manual",
        advice_id: adviceId,
        name: "E2E advice of record",
        content: "Exact E2E advisory content.",
      },
      failOnStatusCode: false,
    });
    if (created.ok()) {
      const body = await created.json();
      memo = { id: body.id as string, revision: body.revision as number };
      memosBySubmission.set(submission, memo);
    } else {
      memo = { id: `memo_${"0".repeat(32)}`, revision: 1 };
    }
  }
  const res = await request.post(`${BACKEND_URL}/api/campaigns/${campaignId}/advice`, {
    data: {
      advice_id: adviceId,
      expected_turn: opts.expectedTurn,
      idempotency_key: opts.idempotencyKey,
      memo_id: memo.id,
      memo_revision: memo.revision,
    },
    failOnStatusCode: false,
  });
  return { status: res.status(), body: await res.json() };
}

/**
 * Drive a campaign to `COMPLETED` or `FAILED` through the real engine. Nothing
 * is written to SQLite that a player could not have produced by playing.
 */
export async function seedTerminalCampaign(
  request: APIRequestContext,
): Promise<{ campaignId: string; summary: Summary }> {
  const campaignId = await createCampaign(request);
  for (let turn = 0; turn < 12; turn += 1) {
    const summary = await getSummary(request, campaignId);
    if (summary.status !== "ACTIVE") return { campaignId, summary };
    const { status } = await submitAdvice(request, campaignId, {
      expectedTurn: summary.turn_number,
      idempotencyKey: `seed-${campaignId}-${turn}`,
    });
    if (status !== 200) throw new Error(`seed turn ${turn} failed with ${status}`);
  }
  throw new Error("Campaign never reached a terminal status within 12 turns.");
}
