import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import ClientDecisionPhase from "../src/components/ClientDecisionPhase";
import type { TurnResult } from "../src/api/client";

// Wave 3 B2: Client Decision leads with the causal headline above the
// existing decision receipt, and holds the future hook back for the
// Consequences phase so the progressive reveal keeps its meaning.

function result(): TurnResult {
  return {
    turn_number: 2,
    advice_id: "controlled_disclosure",
    advice_label: "Controlled disclosure",
    decision: {
      advice_id: "controlled_disclosure",
      decision_type: "MODIFIED",
      decider: "Northbridge Utilities Authority",
      rationale: "The Authority narrowed the disclosure scope.",
      adherence: 0.6,
      modifications: {},
      deviation: "Scope narrowed",
      public_explanation: "",
      private_motive: "",
      resulting_risk: "",
      off_brief: false,
      off_brief_adjustments: {},
      cost_reason: "",
      precedent_adjustments: {},
      precedent_reason: "",
      cited_document_ids: [],
      citation_adjustments: {},
      citation_reason: "",
      explanation: null,
      memo_id: null,
      memo_revision: null,
    },
    diffs: [],
    aftermath_summary: "The turn resolved.",
    canon_entry: {
      id: "canon_turn_2",
      turn_number: 2,
      category: "decision",
      title: "Turn 2",
      body: "b",
      source: "s",
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
    powered_subsystem: null,
    consequence_lead: {
      headline:
        "You advised Controlled disclosure; the Northbridge Utilities Authority acted, but changed the terms. This turn's largest recorded move: Public Trust rose 3 under the recorded decision.",
      future_hook: "Contractor warning is now open on the record.",
      references: [
        { kind: "decision", id: "controlled_disclosure", label: "Controlled disclosure" },
        { kind: "diff", id: "public_trust", label: "Public Trust" },
        { kind: "thread", id: "th_contractor", label: "Contractor warning" },
      ],
    },
  };
}

describe("ClientDecisionPhase causal lead (Wave 3 B2)", () => {
  test("leads with the headline above the decision receipt", () => {
    render(<ClientDecisionPhase result={result()} />);
    const headline = screen.getByText(/You advised Controlled disclosure;/);
    const receipt = screen.getByText("Northbridge Utilities Authority");
    expect(
      headline.compareDocumentPosition(receipt) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    // The receipt itself is unchanged: decision type, adherence, reason.
    expect(screen.getByText(/adherence 60%/)).toBeInTheDocument();
    expect(
      screen.getByText("The Authority narrowed the disclosure scope."),
    ).toBeInTheDocument();
  });

  test("shows headline references but never the future hook or its references", () => {
    render(<ClientDecisionPhase result={result()} />);
    expect(screen.getByText(/On the record:/)).toHaveTextContent(
      "Controlled disclosure · Public Trust",
    );
    // The hook and its thread reference stay for the Consequences phase.
    expect(
      screen.queryByText(/Contractor warning/),
    ).not.toBeInTheDocument();
  });

  test("renders the pre-lead receipt unchanged for default (older) leads", () => {
    const older = result();
    older.consequence_lead = { headline: "", future_hook: "", references: [] };
    render(<ClientDecisionPhase result={older} />);
    expect(screen.queryByText(/You advised Controlled disclosure;/)).not.toBeInTheDocument();
    expect(screen.queryByText(/On the record:/)).not.toBeInTheDocument();
    expect(screen.getByText(/adherence 60%/)).toBeInTheDocument();
  });
});
