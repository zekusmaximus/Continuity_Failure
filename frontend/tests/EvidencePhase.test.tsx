import { beforeEach, describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";

import EvidencePhase from "../src/components/EvidencePhase";
import type { ClientCall, DocumentRecord } from "../src/api/client";

// Wave 3 C1: the turn-1 evidence prompt teaches evidentiary weight through
// the real attached record, without ever requiring a citation.

const DOC: DocumentRecord = {
  id: "doc_lab",
  title: "Preliminary lab report",
  type: "lab_report",
  source: "County lab",
  turn_number: 1,
  public_status: "private",
  reliability: "medium",
  summary: "s",
  content: "c",
  tags: ["water"],
  unverified_offline: false,
};

const CALL = {
  attached_document_ids: ["doc_lab"],
} as unknown as ClientCall;

function renderPhase(turnNumber: number, call: ClientCall | null = CALL) {
  return render(
    <EvidencePhase
      documents={[DOC]}
      call={call}
      onOpenCaseFile={() => undefined}
      turnNumber={turnNumber}
    />,
  );
}

describe("EvidencePhase turn-1 prompt (Wave 3 C1)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test("asks the authored-neutral question above turn-1 attached evidence", () => {
    renderPhase(1);
    expect(
      screen.getByText(
        "Which record can bear the sentence you are about to put in writing?",
      ),
    ).toBeInTheDocument();
    // The attached record is highlighted as Critical, with its qualifiers.
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText(/read these first/)).toBeInTheDocument();
  });

  test("does not repeat the prompt from turn 2 onward", () => {
    renderPhase(2);
    expect(
      screen.queryByText(/Which record can bear the sentence/),
    ).not.toBeInTheDocument();
  });

  test("shows no prompt when the call attaches nothing", () => {
    renderPhase(1, { attached_document_ids: [] } as unknown as ClientCall);
    expect(
      screen.queryByText(/Which record can bear the sentence/),
    ).not.toBeInTheDocument();
  });

  test("teaches evidentiary weight beside the first attached document", () => {
    renderPhase(1);
    expect(
      screen.getByRole("note", { name: "Desk guide: Evidentiary weight" }),
    ).toHaveTextContent(/You never have to cite/);
  });
});
