interface Props {
  /** Primary button label — the one obvious next action for this phase. */
  label: string;
  onClick: () => void;
  disabled?: boolean;
  busy?: boolean;
  /** Optional muted secondary action (e.g. "Skip to Advice"). */
  secondaryLabel?: string;
  onSecondary?: () => void;
  secondaryDisabled?: boolean;
  /** Short line explaining what happens next, shown above the buttons. */
  hint?: string;
}

/**
 * The persistent action bar at the foot of the guided stage. Every phase has
 * exactly one primary action; secondary actions are visually muted.
 */
export default function PrimaryAction({
  label,
  onClick,
  disabled,
  busy,
  secondaryLabel,
  onSecondary,
  secondaryDisabled,
  hint,
}: Props) {
  return (
    <div className="cd-actionbar">
      <div className="cd-actionbar-inner">
        {hint && <span className="cd-actionbar-hint">{hint}</span>}
        <div className="cd-actionbar-buttons">
          {secondaryLabel && onSecondary && (
            <button
              className="cd-btn cd-btn-ghost"
              onClick={onSecondary}
              disabled={secondaryDisabled || busy}
            >
              {secondaryLabel}
            </button>
          )}
          <button
            className="cd-btn cd-btn-primary cd-btn-action"
            onClick={onClick}
            disabled={disabled || busy}
          >
            {busy ? "Working…" : label}
          </button>
        </div>
      </div>
    </div>
  );
}
