import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type {
  CampaignSummary,
  CurrentTurn,
  TurnHistory,
  TurnResult,
} from "./api/client";
import StatePanel from "./components/StatePanel";
import ClientCallPanel from "./components/ClientCallPanel";
import AdvicePanel from "./components/AdvicePanel";
import AftermathPanel from "./components/AftermathPanel";
import TurnHistoryPanel from "./components/TurnHistory";

export default function App() {
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [current, setCurrent] = useState<CurrentTurn | null>(null);
  const [lastResult, setLastResult] = useState<TurnResult | null>(null);
  const [history, setHistory] = useState<TurnHistory | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

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
    <div className="workstation">
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand">CONTINUITY FAILURE</div>
          <div className="subtitle">Crisis Consulting Workstation</div>
        </div>
        <div className="topbar-center">
          {summary && (
            <>
              <div className="campaign-name">{summary.name}</div>
              <div className="campaign-meta">
                <span>Turn {Math.min(summary.turn_number, summary.max_turns)} / {summary.max_turns}</span>
                <span className={`status-pill status-${summary.status.toLowerCase()}`}>{summary.status}</span>
              </div>
            </>
          )}
        </div>
        <div className="topbar-right">
          <button className="ghost-btn" onClick={startCampaign} disabled={loading || submitting}>
            {loading ? "Starting…" : "Restart Engagement"}
          </button>
        </div>
      </header>

      {error && (
        <div className="alert error">
          <strong>System alert:</strong> {error}
        </div>
      )}

      {terminal && summary && (
        <div className={`alert ${summary.status === "COMPLETED" ? "ok" : "critical"}`}>
          <strong>Engagement {summary.status.toLowerCase()}.</strong>{" "}
          {summary.failure_reason
            ? summary.failure_reason
            : "The 10-turn stabilization window closed without a critical failure."}
        </div>
      )}

      <main className="grid">
        <div className="col col-left">
          {current ? <StatePanel state={current.world_state} /> : <Loading />}
        </div>
        <div className="col col-mid">
          {current ? (
            <>
              <ClientCallPanel call={current.client_call} />
              <AdvicePanel
                options={current.advice_options}
                selected={selected}
                onSelect={setSelected}
                onSubmit={handleSubmit}
                disabled={terminal}
                submitting={submitting}
              />
            </>
          ) : (
            <Loading />
          )}
        </div>
        <div className="col col-right">
          <AftermathPanel result={lastResult} />
          <TurnHistoryPanel history={history} />
        </div>
      </main>

      <footer className="footbar">
        <span>Deterministic engine · Northbridge MVP · AI integration not implemented</span>
      </footer>
    </div>
  );
}

function Loading() {
  return (
    <section className="panel">
      <p className="muted">Initializing workstation…</p>
    </section>
  );
}
