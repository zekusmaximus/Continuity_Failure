import { describe, expect, it } from "vitest";
import {
  TELEMETRY_EVENT_CAP,
  TELEMETRY_STORAGE_KEY,
  appendTelemetryEvent,
  clearTelemetryEvents,
  readTelemetryEvents,
  type TelemetryStorage,
} from "../src/telemetry/store";
import type { TelemetryEventV1 } from "../src/telemetry/events";

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

function brokenStorage(): TelemetryStorage {
  const refuse = () => {
    throw new DOMException("QuotaExceededError");
  };
  return { getItem: refuse, setItem: refuse, removeItem: refuse };
}

function sampleEvent(n: number): TelemetryEventV1 {
  return {
    schema_version: 1,
    event_id: `e-${n}`,
    session_id: "s-1",
    event_type: "case_file_opened",
    occurred_at: "2026-07-11T12:00:00.000Z",
    tab_id: `tab-${n}`,
  };
}

describe("telemetry store", () => {
  it("appends and reads back events oldest first", () => {
    const storage = memoryStorage();
    expect(appendTelemetryEvent(sampleEvent(1), storage)).toBe(true);
    expect(appendTelemetryEvent(sampleEvent(2), storage)).toBe(true);
    expect(readTelemetryEvents(storage).map((e) => e.event_id)).toEqual(["e-1", "e-2"]);
  });

  it("caps the ring and evicts the oldest events deterministically", () => {
    const storage = memoryStorage();
    const overflow = 5;
    // Seed one write with a nearly full ring, then push it over the cap one
    // event at a time — each append drops exactly the oldest survivor.
    const seed = Array.from({ length: TELEMETRY_EVENT_CAP }, (_, i) => sampleEvent(i));
    storage.setItem(TELEMETRY_STORAGE_KEY, JSON.stringify(seed));
    for (let i = 0; i < overflow; i += 1) {
      expect(appendTelemetryEvent(sampleEvent(TELEMETRY_EVENT_CAP + i), storage)).toBe(true);
    }
    const events = readTelemetryEvents(storage);
    expect(events).toHaveLength(TELEMETRY_EVENT_CAP);
    expect(events[0].event_id).toBe(`e-${overflow}`);
    expect(events[events.length - 1].event_id).toBe(
      `e-${TELEMETRY_EVENT_CAP + overflow - 1}`,
    );
  });

  it("drops malformed payloads and invalid records on read", () => {
    expect(
      readTelemetryEvents(memoryStorage({ [TELEMETRY_STORAGE_KEY]: "not json{" })),
    ).toEqual([]);
    expect(
      readTelemetryEvents(memoryStorage({ [TELEMETRY_STORAGE_KEY]: '{"a":1}' })),
    ).toEqual([]);
    const mixed = memoryStorage({
      [TELEMETRY_STORAGE_KEY]: JSON.stringify([
        sampleEvent(1),
        { event_type: "case_file_opened", smuggled: "memo prose" },
        42,
        sampleEvent(2),
      ]),
    });
    expect(readTelemetryEvents(mixed).map((e) => e.event_id)).toEqual(["e-1", "e-2"]);
  });

  it("refuses to append an event that fails validation", () => {
    const storage = memoryStorage();
    const invalid = {
      ...sampleEvent(1),
      memo_content: "should never be stored",
    } as unknown as TelemetryEventV1;
    expect(appendTelemetryEvent(invalid, storage)).toBe(false);
    expect(readTelemetryEvents(storage)).toEqual([]);
  });

  it("survives unavailable storage without throwing", () => {
    expect(readTelemetryEvents(null)).toEqual([]);
    expect(appendTelemetryEvent(sampleEvent(1), null)).toBe(false);
    expect(() => clearTelemetryEvents(null)).not.toThrow();

    const broken = brokenStorage();
    expect(readTelemetryEvents(broken)).toEqual([]);
    expect(appendTelemetryEvent(sampleEvent(1), broken)).toBe(false);
    expect(() => clearTelemetryEvents(broken)).not.toThrow();
  });

  it("reports a failed write when the quota is exhausted mid-session", () => {
    const storage = memoryStorage();
    expect(appendTelemetryEvent(sampleEvent(1), storage)).toBe(true);
    storage.setItem = () => {
      throw new DOMException("QuotaExceededError");
    };
    expect(appendTelemetryEvent(sampleEvent(2), storage)).toBe(false);
    // The earlier record is untouched.
    expect(readTelemetryEvents(storage).map((e) => e.event_id)).toEqual(["e-1"]);
  });

  it("clears only the telemetry key, never campaign or preference keys", () => {
    const storage = memoryStorage({
      "continuity-failure.campaign-id": "campaign-1",
      "continuity-failure.desk-guide.v1": "acknowledged",
    });
    appendTelemetryEvent(sampleEvent(1), storage);
    clearTelemetryEvents(storage);
    expect(readTelemetryEvents(storage)).toEqual([]);
    expect(storage.data.get("continuity-failure.campaign-id")).toBe("campaign-1");
    expect(storage.data.get("continuity-failure.desk-guide.v1")).toBe("acknowledged");
  });
});
