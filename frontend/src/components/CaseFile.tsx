import { useEffect, useState } from "react";
import type { CurrentTurn, TurnHistory } from "../api/client";
import EvidenceBoard from "./EvidenceBoard";
import FactionPanel from "./FactionPanel";
import StateReadout from "./StateReadout";
import CanonPanel from "./CanonPanel";
import TurnHistoryPanel from "./TurnHistory";
import CampaignDossier from "./CampaignDossier";
import ModelRunPanel from "./ModelRunPanel";

type Tab = "Evidence" | "Factions" | "Full State" | "Canon" | "Timeline" | "Model Runs" | "Dossier";
const TABS: Tab[] = ["Evidence", "Factions", "Full State", "Canon", "Timeline", "Model Runs", "Dossier"];

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

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="cd-drawer-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cd-case-file-title"
      onClick={onClose}
    >
      <aside className="cd-drawer" onClick={(e) => e.stopPropagation()}>
        <header className="cd-drawer-head">
          <h2 id="cd-case-file-title">Case File</h2>
          <button className="cd-btn cd-btn-ghost cd-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        <nav className="cd-drawer-tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={`cd-drawer-tab ${tab === t ? "cd-drawer-tab-active" : ""}`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </nav>

        <div className="cd-drawer-body">
          {tab === "Evidence" &&
            (current ? (
              <EvidenceBoard documents={current.documents} call={current.client_call} />
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
              <StateReadout state={current.world_state} />
            ) : (
              <p className="cd-muted">No state loaded.</p>
            ))}
          {tab === "Canon" &&
            (history ? (
              <CanonPanel canon={history.canon} threads={history.open_threads} />
            ) : (
              <p className="cd-muted">No canon on record.</p>
            ))}
          {tab === "Timeline" && <TurnHistoryPanel history={history} />}
          {tab === "Model Runs" && <ModelRunPanel campaignId={campaignId} />}
          {tab === "Dossier" && <CampaignDossier campaignId={campaignId} embedded />}
        </div>
      </aside>
    </div>
  );
}
