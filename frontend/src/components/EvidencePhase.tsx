import { useMemo, useState } from "react";
import type { ClientCall, DocumentRecord } from "../api/client";
import DocumentDetail from "./DocumentDetail";
import StatusTag from "./StatusTag";
import {
  EvidenceTier,
  EVIDENCE_TIER_ORDER,
  EVIDENCE_TIER_HINT,
  RELIABILITY_LABEL,
  RELIABILITY_CLASS,
  PUBLIC_STATUS_LABEL,
  PUBLIC_STATUS_CLASS,
  whyItMatters,
  titleCase,
} from "../domain";

interface Props {
  documents: DocumentRecord[];
  call: ClientCall | null;
  onOpenCaseFile: () => void;
}

function tierOf(doc: DocumentRecord, attached: boolean): EvidenceTier {
  if (attached) return "Critical";
  if (doc.reliability === "high" || doc.public_status === "leaked" || doc.public_status === "disputed")
    return "Relevant";
  return "Background";
}

/**
 * EVIDENCE phase — a prioritized list, not a wall of cards. Documents are
 * grouped Critical / Relevant / Background (deterministically), each showing a
 * one-line "why it matters". Clicking opens a readable detail overlay.
 */
export default function EvidencePhase({ documents, call, onOpenCaseFile }: Props) {
  const [openDoc, setOpenDoc] = useState<DocumentRecord | null>(null);
  const attachedIds = useMemo(
    () => new Set(call?.attached_document_ids ?? []),
    [call],
  );

  const grouped = useMemo(() => {
    const byTier: Record<EvidenceTier, DocumentRecord[]> = {
      Critical: [],
      Relevant: [],
      Background: [],
    };
    for (const doc of documents) {
      byTier[tierOf(doc, attachedIds.has(doc.id))].push(doc);
    }
    return byTier;
  }, [documents, attachedIds]);

  return (
    <section className="cd-stage-panel cd-evidence">
      <h1 className="cd-eyebrow">
        <span className="cd-eyebrow-dot" aria-hidden />
        Evidence review · {documents.length} on file
      </h1>

      <details className="cd-context-help">
        <summary>How to read this evidence</summary>
        <p>
          Turn is the freshness marker. Source and reliability tell you how much
          weight the record can bear; public status tells you who may already know it.
          Priority reflects relevance to this call, not certainty.
        </p>
      </details>

      {documents.length === 0 ? (
        <p className="cd-muted">No documents available yet.</p>
      ) : (
        EVIDENCE_TIER_ORDER.map((tier) => {
          const docs = grouped[tier];
          if (docs.length === 0) return null;
          return (
            <div key={tier} className="cd-ev-group">
              <div className="cd-ev-group-head">
                <h2 className={`cd-ev-tier cd-ev-tier-${tier.toLowerCase()}`}>{tier}</h2>
                <span className="cd-ev-group-hint">{EVIDENCE_TIER_HINT[tier]}</span>
              </div>
              <ul className="cd-ev-list">
                {docs.map((doc) => (
                  <li key={doc.id}>
                    <button className="cd-ev-item" onClick={() => setOpenDoc(doc)}>
                      <div className="cd-ev-item-main">
                        <span className="cd-doc-type">{titleCase(doc.type)}</span>
                        <span className="cd-ev-item-title">{doc.title}</span>
                        <span className="cd-ev-item-source">— {doc.source}</span>
                        <span className="cd-ev-item-why">{whyItMatters(doc, attachedIds.has(doc.id))}</span>
                      </div>
                      <div className="cd-ev-item-tags">
                        <StatusTag
                          label={RELIABILITY_LABEL[doc.reliability] ?? doc.reliability}
                          className={RELIABILITY_CLASS[doc.reliability] ?? "rel-medium"}
                        />
                        <StatusTag
                          label={PUBLIC_STATUS_LABEL[doc.public_status] ?? doc.public_status}
                          className={PUBLIC_STATUS_CLASS[doc.public_status] ?? "tag-private"}
                        />
                        <StatusTag label={`Turn ${doc.turn_number}`} className="tag-turn" />
                        {doc.unverified_offline && (
                          <StatusTag
                            label="Unverified — offline"
                            className="tag-offline"
                            title="Live feeds were already down when this record reached the desk."
                          />
                        )}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          );
        })
      )}

      <button className="cd-linkbtn" onClick={onOpenCaseFile}>
        Open Case File →
      </button>

      <DocumentDetail doc={openDoc} onClose={() => setOpenDoc(null)} />
    </section>
  );
}
