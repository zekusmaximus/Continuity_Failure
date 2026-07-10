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

    await pressButton(page, "Send Advice");
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();

    await pressButton(page, "Resolve Consequences");
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
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();

    await pressButton(page, "Case File");
    const drawer = page.getByRole("dialog", { name: "Case File" });
    await expect(drawer).toBeVisible();

    // Tabs inside the drawer are reachable and operable.
    const factions = drawer.getByRole("button", { name: "Factions", exact: true });
    await tabTo(page, factions, 'The drawer\'s "Factions" tab');
    await page.keyboard.press("Enter");
    await expect(drawer.getByRole("heading", { name: "Factions" })).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });

  test("the document overlay opens from the keyboard and closes with Escape", async ({
    page,
  }) => {
    await page.goto("/");
    await pressButton(page, "Begin Intake");
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
  });
});
