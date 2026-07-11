import { describe, expect, it } from "vitest";
import {
  GUIDE_STORAGE_KEY,
  GUIDE_TOPIC_IDS,
  GUIDE_TOPICS,
  acknowledgeTopic,
  readAcknowledgedTopics,
} from "../src/guide/topics";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function memoryStorage(seed: Record<string, string> = {}): StorageLike & {
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

function brokenStorage(): StorageLike {
  const refuse = () => {
    throw new DOMException("SecurityError");
  };
  return { getItem: refuse, setItem: refuse, removeItem: refuse };
}

describe("guide topic acknowledgements", () => {
  it("uses the versioned v2 presentation key", () => {
    expect(GUIDE_STORAGE_KEY).toBe("continuity-failure.guide.v2");
  });

  it("has copy for every topic in the C1 vocabulary", () => {
    expect(new Set(GUIDE_TOPIC_IDS)).toEqual(
      new Set([
        "adherence",
        "evidence_weight",
        "citation",
        "thread_deadline",
        "precedent",
        "stale_feed",
        "power_allocation",
        "record_detail",
      ]),
    );
    for (const id of GUIDE_TOPIC_IDS) {
      expect(GUIDE_TOPICS[id].title).toBeTruthy();
      expect(GUIDE_TOPICS[id].body).toBeTruthy();
    }
  });

  it("round-trips acknowledgements and triggers each topic only once", () => {
    const storage = memoryStorage();
    expect(readAcknowledgedTopics(storage).size).toBe(0);
    acknowledgeTopic("adherence", storage);
    acknowledgeTopic("citation", storage);
    acknowledgeTopic("adherence", storage);
    expect(readAcknowledgedTopics(storage)).toEqual(new Set(["adherence", "citation"]));
    // Stored under the versioned key only.
    expect([...storage.data.keys()]).toEqual([GUIDE_STORAGE_KEY]);
  });

  it("drops unknown ids and survives malformed payloads", () => {
    expect(
      readAcknowledgedTopics(
        memoryStorage({
          [GUIDE_STORAGE_KEY]: JSON.stringify(["adherence", "not_a_topic", 42]),
        }),
      ),
    ).toEqual(new Set(["adherence"]));
    expect(
      readAcknowledgedTopics(memoryStorage({ [GUIDE_STORAGE_KEY]: "not json{" })).size,
    ).toBe(0);
    expect(
      readAcknowledgedTopics(memoryStorage({ [GUIDE_STORAGE_KEY]: '{"a":1}' })).size,
    ).toBe(0);
  });

  it("never throws when storage is unavailable — topics may simply repeat", () => {
    expect(readAcknowledgedTopics(null).size).toBe(0);
    expect(() => acknowledgeTopic("adherence", null)).not.toThrow();
    const broken = brokenStorage();
    expect(readAcknowledgedTopics(broken).size).toBe(0);
    expect(() => acknowledgeTopic("adherence", broken)).not.toThrow();
  });

  it("does not read the retired v1 desk-guide key", () => {
    const storage = memoryStorage({
      "continuity-failure.desk-guide.v1": "acknowledged",
    });
    expect(readAcknowledgedTopics(storage).size).toBe(0);
  });
});
