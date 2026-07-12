import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App from "../src/App";
import { REVIEW_MODE_STORAGE_KEY } from "../src/guide/reviewMode";
import { createFakeBackend, type FakeBackend } from "./support/fakeBackend";

// Wave 3 C2: expedited review is a local presentation preference that becomes
// effective only after two acknowledged turns, composes the same package on
// one screen, and never calls the backend or loses composed state.

let backend: FakeBackend;

beforeEach(() => {
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  backend = createFakeBackend();
  backend.install();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

type User = ReturnType<typeof userEvent.setup>;

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

const modeRadio = (name: RegExp) => screen.queryByRole("radio", { name });

async function begin(user: User) {
  await user.click(await screen.findByRole("button", { name: "Begin Intake" }));
  await user.click(await screen.findByRole("button", { name: "Acknowledge briefing" }));
  await screen.findByText(/Incoming call · Turn 1/);
}

/** Play one full guided turn from its CALL phase through Next Call. */
async function playGuidedTurn(user: User) {
  await user.click(screen.getByRole("button", { name: "Accept Call" }));
  await user.click(await screen.findByRole("button", { name: "Skip to Advice" }));
  await screen.findByText(/Advisory · choose one recommendation/);
  await user.click(screen.getByRole("radio", { name: FULL_DISCLOSURE }));
  await user.click(screen.getByRole("button", { name: "Create desk template" }));
  await screen.findByText(/Memo attached for send/);
  await user.click(screen.getByRole("button", { name: "Send Advice" }));
  await screen.findByText(/Client decision · Turn \d+/);
  await user.click(screen.getByRole("button", { name: "Review Consequences" }));
  await user.click(screen.getByRole("button", { name: "Close Turn" }));
  await user.click(screen.getByRole("button", { name: "Next Call" }));
}

describe("expedited review (Wave 3 C2)", () => {
  test("unlocks after two acknowledged turns, composes one screen, and never calls the backend on switch", async () => {
    const user = userEvent.setup();
    render(<App />);
    await begin(user);

    // Turns 1 and 2: the ritual has not been experienced twice; no offer.
    expect(modeRadio(/Expedited review/)).not.toBeInTheDocument();
    await playGuidedTurn(user);
    await screen.findByText(/Incoming call · Turn 2/);
    expect(modeRadio(/Expedited review/)).not.toBeInTheDocument();
    await playGuidedTurn(user);
    await screen.findByText(/Incoming call · Turn 3/);

    // Two acknowledged turns: the explicit preference is now offered.
    const expedited = modeRadio(/Expedited review/);
    expect(expedited).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Guided review/ })).toBeChecked();

    // Switching is pure presentation: not one request leaves the desk.
    const requestsBefore = backend.requests.length;
    await user.click(expedited!);
    expect(backend.requests.length).toBe(requestsBefore);
    expect(window.localStorage.getItem(REVIEW_MODE_STORAGE_KEY)).toBe("expedited");

    // REVIEW composes the same package on one screen: call, brief, evidence.
    await screen.findByText(/Expedited review · the complete call package/);
    expect(screen.getByText(/Incoming call · Turn 3/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence review · \d+ on file/)).toBeInTheDocument();

    // The stepper exposes the active mode semantically, with the short spine.
    const stepper = screen.getByRole("tablist", { name: "Turn phases · expedited review" });
    expect(within(stepper).getAllByRole("tab")).toHaveLength(5);
  });

  test("mode switches preserve selection, memo, and citations mid-composition", async () => {
    const user = userEvent.setup();
    render(<App />);
    await begin(user);
    await playGuidedTurn(user);
    await screen.findByText(/Incoming call · Turn 2/);
    await playGuidedTurn(user);
    await screen.findByText(/Incoming call · Turn 3/);

    // Compose in expedited mode: select an option and attach the memo.
    await user.click(modeRadio(/Expedited review/)!);
    await screen.findByText(/Expedited review · the complete call package/);
    await user.click(screen.getByRole("button", { name: "Compose Advice" }));
    await user.click(screen.getByRole("radio", { name: FULL_DISCLOSURE }));
    await user.click(screen.getByRole("button", { name: "Create desk template" }));
    await screen.findByText(/Memo attached for send/);

    // Back to the review screen, then back to guided: the corresponding
    // guided review phase opens and nothing composed is lost.
    await user.click(screen.getByRole("tab", { name: /Review, current phase|Review,/ }));
    const requestsBefore = backend.requests.length;
    await user.click(modeRadio(/Guided review/)!);
    expect(backend.requests.length).toBe(requestsBefore);
    await screen.findByText(/Incoming call · Turn 3/);
    expect(
      screen.getByRole("tablist", { name: "Turn phases · guided review" }),
    ).toBeInTheDocument();

    // The previously reached Advice phase is still reachable with state intact.
    await user.click(screen.getByRole("tab", { name: /Advice/ }));
    expect(screen.getByRole("radio", { name: FULL_DISCLOSURE })).toBeChecked();
    expect(screen.getByText(/Memo attached for send/)).toBeInTheDocument();

    // The submission gate is exactly the guided one: with the memo attached,
    // Send Advice is armed and no extra requirement appeared. (Real turn-3+
    // resolution in expedited mode is proven end-to-end in e2e/expedited.spec.)
    expect(screen.getByRole("button", { name: "Send Advice" })).toBeEnabled();
    expect(backend.resolvedTurns).toBe(2);
  });

  test("a stored expedited preference still starts a fresh campaign guided", async () => {
    window.localStorage.setItem(REVIEW_MODE_STORAGE_KEY, "expedited");
    const user = userEvent.setup();
    render(<App />);
    await begin(user);

    // Turn 1 runs the guided spine: the loop is taught before the shortcut.
    expect(screen.getByRole("button", { name: "Accept Call" })).toBeInTheDocument();
    expect(screen.queryByText(/Expedited review · the complete call package/)).not.toBeInTheDocument();
    expect(
      screen.getByRole("tablist", { name: "Turn phases · guided review" }),
    ).toBeInTheDocument();
    expect(modeRadio(/Expedited review/)).not.toBeInTheDocument();
  });
});
