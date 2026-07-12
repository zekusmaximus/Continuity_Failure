// Local completion hint — Wave 3 Batch C3.
//
// A presentation flag only: returning players see alternate intake conditions
// more prominently. Campaign completion remains authoritative in SQLite; this
// flag grants no game state, may be absent, and losing it merely restores the
// first-run intake emphasis.

export const COMPLETED_STORAGE_KEY = "continuity-failure.completed-engagement.v1";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readHasCompletedEngagement(
  storage: StorageLike | null = defaultStorage(),
): boolean {
  if (!storage) return false;
  try {
    return storage.getItem(COMPLETED_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

export function writeHasCompletedEngagement(
  storage: StorageLike | null = defaultStorage(),
): void {
  try {
    storage?.setItem(COMPLETED_STORAGE_KEY, "true");
  } catch {
    // The hint simply does not persist.
  }
}
