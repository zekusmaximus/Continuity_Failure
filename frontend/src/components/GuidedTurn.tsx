import { useEffect, useRef } from "react";
import type { AdviceMemo, CurrentTurn, TurnHistory, TurnResult } from "../api/client";
import type { Phase } from "../domain";
import { TURN_STEPS } from "../domain";
import CallPhase from "./CallPhase";
import BriefPhase from "./BriefPhase";
import EvidencePhase from "./EvidencePhase";
import AdvicePhase from "./AdvicePhase";
import ClientDecisionPhase from "./ClientDecisionPhase";
import ConsequencesPhase from "./ConsequencesPhase";
import ArchivePhase from "./ArchivePhase";
import CampaignDossier from "./CampaignDossier";
import PrimaryAction from "./PrimaryAction";

interface Props {
  phase: Phase;
  campaignId: string | null;
  current: CurrentTurn | null;
  lastResult: TurnResult | null;
  history: TurnHistory | null;
  terminal: boolean;
  selected: string | null;
  citedDocs: string[];
  onToggleCite: (id: string) => void;
  submitting: boolean;
  onSelect: (id: string) => void;
  onGoto: (phase: Phase) => void;
  onSendAdvice: () => void;
  onNextCall: () => void;
  onOpenDossier: () => void;
  onRestart: () => void;
  onOpenCaseFile: () => void;
  memo: AdviceMemo | null;
  memoLoading: boolean;
  memoSaving: boolean;
  memoError: string | null;
  onDraftMemo: () => void;
  onCreateManualMemo: () => void;
  onSaveMemo: (name: string, content: string) => void;
}

/**
 * The guided stage: renders exactly one phase panel and its single primary
 * action. All turn-flow transitions are decided here, keeping App focused on
 * data and state.
 */
export default function GuidedTurn(props: Props) {
  const {
    phase,
    campaignId,
    current,
    lastResult,
    history,
    terminal,
    selected,
    citedDocs,
    onToggleCite,
    submitting,
    onSelect,
    onGoto,
    onSendAdvice,
    onNextCall,
    onOpenDossier,
    onRestart,
    onOpenCaseFile,
    memo,
    memoLoading,
    memoSaving,
    memoError,
    onDraftMemo,
    onCreateManualMemo,
    onSaveMemo,
  } = props;

  const call = current?.client_call ?? null;
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (document.activeElement?.getAttribute("role") === "tab") return;
    mainRef.current?.focus();
  }, [phase]);

  let panel: React.ReactNode = null;
  let action: React.ReactNode = null;

  switch (phase) {
    case "CALL":
      panel = <CallPhase call={call} disposition={current?.caller_disposition ?? ""} />;
      action = call ? (
        <PrimaryAction
          label="Accept Call"
          hint="Take the call and open the situation brief."
          onClick={() => onGoto("BRIEF")}
        />
      ) : (
        <PrimaryAction
          label="View Campaign Dossier"
          onClick={onOpenDossier}
          busy={submitting}
        />
      );
      break;

    case "BRIEF":
      panel = current ? <BriefPhase call={call} state={current.world_state} /> : null;
      action = (
        <PrimaryAction
          label="Review Evidence"
          hint="Read the record before you advise — or skip straight to advice."
          onClick={() => onGoto("EVIDENCE")}
          secondaryLabel="Skip to Advice"
          onSecondary={() => onGoto("ADVICE")}
        />
      );
      break;

    case "EVIDENCE":
      panel = current ? (
        <EvidencePhase
          documents={current.documents}
          call={call}
          onOpenCaseFile={onOpenCaseFile}
        />
      ) : null;
      action = (
        <PrimaryAction
          label="Continue to Advice"
          hint="Weigh your recommendation options."
          onClick={() => onGoto("ADVICE")}
        />
      );
      break;

    case "ADVICE":
      panel = current ? (
        <AdvicePhase
          options={current.advice_options}
          call={call}
          factions={current.world_state.factions}
          selected={selected}
          onSelect={onSelect}
          memo={memo}
          memoLoading={memoLoading}
          memoSaving={memoSaving}
          memoError={memoError}
          onDraftMemo={onDraftMemo}
          onCreateManualMemo={onCreateManualMemo}
          onSaveMemo={onSaveMemo}
          readOnly={lastResult !== null}
          documents={current.documents}
          citedDocs={citedDocs}
          onToggleCite={onToggleCite}
        />
      ) : null;
      action = (
        <PrimaryAction
          label="Send Advice"
          hint={
            selected
              ? memo
                ? `Send ${memo.name}, revision ${memo.revision}. The client decides what to do with it.`
                : "Create and attach a memo before sending this recommendation."
              : "Select a recommendation to send."
          }
          onClick={onSendAdvice}
          disabled={!selected || !memo || memo.status !== "draft"}
          busy={submitting}
        />
      );
      break;

    case "CLIENT_DECISION":
      panel = lastResult ? <ClientDecisionPhase result={lastResult} /> : null;
      action = (
        <PrimaryAction
          label="Review Consequences"
          hint="The turn is already resolved. Review what the recorded decision set in motion."
          onClick={() => onGoto("CONSEQUENCES")}
        />
      );
      break;

    case "CONSEQUENCES":
      panel = lastResult ? <ConsequencesPhase result={lastResult} /> : null;
      action = (
        <PrimaryAction
          label="Close Turn"
          hint="Close this turn's record and move on."
          onClick={() => onGoto("ARCHIVE")}
        />
      );
      break;

    case "ARCHIVE":
      panel = lastResult ? <ArchivePhase result={lastResult} history={history} /> : null;
      action = terminal ? (
        <PrimaryAction
          label="View Campaign Dossier"
          hint="The engagement has closed. Review the final record."
          onClick={onOpenDossier}
          busy={submitting}
        />
      ) : (
        <PrimaryAction
          label="Next Call"
          hint="Load the next authoritative call. This does not resolve another turn."
          onClick={onNextCall}
          busy={submitting}
        />
      );
      break;

    case "DOSSIER":
      panel = <CampaignDossier campaignId={campaignId} />;
      action = (
        <PrimaryAction
          label="New Engagement"
          hint="Start a fresh Northbridge engagement."
          onClick={onRestart}
          busy={submitting}
        />
      );
      break;

    default:
      panel = null;
  }

  if (lastResult && TURN_STEPS.indexOf(phase) < TURN_STEPS.indexOf("CLIENT_DECISION")) {
    action = (
      <PrimaryAction
        label="Return to Client Decision"
        hint="This turn is already resolved; the earlier record is read-only."
        onClick={() => onGoto("CLIENT_DECISION")}
      />
    );
  }

  return (
    <>
      <main
        ref={mainRef}
        id="main-content"
        className="cd-stage"
        role={TURN_STEPS.includes(phase) ? "tabpanel" : undefined}
        aria-labelledby={TURN_STEPS.includes(phase) ? `cd-phase-tab-${phase.toLowerCase()}` : undefined}
        tabIndex={0}
      >
        <div className="cd-stage-inner">{panel}</div>
      </main>
      {action}
    </>
  );
}
