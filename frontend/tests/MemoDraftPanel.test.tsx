import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import type { AdviceMemo } from "../src/api/client";
import MemoDraftPanel from "../src/components/MemoDraftPanel";

const memo: AdviceMemo = {
  id: `memo_${"1".repeat(32)}`,
  campaign_id: "campaign",
  status: "draft",
  name: "Advice of record",
  content: "Exact draft content",
  revision: 1,
  created_at: "2026-07-10T00:00:00Z",
  updated_at: "2026-07-10T00:00:00Z",
  author: "Continuity Desk",
  source: "system",
  classification: "proposed",
  provenance: {
    workflow: "deterministic_fallback",
    model_run_id: "run_1",
    prompt_version: "v1",
    model_name: "disabled",
    provider: "disabled",
    validation_status: "fallback",
    fallback_used: true,
  },
  turn_number: 1,
  call_id: "call_1",
  advice_id: "controlled_disclosure",
  revisions: [],
  sent_snapshot: null,
};

describe("persistent memo workbench", () => {
  test("shows an actionable empty state", () => {
    render(<MemoDraftPanel memo={null} loading={false} saving={false} error={null} onSave={vi.fn()} />);
    expect(screen.getByText(/No memo attached/)).toBeInTheDocument();
  });

  test("labels fallback provenance and saves a player edit as a new revision", async () => {
    const onSave = vi.fn();
    render(<MemoDraftPanel memo={memo} loading={false} saving={false} error={null} onSave={onSave} />);
    expect(screen.getByText(/Deterministic system fallback/)).toBeInTheDocument();
    expect(screen.getByText(/Live AI is unavailable/)).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Memo content"));
    await userEvent.type(screen.getByLabelText("Memo content"), "Player-edited content");
    await userEvent.click(screen.getByRole("button", { name: "Save new revision" }));
    expect(onSave).toHaveBeenCalledWith("Advice of record", "Player-edited content");
  });

  test("distinguishes a desk template from a later player revision", () => {
    const template = {
      ...memo,
      source: "system" as const,
      provenance: {
        ...memo.provenance,
        workflow: "deterministic_template" as const,
        fallback_used: false,
        validation_status: null,
      },
    };
    const { rerender } = render(
      <MemoDraftPanel memo={template} loading={false} saving={false} error={null} onSave={vi.fn()} />,
    );
    expect(screen.getByText("Deterministic desk template")).toBeInTheDocument();
    expect(screen.queryByText(/Player-edited from/)).not.toBeInTheDocument();

    rerender(
      <MemoDraftPanel
        memo={{ ...template, source: "player", revision: 2 }}
        loading={false}
        saving={false}
        error={null}
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByText(/Player-edited from deterministic desk template/)).toBeInTheDocument();
  });

  test("sent artifacts are visibly immutable", () => {
    render(
      <MemoDraftPanel
        memo={{ ...memo, status: "sent" }}
        loading={false}
        saving={false}
        error={null}
        onSave={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("Memo name")).toBeDisabled();
    expect(screen.getByLabelText("Memo content")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save new revision" })).toBeDisabled();
  });
});
