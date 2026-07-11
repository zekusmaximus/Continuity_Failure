import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TelemetryPanel from "../src/components/TelemetryPanel";
import { TelemetryProvider, type TelemetryApi } from "../src/telemetry/TelemetryProvider";
import {
  TELEMETRY_STORAGE_KEY,
  readTelemetryEvents,
  type TelemetryStorage,
} from "../src/telemetry/store";
import type { TelemetryEventV1 } from "../src/telemetry/events";
import type { CampaignSummary } from "../src/api/client";

function memoryStorage(seed: Record<string, string> = {}): TelemetryStorage & {
  data: Map<string, string>;
} {
  const data = new Map(Object.entries(seed));
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  };
}

function seededEvents(): TelemetryEventV1[] {
  return [
    {
      schema_version: 1,
      event_id: "e-1",
      session_id: "s-1",
      event_type: "phase_entered",
      occurred_at: "2026-07-11T12:00:00.000Z",
      campaign_id: "c1",
      turn_number: 1,
      phase: "CALL",
    },
    {
      schema_version: 1,
      event_id: "e-2",
      session_id: "s-1",
      event_type: "phase_left",
      occurred_at: "2026-07-11T12:00:30.000Z",
      campaign_id: "c1",
      turn_number: 1,
      phase: "CALL",
      elapsed_ms: 30_000,
    },
  ];
}

const SUMMARY: CampaignSummary = {
  id: "c1",
  name: "Northbridge Engagement",
  scenario_id: "northbridge_water_failure",
  status: "ACTIVE",
  turn_number: 1,
  max_turns: 10,
  failure_reason: null,
  created_at: "2026-07-11T11:59:00.000Z",
  ruleset_version: "3",
  variant_id: "baseline",
};

function renderPanel(storage: TelemetryStorage, overrides: Partial<TelemetryApi> = {}) {
  const api: TelemetryApi = {
    report: () => undefined,
    enabled: true,
    setEnabled: () => undefined,
    storage,
    ...overrides,
  };
  return render(
    <TelemetryProvider value={api}>
      <TelemetryPanel summary={SUMMARY} />
    </TelemetryProvider>,
  );
}

describe("TelemetryPanel", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:mock"),
      revokeObjectURL: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("explains the privacy boundary and shows the footprint", () => {
    const storage = memoryStorage({
      [TELEMETRY_STORAGE_KEY]: JSON.stringify(seededEvents()),
    });
    renderPanel(storage);
    expect(
      screen.getByText(/The data stays in this browser/),
    ).toBeInTheDocument();
    expect(screen.getByText("Events on record").nextElementSibling).toHaveTextContent("2");
    expect(screen.getByText(/Incoming Call: 30s across 1 visit/)).toBeInTheDocument();
  });

  it("exports a manifest plus events only on explicit click", async () => {
    const user = userEvent.setup();
    const storage = memoryStorage({
      [TELEMETRY_STORAGE_KEY]: JSON.stringify(seededEvents()),
    });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    renderPanel(storage);

    const createObjectURL = URL.createObjectURL as ReturnType<typeof vi.fn>;
    expect(createObjectURL).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Export JSON" }));
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(createObjectURL).toHaveBeenCalledTimes(1);

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const payload = JSON.parse(await blob.text());
    expect(payload.manifest).toEqual({
      schema_version: 1,
      app_version: "0.1.0",
      ruleset_version: "3",
      variant_id: "baseline",
      exported_at: expect.any(String),
    });
    expect(payload.events).toHaveLength(2);
    expect(Object.keys(payload)).toEqual(["manifest", "events"]);
    clickSpy.mockRestore();
  });

  it("clears only behind confirmation and leaves other keys intact", async () => {
    const user = userEvent.setup();
    const storage = memoryStorage({
      [TELEMETRY_STORAGE_KEY]: JSON.stringify(seededEvents()),
      "continuity-failure.campaign-id": "c1",
    });
    renderPanel(storage);

    // Backing out keeps the data.
    await user.click(screen.getByRole("button", { name: "Clear local data" }));
    await user.click(screen.getByRole("button", { name: "Keep data" }));
    expect(readTelemetryEvents(storage)).toHaveLength(2);

    await user.click(screen.getByRole("button", { name: "Clear local data" }));
    expect(
      screen.getByText(/Delete 2 locally stored playtest events\?/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Delete playtest data" }));

    expect(readTelemetryEvents(storage)).toEqual([]);
    expect(screen.getByText("Events on record").nextElementSibling).toHaveTextContent("0");
    expect(storage.data.get("continuity-failure.campaign-id")).toBe("c1");
  });

  it("drives the collection switch through setEnabled", async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const setEnabled = vi.fn();
    renderPanel(storage, { enabled: false, setEnabled });
    const toggle = screen.getByRole("checkbox", {
      name: /Collect local playtest events/,
    });
    expect(toggle).not.toBeChecked();
    await user.click(toggle);
    expect(setEnabled).toHaveBeenCalledWith(true);
  });

  it("disables export and clear when nothing is recorded", () => {
    renderPanel(memoryStorage());
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Clear local data" })).toBeDisabled();
  });
});
