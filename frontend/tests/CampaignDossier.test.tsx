import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import CampaignDossier from "../src/components/CampaignDossier";
import { CAMPAIGN_ID, createFakeBackend, type FakeBackend } from "./support/fakeBackend";

let backend: FakeBackend;

beforeEach(() => {
  backend = createFakeBackend();
  backend.install();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CampaignDossier loading / error / content states", () => {
  test("shows a loading state, then the fetched dossier", async () => {
    render(<CampaignDossier campaignId={CAMPAIGN_ID} />);

    expect(screen.getByText(/Compiling case file/)).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.queryByText(/Compiling case file/)).not.toBeInTheDocument(),
    );
    // Real dossier markdown mentions the scenario.
    expect(screen.getByText(/Northbridge/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy as Markdown" })).toBeEnabled();
  });

  test("renders a player-safe alert when the fetch fails", async () => {
    backend.failNext("/dossier", {
      kind: "status",
      status: 500,
      error: "corrupt_record",
      message: "A stored record for this engagement could not be read.",
    });

    render(<CampaignDossier campaignId={CAMPAIGN_ID} />);

    await screen.findByText(/could not be read/);
    expect(screen.getByText(/System alert/)).toBeInTheDocument();
    // Export controls stay disabled while there is nothing to export.
    expect(screen.getByRole("button", { name: "Copy as Markdown" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Download .md" })).toBeDisabled();
  });

  test("does not fetch when there is no campaign", () => {
    render(<CampaignDossier campaignId={null} />);
    expect(backend.requestsFor("/dossier").length).toBe(0);
    expect(screen.getByText(/No dossier available/)).toBeInTheDocument();
  });
});
