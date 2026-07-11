import { useCallback, useEffect, useState } from "react";
import { ApiError, api, newIdempotencyKey } from "./api/client";
import type {
  CampaignSummary,
  CurrentTurn,
  TurnHistory,
  TurnResult,
  AdviceMemo,
  PowerAllocation,
  RecentCampaign,
  ScenarioVariant,
} from "./api/client";
import type { Phase } from "./domain";
import { PHASE_LABEL, TURN_STEPS } from "./domain";
import IntroScreen from "./components/IntroScreen";
import ContinuityHeader from "./components/ContinuityHeader";
import GuidedTurn from "./components/GuidedTurn";
import CaseFile from "./components/CaseFile";
import DeskGuide, { ONBOARDING_STORAGE_KEY } from "./components/DeskGuide";
import { DegradationBanner } from "./components/SystemStatusPanel";

const CAMPAIGN_STORAGE_KEY = "continuity-failure.campaign-id";
const SCENARIO_ID = "northbridge_water_failure";

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

function hasCompletedDeskGuide(): boolean {
  try {
    return window.localStorage.getItem(ONBOARDING_STORAGE_KEY) === "acknowledged";
  } catch {
    return false;
  }
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
  const [maxReachedIndex, setMaxReachedIndex] = useState(0);
  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [summary, setSummary] = useState<CampaignSummary | null>(null);
  const [current, setCurrent] = useState<CurrentTurn | null>(null);
  const [lastResult, setLastResult] = useState<TurnResult | null>(null);
  const [history, setHistory] = useState<TurnHistory | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [citedDocs, setCitedDocs] = useState<string[]>([]);
  // Auxiliary-power allocation for the current turn (CRITICAL band only).
  const [poweredSubsystem, setPoweredSubsystem] = useState<PowerAllocation | null>(null);
  const [caseFileOpen, setCaseFileOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guideFirstRun, setGuideFirstRun] = useState(false);
  const [recentCampaigns, setRecentCampaigns] = useState<RecentCampaign[]>([]);
  const [variants, setVariants] = useState<ScenarioVariant[]>([]);
  const [selectedVariant, setSelectedVariant] = useState<string>("");

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveMessage, setLiveMessage] = useState("");

  // Advisory memo draft for the selected advice option. AI-assist is off by
  // default, so this returns a deterministic fallback unless a live provider is
  // configured. Drafting never advances the turn or changes state.
  const [memo, setMemo] = useState<AdviceMemo | null>(null);
  const [memos, setMemos] = useState<AdviceMemo[]>([]);
  const [memoLoading, setMemoLoading] = useState(false);
  const [memoSaving, setMemoSaving] = useState(false);
  const [memoError, setMemoError] = useState<string | null>(null);

  const gotoPhase = useCallback((next: Phase, announcement?: string) => {
    setPhase(next);
    const index = TURN_STEPS.indexOf(next);
    if (index >= 0) setMaxReachedIndex((currentMax) => Math.max(currentMax, index));
    setLiveMessage(announcement ?? `${PHASE_LABEL[next]} phase.`);
  }, []);

  const showFirstTurnGuide = useCallback((turnNumber: number) => {
    if (turnNumber !== 1 || hasCompletedDeskGuide()) return;
    setGuideFirstRun(true);
    setGuideOpen(true);
  }, []);

  const closeGuide = useCallback(() => {
    try {
      window.localStorage.setItem(ONBOARDING_STORAGE_KEY, "acknowledged");
    } catch {
      // The guide may repeat, but campaign authority never depends on storage.
    }
    setGuideOpen(false);
    setGuideFirstRun(false);
  }, []);

  const openGuide = useCallback(() => {
    setGuideFirstRun(false);
    setGuideOpen(true);
  }, []);

  const refreshCurrent = useCallback(async (id: string) => {
    const cur = await api.getCurrent(id);
    setCurrent(cur);
    setSummary(cur.summary);
    return cur;
  }, []);

  const refreshHistory = useCallback(async (id: string) => {
    setHistory(await api.getTurns(id));
  }, []);

  const refreshMemos = useCallback(async (id: string) => {
    const records = await api.getMemos(id);
    setMemos(records);
    return records;
  }, []);

  const reopenCampaign = useCallback(async (id: string) => {
    const [cur, turns, memoRecords, presentation] = await Promise.all([
      api.getCurrent(id),
      api.getTurns(id),
      api.getMemos(id),
      api.getPresentation(id),
    ]);
    setCampaignId(id);
    setHistory(turns);
    setMemos(memoRecords);
    setMemoError(null);
    if (presentation) {
      const frozen = presentation.current_turn;
      const result = presentation.result;
      setCurrent(frozen);
      setSummary(frozen.summary);
      setLastResult(result);
      setSelected(result.advice_id);
      setCitedDocs(result.decision.cited_document_ids ?? []);
      setPoweredSubsystem(result.powered_subsystem);
      setMemo(
        memoRecords.find((item) => item.id === result.sent_memo?.memo_id) ?? null,
      );
      setMaxReachedIndex(TURN_STEPS.indexOf("CLIENT_DECISION"));
      gotoPhase(
        "CLIENT_DECISION",
        `Turn ${result.turn_number} remains resolved. Review it before loading the next call.`,
      );
    } else if (cur.summary.status === "ACTIVE") {
      setCurrent(cur);
      setSummary(cur.summary);
      setLastResult(null);
      setSelected(null);
      setCitedDocs([]);
      setPoweredSubsystem(null);
      setMemo(null);
      setMaxReachedIndex(0);
      gotoPhase("CALL", `Turn ${cur.summary.turn_number} incoming call loaded.`);
      showFirstTurnGuide(cur.summary.turn_number);
    } else {
      setCurrent(cur);
      setSummary(cur.summary);
      setLastResult(null);
      setSelected(null);
      setCitedDocs([]);
      setPoweredSubsystem(null);
      setMemo(null);
      setMaxReachedIndex(TURN_STEPS.length - 1);
      gotoPhase("DOSSIER", "Campaign dossier loaded.");
    }
    saveCampaignId(id);
  }, [gotoPhase, showFirstTurnGuide]);

  useEffect(() => {
    const savedId = readSavedCampaignId();
    let cancelled = false;
    setLoading(true);
    setError(null);
    void (async () => {
      // Seed variants are presentation sugar on the intake screen: if the
      // fetch fails, the selector simply doesn't render.
      try {
        const available = await api.listScenarioVariants(SCENARIO_ID);
        if (!cancelled) setVariants(available);
      } catch {
        if (!cancelled) setVariants([]);
      }
      try {
        const recent = await api.listRecentCampaigns();
        if (!cancelled) setRecentCampaigns(recent);
      } catch (e) {
        if (!cancelled && !savedId) {
          setError(
            `Could not load saved engagements: ${
              e instanceof Error ? e.message : String(e)
            }`,
          );
        }
      }

      if (savedId) {
        try {
          await reopenCampaign(savedId);
        } catch (e) {
          if (!cancelled) {
            clearSavedCampaignId();
            setError(
              `The saved engagement could not be reopened: ${
                e instanceof Error ? e.message : String(e)
              }. Choose another recent engagement or begin a new intake.`,
            );
          }
        }
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [reopenCampaign]);

  const handleResume = useCallback(
    async (id: string) => {
      setLoading(true);
      setError(null);
      try {
        await reopenCampaign(id);
      } catch (e) {
        if (readSavedCampaignId() === id) clearSavedCampaignId();
        setError(
          `Engagement ${id} could not be reopened: ${
            e instanceof Error ? e.message : String(e)
          }. It may have been deleted or its record may be damaged.`,
        );
      } finally {
        setLoading(false);
      }
    },
    [reopenCampaign],
  );

  const startCampaign = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await api.createCampaign(undefined, selectedVariant || undefined);
      setCampaignId(created.id);
      saveCampaignId(created.id);
      setLastResult(null);
      setSelected(null);
      setCitedDocs([]);
      setPoweredSubsystem(null);
      setMemo(null);
      setMemoError(null);
      const [cur] = await Promise.all([refreshCurrent(created.id), refreshHistory(created.id)]);
      setMemos([]);
      setMaxReachedIndex(0);
      gotoPhase("CALL", "Turn 1 incoming call loaded.");
      showFirstTurnGuide(cur.summary.turn_number);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [gotoPhase, refreshCurrent, refreshHistory, showFirstTurnGuide, selectedVariant]);

  const handleSendAdvice = useCallback(async () => {
    if (!campaignId || !selected || !current || !memo || submitting) return;
    // The CRITICAL-band constraint: the backend will 409 without an
    // allocation, so hold the submission client-side with the same rule.
    if (current.system_status.requires_power_allocation && !poweredSubsystem) {
      setError(
        "The workstation is critical: allocate auxiliary power to one "
        + "subsystem before sending advice.",
      );
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      // One key per deliberate submission. `api.submitAdvice` reuses it for its
      // own transport retries, so a dropped response never resolves a second
      // turn. `expected_turn` pins the revision this advice was composed for.
      const result = await api.submitAdvice(
        campaignId,
        selected,
        current.summary.turn_number,
        newIdempotencyKey(),
        memo.id,
        memo.revision,
        citedDocs,
        current.system_status.requires_power_allocation ? poweredSubsystem : null,
      );
      setLastResult(result);
      setMemo((record) => record ? { ...record, status: "sent", sent_snapshot: result.sent_memo } : record);
      // Keep `current` frozen on the turn that was just resolved. That prevents
      // the header and Case File from exposing the next call, documents, or
      // state before the player closes this turn. History may safely refresh:
      // it contains the new decision/canon record but no next-turn package.
      await refreshHistory(campaignId);
      gotoPhase(
        "CLIENT_DECISION",
        `Turn ${result.turn_number} resolved. Client decision available.`,
      );
    } catch (e) {
      if (e instanceof ApiError && (e.code === "stale_turn" || e.code === "campaign_terminal")) {
        // The backend holds newer state than this desk. Resync rather than let
        // the player resubmit against a revision that no longer exists.
        setError(`${e.message} Reloading the engagement record.`);
        try {
          await Promise.all([refreshCurrent(campaignId), refreshHistory(campaignId)]);
        } catch {
          /* keep the original conflict message */
        }
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setSubmitting(false);
    }
  }, [campaignId, selected, citedDocs, current, submitting, memo, refreshCurrent, refreshHistory, gotoPhase]);

  const handleNextCall = useCallback(async () => {
    if (!campaignId || !lastResult) return;
    setLoading(true);
    setError(null);
    try {
      await api.acknowledgePresentation(campaignId, lastResult.turn_number);
      await reopenCampaign(campaignId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [campaignId, lastResult, reopenCampaign]);

  const handleOpenDossier = useCallback(async () => {
    if (!campaignId) return;
    setLoading(true);
    setError(null);
    try {
      if (lastResult) {
        await api.acknowledgePresentation(campaignId, lastResult.turn_number);
      }
      await Promise.all([refreshCurrent(campaignId), refreshHistory(campaignId)]);
      setLastResult(null);
      gotoPhase("DOSSIER", "Campaign dossier loaded.");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [campaignId, lastResult, refreshCurrent, refreshHistory, gotoPhase]);

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
      const option = current?.advice_options.find((item) => item.id === selected);
      const draft = await api.createMemo(campaignId, {
        creation_mode: "ai",
        advice_id: selected,
        name: `Advice of record — ${option?.title || option?.label || selected}`,
        ...(current?.system_status.requires_power_allocation && poweredSubsystem
          ? { powered_subsystem: poweredSubsystem }
          : {}),
      });
      setMemo(draft);
      setMemos((records) => [...records, draft]);
    } catch (e) {
      setMemo(null);
      setMemoError(e instanceof Error ? e.message : String(e));
    } finally {
      setMemoLoading(false);
    }
  }, [campaignId, selected, current, poweredSubsystem]);

  const handleCreateManualMemo = useCallback(async () => {
    if (!campaignId || !selected || !current) return;
    const option = current.advice_options.find((item) => item.id === selected);
    if (!option) return;
    setMemoLoading(true);
    setMemoError(null);
    try {
      const created = await api.createMemo(campaignId, {
        creation_mode: "template",
        advice_id: selected,
        name: `Advice of record — ${option.title || option.label}`,
      });
      setMemo(created);
      setMemos((records) => [...records, created]);
    } catch (e) {
      setMemoError(e instanceof Error ? e.message : String(e));
    } finally {
      setMemoLoading(false);
    }
  }, [campaignId, selected, current]);

  const handleSaveMemo = useCallback(async (name: string, content: string) => {
    if (!campaignId || !memo) return;
    setMemoSaving(true);
    setMemoError(null);
    try {
      const updated = await api.updateMemo(campaignId, memo.id, {
        expected_revision: memo.revision,
        name,
        content,
      });
      setMemo(updated);
      setMemos((records) => records.map((item) => item.id === updated.id ? updated : item));
    } catch (e) {
      setMemoError(e instanceof Error ? e.message : String(e));
      if (e instanceof ApiError && e.code === "stale_memo_revision") {
        await refreshMemos(campaignId).catch(() => undefined);
      }
    } finally {
      setMemoSaving(false);
    }
  }, [campaignId, memo, refreshMemos]);

  const handleToggleCite = useCallback((docId: string) => {
    // At CRITICAL, evidence verification runs on the live-data circuit: no
    // citations unless auxiliary power is allocated there.
    if (
      current?.system_status.requires_power_allocation &&
      poweredSubsystem !== "LIVE_DATA"
    ) {
      return;
    }
    setCitedDocs((ids) =>
      ids.includes(docId)
        ? ids.filter((d) => d !== docId)
        : ids.length >= 3
          ? ids
          : [...ids, docId],
    );
  }, [current, poweredSubsystem]);

  const handleAllocatePower = useCallback((allocation: PowerAllocation) => {
    setPoweredSubsystem(allocation);
    // Moving auxiliary power off the live-data circuit invalidates any
    // citations composed under it.
    if (allocation !== "LIVE_DATA") setCitedDocs([]);
  }, []);

  const handleSelectAdvice = useCallback(
    (id: string) => {
      // Switching options invalidates any prior memo draft.
      setSelected(id);
      setMemo(
        memos.find((item) => item.status === "draft" && item.advice_id === id) ?? null,
      );
      setMemoError(null);
    },
    [memos],
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
        <a className="cd-skip-link" href="#main-content">Skip to main content</a>
        <IntroScreen
          onBegin={startCampaign}
          onResume={handleResume}
          recentCampaigns={recentCampaigns}
          loading={loading}
          variants={variants}
          selectedVariant={selectedVariant}
          onVariantChange={setSelectedVariant}
        />
        {error && (
          <div className="cd-banner-alert cd-alert cd-alert-error" role="alert">
            <strong>System alert:</strong> {error}
          </div>
        )}
        <div className="cd-sr-only" role="status" aria-live="polite" aria-atomic="true">
          {loading ? "Opening continuity desk." : ""}
        </div>
      </div>
    );
  }

  const systemStatus = current?.system_status ?? null;
  const degradedClass =
    systemStatus && systemStatus.degradation_band !== "NOMINAL"
      ? ` cd-degraded-${systemStatus.degradation_band.toLowerCase()}`
      : "";

  return (
    <div className={`cd-app${degradedClass}`}>
      <a className="cd-skip-link" href="#main-content">Skip to main content</a>
      <ContinuityHeader
        summary={headerSummary}
        worldState={current?.world_state ?? null}
        phase={phase}
        maxReachedIndex={maxReachedIndex}
        onGoto={gotoPhase}
        onOpenCaseFile={() => setCaseFileOpen(true)}
        onOpenGuide={openGuide}
        onRestart={handleRestart}
        busy={busy}
      />

      <DegradationBanner status={systemStatus} />

      {error && (
        <div className="cd-banner-alert cd-alert cd-alert-error" role="alert">
          <strong>System alert:</strong> {error}
        </div>
      )}

      {terminal && summary && phase === "ARCHIVE" && (
        <div
          className={`cd-banner-alert cd-alert ${
            resolvedStatus === "COMPLETED" ? "cd-alert-ok" : "cd-alert-crit"
          }`}
          role="status"
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
        citedDocs={citedDocs}
        onToggleCite={handleToggleCite}
        poweredSubsystem={poweredSubsystem}
        onAllocatePower={handleAllocatePower}
        submitting={busy}
        onSelect={handleSelectAdvice}
        onGoto={gotoPhase}
        onSendAdvice={handleSendAdvice}
        onNextCall={handleNextCall}
        onOpenDossier={handleOpenDossier}
        onRestart={handleRestart}
        onOpenCaseFile={() => setCaseFileOpen(true)}
        memo={memo}
        memoLoading={memoLoading}
        memoSaving={memoSaving}
        memoError={memoError}
        onDraftMemo={handleDraftMemo}
        onCreateManualMemo={handleCreateManualMemo}
        onSaveMemo={handleSaveMemo}
      />

      <CaseFile
        open={caseFileOpen}
        onClose={() => setCaseFileOpen(false)}
        campaignId={campaignId}
        current={current}
        history={history}
      />

      <DeskGuide open={guideOpen} firstRun={guideFirstRun} onClose={closeGuide} />

      <div className="cd-sr-only" role="status" aria-live="polite" aria-atomic="true">
        {loading
          ? "Desk request in progress."
          : submitting
            ? "Resolving turn."
            : liveMessage}
      </div>
    </div>
  );
}
