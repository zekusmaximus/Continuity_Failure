import { useState } from "react";
import type { ClientCall, DocumentRecord, SystemStatus } from "../api/client";
import DocumentCard from "./DocumentCard";

interface Props {
  documents: DocumentRecord[];
  call: ClientCall | null;
  systemStatus?: SystemStatus | null;
}

export default function EvidenceBoard({ documents, call, systemStatus = null }: Props) {
  const [openId, setOpenId] = useState<string | null>(null);
  const attached = new Set(call?.attached_document_ids ?? []);

  const toggle = (id: string) => setOpenId((cur) => (cur === id ? null : id));

  // Attached-to-this-call documents float to the top so the player sees the
  // most relevant evidence first.
  const ordered = [...documents].sort((a, b) => {
    const ax = attached.has(a.id) ? 0 : 1;
    const bx = attached.has(b.id) ? 0 : 1;
    if (ax !== bx) return ax - bx;
    return a.turn_number - b.turn_number;
  });

  const stale = systemStatus ? !systemStatus.live_feeds : false;
  const staleAnchor =
    systemStatus && systemStatus.last_live_turn > 0
      ? `turn ${systemStatus.last_live_turn} close-out`
      : "engagement intake";

  return (
    <section className="cd-panel">
      <header className="cd-panel-head">
        <h2>Evidence Board</h2>
        <span className="cd-verified">{documents.length} on file</span>
      </header>
      {stale && (
        <p className="cd-evidence-stale" role="status">
          <span aria-hidden>⚠ </span>
          Stale snapshot — live feeds lost; documents last verified at the {staleAnchor}.
        </p>
      )}
      {ordered.length === 0 ? (
        <p className="cd-muted">No documents available yet.</p>
      ) : (
        <ul className="cd-doc-list">
          {ordered.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              expanded={openId === doc.id}
              onToggle={toggle}
              highlighted={attached.has(doc.id)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
