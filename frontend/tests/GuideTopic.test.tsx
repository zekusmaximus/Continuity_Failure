import { beforeEach, describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GuideTopic, { GuideProvider } from "../src/components/GuideTopic";
import { GUIDE_STORAGE_KEY } from "../src/guide/topics";
import { TelemetryProvider, type TelemetryApi } from "../src/telemetry/TelemetryProvider";

function withTelemetry(node: React.ReactNode, report = vi.fn()) {
  const api: TelemetryApi = {
    report,
    enabled: true,
    setEnabled: () => undefined,
    storage: null,
  };
  return { report, ui: <TelemetryProvider value={api}>{node}</TelemetryProvider> };
}

describe("GuideTopic (Wave 3 C1)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test("auto-shows once when its object first matters, then dismisses for good", async () => {
    const user = userEvent.setup();
    const { report, ui } = withTelemetry(<GuideTopic topic="adherence" />);
    const { unmount } = render(ui);

    const note = screen.getByRole("note", { name: "Desk guide: Adherence" });
    expect(note).toHaveTextContent(/You recommend; the client decides/);
    expect(report).toHaveBeenCalledWith({
      event_type: "guide_topic_shown",
      topic_id: "adherence",
    });

    await user.click(screen.getByRole("button", { name: "Got it" }));
    expect(
      screen.queryByRole("note", { name: "Desk guide: Adherence" }),
    ).not.toBeInTheDocument();
    expect(window.localStorage.getItem(GUIDE_STORAGE_KEY)).toContain("adherence");

    // A fresh mount respects the persisted acknowledgement: no auto-show.
    unmount();
    render(withTelemetry(<GuideTopic topic="adherence" />).ui);
    expect(
      screen.queryByRole("note", { name: "Desk guide: Adherence" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "? About adherence" }),
    ).toBeInTheDocument();
  });

  test("stays reopenable after dismissal, reporting topic ids only", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(GUIDE_STORAGE_KEY, JSON.stringify(["citation"]));
    const { report, ui } = withTelemetry(<GuideTopic topic="citation" />);
    render(ui);

    await user.click(screen.getByRole("button", { name: "? About citations" }));
    expect(
      screen.getByRole("note", { name: "Desk guide: Citations" }),
    ).toBeInTheDocument();
    expect(report).toHaveBeenCalledWith({
      event_type: "guide_topic_opened",
      topic_id: "citation",
    });
    // No prose beyond the id crosses into telemetry.
    for (const call of report.mock.calls) {
      expect(Object.keys(call[0]).sort()).toEqual(["event_type", "topic_id"]);
    }

    await user.click(screen.getByRole("button", { name: "Got it" }));
    expect(
      screen.queryByRole("note", { name: "Desk guide: Citations" }),
    ).not.toBeInTheDocument();
  });

  test("renders nothing while its object does not matter yet", () => {
    render(withTelemetry(<GuideTopic topic="power_allocation" active={false} />).ui);
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  test("never steals focus from the primary action", () => {
    render(withTelemetry(<GuideTopic topic="evidence_weight" />).ui);
    expect(screen.getByRole("note", { name: /Evidentiary weight/ })).toBeInTheDocument();
    expect(document.body).toHaveFocus();
  });

  test("links to the complete desk guide when a provider supplies it", async () => {
    const user = userEvent.setup();
    const openGuide = vi.fn();
    const { ui } = withTelemetry(
      <GuideProvider openGuide={openGuide}>
        <GuideTopic topic="thread_deadline" />
      </GuideProvider>,
    );
    render(ui);
    await user.click(screen.getByRole("button", { name: "Open desk guide" }));
    expect(openGuide).toHaveBeenCalledTimes(1);
  });

  test("omits the guide link without a provider and still teaches", () => {
    render(withTelemetry(<GuideTopic topic="stale_feed" />).ui);
    expect(screen.getByRole("note", { name: /Stale feeds/ })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open desk guide" }),
    ).not.toBeInTheDocument();
  });
});
