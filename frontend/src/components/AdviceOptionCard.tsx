import type { AdviceOption, Faction } from "../api/client";
import { levelClass, titleCase } from "../domain";

interface Props {
  option: AdviceOption;
  selected: boolean;
  disabled: boolean;
  onSelect: (id: string) => void;
  factions: Faction[];
}

function RiskBar({ label, value }: { label: string; value: number }) {
  // Risk bars invert the color semantics: higher risk = redder.
  const inv = 100 - value;
  return (
    <div className="cd-risk-row">
      <span className="cd-risk-k">{label}</span>
      <span className="cd-risk-track">
        <span className={`cd-risk-fill ${levelClass(inv)}`} style={{ width: `${value}%` }} />
      </span>
      <span className="cd-risk-v">{value}</span>
    </div>
  );
}

export default function AdviceOptionCard({
  option,
  selected,
  disabled,
  onSelect,
  factions,
}: Props) {
  const factionName = (id: string) =>
    factions.find((f) => f.id === id)?.name ?? id;

  return (
    <li>
      <label className={`cd-advice ${selected ? "cd-advice-sel" : ""}`}>
        <input
          type="radio"
          name="advice"
          value={option.id}
          checked={selected}
          disabled={disabled}
          onChange={() => onSelect(option.id)}
        />
        <div className="cd-advice-body">
          <div className="cd-advice-top">
            <span className="cd-advice-chip">{titleCase(option.type)}</span>
            <span className="cd-advice-title">{option.title || option.label}</span>
          </div>
          <div className="cd-advice-summary">{option.summary}</div>
          {option.recommendation && (
            <div className="cd-advice-rec">{option.recommendation}</div>
          )}

          <div className="cd-advice-cols">
            <div className="cd-advice-col">
              <div className="cd-subhead cd-subhead-good">Expected benefits</div>
              <ul className="cd-advice-list cd-good-list">
                {option.expected_benefits.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
            <div className="cd-advice-col">
              <div className="cd-subhead cd-subhead-bad">Expected harms</div>
              <ul className="cd-advice-list cd-bad-list">
                {option.expected_harms.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="cd-advice-risks">
            <RiskBar label="Legal" value={option.legal_risk} />
            <RiskBar label="Political" value={option.political_risk} />
            <RiskBar label="Operational" value={option.operational_risk} />
          </div>

          {option.affected_factions.length > 0 && (
            <div className="cd-advice-aff">
              <span className="cd-meta-k">Affects</span>
              <span className="cd-meta-v">
                {option.affected_factions.map(factionName).join(" · ")}
              </span>
            </div>
          )}
        </div>
      </label>
    </li>
  );
}
