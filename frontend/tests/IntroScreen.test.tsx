import { describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import IntroScreen from "../src/components/IntroScreen";
import type { ScenarioVariant } from "../src/api/client";
import {
  readHasCompletedEngagement,
  writeHasCompletedEngagement,
} from "../src/guide/completion";

// Wave 3 C3: baseline is the clear first-run recommendation; the authored
// variants sit beneath it as alternate intake conditions — available from the
// start, never pretending to be locked progression.

const VARIANTS: ScenarioVariant[] = [
  {
    id: "hot_summer",
    name: "Hot summer",
    description: "A regional heat event is already stressing the grid when the first call lands.",
  },
  {
    id: "strained_finances",
    name: "Strained finances",
    description: "The town enters the crisis with its reserves already committed elsewhere.",
  },
];

function renderIntro(overrides: Partial<Parameters<typeof IntroScreen>[0]> = {}) {
  const onVariantChange = vi.fn();
  const onBegin = vi.fn();
  render(
    <IntroScreen
      onBegin={onBegin}
      onResume={() => undefined}
      recentCampaigns={[]}
      loading={false}
      variants={VARIANTS}
      selectedVariant=""
      onVariantChange={onVariantChange}
      {...overrides}
    />,
  );
  return { onVariantChange, onBegin };
}

describe("intake framing (Wave 3 C3)", () => {
  test("recommends baseline as the primary path, selected by default", () => {
    renderIntro();
    const baseline = screen.getByRole("radio", { name: /Baseline engagement/ });
    expect(baseline).toBeChecked();
    expect(screen.getByText(/recommended first case/)).toBeInTheDocument();
  });

  test("keeps alternates behind a closed disclosure on a first run", () => {
    renderIntro();
    const alternates = screen
      .getByText("Alternate intake conditions")
      .closest("details");
    expect(alternates).not.toHaveAttribute("open");
    // Available, not locked: the variants are in the document with their
    // one-sentence framing.
    expect(screen.getByRole("radio", { name: /Hot summer/, hidden: true })).toBeInTheDocument();
  });

  test("opens the alternates for a returning player who completed a run", () => {
    renderIntro({ completedBefore: true });
    const alternates = screen
      .getByText("Alternate intake conditions")
      .closest("details");
    expect(alternates).toHaveAttribute("open");
  });

  test("shows a preselected alternate without creating anything", () => {
    const { onBegin } = renderIntro({ selectedVariant: "hot_summer" });
    const alternates = screen
      .getByText("Alternate intake conditions")
      .closest("details");
    expect(alternates).toHaveAttribute("open");
    expect(screen.getByRole("radio", { name: /Hot summer/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /Baseline engagement/ })).not.toBeChecked();
    // Preselection is framing only: no campaign was begun.
    expect(onBegin).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Begin Intake" })).toBeEnabled();
  });

  test("selecting an alternate reports the variant id", async () => {
    const user = userEvent.setup();
    const { onVariantChange } = renderIntro({ completedBefore: true });
    await user.click(screen.getByRole("radio", { name: /Strained finances/ }));
    expect(onVariantChange).toHaveBeenCalledWith("strained_finances");
  });
});

describe("local completion hint", () => {
  test("round-trips and fails harmlessly without storage", () => {
    window.localStorage.clear();
    expect(readHasCompletedEngagement()).toBe(false);
    writeHasCompletedEngagement();
    expect(readHasCompletedEngagement()).toBe(true);

    const refuse = () => {
      throw new DOMException("SecurityError");
    };
    const broken = { getItem: refuse, setItem: refuse, removeItem: refuse };
    expect(readHasCompletedEngagement(broken)).toBe(false);
    expect(() => writeHasCompletedEngagement(broken)).not.toThrow();
    expect(readHasCompletedEngagement(null)).toBe(false);
  });
});
