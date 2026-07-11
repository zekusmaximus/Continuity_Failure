import { describe, expect, it } from "vitest";
import type { TelemetryEventV1 } from "../src/telemetry/events";
import { summarizeTelemetry } from "../src/telemetry/summary";

let sequence = 0;
function event(partial: Record<string, unknown>): TelemetryEventV1 {
  sequence += 1;
  return {
    schema_version: 1,
    event_id: `e-${sequence}`,
    session_id: "s-1",
    occurred_at: "2026-07-11T12:00:00.000Z",
    ...partial,
  } as TelemetryEventV1;
}

// A fixed two-turn journey: phases timed, evidence opened, advice compared,
// the Case File visited, and the record expanded. The summary is asserted
// exactly — this module is pure and deterministic.
const FIXTURE: TelemetryEventV1[] = [
  event({ event_type: "campaign_started", campaign_id: "c1", turn_number: 1 }),
  event({ event_type: "phase_entered", phase: "CALL", campaign_id: "c1", turn_number: 1 }),
  event({
    event_type: "phase_left",
    phase: "CALL",
    elapsed_ms: 4000,
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({ event_type: "phase_entered", phase: "ADVICE", campaign_id: "c1", turn_number: 1 }),
  event({
    event_type: "evidence_opened",
    document_id: "doc_lab",
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "evidence_opened",
    document_id: "doc_lab",
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "evidence_opened",
    document_id: "doc_budget",
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "advice_selected",
    advice_id: "advice_a",
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "advice_selected",
    advice_id: "advice_b",
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "alternative_section_toggled",
    expanded: true,
    alternative_count: 2,
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "alternative_section_toggled",
    expanded: false,
    alternative_count: 2,
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({
    event_type: "phase_left",
    phase: "ADVICE",
    elapsed_ms: 30000,
    campaign_id: "c1",
    turn_number: 1,
  }),
  event({ event_type: "case_file_opened", tab_id: "evidence", campaign_id: "c1", turn_number: 2 }),
  event({ event_type: "case_file_opened", tab_id: "canon", campaign_id: "c1", turn_number: 2 }),
  event({ event_type: "case_file_opened", tab_id: "evidence", campaign_id: "c1", turn_number: 2 }),
  event({
    event_type: "record_detail_toggled",
    detail_kind: "applied_diff_record",
    expanded: true,
    campaign_id: "c1",
    turn_number: 2,
  }),
  event({
    event_type: "record_detail_toggled",
    detail_kind: "applied_diff_record",
    expanded: false,
    campaign_id: "c1",
    turn_number: 2,
  }),
  event({ event_type: "guide_topic_opened", topic_id: "adherence" }),
  event({ event_type: "guide_topic_opened", topic_id: "evidence_freshness" }),
  event({ event_type: "guide_topic_opened", topic_id: "adherence" }),
  event({
    event_type: "advice_selected",
    advice_id: "advice_a",
    campaign_id: "c1",
    turn_number: 2,
  }),
  event({
    event_type: "phase_left",
    phase: "ADVICE",
    elapsed_ms: 12000,
    campaign_id: "c1",
    turn_number: 2,
  }),
  event({
    event_type: "desk_session_ended",
    phase: "CONSEQUENCES",
    campaign_id: "c1",
    turn_number: 2,
  }),
];

describe("summarizeTelemetry", () => {
  it("computes the exact summary from a fixed event fixture", () => {
    expect(summarizeTelemetry(FIXTURE)).toEqual({
      event_count: FIXTURE.length,
      phase_durations: [
        { phase: "CALL", total_ms: 4000, visits: 1 },
        { phase: "ADVICE", total_ms: 42000, visits: 2 },
      ],
      turn_durations: [
        { turn_number: 1, total_ms: 34000 },
        { turn_number: 2, total_ms: 12000 },
      ],
      evidence_opens: [
        { id: "doc_lab", count: 2 },
        { id: "doc_budget", count: 1 },
      ],
      advice_selection_count: 3,
      // Two selections on turn 1 → one change; a single selection on turn 2.
      advice_change_count: 1,
      alternatives_expanded_count: 1,
      case_file_opens: [
        { id: "evidence", count: 2 },
        { id: "canon", count: 1 },
      ],
      record_detail_expansions: 1,
      guide_topics_opened: ["adherence", "evidence_freshness"],
      final_phase: "CONSEQUENCES",
      final_turn_number: 2,
    });
  });

  it("summarizes an empty export without inventing behavior", () => {
    expect(summarizeTelemetry([])).toEqual({
      event_count: 0,
      phase_durations: [],
      turn_durations: [],
      evidence_opens: [],
      advice_selection_count: 0,
      advice_change_count: 0,
      alternatives_expanded_count: 0,
      case_file_opens: [],
      record_detail_expansions: 0,
      guide_topics_opened: [],
      final_phase: null,
      final_turn_number: null,
    });
  });

  it("orders evidence and tab counts deterministically", () => {
    const tied = [
      event({ event_type: "evidence_opened", document_id: "doc_b" }),
      event({ event_type: "evidence_opened", document_id: "doc_a" }),
    ];
    expect(summarizeTelemetry(tied).evidence_opens).toEqual([
      { id: "doc_a", count: 1 },
      { id: "doc_b", count: 1 },
    ]);
  });
});
