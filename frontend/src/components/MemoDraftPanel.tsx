import { useEffect, useState } from "react";
import type { AdviceMemo } from "../api/client";

interface Props {
  memo: AdviceMemo | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  onSave: (name: string, content: string) => void;
}

export default function MemoDraftPanel({ memo, loading, saving, error, onSave }: Props) {
  const [name, setName] = useState("");
  const [content, setContent] = useState("");

  useEffect(() => {
    setName(memo?.name ?? "");
    setContent(memo?.content ?? "");
  }, [memo?.id, memo?.revision]);

  if (loading) {
    return <div className="cd-memo-panel cd-muted" role="status">Creating persistent memo draft…</div>;
  }
  if (error) {
    return <div className="cd-memo-panel cd-alert cd-alert-error" role="alert">Memo workflow failed: {error}</div>;
  }
  if (!memo) {
    return (
      <div className="cd-memo-panel cd-muted" role="status">
        No memo attached. Create a desk template or request an assisted draft before sending.
      </div>
    );
  }

  const immutable = memo.status !== "draft";
  const changed = name.trim() !== memo.name || content.trim() !== memo.content;
  const origin = memo.provenance.workflow === "ai_assisted"
    ? "Validated AI-assisted source"
    : memo.provenance.workflow === "deterministic_fallback"
      ? "Deterministic system fallback"
      : memo.provenance.workflow === "deterministic_template"
        ? "Deterministic desk template"
        : "Manual player draft";

  return (
    <div className="cd-memo-panel">
      <div className="cd-memo-head">
        <span className="cd-eyebrow-dot" aria-hidden />
        <span className="cd-subhead">Memo attached for send</span>
        <span className={`cd-memo-src ${memo.source === "ai" ? "cd-memo-src-ai" : "cd-memo-src-system"}`}>
          {origin}
        </span>
        <span className="cd-muted cd-memo-advisory">
          {memo.id} · revision {memo.revision} · {memo.classification}
        </span>
      </div>

      {memo.provenance.fallback_used && (
        <div className="cd-alert cd-alert-warn" role="status">
          Live AI is unavailable or did not validate. This draft uses the deterministic fallback.
        </div>
      )}
      {memo.source === "player" && memo.provenance.workflow !== "manual" && (
        <p className="cd-muted">Player-edited from {origin.toLowerCase()}; the generated source remains in revision history.</p>
      )}

      <label className="cd-field">
        <span className="cd-field-k">Memo name</span>
        <input
          aria-label="Memo name"
          value={name}
          maxLength={120}
          disabled={immutable || saving}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <label className="cd-field">
        <span className="cd-field-k">Exact content to be sent</span>
        <textarea
          aria-label="Memo content"
          value={content}
          maxLength={12000}
          rows={16}
          disabled={immutable || saving}
          onChange={(event) => setContent(event.target.value)}
        />
      </label>
      <div className="cd-memo-head">
        <button
          className="cd-btn cd-btn-ghost"
          disabled={immutable || saving || !changed || !name.trim() || !content.trim()}
          onClick={() => onSave(name.trim(), content.trim())}
        >
          {saving ? "Saving revision…" : "Save new revision"}
        </button>
        <span className="cd-muted">
          Sending seals this exact revision and SHA-256 digest. Sent records cannot be edited or deleted.
        </span>
      </div>
    </div>
  );
}
