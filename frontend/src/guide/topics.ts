// Contextual guide topics — Wave 3 Batch C1.
//
// Each topic teaches one real game object the first time it matters, as an
// inline, non-modal callout beside the object itself. Acknowledgements are
// versioned local presentation preferences: losing them repeats a callout,
// never blocks gameplay, and grants nothing. Campaign authority never reads
// this key.

export const GUIDE_STORAGE_KEY = "continuity-failure.guide.v2";

export const GUIDE_TOPIC_IDS = [
  "adherence",
  "evidence_weight",
  "citation",
  "thread_deadline",
  "precedent",
  "stale_feed",
  "power_allocation",
  "record_detail",
] as const;

export type GuideTopicId = (typeof GUIDE_TOPIC_IDS)[number];

export interface GuideTopicCopy {
  title: string;
  body: string;
}

// Deterministic controlled copy. Short enough to sit beside the object it
// explains; the complete operating brief remains in Help.
export const GUIDE_TOPICS: Record<GuideTopicId, GuideTopicCopy> = {
  adherence: {
    title: "Adherence",
    body:
      "You recommend; the client decides. Adherence is the share of your "
      + "advice the client actually carries into resolution — follow, modify, "
      + "delay, and reject all leave a different record.",
  },
  evidence_weight: {
    title: "Evidentiary weight",
    body:
      "A record's turn number is its freshness; source and reliability say "
      + "how much weight it can bear; public status says who may already know "
      + "it. You never have to cite — but what you stake a memo on is remembered.",
  },
  citation: {
    title: "Citations",
    body:
      "Staking the memo on up to three records changes how the client weighs "
      + "it: relevant, reliable backing strengthens adherence; contested "
      + "material carries a recorded cost. Citing is optional every turn.",
  },
  thread_deadline: {
    title: "Open threads",
    body:
      "A thread with a deadline is a scheduled consequence: leave it "
      + "unresolved and it escalates on the record when its turn comes. "
      + "Resolving it takes advice the client acts on, not intent.",
  },
  precedent: {
    title: "Precedent ledger",
    body:
      "An expedient decision is now on the institutional debt ledger. "
      + "Repeating a recorded precedent gets easier for the client and costs "
      + "more each time — the ledger never forgets.",
  },
  stale_feed: {
    title: "Stale feeds",
    body:
      "The desk is degraded: live feeds have stopped refreshing, so records "
      + "carry last-verified stamps instead of certainty. Old data is still "
      + "evidence — just not equivalent evidence.",
  },
  power_allocation: {
    title: "Auxiliary power",
    body:
      "The workstation is critical: exactly one subsystem gets auxiliary "
      + "power this turn. Communications reads the caller, live data verifies "
      + "citations, model access keeps drafting — choose what this turn needs; "
      + "the allocation binds when committed.",
  },
  record_detail: {
    title: "The full record",
    body:
      "The headline is a derived summary; the authoritative record beneath it "
      + "never goes away. Show the full record opens the complete audit — "
      + "every applied change, attributed and reconciled.",
  },
};

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Topic ids the player has acknowledged. Malformed storage reads as none. */
export function readAcknowledgedTopics(
  storage: StorageLike | null = defaultStorage(),
): Set<GuideTopicId> {
  if (!storage) return new Set();
  let raw: string | null;
  try {
    raw = storage.getItem(GUIDE_STORAGE_KEY);
  } catch {
    return new Set();
  }
  if (!raw) return new Set();
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return new Set();
  }
  if (!Array.isArray(parsed)) return new Set();
  return new Set(
    parsed.filter((id): id is GuideTopicId =>
      (GUIDE_TOPIC_IDS as readonly string[]).includes(id as string),
    ),
  );
}

/**
 * Record one acknowledgement. Never throws: on storage failure the topic may
 * simply reappear next session, which is harmless.
 */
export function acknowledgeTopic(
  topic: GuideTopicId,
  storage: StorageLike | null = defaultStorage(),
): void {
  if (!storage) return;
  const acknowledged = readAcknowledgedTopics(storage);
  acknowledged.add(topic);
  try {
    storage.setItem(
      GUIDE_STORAGE_KEY,
      JSON.stringify(
        GUIDE_TOPIC_IDS.filter((id) => acknowledged.has(id)),
      ),
    );
  } catch {
    // The preference simply does not persist.
  }
}
