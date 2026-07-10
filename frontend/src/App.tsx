import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type {
  CampaignSummary,
  CurrentTurn,
  TurnHistory,
  TurnResult,
  MemoDraft,
} from "./api/client";
import type { Phase } from "./domain";
import IntroScreen from "./components/IntroScreen";
import ContinuityHeader from "./components/ContinuityHeader";
import GuidedTurn from "./components/GuidedTurn";
import CaseFile from "./components/CaseFile";

const CAMPAIGN_STORAGE_KEY = "continuity-failure.campaign-id";

function readSavedCampaignId(): string | null {
  const fromUrl = new URL(window.location.href).searchParams.get("campaign");
  if (fromUrl) return fromUrl;
  try {
    return window.localStorage.getItem(CAMPAIGN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function saveCampaignId(id: string) {
  try {
    window.localStorage.setItem(CAMPAIGN_STORAGE_KEY, id);
  } catch {
    // URL persistence still works when storage is unavailable.
  }
  const url = new URL(window.location.href);
  url.searchParams.set("campaign", id);
  window.history.replaceState({}, "", url);
}

function clearSavedCampaignId() {
  try {
    window.localStorage.removeItem(CAMPAIGN_STORAGE_KEY);
  } catch {
    // Nothing else to clear when storage is unavailable.
  }
  const url = new URL(window.location.href);
  url.searchParams.delete("campaign");
  window.history.replaceState({}, "", url);
}

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

  // Advisory memo draft for the selected advice option. AI-assist is off by
  // default, so this returns a deterministic fallback unless a live provider is
  // configured. Drafting never advances the turn or changes state.
  const [memo, setMemo] = useState<MemoDraft | null>(null);
  const [memoLoading, setMemoLoading] = useState(false);
  const [memoError, setMemoError] = useState<string | null>(null);

  const refreshCurrent = useCallback(async (id: string) => {
    const cur = await api.getCurrent(id);
    setCurrent(cur);
    setSummary(cur.summary);
    return cur;
  }, []);

  const refreshHistory = useCallback(async (id: string) => {
    setHistory(await api.getTurns(id));
  }, []);

  useEffect(() => {
    const savedId = readSavedCampaignId();
    if (!savedId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([api.getCurrent(savedId), api.getTurns(savedId)])
      .then(([cur, turns]) => {
        if (cancelled) return;
        setCampaignId(savedId);
        setCurrent(cur);
        setSummary(cur.summary);
        setHistory(turns);
        setLastResult(null);
        setSelected(null);
        setPhase(cur.summary.status === "ACTIVE" ? "CALL" : "DOSSIER");
        saveCampaignId(savedId);
      })
      .catch(() => {
        if (cancelled) return;
        clearSavedCampaignId();
        setError(
          "The saved engagement is no longer available. The backend may have restarted; begin a new intake.",
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const startCampaign = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await api.createCampaign();
      setCampaignId(created.id);
      saveCampaignId(created.id);
      setLastResult(null);
      setSelected(null);
      setMemo(null);
      setMemoError(null);
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
      // Keep `current` frozen on the turn that was just resolved. That prevents
      // the header and Case File from exposing the next call, documents, or
      // state before the player closes this turn. History may safely refresh:
      // it contains the new decision/canon record but no next-turn package.
      await refreshHistory(campaignId);
      setPhase("CLIENT_DECISION");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }, [campaignId, selected, refreshHistory]);

  const handleNextCall = useCallback(async () => {
    if (!campaignId) return;
    setLoading(true);
    setError(null);
    try {
      await refreshCurrent(campaignId);
      setSelected(null);
      setLastResult(null);
      setMemo(null);
      setMemoError(null);
      setPhase("CALL");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [campaignId, refreshCurrent]);

  const handleOpenDossier = useCallback(async () => {
    if (!campaignId) return;
    setLoading(true);
    setError(null);
    try {
      await Promise.all([refreshCurrent(campaignId), refreshHistory(campaignId)]);
      setLastResult(null);
      setPhase("DOSSIER");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [campaignId, refreshCurrent, refreshHistory]);

  const handleRestart = useCallback(() => {
    if (
      campaignId &&
      !window.confirm(
        "Start a new engagement? Your current campaign remains on the backend, but this desk will switch to the new engagement.",
      )
    ) {
      return;
    }
    void startCampaign();
  }, [campaignId, startCampaign]);

  const handleDraftMemo = useCallback(async () => {
    if (!campaignId || !selected) return;
    setMemoLoading(true);
    setMemoError(null);
    try {
      const draft = await api.draftMemo(campaignId, selected);
      setMemo(draft);
    } catch (e) {
      setMemo(null);
      setMemoError(e instanceof Error ? e.message : String(e));
    } finally {
      setMemoLoading(false);
    }
  }, [campaignId, selected]);

  const handleSelectAdvice = useCallback(
    (id: string) => {
      // Switching options invalidates any prior memo draft.
      setSelected(id);
      setMemo(null);
      setMemoError(null);
    },
    [],
  );

  const resolvedStatus = lastResult?.status_after ?? summary?.status;
  const terminalReason = lastResult?.failure_reason ?? summary?.failure_reason;
  const terminal = resolvedStatus === "COMPLETED" || resolvedStatus === "FAILED";
  const headerSummary =
    summary && lastResult && phase === "ARCHIVE"
      ? {
          ...summary,
          status: lastResult.status_after,
          failure_reason: lastResult.failure_reason,
        }
      : summary;
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
        summary={headerSummary}
        worldState={current?.world_state ?? null}
        phase={phase}
        onOpenCaseFile={() => setCaseFileOpen(true)}
        onRestart={handleRestart}
        busy={busy}
      />

      {error && (
        <div className="cd-banner-alert cd-alert cd-alert-error">
          <strong>System alert:</strong> {error}
        </div>
      )}

      {terminal && summary && phase === "ARCHIVE" && (
        <div
          className={`cd-banner-alert cd-alert ${
            resolvedStatus === "COMPLETED" ? "cd-alert-ok" : "cd-alert-crit"
          }`}
        >
          <strong>Engagement {resolvedStatus?.toLowerCase()}.</strong>{" "}
          {terminalReason
            ? terminalReason
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
        submitting={busy}
        onSelect={handleSelectAdvice}
        onGoto={setPhase}
        onSendAdvice={handleSendAdvice}
        onNextCall={handleNextCall}
        onOpenDossier={handleOpenDossier}
        onRestart={handleRestart}
        onOpenCaseFile={() => setCaseFileOpen(true)}
        memo={memo}
        memoLoading={memoLoading}
        memoError={memoError}
        onDraftMemo={handleDraftMemo}
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
