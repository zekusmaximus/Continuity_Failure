import type { TurnResult } from "../api/client";
import { DECISION_BADGE, titleCase } from "../domain";
import AppliedDiffList from "./AppliedDiffList";

function StackSection({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className={`cd-stack-sec cd-stack-${tone}`}>
      <div className="cd-subhead">{title}</div>
      <ul className="cd-stack-list">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}

function MediationRow({ k, v }: { k: string; v: string }) {
  if (!v) return null;
  return (
    <div className="cd-med-row">
      <span className="cd-meta-k">{k}</span>
      <span className="cd-meta-v">{v}</span>
    </div>
  );
}

export default function ConsequenceStack({ result }: { result: TurnResult | null }) {
  if (!result) {
    return (
      <section className="cd-panel">
        <header className="cd-panel-head">
          <h2>Aftermath</h2>
        </header>
        <p className="cd-muted">
          No turn resolved yet. Issue advice to advance the engagement.
        </p>
      </section>
    );
  }

  const d = result.decision;
  const stack = result.consequence_stack;

  return (
    <section className="cd-panel cd-aftermath">
      <header className="cd-panel-head">
        <h2>Aftermath</h2>
        <span className="cd-verified">Resolved Turn {result.turn_number}</span>
      </header>

      <div className="cd-med-head">
        <span className={`cd-decision-badge ${DECISION_BADGE[d.decision_type] ?? ""}`}>
          {titleCase(d.decision_type)}
        </span>
        <span className="cd-decider">{d.decider}</span>
        <span className="cd-adherence">adherence {Math.round(d.adherence * 100)}%</span>
        <span className="cd-turn-status">{result.status_after}</span>
      </div>

      <div className="cd-med-grid">
        <MediationRow k="Player advised" v={result.advice_label} />
        <MediationRow k="Client did" v={titleCase(d.decision_type)} />
        <MediationRow k="Deviation" v={d.deviation} />
        <MediationRow k="Public explanation" v={d.public_explanation} />
        <MediationRow k="Private motive" v={d.private_motive} />
        <MediationRow k="Resulting risk" v={d.resulting_risk} />
      </div>

      <div className="cd-stack-grid">
        <StackSection title="Immediate Consequences" items={stack.immediate} tone="immediate" />
        <StackSection title="Second-Order Consequences" items={stack.second_order} tone="second" />
        <StackSection
          title="Faction Reactions"
          items={stack.faction_reactions.map(
            (r) => `${r.faction_name}: ${r.reaction}`,
          )}
          tone="faction"
        />
        <StackSection title="Media / Rumor Framing" items={stack.media_framing} tone="media" />
        <StackSection title="Legal / Procedural Fallout" items={stack.legal_fallout} tone="legal" />
        {stack.opened_threads.length > 0 && (
          <StackSection title="Threads Opened" items={stack.opened_threads} tone="thread" />
        )}
        {stack.canonized_events.length > 0 && (
          <StackSection title="Canonized Events" items={stack.canonized_events} tone="canon" />
        )}
      </div>

      <AppliedDiffList diffs={result.diffs} />

      <div className="cd-subhead">Summary</div>
      <p className="cd-aftermath-text">{result.aftermath_summary}</p>
    </section>
  );
}
