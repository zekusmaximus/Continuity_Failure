// Review-mode preference — Wave 3 Batch C2.
//
// Guided versus expedited review is local browser presentation state, never
// campaign state: it changes which screens compose the same current-turn
// package, and nothing else. Losing the preference falls back to the guided
// default; storage failure never blocks play.

import type { ReviewMode } from "../domain";

export const REVIEW_MODE_STORAGE_KEY = "continuity-failure.review-mode.v1";

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function defaultStorage(): StorageLike | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readReviewMode(
  storage: StorageLike | null = defaultStorage(),
): ReviewMode {
  if (!storage) return "guided";
  let stored: string | null;
  try {
    stored = storage.getItem(REVIEW_MODE_STORAGE_KEY);
  } catch {
    return "guided";
  }
  return stored === "expedited" ? "expedited" : "guided";
}

export function writeReviewMode(
  mode: ReviewMode,
  storage: StorageLike | null = defaultStorage(),
): void {
  try {
    storage?.setItem(REVIEW_MODE_STORAGE_KEY, mode);
  } catch {
    // The preference simply does not persist beyond this page session.
  }
}
