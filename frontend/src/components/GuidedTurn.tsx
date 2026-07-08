import type { CurrentTurn, TurnHistory, TurnResult } from "../api/client";
import type { Phase } from "../domain";
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
  submitting: boolean;
  onSelect: (id: string) => void;
  onGoto: (phase: Phase) => void;
  onSendAdvice: () => void;
  onNextCall: () => void;
  onRestart: () => void;
  onOpenCaseFile: () => void;
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
    submitting,
    onSelect,
    onGoto,
    onSendAdvice,
    onNextCall,
    onRestart,
    onOpenCaseFile,
  } = props;

  const call = current?.client_call ?? null;

  let panel: React.ReactNode = null;
  let action: React.ReactNode = null;

  switch (phase) {
    case "CALL":
      panel = <CallPhase call={call} />;
      action = call ? (
        <PrimaryAction
          label="Accept Call"
          hint="Take the call and open the situation brief."
          onClick={() => onGoto("BRIEF")}
        />
      ) : (
        <PrimaryAction label="View Campaign Dossier" onClick={() => onGoto("DOSSIER")} />
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
          factions={current.world_state.factions}
          selected={selected}
          onSelect={onSelect}
        />
      ) : null;
      action = (
        <PrimaryAction
          label="Send Advice"
          hint={
            selected
              ? "Transmit your recommendation. The client decides what to do with it."
              : "Select a recommendation to send."
          }
          onClick={onSendAdvice}
          disabled={!selected}
          busy={submitting}
        />
      );
      break;

    case "CLIENT_DECISION":
      panel = lastResult ? <ClientDecisionPhase result={lastResult} /> : null;
      action = (
        <PrimaryAction
          label="Resolve Consequences"
          hint="See what your advice — and the client's decision — set in motion."
          onClick={() => onGoto("CONSEQUENCES")}
        />
      );
      break;

    case "CONSEQUENCES":
      panel = lastResult ? <ConsequencesPhase result={lastResult} /> : null;
      action = (
        <PrimaryAction
          label="Archive Turn"
          hint="File this turn to the record and move on."
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
          onClick={() => onGoto("DOSSIER")}
        />
      ) : (
        <PrimaryAction
          label="Next Call"
          hint="Take the next incoming call."
          onClick={onNextCall}
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
        />
      );
      break;

    default:
      panel = null;
  }

  return (
    <>
      <main className="cd-stage">
        <div className="cd-stage-inner">{panel}</div>
      </main>
      {action}
    </>
  );
}
