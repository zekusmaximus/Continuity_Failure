import { afterEach, describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ReplayInvitation from "../src/components/ReplayInvitation";
import type { CampaignSummary, TurnHistory } from "../src/api/client";

// Wave 3 C3: the terminal replay invitation surfaces only facts already on
// the record — variant/ruleset, the assessment's verdict and weakest axis,
// and one unresolved thread or future hook — and creates nothing itself.

function summary(status: CampaignSummary["status"]): CampaignSummary {
  return {
    id: "c1",
    name: "Northbridge",
    scenario_id: "northbridge_water_failure",
    status,
    turn_number: 11,
    max_turns: 10,
    failure_reason: null,
    created_at: "2026-07-11T00:00:00Z",
    ruleset_version: "3",
    variant_id: "hot_summer",
  };
}

const HISTORY = {
  open_threads: [
    { id: "th_1", title: "Grid margin erosion", status: "open" },
    { id: "th_2", title: "Resolved thing", status: "resolved" },
  ],
  turns: [
    {
      consequence_lead: {
        headline: "…",
        future_hook: "Grid margin erosion escalated this turn.",
        references: [],
      },
    },
  ],
} as unknown as TurnHistory;

const DOSSIER_RESPONSE = {
  campaign_id: "c1",
  name: "Northbridge",
  status: "COMPLETED",
  filename: "northbridge-completed.md",
  markdown: "# Dossier",
  assessment: {
    verdict_title: "A brittle stabilization",
    verdict_body: ["The water kept flowing."],
    campaign_status: "COMPLETED",
    axes: [
      { id: "stability", label: "Stability", score: 62, band: "holding", factors: [] },
      { id: "trust", label: "Public legitimacy", score: 31, band: "eroded", factors: [] },
      { id: "debt", label: "Institutional debt", score: 55, band: "strained", factors: [] },
    ],
  },
};

function stubDossierFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(JSON.stringify(DOSSIER_RESPONSE), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ReplayInvitation (Wave 3 C3)", () => {
  test("surfaces the record: variant, ruleset, verdict, weakest axis, open thread", async () => {
    stubDossierFetch();
    const onReopenIntake = vi.fn();
    render(
      <ReplayInvitation
        campaignId="c1"
        summary={summary("COMPLETED")}
        history={HISTORY}
        onReopenIntake={onReopenIntake}
      />,
    );

    expect(screen.getByText("hot_summer · ruleset 3")).toBeInTheDocument();
    expect(await screen.findByText("A brittle stabilization")).toBeInTheDocument();
    // Weakest axis is the assessment's lowest score, verbatim.
    expect(screen.getByText("Public legitimacy — 31/100 (eroded)")).toBeInTheDocument();
    // One unresolved thread from the record, not a resolved one.
    expect(
      screen.getByText("Still open on the record: Grid margin erosion."),
    ).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "Reopen intake with alternate conditions" }),
    );
    expect(onReopenIntake).toHaveBeenCalledTimes(1);
    // The invitation itself never creates a campaign.
    expect(screen.getByText(/No campaign is created until you choose Begin Intake/)).toBeInTheDocument();
  });

  test("falls back to the final turn's future hook when no thread is open", async () => {
    stubDossierFetch();
    const history = {
      ...HISTORY,
      open_threads: [{ id: "th_2", title: "Resolved thing", status: "resolved" }],
    } as unknown as TurnHistory;
    render(
      <ReplayInvitation
        campaignId="c1"
        summary={summary("FAILED")}
        history={history}
        onReopenIntake={() => undefined}
      />,
    );
    expect(await screen.findByText("A brittle stabilization")).toBeInTheDocument();
    expect(
      screen.getByText("Grid margin erosion escalated this turn."),
    ).toBeInTheDocument();
  });

  test("renders nothing for an active campaign", () => {
    stubDossierFetch();
    render(
      <ReplayInvitation
        campaignId="c1"
        summary={summary("ACTIVE")}
        history={HISTORY}
        onReopenIntake={() => undefined}
      />,
    );
    expect(screen.queryByText(/Reopen intake/)).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });
});
