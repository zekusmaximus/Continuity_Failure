import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import {
  adviceOption,
  beginIntake,
  primaryAction,
  sendAdvice,
  walkToArchive,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;
const GUIDE_KEY = "continuity-failure.guide.v2";

const topicNote = (page: Page, title: string) =>
  page.getByRole("note", { name: `Desk guide: ${title}` });

async function scanForSeriousViolations(page: Page, where: string): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(["color-contrast"])
    .analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(
    blocking.map((v) => `${v.id} (${v.impact}): ${v.help}`),
    `Accessibility violations on ${where}`,
  ).toEqual([]);
}

test.describe("progressive first-engagement teaching", () => {
  /**
   * Wave 3 C1, the clean first run: each topic teaches itself beside its real
   * object the first time it matters, never steals focus, dismisses into a
   * reopenable affordance, and the acknowledgement survives a reload via the
   * versioned presentation key.
   */
  test("topics appear in context, dismiss, persist, and stay reopenable", async ({
    page,
  }) => {
    await beginIntake(page);

    // Evidence: the turn-1 prompt and evidentiary-weight topic sit beside the
    // attached record.
    await primaryAction(page, "Accept Call").click();
    await primaryAction(page, "Review Evidence").click();
    await expect(
      page.getByText("Which record can bear the sentence you are about to put in writing?"),
    ).toBeVisible();
    const evidenceTopic = topicNote(page, "Evidentiary weight");
    await expect(evidenceTopic).toBeVisible();
    // Non-modal by construction: the callout never takes focus from the desk.
    await expect(evidenceTopic).not.toBeFocused();
    await scanForSeriousViolations(page, "evidence with teaching topics");
    await evidenceTopic.getByRole("button", { name: "Got it" }).click();
    await expect(evidenceTopic).toBeHidden();
    await expect(
      page.getByRole("button", { name: "? About evidentiary weight" }),
    ).toBeVisible();

    // Advice: adherence teaches at the first comparison; the citation topic
    // arrives with the citation workbench once an option is selected.
    await primaryAction(page, "Continue to Advice").click();
    const adherenceTopic = topicNote(page, "Adherence");
    await expect(adherenceTopic).toBeVisible();
    await expect(topicNote(page, "Citations")).toHaveCount(0);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await expect(topicNote(page, "Citations")).toBeVisible();
    await adherenceTopic.getByRole("button", { name: "Got it" }).click();
    await topicNote(page, "Citations").getByRole("button", { name: "Got it" }).click();

    // Resolve the turn: the causal lead's record_detail topic appears before
    // the audit disclosure on Consequences.
    await sendAdvice(page);
    await primaryAction(page, "Review Consequences").click();
    const recordTopic = topicNote(page, "The full record");
    await expect(recordTopic).toBeVisible();
    await expect(
      page.getByRole("button", { name: /Show the full record/ }),
    ).toBeVisible();
    await recordTopic.getByRole("button", { name: "Got it" }).click();

    // Reload: acknowledgements are versioned local presentation preferences.
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await primaryAction(page, "Review Consequences").click();
    await expect(topicNote(page, "The full record")).toHaveCount(0);
    const reopen = page.getByRole("button", { name: "? About the full record" });
    await expect(reopen).toBeVisible();

    // Reopened on demand, then dismissed again — no dead ends.
    await reopen.click();
    await expect(topicNote(page, "The full record")).toBeVisible();
    await topicNote(page, "The full record")
      .getByRole("button", { name: "Got it" })
      .click();
    await expect(topicNote(page, "The full record")).toHaveCount(0);

    const stored = await page.evaluate(
      (key) => JSON.parse(localStorage.getItem(key) ?? "[]"),
      GUIDE_KEY,
    );
    expect(stored).toEqual(
      expect.arrayContaining(["adherence", "evidence_weight", "citation", "record_detail"]),
    );
  });

  /**
   * The returning player: with every topic acknowledged, nothing auto-shows,
   * the compact reopen affordances remain, and the turn loop is undisturbed.
   */
  test("a returning player sees affordances, not callouts", async ({ page }) => {
    await page.addInitScript(
      ([guideKey]) => {
        localStorage.setItem("continuity-failure.desk-guide.v1", "acknowledged");
        localStorage.setItem(
          guideKey,
          JSON.stringify([
            "adherence",
            "evidence_weight",
            "citation",
            "thread_deadline",
            "precedent",
            "stale_feed",
            "power_allocation",
            "record_detail",
          ]),
        );
      },
      [GUIDE_KEY],
    );

    await page.goto("/");
    await page.getByRole("button", { name: "Begin Intake" }).click();
    // No first-run brief for a returning player.
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();
    await expect(
      page.getByRole("dialog", { name: "Desk operating brief" }),
    ).toBeHidden();

    await primaryAction(page, "Accept Call").click();
    await primaryAction(page, "Review Evidence").click();
    await expect(topicNote(page, "Evidentiary weight")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "? About evidentiary weight" }),
    ).toBeVisible();

    await primaryAction(page, "Continue to Advice").click();
    await expect(topicNote(page, "Adherence")).toHaveCount(0);

    // The loop itself is untouched: a full turn still resolves normally.
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);
    await walkToArchive(page);
    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
  });
});
