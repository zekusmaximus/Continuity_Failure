import type { AdviceOption, Faction } from "../api/client";
import AdviceOptionCard from "./AdviceOptionCard";

interface Props {
  options: AdviceOption[];
  factions: Faction[];
  selected: string | null;
  onSelect: (id: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  submitting: boolean;
}

export default function AdviceWorkbench({
  options,
  factions,
  selected,
  onSelect,
  onSubmit,
  disabled,
  submitting,
}: Props) {
  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Advice Workbench</h2>
        <span className="cd-verified">Select a recommendation</span>
      </header>
      <p className="cd-workbench-note">
        The client mediates your advice. No option is risk-free; every path
        creates exposure the engine will resolve.
      </p>
      <ul className="cd-advice-list-outer">
        {options.map((opt) => (
          <AdviceOptionCard
            key={opt.id}
            option={opt}
            selected={selected === opt.id}
            disabled={disabled}
            onSelect={onSelect}
            factions={factions}
          />
        ))}
      </ul>
      <button
        className="cd-btn cd-btn-primary"
        onClick={onSubmit}
        disabled={disabled || !selected || submitting}
      >
        {submitting ? "Transmitting advice…" : "Issue Advice & Advance Turn"}
      </button>
    </section>
  );
}
