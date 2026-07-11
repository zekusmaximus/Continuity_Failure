import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type { CurrentTurn, TurnHistory } from "../api/client";
import EvidenceBoard from "./EvidenceBoard";
import FactionPanel from "./FactionPanel";
import SystemStatusPanel from "./SystemStatusPanel";
import StateReadout from "./StateReadout";
import CanonPanel from "./CanonPanel";
import TurnHistoryPanel from "./TurnHistory";
import CampaignDossier from "./CampaignDossier";
import ModelRunPanel from "./ModelRunPanel";
import AccessibleDialog from "./AccessibleDialog";
import TelemetryPanel from "./TelemetryPanel";
import { useTelemetry } from "../telemetry/TelemetryProvider";

type Tab =
  | "Evidence"
  | "Factions"
  | "Full State"
  | "Canon"
  | "Timeline"
  | "Model Runs"
  | "Dossier"
  | "Playtest Data";
const TABS: Tab[] = [
  "Evidence",
  "Factions",
  "Full State",
  "Canon",
  "Timeline",
  "Model Runs",
  "Dossier",
  "Playtest Data",
];

// Stable scalar ids for telemetry — display names may change wording.
const TAB_IDS: Record<Tab, string> = {
  Evidence: "evidence",
  Factions: "factions",
  "Full State": "full_state",
  Canon: "canon",
  Timeline: "timeline",
  "Model Runs": "model_runs",
  Dossier: "dossier",
  "Playtest Data": "playtest_data",
};

interface Props {
  open: boolean;
  onClose: () => void;
  campaignId: string | null;
  current: CurrentTurn | null;
  history: TurnHistory | null;
}

/**
 * The Case File: a slide-in drawer holding every dense view that used to crowd
 * the dashboard. Available on demand from any phase, but never the default.
 */
export default function CaseFile({ open, onClose, campaignId, current, history }: Props) {
  const [tab, setTab] = useState<Tab>("Evidence");
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const { report } = useTelemetry();

  // One event per drawer opening, carrying the tab it opened on; further tab
  // selections report through selectTab. The ref survives StrictMode's
  // double effect run.
  const reportedOpen = useRef(false);
  useEffect(() => {
    if (!open) {
      reportedOpen.current = false;
      return;
    }
    if (reportedOpen.current) return;
    reportedOpen.current = true;
    report({ event_type: "case_file_opened", tab_id: TAB_IDS[tab] });
  }, [open, report, tab]);

  const selectTab = (next: Tab) => {
    if (next !== tab) report({ event_type: "case_file_opened", tab_id: TAB_IDS[next] });
    setTab(next);
  };

  const selectByKeyboard = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % TABS.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + TABS.length) % TABS.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = TABS.length - 1;
    else return;
    event.preventDefault();
    selectTab(TABS[next]);
    tabRefs.current[next]?.focus();
  };

  const tabId = `cd-case-tab-${TABS.indexOf(tab)}`;
  const panelId = `cd-case-panel-${TABS.indexOf(tab)}`;

  return (
    <AccessibleDialog
      open={open}
      onClose={onClose}
      overlayClassName="cd-drawer-overlay"
      className="cd-drawer"
      titleId="cd-case-file-title"
    >
      <div className="cd-drawer-head">
        <h2 id="cd-case-file-title">Case File</h2>
        <button
          className="cd-btn cd-btn-ghost cd-modal-close"
          onClick={onClose}
          aria-label="Close Case File"
        >
          ✕
        </button>
      </div>

      <div className="cd-drawer-tabs" role="tablist" aria-label="Case File sections">
          {TABS.map((t, index) => (
            <button
              key={t}
              ref={(node) => { tabRefs.current[index] = node; }}
              id={`cd-case-tab-${index}`}
              role="tab"
              aria-selected={tab === t}
              aria-controls={`cd-case-panel-${index}`}
              tabIndex={tab === t ? 0 : -1}
              className={`cd-drawer-tab ${tab === t ? "cd-drawer-tab-active" : ""}`}
              onClick={() => selectTab(t)}
              onKeyDown={(event) => selectByKeyboard(event, index)}
            >
              {t}
            </button>
          ))}
      </div>

      <div
        className="cd-drawer-body"
        id={panelId}
        role="tabpanel"
        aria-labelledby={tabId}
        tabIndex={0}
      >
          {tab === "Evidence" &&
            (current ? (
              <EvidenceBoard
                documents={current.documents}
                call={current.client_call}
                systemStatus={current.system_status}
              />
            ) : (
              <p className="cd-muted">No evidence loaded.</p>
            ))}
          {tab === "Factions" &&
            (current ? (
              <FactionPanel factions={current.world_state.factions} />
            ) : (
              <p className="cd-muted">No factions loaded.</p>
            ))}
          {tab === "Full State" &&
            (current ? (
              <>
                <SystemStatusPanel status={current.system_status} />
                <StateReadout
                  state={current.world_state}
                  stale={!current.system_status.live_feeds}
                />
              </>
            ) : (
              <p className="cd-muted">No state loaded.</p>
            ))}
          {tab === "Canon" &&
            (history ? (
              <CanonPanel
                canon={history.canon}
                threads={history.open_threads}
                ledger={history.debt_ledger ?? []}
              />
            ) : (
              <p className="cd-muted">No canon on record.</p>
            ))}
          {tab === "Timeline" && <TurnHistoryPanel history={history} />}
          {tab === "Model Runs" && <ModelRunPanel campaignId={campaignId} />}
          {tab === "Dossier" && <CampaignDossier campaignId={campaignId} embedded />}
          {tab === "Playtest Data" && <TelemetryPanel summary={current?.summary ?? null} />}
      </div>
    </AccessibleDialog>
  );
}
