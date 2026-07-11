import { expect, test } from "@playwright/test";

import { restartBackend } from "./support/backend";
import {
  adviceOption,
  beginIntake,
  primaryAction,
  sendAdvice,
  walkToAdvice,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

test.describe("causal lead and consequence hierarchy", () => {
  /**
   * Wave 3 B2: the resolved turn leads with a truthful causal orientation,
   * the Consequences phase names one future hook before the audit, and the
   * complete existing record stays one action away. Because the lead is
   * built by the engine and frozen with the presentation, refresh and a
   * full backend restart must restore the exact same sentences.
   */
  test("the lead reads first and survives refresh and backend restart", async ({
    page,
  }) => {
    await beginIntake(page);
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);

    // Client Decision leads with the causal headline above the receipt.
    const headline = page.locator(".cd-causal-headline");
    await expect(headline).toBeVisible();
    await expect(headline).toContainText(/You advised/);
    const headlineText = (await headline.innerText()).trim();
    // The future hook is not exposed yet: the progressive reveal holds.
    await expect(page.locator(".cd-future-hook")).toHaveCount(0);

    await primaryAction(page, "Review Consequences").click();

    // Consequences: the same headline context, and the full record defaults
    // open on turn 1 — the player learns the proof before the shortcut.
    await expect(page.locator(".cd-causal-headline")).toHaveText(headlineText);
    const fullRecord = page.getByRole("button", { name: /Show the full record/ });
    await expect(fullRecord).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByText("How the state moved")).toBeVisible();

    // The disclosure is presentation state only: collapsing hides the audit
    // without losing it, and expanding brings the identical record back.
    await fullRecord.click();
    await expect(page.getByText("How the state moved")).not.toBeVisible();
    await fullRecord.click();
    await expect(page.getByText("How the state moved")).toBeVisible();

    // Refresh: the frozen presentation reopens at Client Decision with the
    // exact same recorded sentences.
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(page.locator(".cd-causal-headline")).toHaveText(headlineText);

    // Backend restart against the same database: still the same record.
    await restartBackend();
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(page.locator(".cd-causal-headline")).toHaveText(headlineText);

    // The audit is intact after the round trip.
    await primaryAction(page, "Review Consequences").click();
    await expect(page.getByText("How the state moved")).toBeVisible();
  });
});
