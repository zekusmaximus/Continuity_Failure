import { useEffect } from "react";
import type { DocumentRecord } from "../api/client";
import StatusTag from "./StatusTag";
import {
  RELIABILITY_LABEL,
  RELIABILITY_CLASS,
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
  titleCase,
} from "../domain";

interface Props {
  doc: DocumentRecord | null;
  onClose: () => void;
}

/** Readable detail overlay for a single document. */
export default function DocumentDetail({ doc, onClose }: Props) {
  useEffect(() => {
    if (!doc) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [doc, onClose]);

  if (!doc) return null;

  return (
    <div className="cd-modal-overlay" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="cd-modal cd-modal-doc" onClick={(e) => e.stopPropagation()}>
        <header className="cd-modal-head">
          <div>
            <span className="cd-doc-type">{titleCase(doc.type)}</span>
            <h2>{doc.title}</h2>
            <span className="cd-verified">— {doc.source}</span>
          </div>
          <button className="cd-btn cd-btn-ghost cd-modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </header>

        <div className="cd-modal-body">
          <div className="cd-tagrow">
            <StatusTag
              label={`Reliability: ${RELIABILITY_LABEL[doc.reliability] ?? doc.reliability}`}
              className={RELIABILITY_CLASS[doc.reliability] ?? "rel-medium"}
            />
            <StatusTag
              label={`Status: ${PUBLIC_STATUS_LABEL[doc.public_status] ?? doc.public_status}`}
              className={PUBLIC_STATUS_CLASS[doc.public_status] ?? "tag-private"}
            />
            <StatusTag label={`Turn ${doc.turn_number}`} className="tag-turn" />
          </div>

          <div className="cd-field">
            <div className="cd-field-k">Summary</div>
            <p className="cd-field-v">{doc.summary}</p>
          </div>

          {doc.content && (
            <div className="cd-field">
              <div className="cd-field-k">Full content</div>
              <pre className="cd-doc-content">{doc.content}</pre>
            </div>
          )}

          {doc.tags.length > 0 && (
            <div className="cd-tagrow">
              {doc.tags.map((t) => (
                <span key={t} className="cd-chip">{t}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
