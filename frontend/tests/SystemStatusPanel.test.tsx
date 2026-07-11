import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import type { AdviceMemo, SystemStatus, WorldState } from "../src/api/client";
import SystemStatusPanel, {
  DegradationBanner,
} from "../src/components/SystemStatusPanel";
import StateReadout from "../src/components/StateReadout";
import EvidenceBoard from "../src/components/EvidenceBoard";
import MemoDraftPanel from "../src/components/MemoDraftPanel";

function status(overrides: Partial<SystemStatus> = {}): SystemStatus {
  return {
    power: 72,
    comms: 72,
    data_freshness: 56,
    staff_capacity: 50,
    ai_available: false,
    model_status: "AI assist present — off by default (returns system drafts)",
    degradation_band: "NOMINAL",
    live_feeds: true,
    last_live_turn: 1,
    requires_power_allocation: false,
    ...overrides,
  };
}

const STRAINED = status({
  power: 40,
  degradation_band: "STRAINED",
  live_feeds: false,
  last_live_turn: 4,
});

const DEGRADED = status({
  power: 30,
  degradation_band: "DEGRADED",
  live_feeds: false,
  last_live_turn: 4,
  model_status:
    "Model access offline — grid power below sustaining threshold (deterministic system drafts only)",
});

const CRITICAL = status({
  power: 10,
  degradation_band: "CRITICAL",
  live_feeds: false,
  last_live_turn: 4,
  requires_power_allocation: true,
  model_status:
    "Model access offline — grid power below sustaining threshold (deterministic system drafts only)",
});

describe("degradation banner", () => {
  test("renders nothing while the workstation is nominal", () => {
    const { container } = render(<DegradationBanner status={status()} />);
    expect(container).toBeEmptyDOMElement();
  });

  test("strained: announces the stale snapshot with its anchor turn", () => {
    render(<DegradationBanner status={STRAINED} />);
    const strip = screen.getByRole("status");
    expect(strip).toHaveTextContent(/Workstation strained/);
    expect(strip).toHaveTextContent(/turn 4 close-out/);
  });

  test("degraded: adds the model-access loss", () => {
    render(<DegradationBanner status={DEGRADED} />);
    expect(screen.getByRole("status")).toHaveTextContent(/Model access offline/);
  });

  test("critical: names the one-subsystem constraint", () => {
    render(<DegradationBanner status={CRITICAL} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      /Auxiliary power supports one subsystem/,
    );
  });
});

describe("workstation status panel", () => {
  test("shows the four meters, the band, and the model line", () => {
    render(<SystemStatusPanel status={STRAINED} />);
    expect(screen.getByRole("progressbar", { name: "Grid power" })).toHaveAttribute(
      "aria-valuenow",
      "40",
    );
    expect(screen.getByRole("progressbar", { name: "Communications" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Data freshness" })).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Operations staff" })).toBeInTheDocument();
    expect(screen.getByLabelText("Degradation band: STRAINED")).toBeInTheDocument();
    expect(screen.getByText(/Live feeds lost/)).toBeInTheDocument();
  });

  test("nominal panel carries no stale line", () => {
    render(<SystemStatusPanel status={status()} />);
    expect(screen.queryByText(/Live feeds lost/)).not.toBeInTheDocument();
  });
});

describe("stale treatments", () => {
  const worldState: WorldState = {
    turn_number: 5,
    variables: { water_security: 46, power_stability: 40 },
    factions: [],
    active_crisis: null,
    last_verified: "LAST VERIFIED — turn 4 close-out · live feed lost (deterministic)",
  };

  test("the state readout marks the freshness stamp as a warning", () => {
    render(<StateReadout state={worldState} stale />);
    const stamp = screen.getByRole("status");
    expect(stamp).toHaveTextContent(/LAST VERIFIED/);
    expect(stamp.className).toContain("cd-verified-stale");
  });

  test("the evidence board carries the stale-snapshot notice", () => {
    render(<EvidenceBoard documents={[]} call={null} systemStatus={STRAINED} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      /documents last verified at the turn 4 close-out/,
    );
  });

  test("the evidence board stays quiet on live feeds", () => {
    render(<EvidenceBoard documents={[]} call={null} systemStatus={status()} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("memo panel diegetic copy", () => {
  const memo: AdviceMemo = {
    id: `memo_${"1".repeat(32)}`,
    campaign_id: "campaign",
    status: "draft",
    name: "Advice of record",
    content: "Exact draft content",
    revision: 1,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z",
    author: "Continuity Desk",
    source: "system",
    classification: "proposed",
    provenance: {
      workflow: "deterministic_fallback",
      model_run_id: "run_1",
      prompt_version: "v1",
      model_name: "offline",
      provider: "offline",
      validation_status: "fallback",
      fallback_used: true,
    },
    turn_number: 1,
    call_id: "call_1",
    advice_id: "controlled_disclosure",
    revisions: [],
    sent_snapshot: null,
  };

  test("degraded band replaces the generic fallback copy with the power reason", () => {
    render(
      <MemoDraftPanel
        memo={memo}
        loading={false}
        saving={false}
        error={null}
        onSave={vi.fn()}
        systemStatus={DEGRADED}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/Model access offline/);
    expect(screen.queryByText(/did not validate/)).not.toBeInTheDocument();
  });

  test("without a degradation gate the generic fallback copy stands", () => {
    render(
      <MemoDraftPanel
        memo={memo}
        loading={false}
        saving={false}
        error={null}
        onSave={vi.fn()}
        systemStatus={status()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/did not validate/);
  });
});
