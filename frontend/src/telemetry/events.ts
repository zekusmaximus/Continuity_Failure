// Local playtest telemetry — Wave 3 Batch A1.
//
// This is the complete, closed vocabulary of playtest events. Telemetry is
// observational and non-authoritative: it lives in this browser only and never
// enters Campaign state, snapshots, fingerprints, prompts, NPC decisions, or
// rule evaluation. There is deliberately no generic payload field — every
// event is a discriminated-union member whose fields are allow-listed scalar
// ids, turn/phase numbers, booleans, and durations. Memo names/content,
// document content, calls, prompts, model input/output, error bodies, and
// free-form player text are not representable here.

export const TELEMETRY_SCHEMA_VERSION = 1 as const;

// Phase ids mirror `domain.Phase`; kept as a local literal list so the
// telemetry vocabulary validates without importing gameplay modules.
export const TELEMETRY_PHASES = [
  "INTRO",
  "CALL",
  "BRIEF",
  "EVIDENCE",
  "REVIEW",
  "ADVICE",
  "CLIENT_DECISION",
  "CONSEQUENCES",
  "ARCHIVE",
  "DOSSIER",
] as const;

export type TelemetryPhase = (typeof TELEMETRY_PHASES)[number];

export const TELEMETRY_EVENT_TYPES = [
  "campaign_started",
  "campaign_resumed",
  "campaign_terminal",
  "phase_entered",
  "phase_left",
  "evidence_opened",
  "evidence_closed",
  "advice_selected",
  "alternative_section_toggled",
  "case_file_opened",
  "record_detail_toggled",
  "guide_topic_shown",
  "guide_topic_opened",
  "review_mode_changed",
  "variant_selected",
  "desk_session_ended",
] as const;

export type TelemetryEventType = (typeof TELEMETRY_EVENT_TYPES)[number];

// Every event carries only this envelope plus its own allow-listed fields.
// Timestamps are wall-clock ISO strings: the data is explicitly
// non-authoritative and never feeds deterministic resolution.
interface TelemetryEnvelopeV1 {
  schema_version: typeof TELEMETRY_SCHEMA_VERSION;
  event_id: string;
  session_id: string;
  occurred_at: string;
  campaign_id?: string;
  turn_number?: number;
  phase?: TelemetryPhase;
}

export type TelemetryEventV1 =
  | (TelemetryEnvelopeV1 & { event_type: "campaign_started" })
  | (TelemetryEnvelopeV1 & { event_type: "campaign_resumed" })
  | (TelemetryEnvelopeV1 & {
      event_type: "campaign_terminal";
      outcome: "COMPLETED" | "FAILED";
    })
  | (TelemetryEnvelopeV1 & { event_type: "phase_entered" })
  | (TelemetryEnvelopeV1 & { event_type: "phase_left"; elapsed_ms: number })
  | (TelemetryEnvelopeV1 & { event_type: "evidence_opened"; document_id: string })
  | (TelemetryEnvelopeV1 & { event_type: "evidence_closed"; document_id: string })
  | (TelemetryEnvelopeV1 & { event_type: "advice_selected"; advice_id: string })
  | (TelemetryEnvelopeV1 & {
      event_type: "alternative_section_toggled";
      expanded: boolean;
      alternative_count: number;
    })
  | (TelemetryEnvelopeV1 & { event_type: "case_file_opened"; tab_id: string })
  | (TelemetryEnvelopeV1 & {
      event_type: "record_detail_toggled";
      detail_kind: string;
      expanded: boolean;
    })
  | (TelemetryEnvelopeV1 & { event_type: "guide_topic_shown"; topic_id: string })
  | (TelemetryEnvelopeV1 & { event_type: "guide_topic_opened"; topic_id: string })
  | (TelemetryEnvelopeV1 & {
      event_type: "review_mode_changed";
      mode: "guided" | "expedited";
    })
  | (TelemetryEnvelopeV1 & { event_type: "variant_selected"; variant_id: string })
  | (TelemetryEnvelopeV1 & { event_type: "desk_session_ended" });

// --- Runtime validation ------------------------------------------------------
// Import/read paths re-validate every record against the same closed
// vocabulary, so hand-edited or stale storage can never smuggle prose or
// unknown fields back in.

type FieldSpec =
  | { kind: "id" }
  | { kind: "duration" }
  | { kind: "count" }
  | { kind: "boolean" }
  | { kind: "enum"; values: readonly string[] };

// Scalar ids are machine identifiers, never sentences: short and whitespace-free.
const ID_PATTERN = /^[A-Za-z0-9_.:-]{1,80}$/;

const EVENT_FIELD_SPECS: Record<TelemetryEventType, Readonly<Record<string, FieldSpec>>> = {
  campaign_started: {},
  campaign_resumed: {},
  campaign_terminal: { outcome: { kind: "enum", values: ["COMPLETED", "FAILED"] } },
  phase_entered: {},
  phase_left: { elapsed_ms: { kind: "duration" } },
  evidence_opened: { document_id: { kind: "id" } },
  evidence_closed: { document_id: { kind: "id" } },
  advice_selected: { advice_id: { kind: "id" } },
  alternative_section_toggled: {
    expanded: { kind: "boolean" },
    alternative_count: { kind: "count" },
  },
  case_file_opened: { tab_id: { kind: "id" } },
  record_detail_toggled: {
    detail_kind: { kind: "id" },
    expanded: { kind: "boolean" },
  },
  guide_topic_shown: { topic_id: { kind: "id" } },
  guide_topic_opened: { topic_id: { kind: "id" } },
  review_mode_changed: { mode: { kind: "enum", values: ["guided", "expedited"] } },
  variant_selected: { variant_id: { kind: "id" } },
  desk_session_ended: {},
};

// Events whose meaning depends on the envelope phase being present.
const PHASE_REQUIRED: ReadonlySet<TelemetryEventType> = new Set([
  "phase_entered",
  "phase_left",
]);

const ENVELOPE_KEYS: ReadonlySet<string> = new Set([
  "schema_version",
  "event_id",
  "session_id",
  "occurred_at",
  "event_type",
  "campaign_id",
  "turn_number",
  "phase",
]);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isId(value: unknown): value is string {
  return typeof value === "string" && ID_PATTERN.test(value);
}

function isEventType(value: unknown): value is TelemetryEventType {
  return (
    typeof value === "string" &&
    (TELEMETRY_EVENT_TYPES as readonly string[]).includes(value)
  );
}

function fieldValid(value: unknown, spec: FieldSpec): boolean {
  switch (spec.kind) {
    case "id":
      return isId(value);
    case "duration":
      return typeof value === "number" && Number.isFinite(value) && value >= 0;
    case "count":
      return typeof value === "number" && Number.isInteger(value) && value >= 0;
    case "boolean":
      return typeof value === "boolean";
    case "enum":
      return typeof value === "string" && spec.values.includes(value);
  }
}

/**
 * Validate one candidate record against the closed vocabulary.
 *
 * Returns a freshly constructed event containing only allow-listed fields, or
 * `null` for anything else: wrong shape, unknown event type, unknown or
 * missing fields, wrong field types, or id values that look like prose.
 */
export function parseTelemetryEvent(value: unknown): TelemetryEventV1 | null {
  if (!isPlainObject(value)) return null;
  if (value.schema_version !== TELEMETRY_SCHEMA_VERSION) return null;
  if (!isEventType(value.event_type)) return null;
  const specs = EVENT_FIELD_SPECS[value.event_type];

  // Closed key set: envelope keys plus this event's own fields, nothing else.
  for (const key of Object.keys(value)) {
    if (!ENVELOPE_KEYS.has(key) && !(key in specs)) return null;
  }

  if (!isId(value.event_id) || !isId(value.session_id)) return null;
  if (
    typeof value.occurred_at !== "string" ||
    value.occurred_at.length > 40 ||
    Number.isNaN(Date.parse(value.occurred_at))
  ) {
    return null;
  }

  if (value.campaign_id !== undefined && !isId(value.campaign_id)) return null;
  if (
    value.turn_number !== undefined &&
    !(
      typeof value.turn_number === "number" &&
      Number.isInteger(value.turn_number) &&
      value.turn_number >= 0
    )
  ) {
    return null;
  }
  if (
    value.phase !== undefined &&
    !(TELEMETRY_PHASES as readonly string[]).includes(value.phase as string)
  ) {
    return null;
  }
  if (PHASE_REQUIRED.has(value.event_type) && value.phase === undefined) return null;

  for (const [field, spec] of Object.entries(specs)) {
    if (!fieldValid(value[field], spec)) return null;
  }

  const event: Record<string, unknown> = {
    schema_version: TELEMETRY_SCHEMA_VERSION,
    event_id: value.event_id,
    session_id: value.session_id,
    event_type: value.event_type,
    occurred_at: value.occurred_at,
  };
  if (value.campaign_id !== undefined) event.campaign_id = value.campaign_id;
  if (value.turn_number !== undefined) event.turn_number = value.turn_number;
  if (value.phase !== undefined) event.phase = value.phase;
  for (const field of Object.keys(specs)) event[field] = value[field];
  return event as unknown as TelemetryEventV1;
}
