// Telemetry session identity and event stamping — Wave 3 Batch A1.
//
// One ephemeral session id is minted per browser page session and never
// persisted: it groups events within a sitting without identifying the
// player across visits. Stamping is the only place envelope fields are
// produced, so every emitted event shares one construction path.

import {
  TELEMETRY_SCHEMA_VERSION,
  type TelemetryEventV1,
  type TelemetryPhase,
} from "./events";

// Kept in sync with package.json by a unit test rather than a JSON import, so
// the manifest metadata stays a plain compile-time constant.
export const TELEMETRY_APP_VERSION = "0.1.0";

type DistributiveOmit<T, K extends PropertyKey> = T extends unknown
  ? Omit<T, K>
  : never;

/**
 * What a component reports: the event type and its own allow-listed fields.
 * The envelope (schema version, ids, timestamp) is stamped centrally; the
 * campaign/turn/phase context may be supplied by the caller or filled in from
 * the ambient context at stamping time.
 */
export type TelemetryIntent = DistributiveOmit<
  TelemetryEventV1,
  "schema_version" | "event_id" | "session_id" | "occurred_at"
>;

export interface TelemetryContext {
  campaign_id?: string | null;
  turn_number?: number | null;
  phase?: TelemetryPhase | null;
}

function randomId(): string {
  const source = globalThis.crypto;
  if (typeof source?.randomUUID === "function") return source.randomUUID();
  if (typeof source?.getRandomValues === "function") {
    const bytes = new Uint8Array(16);
    source.getRandomValues(bytes);
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  // No Web Crypto at all: still unique within a page session.
  idCounter += 1;
  return `t-${Date.now().toString(36)}-${idCounter.toString(36)}`;
}

let idCounter = 0;
let sessionId: string | null = null;

/** The page session's ephemeral id — minted on first use, never stored. */
export function telemetrySessionId(): string {
  if (sessionId === null) sessionId = randomId();
  return sessionId;
}

/** Test hook: forget the current session id so a new one is minted. */
export function resetTelemetrySessionForTests(): void {
  sessionId = null;
}

/**
 * Build a complete event from a reported intent plus ambient context.
 * Context fields the intent already carries win over the ambient ones.
 */
export function stampTelemetryEvent(
  intent: TelemetryIntent,
  context: TelemetryContext = {},
  occurredAt: Date = new Date(),
): TelemetryEventV1 {
  return {
    schema_version: TELEMETRY_SCHEMA_VERSION,
    event_id: randomId(),
    session_id: telemetrySessionId(),
    occurred_at: occurredAt.toISOString(),
    ...(context.campaign_id ? { campaign_id: context.campaign_id } : {}),
    ...(context.turn_number != null ? { turn_number: context.turn_number } : {}),
    ...(context.phase ? { phase: context.phase } : {}),
    ...intent,
  } as TelemetryEventV1;
}
