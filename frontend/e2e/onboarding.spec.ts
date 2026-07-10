import { expect, test } from "@playwright/test";

import { adviceOption, primaryAction, sendAdvice, walkToAdvice, walkToArchive } from "./support/desk";

const GUIDE_KEY = "continuity-failure.desk-guide.v1";

test.describe("desk guide and announcements", () => {
  test("first-run help traps focus, persists locally, restores focus, and does not repeat", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Begin Intake" }).click();

    const guide = page.getByRole("dialog", { name: "Desk operating brief" });
    await expect(guide).toBeVisible();
    await expect(guide).toContainText("You advise from inside the machinery");
    await expect(guide).toContainText("Higher is not always better");
    await expect(guide).toContainText("Ambient crisis pressure");
    await expect(guide).toContainText("Next Call performs no new decision");
    await expect(guide).toBeFocused();

    expect(await page.locator("#root").evaluate((root) => ({
      inert: (root as HTMLElement).inert,
      hidden: root.getAttribute("aria-hidden"),
    }))).toEqual({ inert: true, hidden: "true" });

    // Shift+Tab from the initially focused surface wraps to the final action;
    // Tab from there wraps to the first control instead of escaping the dialog.
    await page.keyboard.press("Shift+Tab");
    await expect(guide.getByRole("button", { name: "Acknowledge briefing" })).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(guide.getByRole("button", { name: "Close desk guide" })).toBeFocused();

    await guide.getByRole("button", { name: "Acknowledge briefing" }).click();
    await expect(guide).toBeHidden();
    expect(await page.evaluate((key) => localStorage.getItem(key), GUIDE_KEY)).toBe("acknowledged");

    const reopen = page.getByRole("button", { name: "Desk Guide" });
    await reopen.focus();
    await page.keyboard.press("Enter");
    await expect(guide).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(guide).toBeHidden();
    await expect(reopen).toBeFocused();
    expect(await page.locator("#root").evaluate((root) => (root as HTMLElement).inert)).toBe(false);

    await walkToAdvice(page);
    await adviceOption(page, /Full disclosure and emergency conservation order/).check();
    await sendAdvice(page);
    await expect(page.getByRole("status")).toContainText("Turn 1 resolved. Client decision available.");
    await walkToArchive(page);
    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(page.getByRole("status")).toContainText("Turn 2 incoming call loaded.");
    await expect(guide).toBeHidden();
  });
});
