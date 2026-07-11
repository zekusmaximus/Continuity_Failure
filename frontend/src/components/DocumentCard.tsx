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
  doc: DocumentRecord;
  expanded: boolean;
  onToggle: (id: string) => void;
  highlighted: boolean;
}

export default function DocumentCard({ doc, expanded, onToggle, highlighted }: Props) {
  return (
    <li className={`cd-doc ${highlighted ? "cd-doc-hl" : ""}`}>
      {/* aria-expanded belongs on the control that toggles, not on the listitem. */}
      <button
        className="cd-doc-head"
        aria-expanded={expanded}
        onClick={() => onToggle(doc.id)}
      >
        <div className="cd-doc-head-main">
          <span className="cd-doc-type">{titleCase(doc.type)}</span>
          <span className="cd-doc-title">{doc.title}</span>
          <span className="cd-doc-source">— {doc.source}</span>
        </div>
        <span className="cd-doc-chev" aria-hidden>{expanded ? "▾" : "▸"}</span>
      </button>
      <div className="cd-doc-tags">
        <StatusTag
          label={`Reliability: ${RELIABILITY_LABEL[doc.reliability] ?? doc.reliability}`}
          className={RELIABILITY_CLASS[doc.reliability] ?? "rel-medium"}
        />
        <StatusTag
          label={`Status: ${PUBLIC_STATUS_LABEL[doc.public_status] ?? doc.public_status}`}
          className={PUBLIC_STATUS_CLASS[doc.public_status] ?? "tag-private"}
        />
        <StatusTag label={`Turn ${doc.turn_number}`} className="tag-turn" />
        {doc.unverified_offline && (
          <StatusTag
            label="Unverified — arrived after feed loss"
            className="tag-offline"
            title="Live feeds were already down when this record reached the desk; it did not come over a verified feed."
          />
        )}
      </div>
      <p className="cd-doc-summary">{doc.summary}</p>
      {expanded && doc.content && (
        <pre className="cd-doc-content">{doc.content}</pre>
      )}
      {expanded && doc.tags.length > 0 && (
        <div className="cd-doc-tagrow">
          {doc.tags.map((t) => (
            <span key={t} className="cd-chip">{t}</span>
          ))}
        </div>
      )}
    </li>
  );
}
