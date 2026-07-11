import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import ConsequencesPhase from "../src/components/ConsequencesPhase";
import type {
  ConsequenceReport,
  TurnResult,
  VariableConsequence,
} from "../src/api/client";

// The component must only FORMAT the server's report, never recompute it, so
// these fixtures deliberately carry exact server-side numbers to assert on.

function baseResult(report: ConsequenceReport, diffs: TurnResult["diffs"] = []): TurnResult {
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
      modifications: { media_pressure: 2 },
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
      explanation: {
        caller: "Northbridge Utilities Authority",
        institutional_mandate: "Keep the system running.",
        incentives: [],
        conflicts: [],
        adherence_factors: [],
        off_brief: false,
        off_brief_note: "",
        outcome_reason:
          "The Authority modified the advice to protect contractor relations.",
        on_brief_options: [],
        memory: [],
      },
      memo_id: "memo_1",
      memo_revision: 2,
    },
    diffs,
    aftermath_summary: "The turn resolved.",
    canon_entry: {
      id: "c",
      turn_number: 2,
      category: "decision",
      title: "Turn 2",
      body: "b",
      source: "Northbridge Utilities Authority",
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
    sent_memo: {
      memo_id: "memo_1",
      revision: 2,
      name: "Advisory memo — disclosure",
      content: "Recommend controlled disclosure.",
      content_digest: "a".repeat(64),
      sent_at: "2026-07-10T00:00:00Z",
      author: "Consultant",
      source: "player",
      classification: "proposed",
      provenance: {
        workflow: "manual",
        model_run_id: null,
        prompt_version: null,
        model_name: null,
        provider: null,
        validation_status: null,
        fallback_used: false,
      },
    },
    consequence_report: report,
    faction_shifts: [],
    call_variant_id: null,
    powered_subsystem: null,
  };
}

const TRUST: VariableConsequence = {
  variable: "public_trust",
  label: "Public Trust",
  direction: "higher_is_better",
  start_value: 50,
  final_value: 53,
  net_delta: 3,
  deltas: [
    {
      source_type: "advice",
      delta: 5,
      reason: "Advice — Controlled disclosure",
      value_before: 50,
      value_after: 55,
    },
    {
      source_type: "npc_modification",
      delta: -2,
      reason: "NPC modification (MODIFIED)",
      value_before: 55,
      value_after: 53,
    },
  ],
  advice: {
    proposed_delta: 8,
    adherence: 0.6,
    expected_delta: 5,
    applied_delta: 5,
    outcome: "reduced",
    clamped: false,
  },
};

const LEGAL: VariableConsequence = {
  variable: "legal_exposure",
  label: "Legal Exposure",
  direction: "higher_is_worse",
  start_value: 30,
  final_value: 32,
  net_delta: 2,
  deltas: [
    {
      source_type: "ambient",
      delta: 2,
      reason: "Ambient crisis pressure",
      value_before: 30,
      value_after: 32,
    },
  ],
  advice: null,
};

const REJECTED_ORDER: VariableConsequence = {
  variable: "public_order",
  label: "Public Order",
  direction: "higher_is_better",
  start_value: 60,
  final_value: 60,
  net_delta: 0,
  deltas: [],
  advice: {
    proposed_delta: 6,
    adherence: 0,
    expected_delta: 0,
    applied_delta: 0,
    outcome: "rejected",
    clamped: false,
  },
};

describe("ConsequencesPhase causal waterfall", () => {
  test("renders start → attributed deltas → final exactly as the server reports", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [TRUST, LEGAL] })} />);

    const trust = screen.getByText("Public Trust").closest("li")!;
    // Start → final and the net verdict, with a text cue (not color-only).
    expect(within(trust).getByText(/50/)).toBeInTheDocument();
    expect(within(trust).getByText(/\+3 improved/)).toBeInTheDocument();
    expect(within(trust).getByText("higher is better")).toBeInTheDocument();
    // Both attributed steps with human source labels and running values.
    expect(within(trust).getByText("Your advice")).toBeInTheDocument();
    expect(within(trust).getByText("+5")).toBeInTheDocument();
    expect(within(trust).getByText("Client action")).toBeInTheDocument();
    expect(within(trust).getByText("-2")).toBeInTheDocument();
    expect(within(trust).getByText(/→ 55/)).toBeInTheDocument();
    expect(within(trust).getByText(/→ 53/)).toBeInTheDocument();
  });

  test("direction semantics stay correct for higher-is-worse variables", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [LEGAL] })} />);
    const legal = screen.getByText("Legal Exposure").closest("li")!;
    expect(within(legal).getByText("higher is worse")).toBeInTheDocument();
    // A positive move on a pressure variable is explicitly "worsened".
    expect(within(legal).getByText(/\+2 worsened/)).toBeInTheDocument();
    expect(within(legal).getByText("Ambient drift")).toBeInTheDocument();
  });

  test("reduced advice shows proposed versus applied instead of implying full effect", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [TRUST] })} />);
    expect(
      screen.getByText(/You proposed \+8; the client applied \+5 at 60% adherence/),
    ).toBeInTheDocument();
    expect(screen.getByText("Reduced")).toBeInTheDocument();
  });

  test("rejected advice is shown as proposed-but-not-applied with no invented delta", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [REJECTED_ORDER] })} />);
    const order = screen.getByText("Public Order").closest("li")!;
    expect(within(order).getByText("no net change")).toBeInTheDocument();
    expect(
      within(order).getByText(/You proposed \+6; the client rejected it — no effect applied/),
    ).toBeInTheDocument();
    expect(within(order).getByText("Rejected")).toBeInTheDocument();
    // No attributed step rows exist for a variable that never moved.
    expect(within(order).queryByText("Your advice")).not.toBeInTheDocument();
  });

  test("summarizes why the client acted and links the sent memo provenance", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [TRUST] })} />);
    expect(
      screen.getByText(/modified the advice to protect contractor relations/),
    ).toBeInTheDocument();
    expect(screen.getByText(/adherence 60%/)).toBeInTheDocument();
    expect(
      screen.getByText(/Advisory memo — disclosure, revision 2/),
    ).toBeInTheDocument();
    expect(screen.getByText(/drafted manually/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp("a".repeat(12)))).toBeInTheDocument();
  });

  test("announces the resolution status in reading order", () => {
    render(<ConsequencesPhase result={baseResult({ variables: [TRUST, LEGAL] })} />);
    expect(screen.getByText(/Turn 2 resolved — 2 variables changed/)).toBeInTheDocument();
  });

  test("falls back to the flat net-change table for turns without a report", () => {
    const legacy = baseResult(
      { variables: [] },
      [
        {
          variable: "public_trust",
          old_value: 50,
          new_value: 53,
          delta: 3,
          reason: "Advice — Controlled disclosure",
          source_type: "advice",
        },
      ],
    );
    render(<ConsequencesPhase result={legacy} />);
    expect(screen.getByText("State changes")).toBeInTheDocument();
    expect(screen.getByText("Public Trust")).toBeInTheDocument();
    expect(screen.getByText("+3")).toBeInTheDocument();
  });

  test("renders escalated and resolved thread sections when present", () => {
    const result = baseResult({ variables: [TRUST] });
    result.consequence_stack.escalated_threads = [
      "Disclosure clock — The disclosure-timing record grew another cycle.",
    ];
    result.consequence_stack.resolved_threads = [
      "Sole-source contractor leverage — A credible squeeze broke the assumption.",
    ];
    render(<ConsequencesPhase result={result} />);
    expect(screen.getByText("Threads escalated")).toBeInTheDocument();
    expect(screen.getByText(/disclosure-timing record grew/)).toBeInTheDocument();
    expect(screen.getByText("Threads resolved")).toBeInTheDocument();
    expect(screen.getByText(/credible squeeze broke/)).toBeInTheDocument();
  });

  test("keeps the authoritative applied-diff record reachable", () => {
    render(
      <ConsequencesPhase
        result={baseResult({ variables: [TRUST] }, TRUST.deltas.map((d) => ({
          variable: "public_trust",
          old_value: d.value_before,
          new_value: d.value_after,
          delta: d.delta,
          reason: d.reason,
          source_type: d.source_type,
        })))}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Authoritative applied-diff record/ }),
    ).toBeInTheDocument();
  });
});
