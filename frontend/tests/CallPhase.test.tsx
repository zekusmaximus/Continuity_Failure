import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import type { ClientCall, SystemStatus } from "../src/api/client";
import CallPhase from "../src/components/CallPhase";

const CALL: ClientCall = {
  id: "call_01",
  turn: 9,
  caller: "Public Works / Water Authority",
  caller_faction_id: "water_authority",
  summary: "Operator overtime is exhausted.",
  known_facts: [],
  ask: "How do we sustain operations?",
  crisis_id: null,
  caller_role: "Public Works Operations",
  urgency: "critical",
  time_horizon: "~1 operational cycle",
  unknown_facts: [],
  immediate_risks: [],
  public_exposure: "private",
  private_pressure: "",
  attached_document_ids: [],
  primary_advice_ids: [],
  decision_profile: null,
};

function criticalStatus(overrides: Partial<SystemStatus> = {}): SystemStatus {
  return {
    power: 10,
    comms: 10,
    data_freshness: 40,
    staff_capacity: 50,
    ai_available: false,
    model_status: "Model access offline — grid power below sustaining threshold",
    degradation_band: "CRITICAL",
    live_feeds: false,
    last_live_turn: 4,
    requires_power_allocation: true,
    power_commitment: null,
    ...overrides,
  } as SystemStatus;
}

describe("Call-phase auxiliary-power commitment (CRITICAL band)", () => {
  test("routing panel commits the selected subsystem", async () => {
    const user = userEvent.setup();
    const onCommitPower = vi.fn();
    render(
      <CallPhase
        call={CALL}
        disposition="Communications dark — the caller's disposition cannot be read."
        systemStatus={criticalStatus()}
        onCommitPower={onCommitPower}
      />,
    );
    expect(
      screen.getByText(/Auxiliary power · one subsystem this turn/),
    ).toBeInTheDocument();
    const commit = screen.getByRole("button", { name: /Route auxiliary power/ });
    expect(commit).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /Communications/ }));
    expect(commit).toBeEnabled();
    await user.click(commit);
    expect(onCommitPower).toHaveBeenCalledWith("COMMUNICATIONS");
  });

  test("a committed turn shows the locked route instead of the chooser", () => {
    render(
      <CallPhase
        call={CALL}
        disposition="The Public Works / Water Authority opens professionally (trust 55/100)."
        systemStatus={criticalStatus({ power_commitment: "COMMUNICATIONS" })}
        onCommitPower={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      /committed to Communications/,
    );
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    // The pre-decision payoff: the live disposition renders on the call.
    expect(screen.getByText(/opens professionally/)).toBeInTheDocument();
  });

  test("no panel renders outside the CRITICAL band", () => {
    render(
      <CallPhase
        call={CALL}
        systemStatus={criticalStatus({
          degradation_band: "STRAINED",
          requires_power_allocation: false,
          power: 40,
        })}
        onCommitPower={vi.fn()}
      />,
    );
    expect(
      screen.queryByText(/Auxiliary power · one subsystem this turn/),
    ).not.toBeInTheDocument();
  });
});
