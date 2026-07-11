import type {
  AdviceMemo,
  AdviceOption,
  ClientCall,
  DocumentRecord,
  Faction,
  PowerAllocation,
  SystemStatus,
} from "../api/client";
import { levelClass, titleCase, POWER_ALLOCATIONS, VARIABLE_META } from "../domain";
import MemoDraftPanel from "./MemoDraftPanel";

interface Props {
  options: AdviceOption[];
  call: ClientCall | null;
  factions: Faction[];
  selected: string | null;
  onSelect: (id: string) => void;
  memo: AdviceMemo | null;
  memoLoading: boolean;
  memoSaving: boolean;
  memoError: string | null;
  onDraftMemo: () => void;
  onCreateManualMemo: () => void;
  onSaveMemo: (name: string, content: string) => void;
  readOnly?: boolean;
  documents?: DocumentRecord[];
  citedDocs?: string[];
  onToggleCite?: (id: string) => void;
  systemStatus?: SystemStatus | null;
  poweredSubsystem?: PowerAllocation | null;
  onAllocatePower?: (allocation: PowerAllocation) => void;
}

// Deterministic preview of how a citation will land — the same tag-overlap
// rule the engine applies, phrased for the consultant before they commit.
function citationPreview(
  doc: DocumentRecord,
  option: AdviceOption | null,
  call: ClientCall | null,
): { text: string; tone: "good" | "bad" | "neutral" } {
  if (!option) return { text: "", tone: "neutral" };
  const relevant =
    doc.tags.some((t) => option.tags.includes(t)) ||
    (call?.attached_document_ids ?? []).includes(doc.id);
  if (!relevant) {
    return {
      text: "Does not bear on this recommendation.",
      tone: "neutral",
    };
  }
  if (doc.reliability === "low" || doc.reliability === "contested") {
    return {
      text: "Contested backing — citing this carries a recorded cost.",
      tone: "bad",
    };
  }
  if (doc.reliability === "high") {
    return {
      text:
        doc.public_status === "public"
          ? "Strong, already-public backing — strengthens adherence."
          : "Strong backing — strengthens adherence.",
      tone: "good",
    };
  }
  return { text: "Relevant backing — helps the memo hold.", tone: "good" };
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

function variableLabel(name: string): string {
  return VARIABLE_META[name]?.label ?? titleCase(name);
}

function AdviceCard({
  option,
  selected,
  onSelect,
  factions,
  offBrief,
  crossesRedLine,
  callerName,
  readOnly = false,
}: {
  option: AdviceOption;
  selected: boolean;
  onSelect: (id: string) => void;
  factions: Faction[];
  offBrief: boolean;
  crossesRedLine: boolean;
  callerName: string;
  readOnly?: boolean;
}) {
  const factionName = (id: string) => factions.find((f) => f.id === id)?.name ?? id;
  const bestFor = option.expected_benefits[0];
  const mainRisk = option.expected_harms[0];

  return (
    <li>
      <label className={`cd-advice ${selected ? "cd-advice-sel" : ""} ${offBrief ? "cd-advice-off" : ""}`}>
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
            {offBrief && !crossesRedLine && (
              <span className="cd-advice-flag cd-flag-off">Off-brief</span>
            )}
            {crossesRedLine && (
              <span className="cd-advice-flag cd-flag-redline">Crosses a red line</span>
            )}
          </div>
          <div className="cd-advice-rec">{option.recommendation || option.summary}</div>

          {/* Off-brief tradeoff shown before submission, not after. */}
          {crossesRedLine ? (
            <div className="cd-offbrief-note cd-offbrief-redline">
              ⚠ This crosses a line the {callerName} has already drawn. Expect an
              outright rejection — and a legal-exposure and oversight cost for
              having proposed it.
            </div>
          ) : (
            offBrief && (
              <div className="cd-offbrief-note">
                Off-brief — the {callerName} did not ask for this. Expect lower
                adherence and a small hit to your perceived neutrality and
                reputation. Choose it only if its own effects are worth the
                friction.
              </div>
            )
          )}

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
 * ADVICE phase — a call-specific decision space, not a reusable global menu.
 *
 * The caller declares the 3-4 options it is actually asking about (its
 * "primary" recommendations); every other known option is a strategic
 * alternative shown behind a labeled path, with its off-brief cost or red-line
 * risk surfaced *before* the player commits. The player still advises and the
 * client still decides — this only makes the relevance and tradeoff of each
 * option legible up front.
 *
 * Selecting an option also unlocks an optional "Draft memo" affordance
 * (advisory only; never advances the turn or changes state).
 */
export default function AdvicePhase({
  options,
  call,
  factions,
  selected,
  onSelect,
  memo,
  memoLoading,
  memoSaving,
  memoError,
  onDraftMemo,
  onCreateManualMemo,
  onSaveMemo,
  readOnly,
  documents = [],
  citedDocs = [],
  onToggleCite,
  systemStatus = null,
  poweredSubsystem = null,
  onAllocatePower,
}: Props) {
  const allocationRequired = !!systemStatus?.requires_power_allocation;
  // Once a gated drafting action has committed the turn's allocation on the
  // backend, the route is locked: the submission must carry the same one.
  const powerCommitment = systemStatus?.power_commitment ?? null;
  const draftingDark = allocationRequired && poweredSubsystem !== "MODEL_ACCESS";
  const citationsDark = allocationRequired && poweredSubsystem !== "LIVE_DATA";
  const selectedOption = options.find((o) => o.id === selected) ?? null;
  const callerName = call?.caller ?? "client";
  const primaryIds = new Set(call?.primary_advice_ids ?? []);
  const redLineTags = new Set(call?.decision_profile?.red_line_tags ?? []);
  const profile = call?.decision_profile ?? null;

  // With no declared primary set (older payloads), treat everything as on-brief.
  const hasPrimary = primaryIds.size > 0;
  const isOffBrief = (o: AdviceOption) => hasPrimary && !primaryIds.has(o.id);
  const crosses = (o: AdviceOption) => o.tags.some((t) => redLineTags.has(t));

  const primary = hasPrimary ? options.filter((o) => primaryIds.has(o.id)) : options;
  const alternatives = hasPrimary ? options.filter((o) => !primaryIds.has(o.id)) : [];

  const card = (opt: AdviceOption) => (
    <AdviceCard
      key={opt.id}
      option={opt}
      selected={selected === opt.id}
      onSelect={onSelect}
      factions={factions}
      offBrief={isOffBrief(opt)}
      crossesRedLine={isOffBrief(opt) && crosses(opt)}
      callerName={callerName}
      readOnly={readOnly}
    />
  );

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

      {profile && (profile.mandate || profile.priorities.length > 0) && (
        <div className="cd-callout cd-caller-weighs">
          <span className="cd-callout-k">What the {callerName} weighs</span>
          <span>
            {profile.mandate}
            {profile.priorities.length > 0 && (
              <>
                {" "}
                Weighs first:{" "}
                {profile.priorities.map(variableLabel).join(", ")}.
              </>
            )}
          </span>
        </div>
      )}

      <details className="cd-context-help">
        <summary>How client decisions mediate advice</summary>
        <p>
          The client may follow, modify, delay, or reject your recommendation.
          Adherence determines how much of its stated effects enter resolution;
          any client modification is recorded as a separate change. Advice the
          caller did not ask for is resolved off-brief: lower adherence and a
          small, recorded cost to your standing.
        </p>
      </details>

      {hasPrimary && (
        <h2 className="cd-advice-group-head">
          Primary recommendations
          <span className="cd-muted"> · what the {callerName} is asking about</span>
        </h2>
      )}
      <ul className="cd-advice-list-outer">{primary.map(card)}</ul>

      {alternatives.length > 0 && (
        <details className="cd-alt-advice">
          <summary>
            Strategic alternatives · off-brief ({alternatives.length})
          </summary>
          <p className="cd-muted cd-alt-note">
            These are not what the {callerName} called about. Each shows its
            off-brief cost or red-line risk before you commit.
          </p>
          <ul className="cd-advice-list-outer">{alternatives.map(card)}</ul>
        </details>
      )}

      {selected && (
        <div className="cd-advice-memo">
          {allocationRequired && (
            <fieldset className="cd-power-allocation">
              <legend className="cd-field-k">
                Auxiliary power · one subsystem this turn
              </legend>
              <p className="cd-muted cd-small">
                The workstation is critical. Route the auxiliary feed before
                sending advice; everything unpowered stays dark this cycle.
              </p>
              {powerCommitment && (
                <p className="cd-muted cd-small" role="status">
                  ⚠ Auxiliary power is committed to{" "}
                  <strong>
                    {POWER_ALLOCATIONS.find((a) => a.id === powerCommitment)?.label ??
                      powerCommitment}
                  </strong>{" "}
                  this turn — a drafting request already energized that
                  circuit. One subsystem per turn; the advice goes out on the
                  same allocation.
                </p>
              )}
              {POWER_ALLOCATIONS.map((allocation) => (
                <label key={allocation.id} className="cd-power-option">
                  <input
                    type="radio"
                    name="power-allocation"
                    value={allocation.id}
                    checked={poweredSubsystem === allocation.id}
                    disabled={readOnly || !!powerCommitment}
                    onChange={() => onAllocatePower?.(allocation.id)}
                  />
                  <span className="cd-power-label">{allocation.label}</span>
                  <span className="cd-muted cd-small">{allocation.detail}</span>
                </label>
              ))}
            </fieldset>
          )}
          <button
            className="cd-btn cd-btn-ghost"
            onClick={onCreateManualMemo}
            disabled={memoLoading || !!memo}
          >
            Create desk template
          </button>
          <button
            className="cd-btn cd-btn-ghost"
            onClick={onDraftMemo}
            disabled={memoLoading || !!memo || draftingDark}
            title={draftingDark ? "Model access is unpowered this turn" : undefined}
          >
            {memoLoading ? "Drafting…" : "Request assisted draft"}
          </button>
          <span className="cd-muted cd-advice-memo-hint">
            Draft and edit are advisory only and never change state. One saved
            memo revision must be attached before the recommendation can be sent.
          </span>
          <MemoDraftPanel
            memo={memo}
            loading={memoLoading}
            saving={memoSaving}
            error={memoError}
            onSave={onSaveMemo}
            systemStatus={systemStatus}
          />

          {onToggleCite && documents.length > 0 && (
            <fieldset className="cd-cite-evidence">
              <legend className="cd-field-k">
                Cite supporting evidence · up to 3 documents
              </legend>
              <p className="cd-muted cd-small">
                The client weighs what the memo is staked on. Relevant,
                reliable records strengthen adherence; contested material
                costs your standing.
              </p>
              <ul className="cd-cite-list">
                {documents.map((doc) => {
                  const checked = citedDocs.includes(doc.id);
                  const preview = citationPreview(doc, selectedOption, call);
                  const atCap = !checked && citedDocs.length >= 3;
                  return (
                    <li key={doc.id} className="cd-cite-row">
                      <label className={atCap && !readOnly ? "cd-cite-capped" : ""}>
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={readOnly || atCap || citationsDark}
                          onChange={() => onToggleCite(doc.id)}
                        />
                        <span className="cd-cite-title">{doc.title}</span>
                        <span className="cd-cite-chips">
                          <span className={`cd-tag cd-rel-${doc.reliability}`}>
                            {titleCase(doc.reliability)}
                          </span>
                          <span className={`cd-tag cd-pub-${doc.public_status}`}>
                            {titleCase(doc.public_status)}
                          </span>
                        </span>
                      </label>
                      {preview.text && (
                        <span className={`cd-cite-preview cd-cite-${preview.tone}`}>
                          {preview.text}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </fieldset>
          )}
        </div>
      )}
    </section>
  );
}
