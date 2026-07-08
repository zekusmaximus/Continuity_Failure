import { useCallback, useState } from "react";
import { api } from "./api/client";
import type {
  CampaignSummary,
  CurrentTurn,
  TurnHistory,
  TurnResult,
} from "./api/client";
import type { Phase } from "./domain";
import IntroScreen from "./components/IntroScreen";
import ContinuityHeader from "./components/ContinuityHeader";
import GuidedTurn from "./components/GuidedTurn";
import CaseFile from "./components/CaseFile";

/**
 * Continuity Desk — Guided Intake.
 *
 * The app walks the player through one focused task per screen:
 *   INTRO → CALL → BRIEF → EVIDENCE → ADVICE → CLIENT_DECISION →
 *   CONSEQUENCES → ARCHIVE → (next call | DOSSIER)
 *
 * The backend still resolves the NPC decision and consequences together on
 * advice submission; that single TurnResult is stored and revealed across the
 * CLIENT_DECISION / CONSEQUENCES / ARCHIVE phases. Dense data lives in the
 * Case File drawer, never in the default view.
 */
export default function App() {
  const [phase, setPhase] = useState<Phase>("INTRO");
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [current, setCurrent] = useState<CurrentTurn | null>(null);
  const [lastResult, setLastResult] = useState<TurnResult | null>(null);
  const [history, setHistory] = useState<TurnHistory | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [caseFileOpen, setCaseFileOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshCurrent = useCallback(async (id: string) => {
    const cur = await api.getCurrent(id);
    setCurrent(cur);
    setSummary(cur.summary);
    return cur;
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
      setLastResult(null);
      setSelected(null);
      await Promise.all([refreshCurrent(created.id), refreshHistory(created.id)]);
      setPhase("CALL");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [refreshCurrent, refreshHistory]);

  const handleSendAdvice = useCallback(async () => {
    if (!campaignId || !selected) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.submitAdvice(campaignId, selected);
      setLastResult(result);
      // Refresh state/history so the header + Case File reflect the resolved
      // turn, then reveal the outcome across the decision → consequences →
      // archive phases.
      await Promise.all([refreshCurrent(campaignId), refreshHistory(campaignId)]);
      setPhase("CLIENT_DECISION");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [campaignId, selected, refreshCurrent, refreshHistory]);

  const handleNextCall = useCallback(() => {
    // `current` was already refreshed after submit and now holds the next call.
    setSelected(null);
    setLastResult(null);
    setPhase("CALL");
  }, []);

  const terminal = summary?.status === "COMPLETED" || summary?.status === "FAILED";
  const busy = loading || submitting;

  if (phase === "INTRO") {
    return (
      <div className="cd-app cd-app-intro">
        <IntroScreen onBegin={startCampaign} loading={loading} />
        {error && (
          <div className="cd-banner-alert cd-alert cd-alert-error">
            <strong>System alert:</strong> {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="cd-app">
      <ContinuityHeader
        summary={summary}
        worldState={current?.world_state ?? null}
        phase={phase}
        onOpenCaseFile={() => setCaseFileOpen(true)}
        onRestart={startCampaign}
        busy={busy}
      />

      {error && (
        <div className="cd-banner-alert cd-alert cd-alert-error">
          <strong>System alert:</strong> {error}
        </div>
      )}

      {terminal && summary && phase !== "DOSSIER" && (
        <div
          className={`cd-banner-alert cd-alert ${
            summary.status === "COMPLETED" ? "cd-alert-ok" : "cd-alert-crit"
          }`}
        >
          <strong>Engagement {summary.status.toLowerCase()}.</strong>{" "}
          {summary.failure_reason
            ? summary.failure_reason
            : "The 10-turn stabilization window closed without a critical failure."}
        </div>
      )}

      <GuidedTurn
        phase={phase}
        campaignId={campaignId}
        current={current}
        lastResult={lastResult}
        history={history}
        terminal={terminal}
        selected={selected}
        submitting={submitting}
        onSelect={setSelected}
        onGoto={setPhase}
        onSendAdvice={handleSendAdvice}
        onNextCall={handleNextCall}
        onRestart={startCampaign}
        onOpenCaseFile={() => setCaseFileOpen(true)}
      />

      <CaseFile
        open={caseFileOpen}
        onClose={() => setCaseFileOpen(false)}
        campaignId={campaignId}
        current={current}
        history={history}
      />
    </div>
  );
}
