// Telemetry instrumentation boundary — Wave 3 Batch A2.
//
// One hook owns collection at the app root; components report typed intents
// through context and never write storage directly. Reporting is fire-and-
// forget and can never throw through a player action; when collection is off
// (the packaged-build default) every report is a no-op.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { TelemetryPhase } from "./events";
import {
  stampTelemetryEvent,
  type TelemetryContext as TelemetryEventContext,
  type TelemetryIntent,
} from "./session";
import {
  appendTelemetryEvent,
  defaultTelemetryStorage,
  readTelemetryEnabled,
  writeTelemetryEnabled,
  type TelemetryStorage,
} from "./store";

export interface TelemetryApi {
  /** Fire-and-forget: stamp the intent with ambient context and store it. */
  report: (intent: TelemetryIntent) => void;
  enabled: boolean;
  setEnabled: (on: boolean) => void;
  storage: TelemetryStorage | null;
}

const noop = () => undefined;

// Default value keeps components renderable (and existing tests green)
// without a provider: reporting is simply off.
const TelemetryReactContext = createContext<TelemetryApi>({
  report: noop,
  enabled: false,
  setEnabled: noop,
  storage: null,
});

export function useTelemetry(): TelemetryApi {
  return useContext(TelemetryReactContext);
}

export function TelemetryProvider({
  value,
  children,
}: {
  value: TelemetryApi;
  children: ReactNode;
}) {
  return (
    <TelemetryReactContext.Provider value={value}>
      {children}
    </TelemetryReactContext.Provider>
  );
}

export interface DeskTelemetryOptions {
  campaignId: string | null;
  turnNumber: number | null;
  phase: TelemetryPhase | null;
  /** Test injection; defaults to window.localStorage when available. */
  storage?: TelemetryStorage | null;
  /** Test injection; defaults to Date.now. */
  now?: () => number;
  /** Collection default absent an explicit player choice. */
  collectByDefault?: boolean;
}

interface OpenPhase {
  phase: TelemetryPhase;
  campaignId: string | null;
  turnNumber: number | null;
  enteredAt: number;
}

/**
 * The app-root telemetry engine.
 *
 * Measures phase dwell time with paired enter/leave events, flushing the open
 * phase on phase change, campaign change, and (best-effort) page hide, where
 * it also records `desk_session_ended` with the last phase and turn seen.
 */
export function useDeskTelemetry(options: DeskTelemetryOptions): TelemetryApi {
  const { campaignId, turnNumber, phase } = options;
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const storage = useMemo(
    () => (options.storage !== undefined ? options.storage : defaultTelemetryStorage()),
    // The storage handle is bound once per mount; swapping it mid-session is
    // not a supported flow.
    [],
  );

  // Collection defaults on for local development builds and off for packaged
  // builds until the player flips the local switch.
  const [enabled, setEnabledState] = useState(() =>
    readTelemetryEnabled(options.collectByDefault ?? import.meta.env.DEV, storage),
  );
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  const emit = useCallback(
    (intent: TelemetryIntent, context: TelemetryEventContext) => {
      if (!enabledRef.current) return;
      try {
        const now = optionsRef.current.now ?? Date.now;
        appendTelemetryEvent(stampTelemetryEvent(intent, context, new Date(now())), storage);
      } catch {
        // Telemetry never throws through a player action.
      }
    },
    [storage],
  );

  const report = useCallback(
    (intent: TelemetryIntent) => {
      const { campaignId: campaign_id, turnNumber: turn_number, phase: ambient } =
        optionsRef.current;
      emit(intent, { campaign_id, turn_number, phase: ambient });
    },
    [emit],
  );

  const setEnabled = useCallback(
    (on: boolean) => {
      setEnabledState(on);
      enabledRef.current = on;
      // The switch's state is stored locally only and never reported anywhere.
      writeTelemetryEnabled(on, storage);
    },
    [storage],
  );

  // Paired enter/leave phase timing. The ref survives StrictMode's double
  // effect run, so re-running with unchanged context emits nothing.
  const openPhaseRef = useRef<OpenPhase | null>(null);
  useEffect(() => {
    const open = openPhaseRef.current;
    if (
      open &&
      open.phase === phase &&
      open.campaignId === campaignId &&
      open.turnNumber === turnNumber
    ) {
      return;
    }
    const now = optionsRef.current.now ?? Date.now;
    const at = now();
    if (open) {
      emit(
        { event_type: "phase_left", phase: open.phase, elapsed_ms: at - open.enteredAt },
        { campaign_id: open.campaignId, turn_number: open.turnNumber },
      );
    }
    if (phase) {
      emit(
        { event_type: "phase_entered", phase },
        { campaign_id: campaignId, turn_number: turnNumber },
      );
      openPhaseRef.current = { phase, campaignId, turnNumber, enteredAt: at };
    } else {
      openPhaseRef.current = null;
    }
  }, [phase, campaignId, turnNumber, emit]);

  // Best-effort session end: flush the open phase and record the last phase
  // and turn seen. Browser close is not proof of abandonment and the export
  // never labels it as such.
  useEffect(() => {
    const onPageHide = () => {
      const open = openPhaseRef.current;
      const now = optionsRef.current.now ?? Date.now;
      if (open) {
        emit(
          {
            event_type: "phase_left",
            phase: open.phase,
            elapsed_ms: now() - open.enteredAt,
          },
          { campaign_id: open.campaignId, turn_number: open.turnNumber },
        );
        openPhaseRef.current = null;
      }
      const { campaignId: campaign_id, turnNumber: turn_number, phase: ambient } =
        optionsRef.current;
      emit({ event_type: "desk_session_ended" }, { campaign_id, turn_number, phase: ambient });
    };
    window.addEventListener("pagehide", onPageHide);
    return () => window.removeEventListener("pagehide", onPageHide);
  }, [emit]);

  return useMemo(
    () => ({ report, enabled, setEnabled, storage }),
    [report, enabled, setEnabled, storage],
  );
}
