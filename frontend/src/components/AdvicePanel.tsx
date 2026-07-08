import type { AdviceOption } from "../api/client";

interface Props {
  options: AdviceOption[];
  selected: string | null;
  onSelect: (id: string) => void;
  onSubmit: () => void;
  disabled: boolean;
  submitting: boolean;
}

export default function AdvicePanel({
  options,
  selected,
  onSelect,
  onSubmit,
  disabled,
  submitting,
}: Props) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Current Advice Options</h2>
      </header>
      <ul className="advice-list">
        {options.map((opt) => (
          <li key={opt.id}>
            <label className={`advice-option ${selected === opt.id ? "selected" : ""}`}>
              <input
                type="radio"
                name="advice"
                value={opt.id}
                checked={selected === opt.id}
                disabled={disabled}
                onChange={() => onSelect(opt.id)}
              />
              <div className="advice-body">
                <div className="advice-label">{opt.label}</div>
                <div className="advice-summary">{opt.summary}</div>
                <div className="advice-rationale">{opt.rationale}</div>
              </div>
            </label>
          </li>
        ))}
      </ul>
      <button
        className="primary-btn"
        onClick={onSubmit}
        disabled={disabled || !selected || submitting}
      >
        {submitting ? "Transmitting advice…" : "Submit Advice & Advance Turn"}
      </button>
    </section>
  );
}
