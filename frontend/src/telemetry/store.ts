// Bounded local storage for playtest telemetry — Wave 3 Batch A1.
//
// Events live in a bounded localStorage ring under one versioned key. This
// module never throws through a player action: storage that is missing, full,
// or corrupted simply means telemetry is skipped for that write while
// gameplay continues untouched. Nothing here reads or writes campaign
// authority — clearing telemetry can never clear campaigns, preferences, or
// canon, which live under their own keys.

import {
  TELEMETRY_SCHEMA_VERSION,
  parseTelemetryEvent,
  type TelemetryEventV1,
} from "./events";

export const TELEMETRY_STORAGE_KEY = "continuity-failure.telemetry.v1";

// Oldest events are evicted beyond this cap. The expected playtest volume is
// far below it; the cap only bounds the worst case.
export const TELEMETRY_EVENT_CAP = 2000;

export type TelemetryStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** window.localStorage when available; null (telemetry disabled) otherwise. */
export function defaultTelemetryStorage(): TelemetryStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/**
 * Read every valid stored event, oldest first.
 *
 * Malformed JSON, non-array payloads, and records that fail the closed-
 * vocabulary validation are silently dropped — stored data re-earns its place
 * on every read.
 */
export function readTelemetryEvents(
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): TelemetryEventV1[] {
  if (!storage) return [];
  let raw: string | null;
  try {
    raw = storage.getItem(TELEMETRY_STORAGE_KEY);
  } catch {
    return [];
  }
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const events: TelemetryEventV1[] = [];
  for (const item of parsed) {
    const event = parseTelemetryEvent(item);
    if (event) events.push(event);
  }
  return events;
}

/**
 * Append one event, evicting the oldest beyond the cap.
 *
 * Returns whether the write landed. `false` (invalid event, no storage, quota
 * exceeded) means telemetry was skipped for this write — never an error the
 * caller must handle.
 */
export function appendTelemetryEvent(
  event: TelemetryEventV1,
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): boolean {
  if (!storage) return false;
  const valid = parseTelemetryEvent(event);
  if (!valid) return false;
  const events = readTelemetryEvents(storage);
  events.push(valid);
  const bounded =
    events.length > TELEMETRY_EVENT_CAP
      ? events.slice(events.length - TELEMETRY_EVENT_CAP)
      : events;
  try {
    storage.setItem(TELEMETRY_STORAGE_KEY, JSON.stringify(bounded));
    return true;
  } catch {
    return false;
  }
}

/** Remove all stored telemetry. Touches only the telemetry key. */
export function clearTelemetryEvents(
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): void {
  try {
    storage?.removeItem(TELEMETRY_STORAGE_KEY);
  } catch {
    // Storage refused the delete; nothing further to do.
  }
}

// --- Collection preference — Wave 3 Batch A2 ---------------------------------
// A local on/off switch under its own key. The switch's state is itself never
// sent anywhere; absent an explicit choice, the build default applies
// (collection on for local development builds, off for packaged builds).

export const TELEMETRY_ENABLED_STORAGE_KEY = "continuity-failure.telemetry-enabled.v1";

export function readTelemetryEnabled(
  defaultEnabled: boolean,
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): boolean {
  if (!storage) return false;
  let stored: string | null;
  try {
    stored = storage.getItem(TELEMETRY_ENABLED_STORAGE_KEY);
  } catch {
    return false;
  }
  if (stored === "on") return true;
  if (stored === "off") return false;
  return defaultEnabled;
}

export function writeTelemetryEnabled(
  enabled: boolean,
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): void {
  try {
    storage?.setItem(TELEMETRY_ENABLED_STORAGE_KEY, enabled ? "on" : "off");
  } catch {
    // The preference simply does not persist; collection still follows it
    // for this page session via component state.
  }
}

// --- Footprint and explicit export — Wave 3 Batch A2 -------------------------

export interface TelemetryFootprint {
  event_count: number;
  first_occurred_at: string | null;
  last_occurred_at: string | null;
  approx_bytes: number;
}

/** What the player sees before deciding to export or clear. */
export function telemetryFootprint(
  storage: TelemetryStorage | null = defaultTelemetryStorage(),
): TelemetryFootprint {
  const events = readTelemetryEvents(storage);
  return {
    event_count: events.length,
    first_occurred_at: events.length > 0 ? events[0].occurred_at : null,
    last_occurred_at: events.length > 0 ? events[events.length - 1].occurred_at : null,
    approx_bytes: events.length > 0 ? JSON.stringify(events).length : 0,
  };
}

export interface TelemetryExportManifestV1 {
  schema_version: typeof TELEMETRY_SCHEMA_VERSION;
  app_version: string;
  ruleset_version: string | null;
  variant_id: string | null;
  exported_at: string;
}

export interface TelemetryExportV1 {
  manifest: TelemetryExportManifestV1;
  events: TelemetryEventV1[];
}

/**
 * Assemble the explicit-download payload: a manifest plus the validated
 * events, nothing else. No campaign snapshot, memo, document, or prose can
 * enter here — the events were already vocabulary-checked on read.
 */
export function buildTelemetryExport(
  events: TelemetryEventV1[],
  manifest: Omit<TelemetryExportManifestV1, "schema_version">,
): TelemetryExportV1 {
  return {
    manifest: { schema_version: TELEMETRY_SCHEMA_VERSION, ...manifest },
    events: events.map((event) => parseTelemetryEvent(event)).filter(
      (event): event is TelemetryEventV1 => event !== null,
    ),
  };
}
