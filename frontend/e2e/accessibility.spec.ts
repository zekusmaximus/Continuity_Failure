import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { beginIntake, openCaseFile, primaryAction, sendAdvice, walkToAdvice } from "./support/desk";

/**
 * A smoke check, not a compliance audit, and explicitly not a substitute for
 * `keyboard.spec.ts` — axe cannot tell you whether the turn loop can be played
 * without a mouse.
 *
 * It is scoped to deterministic, structural rules (WCAG A/AA) at serious and
 * critical impact. Colour-contrast is excluded on purpose: it is evaluated
 * against rendered pixels and turns amber the moment a designer nudges a token,
 * which would make this suite a tax rather than a signal.
 */
async function scan(page: Page, where: string): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(["color-contrast"])
    .analyze();

  const blocking = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );

  expect(
    blocking.map((v) => `${v.id} (${v.impact}) — ${v.nodes.length} node(s): ${v.help}`),
    `Accessibility violations on ${where}`,
  ).toEqual([]);
}

test.describe("accessibility smoke", () => {
  test("the intake screen has no serious violations", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Begin Intake" })).toBeVisible();
    await scan(page, "intake");
  });

  test("the first-turn operating brief has no serious violations", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Begin Intake" }).click();
    await expect(page.getByRole("dialog", { name: "Desk operating brief" })).toBeVisible();
    await scan(page, "first-turn operating brief");
  });

  test("the pre-resolution phases have no serious violations", async ({ page }) => {
    await beginIntake(page);
    await scan(page, "incoming call");

    await primaryAction(page, "Accept Call").click();
    await scan(page, "situation brief");
    await primaryAction(page, "Review Evidence").click();
    await scan(page, "evidence review");
    await primaryAction(page, "Continue to Advice").click();
    await scan(page, "advice");
  });

  test("the Case File drawer has no serious violations", async ({ page }) => {
    await beginIntake(page);
    await openCaseFile(page);
    await scan(page, "case file drawer");
  });

  test("the resolved-turn phases have no serious violations", async ({ page }) => {
    await beginIntake(page);
    await walkToAdvice(page);
    await page
      .getByRole("radio", { name: /Full disclosure and emergency conservation order/ })
      .check();
    await sendAdvice(page);
    await scan(page, "client decision");
    await primaryAction(page, "Review Consequences").click();
    await scan(page, "consequences");
    await primaryAction(page, "Close Turn").click();
    await scan(page, "turn archive");
  });
});
