import { expect, test } from "@playwright/test";

import { countTurns, seedTerminalCampaign, submitAdvice } from "./support/api";
import { openCaseFile, primaryAction } from "./support/desk";

test.describe("terminal campaign", () => {
  /**
   * Design invariant 5: a campaign that has completed or failed never advances
   * again. The desk must reflect that — no path back into the turn loop — while
   * the dossier stays fully readable, because the record is the whole point of
   * a failed engagement.
   */
  test("a failed campaign cannot advance but its dossier still works", async ({
    page,
    request,
  }) => {
    const { campaignId, summary } = await seedTerminalCampaign(request);
    expect(summary.status).toBe("FAILED");
    expect(summary.failure_reason).toBeTruthy();
    const turnsAtStart = await countTurns(request, campaignId);

    await page.goto(`/?campaign=${campaignId}`);

    // The desk opens straight into the dossier, not into a call.
    await expect(page.getByText(/Campaign dossier/)).toBeVisible();
    await expect(page.getByText(/Compiling case file/)).toBeHidden();

    // No affordance advances the engagement.
    for (const gone of ["Accept Call", "Send Advice", "Next Call", "Close Turn"]) {
      await expect(primaryAction(page, gone)).toHaveCount(0);
    }

    // The dossier is usable: real content, and both export controls live.
    await expect(page.getByText(/Northbridge/).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Copy as Markdown" })).toBeEnabled();
    await expect(page.getByRole("button", { name: "Download .md" })).toBeEnabled();

    // The Case File remains available for the whole record.
    const drawer = await openCaseFile(page);
    await drawer.getByRole("button", { name: "Timeline" }).click();
    await expect(drawer).toBeVisible();
    await page.keyboard.press("Escape");

    // And the backend refuses another turn outright.
    const refused = await submitAdvice(request, campaignId, {
      expectedTurn: summary.turn_number,
      idempotencyKey: "after-terminal",
    });
    expect(refused.status).toBe(409);
    expect((refused.body.detail as { error: string }).error).toBe("campaign_terminal");
    expect(await countTurns(request, campaignId)).toBe(turnsAtStart);
  });
});
