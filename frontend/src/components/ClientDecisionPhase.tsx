import type { AdherenceFactor, DecisionExplanation, TurnResult } from "../api/client";
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

const DIRECTION_MARK: Record<string, string> = {
  increase: "▲",
  decrease: "▼",
  neutral: "•",
};

function FactorRow({ factor }: { factor: AdherenceFactor }) {
  const dir = factor.direction || "neutral";
  return (
    <li className={`cd-factor cd-factor-${dir}`}>
      <span className="cd-factor-mark" aria-hidden>
        {DIRECTION_MARK[dir] ?? "•"}
      </span>
      <span className="cd-factor-body">
        <span className="cd-factor-k">{factor.label}</span>
        <span className="cd-factor-v">{factor.detail}</span>
      </span>
    </li>
  );
}

/**
 * The "why" panel: the human-labeled account of how the caller weighed the
 * advice — incentives, conflicts, the adherence factors, and the plain-language
 * outcome reason. No raw internal scores, only labeled factors.
 */
function DecisionRationale({ ex }: { ex: DecisionExplanation }) {
  return (
    <div className="cd-decision-why">
      {ex.off_brief && ex.off_brief_note && (
        <div className="cd-callout cd-callout-warn">
          <span className="cd-callout-k">Off-brief</span>
          <span>{ex.off_brief_note}</span>
        </div>
      )}

      {ex.institutional_mandate && (
        <Row k="Institutional mandate" v={ex.institutional_mandate} />
      )}

      {ex.incentives.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">Caller incentives</div>
          <ul className="cd-why-list">
            {ex.incentives.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {ex.conflicts.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">Conflicts</div>
          <ul className="cd-why-list cd-bad-list">
            {ex.conflicts.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {ex.adherence_factors.length > 0 && (
        <div className="cd-field">
          <div className="cd-field-k">How adherence was weighed</div>
          <ul className="cd-factor-list">
            {ex.adherence_factors.map((f, i) => (
              <FactorRow key={i} factor={f} />
            ))}
          </ul>
        </div>
      )}

      {ex.on_brief_options.length > 0 && (
        <p className="cd-muted cd-onbrief-line">
          On-brief for this call: {ex.on_brief_options.join(", ")}.
        </p>
      )}

      {ex.outcome_reason && (
        <div className="cd-callout">
          <span className="cd-callout-k">Why this outcome</span>
          <span>{ex.outcome_reason}</span>
        </div>
      )}
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
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Client decision · Turn {result.turn_number}
      </h1>

      <div className="cd-decision-head">
        <span className={`cd-decision-badge ${DECISION_BADGE[d.decision_type] ?? ""}`}>
          {titleCase(d.decision_type)}
        </span>
        <span className="cd-decider">{d.decider}</span>
        <span className="cd-adherence">adherence {Math.round(d.adherence * 100)}%</span>
        {d.off_brief && <span className="cd-advice-flag cd-flag-off">Off-brief</span>}
      </div>

      <p className="cd-context-note">
        Adherence shows how much of your recommendation the client carried into
        the resolved turn; deviation records what they changed or withheld.
      </p>

      <Row k="You advised" v={result.advice_label} />
      <Row k="The client did" v={d.rationale || titleCase(d.decision_type)} />
      <Row k="Deviation from advice" v={d.deviation} />
      <Row k="Public explanation" v={d.public_explanation} />
      <Row k="Private motive" v={d.private_motive} />

      {d.explanation && <DecisionRationale ex={d.explanation} />}

      {d.resulting_risk && (
        <div className="cd-callout cd-callout-warn">
          <span className="cd-callout-k">Resulting risk</span>
          <span>{d.resulting_risk}</span>
        </div>
      )}
    </section>
  );
}
