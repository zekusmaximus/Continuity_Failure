import type { TurnResult } from "../api/client";
import { DECISION_BADGE, titleCase } from "../domain";

function Row({ k, v }: { k: string; v: string }) {
  if (!v) return null;
  return (
    <div className="cd-field">
      <div className="cd-field-k">{k}</div>
      <p className="cd-field-v">{v}</p>
    </div>
  );
}

/**
 * CLIENT_DECISION phase — how the NPC actually used the advice. This is
 * separated from consequences on purpose: the player advises, the client
 * decides, and that gap is the point of the game.
 */
export default function ClientDecisionPhase({ result }: { result: TurnResult }) {
  const d = result.decision;
  return (
    <section className="cd-stage-panel cd-decision">
      <div className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Client decision · Turn {result.turn_number}
      </div>

      <div className="cd-decision-head">
        <span className={`cd-decision-badge ${DECISION_BADGE[d.decision_type] ?? ""}`}>
          {titleCase(d.decision_type)}
        </span>
        <span className="cd-decider">{d.decider}</span>
        <span className="cd-adherence">adherence {Math.round(d.adherence * 100)}%</span>
      </div>

      <Row k="You advised" v={result.advice_label} />
      <Row k="The client did" v={d.rationale || titleCase(d.decision_type)} />
      <Row k="Deviation from advice" v={d.deviation} />
      <Row k="Public explanation" v={d.public_explanation} />
      <Row k="Private motive" v={d.private_motive} />

      {d.resulting_risk && (
        <div className="cd-callout cd-callout-warn">
          <span className="cd-callout-k">Resulting risk</span>
          <span>{d.resulting_risk}</span>
        </div>
      )}
    </section>
  );
}
