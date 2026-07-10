import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import App from "../src/App";
import { createFakeBackend, type FakeBackend } from "./support/fakeBackend";

let backend: FakeBackend;

beforeEach(() => {
  // A stable, bare URL and clean storage: the app reads both to decide what to
  // resume, and one test's persisted campaign must not leak into the next.
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  backend = createFakeBackend();
  backend.install();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Start a campaign and walk CALL → ADVICE. */
async function startAndReachAdvice(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Begin Intake" }));
  await screen.findByText(/Incoming call · Turn 1/);
  await user.click(screen.getByRole("button", { name: "Accept Call" }));
  await user.click(await screen.findByRole("button", { name: "Skip to Advice" }));
  await screen.findByText(/Advisory · choose one recommendation/);
}

const header = () => screen.getByRole("banner");
const turnText = () => within(header()).getByText(/^TURN \d+ \/ \d+$/).textContent;

describe("temporal snapshot", () => {
  /**
   * The regression this exists to catch: after advice is sent, the header must
   * stay pinned to the resolved turn. `refreshHistory` runs, but `current` is
   * deliberately frozen, so the masthead cannot start advertising turn 2 before
   * the player presses Next Call.
   */
  test("resolving a turn does not advance the header or leak the next call", async () => {
    const user = userEvent.setup();
    render(<App />);

    await startAndReachAdvice(user);
    expect(turnText()).toBe("TURN 1 / 10");

    await user.click(
      screen.getByRole("radio", { name: /Full disclosure and emergency conservation order/ }),
    );
    await user.click(screen.getByRole("button", { name: "Send Advice" }));
    await screen.findByText(/Client decision · Turn 1/);

    // History was refreshed (proving we did fetch) but the header is frozen.
    expect(backend.requestsFor("/turns", "GET").length).toBeGreaterThan(0);
    expect(turnText()).toBe("TURN 1 / 10");

    // The next caller must not be anywhere on screen yet.
    expect(screen.queryByText("Northbridge Public Schools")).not.toBeInTheDocument();

    // Case File still reflects turn 1's three documents, not turn 2's four.
    await user.click(within(header()).getByRole("button", { name: "Case File" }));
    const drawer = await screen.findByRole("dialog", { name: "Case File" });
    expect(within(drawer).getByText("3 on file")).toBeInTheDocument();
  });

  test("Next Call advances the header exactly once", async () => {
    const user = userEvent.setup();
    render(<App />);

    await startAndReachAdvice(user);
    await user.click(
      screen.getByRole("radio", { name: /Full disclosure and emergency conservation order/ }),
    );
    await user.click(screen.getByRole("button", { name: "Send Advice" }));
    await user.click(await screen.findByRole("button", { name: "Resolve Consequences" }));
    await user.click(await screen.findByRole("button", { name: "Close Turn" }));
    await screen.findByText(/Turn archive · Turn 1 filed/);

    await user.click(screen.getByRole("button", { name: "Next Call" }));
    await screen.findByText(/Incoming call · Turn 2/);

    expect(turnText()).toBe("TURN 2 / 10");
    expect(backend.resolvedTurns, "one turn resolved, not two").toBe(1);
    expect(backend.requestsFor("/advice", "POST").length).toBe(1);
  });
});

describe("restart confirmation", () => {
  test("New Engagement asks for confirmation before abandoning a campaign", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: "Begin Intake" }));
    await screen.findByText(/Incoming call · Turn 1/);
    expect(backend.campaignsCreated).toBe(1);

    // Decline: no new campaign is created.
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    await user.click(within(header()).getByRole("button", { name: "New Engagement" }));
    expect(confirmSpy).toHaveBeenCalledOnce();
    expect(backend.campaignsCreated).toBe(1);

    // Accept: a new campaign is created and we return to a fresh turn 1.
    confirmSpy.mockReturnValue(true);
    await user.click(within(header()).getByRole("button", { name: "New Engagement" }));
    await waitFor(() => expect(backend.campaignsCreated).toBe(2));
    await screen.findByText(/Incoming call · Turn 1/);
  });
});
