import type { DocumentRecord } from "../api/client";
import StatusTag from "./StatusTag";
import AccessibleDialog from "./AccessibleDialog";
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
  return (
    <AccessibleDialog
      open={doc !== null}
      onClose={onClose}
      titleId="cd-doc-detail-title"
      overlayClassName="cd-modal-overlay"
      className="cd-modal cd-modal-doc"
    >
      {doc && (
        <>
        <div className="cd-modal-head">
          <div>
            <span className="cd-doc-type">{titleCase(doc.type)}</span>
            <h2 id="cd-doc-detail-title">{doc.title}</h2>
            <span className="cd-verified">— {doc.source}</span>
          </div>
          <button className="cd-btn cd-btn-ghost cd-modal-close" onClick={onClose} aria-label="Close document">
            ✕
          </button>
        </div>

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
        </>
      )}
    </AccessibleDialog>
  );
}
