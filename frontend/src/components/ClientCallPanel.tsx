import type { ClientCall } from "../api/client";

export default function ClientCallPanel({ call }: { call: ClientCall | null }) {
  if (!call) {
    return (
      <section className="panel">
        <header className="panel-head">
          <h2>Client Call</h2>
        </header>
        <p className="muted">No active call for this turn.</p>
      </section>
    );
  }
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Client Call</h2>
        <span className="verified">Turn {call.turn}</span>
      </header>
      <div className="caller-line">
        <span className="caller-tag">INCOMING</span>
        <strong>{call.caller}</strong>
      </div>
      <p className="call-summary">{call.summary}</p>

      <div className="subhead">Known Facts</div>
      <ul className="facts">
        {call.known_facts.map((fact, i) => (
          <li key={i}>{fact}</li>
        ))}
      </ul>

      <div className="subhead">The Ask</div>
      <p className="ask">{call.ask}</p>
    </section>
  );
}
