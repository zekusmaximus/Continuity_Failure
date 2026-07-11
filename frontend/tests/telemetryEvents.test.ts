import { describe, expect, it } from "vitest";
import {
  TELEMETRY_EVENT_TYPES,
  TELEMETRY_PHASES,
  TELEMETRY_SCHEMA_VERSION,
  parseTelemetryEvent,
  type TelemetryEventV1,
} from "../src/telemetry/events";
import {
  TELEMETRY_APP_VERSION,
  resetTelemetrySessionForTests,
  stampTelemetryEvent,
  telemetrySessionId,
} from "../src/telemetry/session";
import { PHASE_LABEL } from "../src/domain";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const envelope = {
  schema_version: TELEMETRY_SCHEMA_VERSION,
  event_id: "e-0001",
  session_id: "s-0001",
  occurred_at: "2026-07-11T12:00:00.000Z",
  campaign_id: "campaign-1",
  turn_number: 2,
  phase: "ADVICE",
} as const;

// One sample per vocabulary member. A test below proves this list covers the
// entire closed vocabulary, so "every variant round-trips" stays true as the
// vocabulary evolves.
const SAMPLE_EVENTS: TelemetryEventV1[] = [
  { ...envelope, event_type: "campaign_started" },
  { ...envelope, event_type: "campaign_resumed" },
  { ...envelope, event_type: "campaign_terminal", outcome: "COMPLETED" },
  { ...envelope, event_type: "phase_entered" },
  { ...envelope, event_type: "phase_left", elapsed_ms: 5400 },
  { ...envelope, event_type: "evidence_opened", document_id: "doc_lab_results" },
  { ...envelope, event_type: "evidence_closed", document_id: "doc_lab_results" },
  { ...envelope, event_type: "advice_selected", advice_id: "advice_disclose" },
  {
    ...envelope,
    event_type: "alternative_section_toggled",
    expanded: true,
    alternative_count: 3,
  },
  { ...envelope, event_type: "case_file_opened", tab_id: "evidence" },
  {
    ...envelope,
    event_type: "record_detail_toggled",
    detail_kind: "applied_diff_record",
    expanded: true,
  },
  { ...envelope, event_type: "guide_topic_shown", topic_id: "desk_operating_brief" },
  { ...envelope, event_type: "guide_topic_opened", topic_id: "adherence" },
  { ...envelope, event_type: "review_mode_changed", mode: "guided" },
  { ...envelope, event_type: "variant_selected", variant_id: "hot_summer" },
  { ...envelope, event_type: "desk_session_ended" },
];

// Fields any event may carry, beyond its own vocabulary entry.
const ENVELOPE_KEYS = new Set([
  "schema_version",
  "event_id",
  "session_id",
  "event_type",
  "occurred_at",
  "campaign_id",
  "turn_number",
  "phase",
]);

// Key names that would indicate prose or authoritative content leaking into
// telemetry. None of these may ever appear as a field name on any event.
const FORBIDDEN_KEYS = [
  "content",
  "memo",
  "memo_name",
  "name",
  "title",
  "summary",
  "body",
  "text",
  "prompt",
  "input",
  "output",
  "message",
  "error",
  "markdown",
  "recommendation",
  "rationale",
  "call",
  "payload",
];

// Representative in-game prose. If any of these ever serialize out of a
// telemetry event, the allow-list has been broken.
const SAMPLE_PROSE = [
  "Recommend controlled disclosure of the preliminary contamination data.",
  "The Town Manager narrowed the order to the affected district.",
  "Preliminary lab results indicate coliform exceedances at the intake.",
  "Traceback failed: sqlite3.OperationalError",
];

describe("telemetry event vocabulary", () => {
  it("has one sample per vocabulary member", () => {
    expect(new Set(SAMPLE_EVENTS.map((e) => e.event_type))).toEqual(
      new Set(TELEMETRY_EVENT_TYPES),
    );
    expect(SAMPLE_EVENTS).toHaveLength(TELEMETRY_EVENT_TYPES.length);
  });

  it("round-trips every event variant through JSON and validation", () => {
    for (const event of SAMPLE_EVENTS) {
      const revived = parseTelemetryEvent(JSON.parse(JSON.stringify(event)));
      expect(revived, event.event_type).toEqual(event);
    }
  });

  it("covers every gameplay phase id", () => {
    expect(new Set(TELEMETRY_PHASES)).toEqual(new Set(Object.keys(PHASE_LABEL)));
  });

  it("rejects unknown fields on every event variant", () => {
    for (const event of SAMPLE_EVENTS) {
      expect(
        parseTelemetryEvent({ ...event, memo_content: "drafted text" }),
        event.event_type,
      ).toBeNull();
      expect(
        parseTelemetryEvent({ ...event, payload: { anything: 1 } }),
        event.event_type,
      ).toBeNull();
    }
  });

  it("rejects prose in id fields", () => {
    expect(
      parseTelemetryEvent({
        ...envelope,
        event_type: "evidence_opened",
        document_id: "the memo said we should disclose everything now",
      }),
    ).toBeNull();
    expect(
      parseTelemetryEvent({
        ...envelope,
        event_type: "advice_selected",
        advice_id: SAMPLE_PROSE[0],
      }),
    ).toBeNull();
  });

  it("rejects structurally invalid records", () => {
    expect(parseTelemetryEvent(null)).toBeNull();
    expect(parseTelemetryEvent([])).toBeNull();
    expect(parseTelemetryEvent("phase_entered")).toBeNull();
    expect(parseTelemetryEvent({ ...envelope, event_type: "made_up_event" })).toBeNull();
    expect(
      parseTelemetryEvent({ ...envelope, event_type: "campaign_started", schema_version: 2 }),
    ).toBeNull();
    // Missing required event field.
    expect(parseTelemetryEvent({ ...envelope, event_type: "phase_left" })).toBeNull();
    // Wrong field types.
    expect(
      parseTelemetryEvent({ ...envelope, event_type: "phase_left", elapsed_ms: -5 }),
    ).toBeNull();
    expect(
      parseTelemetryEvent({
        ...envelope,
        event_type: "alternative_section_toggled",
        expanded: "yes",
        alternative_count: 3,
      }),
    ).toBeNull();
    expect(
      parseTelemetryEvent({ ...envelope, event_type: "campaign_terminal", outcome: "WON" }),
    ).toBeNull();
    // Phase-scoped events need the envelope phase.
    const { phase: _phase, ...noPhase } = envelope;
    expect(
      parseTelemetryEvent({ ...noPhase, event_type: "phase_entered" }),
    ).toBeNull();
    // Bad envelope values.
    expect(
      parseTelemetryEvent({
        ...envelope,
        event_type: "campaign_started",
        occurred_at: "not a timestamp",
      }),
    ).toBeNull();
    expect(
      parseTelemetryEvent({ ...envelope, event_type: "campaign_started", turn_number: 1.5 }),
    ).toBeNull();
    expect(
      parseTelemetryEvent({ ...envelope, event_type: "campaign_started", phase: "LOBBY" }),
    ).toBeNull();
  });

  it("serializes no forbidden keys and no sample prose", () => {
    for (const event of SAMPLE_EVENTS) {
      const keys = Object.keys(event);
      for (const key of keys) {
        expect(FORBIDDEN_KEYS, `${event.event_type}.${key}`).not.toContain(key);
      }
      const json = JSON.stringify(event);
      for (const forbidden of FORBIDDEN_KEYS) {
        expect(json).not.toContain(`"${forbidden}":`);
      }
      for (const prose of SAMPLE_PROSE) {
        expect(json).not.toContain(prose);
      }
    }
  });

  it("keeps every non-envelope field a scalar id, number, or boolean", () => {
    for (const event of SAMPLE_EVENTS) {
      for (const [key, value] of Object.entries(event)) {
        if (ENVELOPE_KEYS.has(key)) continue;
        expect(
          ["string", "number", "boolean"].includes(typeof value),
          `${event.event_type}.${key}`,
        ).toBe(true);
        if (typeof value === "string") {
          expect(value.length, `${event.event_type}.${key}`).toBeLessThanOrEqual(80);
          expect(value, `${event.event_type}.${key}`).not.toMatch(/\s/);
        }
      }
    }
  });
});

describe("telemetry stamping", () => {
  it("stamps a complete valid event from an intent plus context", () => {
    resetTelemetrySessionForTests();
    const stamped = stampTelemetryEvent(
      { event_type: "advice_selected", advice_id: "advice_disclose" },
      { campaign_id: "campaign-9", turn_number: 4, phase: "ADVICE" },
      new Date("2026-07-11T15:30:00.000Z"),
    );
    expect(parseTelemetryEvent(stamped)).toEqual(stamped);
    expect(stamped).toMatchObject({
      schema_version: 1,
      event_type: "advice_selected",
      advice_id: "advice_disclose",
      campaign_id: "campaign-9",
      turn_number: 4,
      phase: "ADVICE",
      occurred_at: "2026-07-11T15:30:00.000Z",
    });
    expect(stamped.session_id).toBe(telemetrySessionId());
    expect(stamped.event_id).not.toBe(stamped.session_id);
  });

  it("mints one ephemeral session id per page session", () => {
    resetTelemetrySessionForTests();
    const first = telemetrySessionId();
    expect(telemetrySessionId()).toBe(first);
    resetTelemetrySessionForTests();
    expect(telemetrySessionId()).not.toBe(first);
  });

  it("omits absent context fields instead of writing null", () => {
    const stamped = stampTelemetryEvent(
      { event_type: "variant_selected", variant_id: "hot_summer" },
      { campaign_id: null, turn_number: null, phase: null },
    );
    expect("campaign_id" in stamped).toBe(false);
    expect("turn_number" in stamped).toBe(false);
    expect("phase" in stamped).toBe(false);
    expect(parseTelemetryEvent(stamped)).toEqual(stamped);
  });

  it("keeps the declared app version in sync with package.json", () => {
    // Vitest runs with the frontend directory as its working directory.
    const pkgPath = join(process.cwd(), "package.json");
    const pkg = JSON.parse(readFileSync(pkgPath, "utf8")) as { version: string };
    expect(TELEMETRY_APP_VERSION).toBe(pkg.version);
  });
});
