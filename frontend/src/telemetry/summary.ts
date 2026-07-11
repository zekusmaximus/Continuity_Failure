// Pure local summary of one telemetry export — Wave 3 Batch A2.
//
// Everything here is a deterministic fold over already-validated events. The
// summary reports behavior only; it never labels a player "understood",
// "ignored", or "abandoned" — playtest notes interpret, this module counts.

import {
  TELEMETRY_PHASES,
  type TelemetryEventV1,
  type TelemetryPhase,
} from "./events";

export interface PhaseDuration {
  phase: TelemetryPhase;
  total_ms: number;
  visits: number;
}

export interface TurnDuration {
  turn_number: number;
  total_ms: number;
}

export interface CountById {
  id: string;
  count: number;
}

export interface TelemetrySummary {
  event_count: number;
  phase_durations: PhaseDuration[];
  turn_durations: TurnDuration[];
  evidence_opens: CountById[];
  advice_selection_count: number;
  /** Selections beyond the first within each campaign turn. */
  advice_change_count: number;
  alternatives_expanded_count: number;
  case_file_opens: CountById[];
  record_detail_expansions: number;
  guide_topics_opened: string[];
  /** The phase and turn on the last event that carried them — never called "abandonment". */
  final_phase: TelemetryPhase | null;
  final_turn_number: number | null;
}

function countedById(counts: Map<string, number>): CountById[] {
  return [...counts.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id));
}

export function summarizeTelemetry(events: TelemetryEventV1[]): TelemetrySummary {
  const phaseTotals = new Map<TelemetryPhase, { total_ms: number; visits: number }>();
  const turnTotals = new Map<number, number>();
  const evidenceOpens = new Map<string, number>();
  const caseFileOpens = new Map<string, number>();
  const selectionsPerTurn = new Map<string, number>();
  const guideTopics: string[] = [];
  let adviceSelections = 0;
  let alternativesExpanded = 0;
  let recordExpansions = 0;
  let finalPhase: TelemetryPhase | null = null;
  let finalTurn: number | null = null;

  for (const event of events) {
    if (event.phase !== undefined) finalPhase = event.phase;
    if (event.turn_number !== undefined) finalTurn = event.turn_number;

    switch (event.event_type) {
      case "phase_left": {
        // phase is validation-required on phase events.
        const phase = event.phase as TelemetryPhase;
        const bucket = phaseTotals.get(phase) ?? { total_ms: 0, visits: 0 };
        bucket.total_ms += event.elapsed_ms;
        bucket.visits += 1;
        phaseTotals.set(phase, bucket);
        if (event.turn_number !== undefined) {
          turnTotals.set(
            event.turn_number,
            (turnTotals.get(event.turn_number) ?? 0) + event.elapsed_ms,
          );
        }
        break;
      }
      case "evidence_opened":
        evidenceOpens.set(
          event.document_id,
          (evidenceOpens.get(event.document_id) ?? 0) + 1,
        );
        break;
      case "advice_selected": {
        adviceSelections += 1;
        const turnKey = `${event.campaign_id ?? ""}:${event.turn_number ?? ""}`;
        selectionsPerTurn.set(turnKey, (selectionsPerTurn.get(turnKey) ?? 0) + 1);
        break;
      }
      case "alternative_section_toggled":
        if (event.expanded) alternativesExpanded += 1;
        break;
      case "case_file_opened":
        caseFileOpens.set(event.tab_id, (caseFileOpens.get(event.tab_id) ?? 0) + 1);
        break;
      case "record_detail_toggled":
        if (event.expanded) recordExpansions += 1;
        break;
      case "guide_topic_opened":
        if (!guideTopics.includes(event.topic_id)) guideTopics.push(event.topic_id);
        break;
      default:
        break;
    }
  }

  let adviceChanges = 0;
  for (const count of selectionsPerTurn.values()) {
    adviceChanges += Math.max(0, count - 1);
  }

  return {
    event_count: events.length,
    phase_durations: TELEMETRY_PHASES.filter((phase) => phaseTotals.has(phase)).map(
      (phase) => ({ phase, ...(phaseTotals.get(phase) as { total_ms: number; visits: number }) }),
    ),
    turn_durations: [...turnTotals.entries()]
      .map(([turn_number, total_ms]) => ({ turn_number, total_ms }))
      .sort((a, b) => a.turn_number - b.turn_number),
    evidence_opens: countedById(evidenceOpens),
    advice_selection_count: adviceSelections,
    advice_change_count: adviceChanges,
    alternatives_expanded_count: alternativesExpanded,
    case_file_opens: countedById(caseFileOpens),
    record_detail_expansions: recordExpansions,
    guide_topics_opened: guideTopics,
    final_phase: finalPhase,
    final_turn_number: finalTurn,
  };
}
