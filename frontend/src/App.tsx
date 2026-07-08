import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type {
  CampaignSummary,
  CurrentTurn,
  TurnHistory,
  TurnResult,
} from "./api/client";
import ContinuityHeader from "./components/ContinuityHeader";
import SystemStatusPanel from "./components/SystemStatusPanel";
import CrisisBriefPanel from "./components/CrisisBriefPanel";
import ClientCallPanel from "./components/ClientCallPanel";
import EvidenceBoard from "./components/EvidenceBoard";
import AdviceWorkbench from "./components/AdviceWorkbench";
import FactionPanel from "./components/FactionPanel";
import StateReadout from "./components/StateReadout";
import ConsequenceStack from "./components/ConsequenceStack";
import CanonPanel from "./components/CanonPanel";
import TurnHistoryPanel from "./components/TurnHistory";
import CampaignDossier from "./components/CampaignDossier";

export default function App() {
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [current, setCurrent] = useState<CurrentTurn | null>(null);
  const [lastResult, setLastResult] = useState<TurnResult | null>(null);
  const [history, setHistory] = useState<TurnHistory | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [dossierOpen, setDossierOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshCurrent = useCallback(async (id: string) => {
    const cur = await api.getCurrent(id);
    setCurrent(cur);
    setSummary(cur.summary);
    setLastResult(cur.last_turn);
    setSelected(null);
  }, []);

  const refreshHistory = useCallback(async (id: string) => {
    setHistory(await api.getTurns(id));
  }, []);

  const startCampaign = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await api.createCampaign();
      setCampaignId(created.id);
      await Promise.all([refreshCurrent(created.id), refreshHistory(created.id)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [refreshCurrent, refreshHistory]);

  useEffect(() => {
    if (!campaignId) startCampaign();
  }, [campaignId, startCampaign]);

  const handleSubmit = useCallback(async () => {
    if (!campaignId || !selected) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.submitAdvice(campaignId, selected);
      setLastResult(result);
      await Promise.all([refreshCurrent(campaignId), refreshHistory(campaignId)]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [campaignId, selected, refreshCurrent, refreshHistory]);

  const terminal = summary?.status === "COMPLETED" || summary?.status === "FAILED";

  return (
    <div className="cd-workstation">
      <ContinuityHeader
        summary={summary}
        loading={loading}
        submitting={submitting}
        onRestart={startCampaign}
        onOpenDossier={() => setDossierOpen(true)}
      />

      {error && (
        <div className="cd-alert cd-alert-error cd-banner-alert">
          <strong>System alert:</strong> {error}
        </div>
      )}

      {terminal && summary && (
        <div className={`cd-banner-alert cd-alert ${summary.status === "COMPLETED" ? "cd-alert-ok" : "cd-alert-crit"}`}>
          <strong>Engagement {summary.status.toLowerCase()}.</strong>{" "}
          {summary.failure_reason
            ? summary.failure_reason
            : "The 10-turn stabilization window closed without a critical failure."}
          <button className="cd-btn cd-btn-ghost cd-inline" onClick={() => setDossierOpen(true)}>
            Review dossier
          </button>
        </div>
      )}

      <main className="cd-main">
        {/* Top row: Client Call · Crisis Brief · System Status */}
        <section className="cd-row cd-row-3">
          <div className="cd-cell">
            {current ? <ClientCallPanel call={current.client_call} /> : <Placeholder />}
          </div>
          <div className="cd-cell">
            {current ? (
              <CrisisBriefPanel call={current.client_call} state={current.world_state} />
            ) : (
              <Placeholder />
            )}
          </div>
          <div className="cd-cell">
            {current ? <SystemStatusPanel status={current.system_status} /> : <Placeholder />}
          </div>
        </section>

        {/* Mid row: Evidence Board · Advice Workbench · Factions */}
        <section className="cd-row cd-row-3">
          <div className="cd-cell">
            {current ? (
              <EvidenceBoard documents={current.documents} call={current.client_call} />
            ) : (
              <Placeholder />
            )}
          </div>
          <div className="cd-cell">
            {current ? (
              <AdviceWorkbench
                options={current.advice_options}
                factions={current.world_state.factions}
                selected={selected}
                onSelect={setSelected}
                onSubmit={handleSubmit}
                disabled={terminal}
                submitting={submitting}
              />
            ) : (
              <Placeholder />
            )}
          </div>
          <div className="cd-cell">
            {current ? (
              <FactionPanel factions={current.world_state.factions} />
            ) : (
              <Placeholder />
            )}
          </div>
        </section>

        {/* Full-width operational state readout */}
        <section className="cd-row cd-row-1">
          {current ? <StateReadout state={current.world_state} /> : <Placeholder />}
        </section>

        {/* Aftermath: consequence stack */}
        <section className="cd-row cd-row-1">
          <ConsequenceStack result={lastResult} />
        </section>

        {/* Archive: canon/threads + turn history */}
        <section className="cd-row cd-row-2">
          <div className="cd-cell">
            {history ? (
              <CanonPanel canon={history.canon} threads={history.open_threads} />
            ) : (
              <Placeholder />
            )}
          </div>
          <div className="cd-cell">
            <TurnHistoryPanel history={history} />
          </div>
        </section>
      </main>

      <footer className="cd-footbar">
        <span>CONTINUITY DESK · Deterministic engine · Northbridge MVP · AI systems unavailable in current build</span>
      </footer>

      <CampaignDossier
        campaignId={campaignId}
        open={dossierOpen}
        onClose={() => setDossierOpen(false)}
      />
    </div>
  );
}

function Placeholder() {
  return (
    <section className="cd-panel">
      <p className="cd-muted">Initializing workstation…</p>
    </section>
  );
}
