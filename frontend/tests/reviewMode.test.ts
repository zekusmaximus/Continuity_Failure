import { describe, expect, it } from "vitest";
import {
  EXPEDITED_STEPS,
  TURN_STEPS,
  phaseForMode,
  stepsForMode,
  type Phase,
} from "../src/domain";
import {
  REVIEW_MODE_STORAGE_KEY,
  readReviewMode,
  writeReviewMode,
} from "../src/guide/reviewMode";

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

describe("review-mode phase maps (Wave 3 C2)", () => {
  it("pins both spines exactly", () => {
    expect(stepsForMode("guided")).toEqual([
      "CALL",
      "BRIEF",
      "EVIDENCE",
      "ADVICE",
      "CLIENT_DECISION",
      "CONSEQUENCES",
      "ARCHIVE",
    ]);
    expect(stepsForMode("expedited")).toEqual([
      "REVIEW",
      "ADVICE",
      "CLIENT_DECISION",
      "CONSEQUENCES",
      "ARCHIVE",
    ]);
  });

  it("shares the resolution phases between modes verbatim", () => {
    // Everything from Advice onward is identical: expedited changes how the
    // package is reviewed, never how the turn resolves or reveals.
    expect(EXPEDITED_STEPS.slice(1)).toEqual(TURN_STEPS.slice(3));
  });

  it("maps the guided review phases onto REVIEW and back onto CALL", () => {
    for (const phase of ["CALL", "BRIEF", "EVIDENCE"] as Phase[]) {
      expect(phaseForMode(phase, "expedited")).toBe("REVIEW");
    }
    expect(phaseForMode("REVIEW", "guided")).toBe("CALL");
  });

  it("leaves every non-review phase untouched in both directions", () => {
    const shared: Phase[] = [
      "ADVICE",
      "CLIENT_DECISION",
      "CONSEQUENCES",
      "ARCHIVE",
      "DOSSIER",
      "INTRO",
    ];
    for (const phase of shared) {
      expect(phaseForMode(phase, "expedited")).toBe(phase);
      expect(phaseForMode(phase, "guided")).toBe(phase);
    }
  });
});

describe("review-mode preference storage", () => {
  it("defaults to guided and round-trips the explicit choice", () => {
    const storage = memoryStorage();
    expect(readReviewMode(storage)).toBe("guided");
    writeReviewMode("expedited", storage);
    expect(readReviewMode(storage)).toBe("expedited");
    expect(storage.data.get(REVIEW_MODE_STORAGE_KEY)).toBe("expedited");
    writeReviewMode("guided", storage);
    expect(readReviewMode(storage)).toBe("guided");
  });

  it("treats unknown values and unavailable storage as guided", () => {
    expect(
      readReviewMode(memoryStorage({ [REVIEW_MODE_STORAGE_KEY]: "warp-speed" })),
    ).toBe("guided");
    expect(readReviewMode(null)).toBe("guided");
    const refuse = () => {
      throw new DOMException("SecurityError");
    };
    const broken: StorageLike = { getItem: refuse, setItem: refuse, removeItem: refuse };
    expect(readReviewMode(broken)).toBe("guided");
    expect(() => writeReviewMode("expedited", broken)).not.toThrow();
  });
});
