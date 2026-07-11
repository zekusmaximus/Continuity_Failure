import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import AdvicePhase from "../src/components/AdvicePhase";
import ClientDecisionPhase from "../src/components/ClientDecisionPhase";
import type {
  AdviceOption,
  ClientCall,
  TurnResult,
} from "../src/api/client";

function option(id: string, tags: string[], label: string): AdviceOption {
  return {
    id,
    label,
    summary: `${label} summary`,
    rationale: "because",
    tags,
    effects: { public_trust: 1 },
    type: "CONTROLLED_DISCLOSURE",
    title: "",
    recommendation: `${label} recommendation`,
    expected_benefits: ["a benefit"],
    expected_harms: ["a harm"],
    operational_steps: ["step"],
    legal_risk: 30,
    political_risk: 30,
    operational_risk: 30,
    affected_factions: [],
  };
}

const CALL: ClientCall = {
  id: "call_x",
  turn: 3,
  caller: "Northbridge Hospital",
  caller_faction_id: "hospital",
  summary: "clinical cascade",
  known_facts: [],
  ask: "protect clinical operations",
  crisis_id: null,
  caller_role: "Counsel",
  urgency: "critical",
  time_horizon: "2 days",
  unknown_facts: [],
  immediate_risks: [],
  public_exposure: "private",
  private_pressure: "",
  attached_document_ids: [],
  primary_advice_ids: ["hospital_priority", "mutual_aid"],
  decision_profile: {
    mandate: "Protect clinical operations.",
    priorities: ["hospital_stability"],
    red_line_tags: ["delay"],
    off_brief_tolerance: 35,
  },
};

const OPTIONS: AdviceOption[] = [
  option("hospital_priority", ["hospital_priority"], "Priority water allocation"),
  option("mutual_aid", ["mutual_aid"], "Convene mutual aid"),
  option("contractor_pressure", ["contractor"], "Pressure the contractor"),
  option("delay_disclosure", ["delay"], "Delay disclosure"),
];

function renderAdvice(selected: string | null = null) {
  const onSelect = vi.fn();
  render(
    <AdvicePhase
      options={OPTIONS}
      call={CALL}
      factions={[]}
      selected={selected}
      onSelect={onSelect}
      memo={null}
      memoLoading={false}
      memoSaving={false}
      memoError={null}
      onDraftMemo={vi.fn()}
      onCreateManualMemo={vi.fn()}
      onSaveMemo={vi.fn()}
    />,
  );
  return { onSelect };
}

describe("AdvicePhase call-specific decision space", () => {
  test("splits primary recommendations from strategic alternatives", () => {
    renderAdvice();
    expect(screen.getByText(/Primary recommendations/)).toBeInTheDocument();
    // Two off-brief options collapse behind a labeled alternatives path.
    expect(
      screen.getByText(/Strategic alternatives · off-brief \(2\)/),
    ).toBeInTheDocument();
    // The caller's institutional weighting is surfaced up front.
    expect(screen.getByText(/What the Northbridge Hospital weighs/)).toBeInTheDocument();
  });

  test("shows the off-brief cost and the red-line risk before submission", () => {
    renderAdvice();
    // Ordinary off-brief option carries a legible standing cost.
    expect(
      screen.getByText(/Off-brief — the Northbridge Hospital did not ask for this/),
    ).toBeInTheDocument();
    // The red-line option is called out as a likely outright rejection.
    expect(
      screen.getByText(/crosses a line the Northbridge Hospital has already drawn/),
    ).toBeInTheDocument();
  });

  test("a primary option is directly selectable", async () => {
    const { onSelect } = renderAdvice();
    await userEvent.click(
      screen.getByRole("radio", { name: /Priority water allocation/ }),
    );
    expect(onSelect).toHaveBeenCalledWith("hospital_priority");
  });
});

describe("ClientDecisionPhase explanation payload", () => {
  const result: TurnResult = {
    turn_number: 3,
    advice_id: "delay_disclosure",
    advice_label: "Delay disclosure",
    decision: {
      advice_id: "delay_disclosure",
      decision_type: "REJECTED",
      decider: "Northbridge Hospital",
      rationale: "The Hospital declined.",
      adherence: 0,
      modifications: {},
      deviation: "",
      public_explanation: "",
      private_motive: "",
      resulting_risk: "",
      off_brief: true,
      off_brief_adjustments: { player_reputation: -3 },
      cost_reason: "Red line crossed",
      precedent_adjustments: {},
      precedent_reason: "",
      cited_document_ids: [],
      citation_adjustments: {},
      citation_reason: "",
      explanation: {
        caller: "Northbridge Hospital",
        institutional_mandate: "Protect clinical operations.",
        incentives: ["Privately: secure priority allocation"],
        conflicts: ["Delay crosses a stated red line for the Hospital."],
        adherence_factors: [
          { label: "Red line", detail: "The advice crossed a drawn line.", direction: "decrease" },
        ],
        off_brief: true,
        off_brief_note: "",
        outcome_reason: "The Hospital rejected the advice because it crossed a red line.",
        on_brief_options: ["Priority water allocation", "Convene mutual aid"],
        memory: [],
      },
      memo_id: null,
      memo_revision: null,
    },
    diffs: [],
    aftermath_summary: "rejected",
    canon_entry: {
      id: "c",
      turn_number: 3,
      category: "decision",
      title: "t",
      body: "b",
      source: "Northbridge Hospital",
      classification: "canon",
      public_status: "public",
      involved_factions: [],
      tags: [],
      memo_id: null,
    },
    status_after: "ACTIVE",
    consequence_stack: {
      immediate: [],
      second_order: [],
      faction_reactions: [],
      media_framing: [],
      legal_fallout: [],
      canonized_events: [],
      opened_threads: [],
      escalated_threads: [],
      resolved_threads: [],
    },
    failure_reason: null,
    sent_memo: null,
    consequence_report: { variables: [] },
    faction_shifts: [],
    call_variant_id: null,
  };

  test("renders human-labeled adherence factors, conflicts, and outcome reason", () => {
    render(<ClientDecisionPhase result={result} />);
    expect(screen.getByText(/How adherence was weighed/)).toBeInTheDocument();
    expect(screen.getByText(/Red line/)).toBeInTheDocument();
    expect(screen.getByText(/Delay crosses a stated red line/)).toBeInTheDocument();
    expect(
      screen.getByText(/rejected the advice because it crossed a red line/),
    ).toBeInTheDocument();
    expect(screen.getByText(/On-brief for this call/)).toBeInTheDocument();
  });
});
