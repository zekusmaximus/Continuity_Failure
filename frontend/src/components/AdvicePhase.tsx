import type { AdviceOption, Faction, MemoDraft } from "../api/client";
import { levelClass, titleCase } from "../domain";
import MemoDraftPanel from "./MemoDraftPanel";

interface Props {
  options: AdviceOption[];
  factions: Faction[];
  selected: string | null;
  onSelect: (id: string) => void;
  memo: MemoDraft | null;
  memoLoading: boolean;
  memoError: string | null;
  onDraftMemo: () => void;
  readOnly?: boolean;
}

function RiskBar({ label, value }: { label: string; value: number }) {
  const inv = 100 - value; // higher risk => redder fill
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

// Deterministic "what the client will weigh" from the dominant risk dimension —
// presentation logic, not generated content.
function clientConcern(opt: AdviceOption): string {
  const dims: [string, number][] = [
    ["legal", opt.legal_risk],
    ["political", opt.political_risk],
    ["operational", opt.operational_risk],
  ];
  dims.sort((a, b) => b[1] - a[1]);
  const [top] = dims[0];
  if (top === "legal") return "The client will weigh legal exposure and the paper trail this creates.";
  if (top === "political") return "The client will weigh political blowback and how this plays publicly.";
  return "The client will weigh whether operations can absorb this right now.";
}

function AdviceCard({
  option,
  selected,
  onSelect,
  factions,
  readOnly = false,
}: {
  option: AdviceOption;
  selected: boolean;
  onSelect: (id: string) => void;
  factions: Faction[];
  readOnly?: boolean;
}) {
  const factionName = (id: string) => factions.find((f) => f.id === id)?.name ?? id;
  const bestFor = option.expected_benefits[0];
  const mainRisk = option.expected_harms[0];

  return (
    <li>
      <label className={`cd-advice ${selected ? "cd-advice-sel" : ""}`}>
        <input
          type="radio"
          name="advice"
          value={option.id}
          checked={selected}
          onChange={() => onSelect(option.id)}
          disabled={readOnly}
        />
        <div className="cd-advice-body">
          <div className="cd-advice-top">
            <span className="cd-advice-chip">{titleCase(option.type)}</span>
            <span className="cd-advice-title">{option.title || option.label}</span>
          </div>
          <div className="cd-advice-rec">{option.recommendation || option.summary}</div>

          <div className="cd-advice-quick">
            {bestFor && (
              <div className="cd-advice-quick-row">
                <span className="cd-advice-quick-k cd-good-k">Best for</span>
                <span>{bestFor}</span>
              </div>
            )}
            {mainRisk && (
              <div className="cd-advice-quick-row">
                <span className="cd-advice-quick-k cd-bad-k">Main risk</span>
                <span>{mainRisk}</span>
              </div>
            )}
          </div>

          <div className="cd-advice-risks">
            <RiskBar label="Legal" value={option.legal_risk} />
            <RiskBar label="Political" value={option.political_risk} />
            <RiskBar label="Operational" value={option.operational_risk} />
          </div>

          {selected && (
            <div className="cd-advice-expand">
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

              {option.affected_factions.length > 0 && (
                <div className="cd-field">
                  <div className="cd-field-k">Affected factions</div>
                  <div className="cd-tagrow">
                    {option.affected_factions.map((id) => (
                      <span key={id} className="cd-chip">{factionName(id)}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="cd-callout">
                <span className="cd-callout-k">Likely client concern</span>
                <span>{clientConcern(option)}</span>
              </div>
            </div>
          )}
        </div>
      </label>
    </li>
  );
}

/**
 * ADVICE phase — concise tradeoffs up front; details expand only for the option
 * the player is actually considering. No consequence stack is shown here; the
 * player commits before the fallout is revealed.
 *
 * Selecting an option also unlocks an optional "Draft memo" affordance, which
 * asks the AI-assist layer (off by default → deterministic fallback) to draft a
 * consultant memo for that option. The draft is advisory only: it never
 * advances the turn or changes state.
 */
export default function AdvicePhase({
  options,
  factions,
  selected,
  onSelect,
  memo,
  memoLoading,
  memoError,
  onDraftMemo,
  readOnly,
}: Props) {
  return (
    <section className="cd-stage-panel cd-advisory">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Advisory · choose one recommendation
      </h1>
      <p className="cd-muted cd-advice-note">
        You advise; the client decides. No option is risk-free — every path
        creates a record.
      </p>
      <details className="cd-context-help">
        <summary>How client decisions mediate advice</summary>
        <p>
          The client may follow, modify, delay, or reject your recommendation.
          Adherence determines how much of its stated effects enter resolution;
          any client modification is recorded as a separate change.
        </p>
      </details>
      <ul className="cd-advice-list-outer">
        {options.map((opt) => (
          <AdviceCard
            key={opt.id}
            option={opt}
            selected={selected === opt.id}
            onSelect={onSelect}
            factions={factions}
            readOnly={readOnly}
          />
        ))}
      </ul>

      {selected && (
        <div className="cd-advice-memo">
          <button
            className="cd-btn cd-btn-ghost"
            onClick={onDraftMemo}
            disabled={memoLoading}
          >
            {memoLoading ? "Drafting…" : "Draft memo"}
          </button>
          <span className="cd-muted cd-advice-memo-hint">
            Advisory only — drafts a memo for the selected option without
            sending advice or changing state. Falls back to a system draft when
            AI is off.
          </span>
          <MemoDraftPanel memo={memo} loading={memoLoading} error={memoError} />
        </div>
      )}
    </section>
  );
}
