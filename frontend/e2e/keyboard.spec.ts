import { expect, test, type Locator, type Page } from "@playwright/test";

import { turnBadge } from "./support/desk";

/**
 * Keyboard operation of the whole turn loop. Nothing here uses `click()` —
 * every control must be reachable by Tab and fired by Enter or Space, and every
 * overlay must be dismissible by Escape.
 */

const MAX_TABS = 40;

async function isFocused(locator: Locator): Promise<boolean> {
  return locator.evaluate((el) => el === document.activeElement);
}

/** Tab forward until `locator` holds focus. Proves reachability, not tab order. */
async function tabTo(page: Page, locator: Locator, what: string): Promise<void> {
  await expect(locator, `${what} must exist before tabbing to it`).toBeVisible();
  for (let i = 0; i < MAX_TABS; i += 1) {
    if (await isFocused(locator)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error(`${what} was not reachable within ${MAX_TABS} Tab presses.`);
}

async function pressButton(page: Page, name: string): Promise<void> {
  const button = page.getByRole("button", { name, exact: true });
  await tabTo(page, button, `Button "${name}"`);
  await page.keyboard.press("Enter");
}

test.describe("keyboard operation", () => {
  test("the core turn flow is fully operable from the keyboard", async ({ page }) => {
    await page.goto("/");

    await pressButton(page, "Begin Intake");
    const guide = page.getByRole("dialog", { name: "Desk operating brief" });
    await expect(guide).toBeVisible();
    await pressButton(page, "Acknowledge briefing");
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();

    await pressButton(page, "Accept Call");
    await expect(page.getByText(/Situation brief · Turn 1/)).toBeVisible();

    // A secondary action is just as reachable as the primary one.
    await pressButton(page, "Skip to Advice");
    await expect(page.getByText(/Advisory · choose one recommendation/)).toBeVisible();

    // Radio groups are selected with Space, not with a pointer.
    const option = page
      .getByRole("radio", { name: /Full disclosure and emergency conservation order/ });
    await tabTo(page, option, "The first advice option");
    await page.keyboard.press("Space");
    await expect(option).toBeChecked();

    await pressButton(page, "Create manual memo");
    await expect(page.getByText(/Memo attached for send/)).toBeVisible();
    await pressButton(page, "Send Advice");
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();

    await pressButton(page, "Review Consequences");
    await pressButton(page, "Close Turn");
    await expect(page.getByText(/Turn archive · Turn 1 filed/)).toBeVisible();

    await pressButton(page, "Next Call");
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
  });

  test("the Case File drawer opens from the keyboard and closes with Escape", async ({
    page,
  }) => {
    await page.goto("/");
    await pressButton(page, "Begin Intake");
    await pressButton(page, "Acknowledge briefing");
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();

    const opener = page.getByRole("button", { name: "Case File" });
    await pressButton(page, "Case File");
    const drawer = page.getByRole("dialog", { name: "Case File" });
    await expect(drawer).toBeVisible();

    // Tabs inside the drawer are reachable and operable.
    const evidence = drawer.getByRole("tab", { name: /Evidence/ });
    const factions = drawer.getByRole("tab", { name: /Factions/ });
    await tabTo(page, evidence, 'The drawer\'s "Evidence" tab');
    await page.keyboard.press("ArrowRight");
    await expect(factions).toHaveAttribute("aria-selected", "true");
    await expect(drawer.getByRole("heading", { name: "Factions" })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
    await expect(opener).toBeFocused();
  });

  test("the document overlay opens from the keyboard and closes with Escape", async ({
    page,
  }) => {
    await page.goto("/");
    await pressButton(page, "Begin Intake");
    await pressButton(page, "Acknowledge briefing");
    await pressButton(page, "Accept Call");
    await pressButton(page, "Review Evidence");
    await expect(page.getByText(/Evidence review · 3 on file/)).toBeVisible();

    const doc = page
      .getByRole("button", { name: /Preliminary Water Quality Lab Report/ })
      .first();
    await tabTo(page, doc, "The first evidence document");
    await page.keyboard.press("Enter");

    const overlay = page.getByRole("dialog", {
      name: "Preliminary Water Quality Lab Report",
    });
    await expect(overlay).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(overlay).toBeHidden();
    await expect(doc).toBeFocused();
  });

  test("phase tabs expose current and unavailable state and use arrow keys", async ({ page }) => {
    await page.goto("/");
    await pressButton(page, "Begin Intake");
    await pressButton(page, "Acknowledge briefing");

    const phases = page.getByRole("tablist", { name: "Turn phases" });
    const call = phases.getByRole("tab", { name: /Call/ });
    const brief = phases.getByRole("tab", { name: /Brief/ });
    const decision = phases.getByRole("tab", { name: /Decision/ });
    await expect(call).toHaveAttribute("aria-selected", "true");
    await expect(call).toHaveAttribute("aria-current", "step");
    await expect(brief).toBeDisabled();
    await expect(decision).toBeDisabled();

    await pressButton(page, "Accept Call");
    await expect(brief).toHaveAttribute("aria-selected", "true");
    await tabTo(page, brief, "Current Brief phase tab");
    await page.keyboard.press("ArrowLeft");
    await expect(call).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();
    await page.keyboard.press("ArrowRight");
    await expect(brief).toHaveAttribute("aria-selected", "true");
    await expect(page.getByText(/Situation brief · Turn 1/)).toBeVisible();
    await expect(decision).toBeDisabled();
  });
});
