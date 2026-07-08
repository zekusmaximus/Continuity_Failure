import type { Faction } from "../api/client";
import FactionCard from "./FactionCard";

export default function FactionPanel({ factions }: { factions: Faction[] }) {
  // Highest-pressure factions first -- those are the ones driving the turn.
  const ordered = [...factions].sort(
    (a, b) => b.current_pressure + b.influence - (a.current_pressure + a.influence),
  );
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Factions</h2>
        <span className="cd-verified">{factions.length} actors</span>
      </header>
      <ul className="cd-faction-list">
        {ordered.map((f) => (
          <FactionCard key={f.id} faction={f} />
        ))}
      </ul>
    </section>
  );
}
