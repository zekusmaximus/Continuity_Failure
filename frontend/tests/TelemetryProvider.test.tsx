import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { TelemetryPhase } from "../src/telemetry/events";
import {
  TelemetryProvider,
  useDeskTelemetry,
  useTelemetry,
} from "../src/telemetry/TelemetryProvider";
import {
  TELEMETRY_ENABLED_STORAGE_KEY,
  readTelemetryEvents,
  type TelemetryStorage,
} from "../src/telemetry/store";

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

function Probe() {
  const { report, enabled, setEnabled } = useTelemetry();
  return (
    <div>
      <button onClick={() => report({ event_type: "case_file_opened", tab_id: "evidence" })}>
        report intent
      </button>
      <button onClick={() => setEnabled(!enabled)}>toggle collection</button>
    </div>
  );
}

interface HarnessProps {
  campaignId: string | null;
  turnNumber: number | null;
  phase: TelemetryPhase | null;
  storage: TelemetryStorage | null;
  now: () => number;
  collectByDefault?: boolean;
}

function Harness(props: HarnessProps) {
  const telemetry = useDeskTelemetry({
    campaignId: props.campaignId,
    turnNumber: props.turnNumber,
    phase: props.phase,
    storage: props.storage,
    now: props.now,
    collectByDefault: props.collectByDefault ?? true,
  });
  return (
    <TelemetryProvider value={telemetry}>
      <Probe />
    </TelemetryProvider>
  );
}

describe("useDeskTelemetry", () => {
  it("emits exact paired enter/leave events from an injected clock", () => {
    const storage = memoryStorage();
    let clock = 10_000;
    const now = () => clock;

    const { rerender } = render(
      <Harness campaignId="c1" turnNumber={1} phase="CALL" storage={storage} now={now} />,
    );
    clock += 5_000;
    rerender(
      <Harness campaignId="c1" turnNumber={1} phase="BRIEF" storage={storage} now={now} />,
    );
    clock += 2_500;
    rerender(
      <Harness campaignId="c1" turnNumber={1} phase="ADVICE" storage={storage} now={now} />,
    );

    const events = readTelemetryEvents(storage);
    expect(
      events.map((e) => [e.event_type, e.phase, "elapsed_ms" in e ? e.elapsed_ms : null]),
    ).toEqual([
      ["phase_entered", "CALL", null],
      ["phase_left", "CALL", 5_000],
      ["phase_entered", "BRIEF", null],
      ["phase_left", "BRIEF", 2_500],
      ["phase_entered", "ADVICE", null],
    ]);
    for (const event of events) {
      expect(event.campaign_id).toBe("c1");
      expect(event.turn_number).toBe(1);
      expect(event.session_id).toBe(events[0].session_id);
    }
    expect(events[1].occurred_at).toBe(new Date(15_000).toISOString());
  });

  it("attributes the leave to the previous campaign and turn on campaign change", () => {
    const storage = memoryStorage();
    let clock = 0;
    const now = () => clock;

    const { rerender } = render(
      <Harness campaignId="c1" turnNumber={3} phase="ARCHIVE" storage={storage} now={now} />,
    );
    clock = 7_000;
    rerender(
      <Harness campaignId="c2" turnNumber={1} phase="CALL" storage={storage} now={now} />,
    );

    const events = readTelemetryEvents(storage);
    expect(events).toHaveLength(3);
    expect(events[1]).toMatchObject({
      event_type: "phase_left",
      phase: "ARCHIVE",
      elapsed_ms: 7_000,
      campaign_id: "c1",
      turn_number: 3,
    });
    expect(events[2]).toMatchObject({
      event_type: "phase_entered",
      phase: "CALL",
      campaign_id: "c2",
      turn_number: 1,
    });
  });

  it("stamps reported intents with the ambient campaign, turn, and phase", async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const { getByRole } = render(
      <Harness
        campaignId="c1"
        turnNumber={2}
        phase="EVIDENCE"
        storage={storage}
        now={() => 1_000}
      />,
    );
    await user.click(getByRole("button", { name: "report intent" }));
    const events = readTelemetryEvents(storage);
    expect(events[events.length - 1]).toMatchObject({
      event_type: "case_file_opened",
      tab_id: "evidence",
      campaign_id: "c1",
      turn_number: 2,
      phase: "EVIDENCE",
    });
  });

  it("collects nothing while disabled and honors the local switch", async () => {
    const user = userEvent.setup();
    const storage = memoryStorage();
    const { getByRole } = render(
      <Harness
        campaignId="c1"
        turnNumber={1}
        phase="CALL"
        storage={storage}
        now={() => 0}
        collectByDefault={false}
      />,
    );
    await user.click(getByRole("button", { name: "report intent" }));
    expect(readTelemetryEvents(storage)).toEqual([]);

    await user.click(getByRole("button", { name: "toggle collection" }));
    expect(storage.data.get(TELEMETRY_ENABLED_STORAGE_KEY)).toBe("on");
    await user.click(getByRole("button", { name: "report intent" }));
    expect(readTelemetryEvents(storage)).toHaveLength(1);
  });

  it("respects a stored off switch over the build default", () => {
    const storage = memoryStorage({ [TELEMETRY_ENABLED_STORAGE_KEY]: "off" });
    render(
      <Harness
        campaignId="c1"
        turnNumber={1}
        phase="CALL"
        storage={storage}
        now={() => 0}
        collectByDefault={true}
      />,
    );
    expect(readTelemetryEvents(storage)).toEqual([]);
  });

  it("flushes the open phase and records the session end on page hide", () => {
    const storage = memoryStorage();
    let clock = 0;
    render(
      <Harness
        campaignId="c1"
        turnNumber={4}
        phase="CONSEQUENCES"
        storage={storage}
        now={() => clock}
      />,
    );
    clock = 9_000;
    window.dispatchEvent(new Event("pagehide"));

    const events = readTelemetryEvents(storage);
    expect(
      events.map((e) => [e.event_type, "elapsed_ms" in e ? e.elapsed_ms : null]),
    ).toEqual([
      ["phase_entered", null],
      ["phase_left", 9_000],
      ["desk_session_ended", null],
    ]);
    expect(events[2]).toMatchObject({
      phase: "CONSEQUENCES",
      turn_number: 4,
      campaign_id: "c1",
    });
  });

  it("never throws through a player action when storage is unavailable", async () => {
    const user = userEvent.setup();
    const { getByRole } = render(
      <Harness campaignId="c1" turnNumber={1} phase="CALL" storage={null} now={() => 0} />,
    );
    await expect(
      user.click(getByRole("button", { name: "report intent" })),
    ).resolves.toBeUndefined();
  });
});
