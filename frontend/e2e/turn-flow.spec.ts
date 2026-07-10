import { expect, test } from "@playwright/test";

import { countTurns } from "./support/api";
import {
  adviceOption,
  beginIntake,
  documentsOnFile,
  openCaseFile,
  primaryAction,
  sendAdvice,
  turnBadge,
  walkToAdvice,
  walkToArchive,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

test.describe("turn presentation", () => {
  /**
   * The temporal snapshot invariant. Resolving a turn must reveal *that turn's*
   * outcome and nothing else: the header, the key indicators, and every Case
   * File tab have to keep showing the world as it stood when the advice was
   * composed. The next call, the next document, and the next state only exist
   * after the player presses Next Call.
   *
   * Turn 1 of Northbridge has 3 documents on file; turn 2 has 4. That single
   * number is enough to catch a leak of next-turn data into the resolved view.
   */
  test("a resolved turn shows its own snapshot and hides the next turn", async ({
    page,
    request,
  }) => {
    const campaignId = await beginIntake(page);

    await expect(turnBadge(page)).toHaveText("TURN 1 / 10");
    const before = await openCaseFile(page);
    expect(await documentsOnFile(before)).toBe(3);
    await page.keyboard.press("Escape");

    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);

    // The turn is resolved on the backend. The desk must not have moved on.
    expect(await countTurns(request, campaignId)).toBe(1);

    for (const step of ["Client decision", "Consequences", "Turn archive"] as const) {
      await expect(turnBadge(page), `${step} must still read turn 1`).toHaveText(
        "TURN 1 / 10",
      );
      const drawer = await openCaseFile(page);
      expect(
        await documentsOnFile(drawer),
        `${step} must not expose turn 2's evidence`,
      ).toBe(3);
      await page.keyboard.press("Escape");

      if (step === "Client decision") await primaryAction(page, "Review Consequences").click();
      if (step === "Consequences") await primaryAction(page, "Close Turn").click();
    }

    await expect(page.getByText(/Turn archive · Turn 1 filed/)).toBeVisible();

    // Only now does turn 2 exist for the player.
    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");

    const after = await openCaseFile(page);
    expect(await documentsOnFile(after)).toBe(4);
  });

  /**
   * Next Call is a read, not a write. Pressing it must surface the turn the
   * backend already holds — never resolve another one.
   */
  test("Next Call advances exactly once", async ({ page, request }) => {
    const campaignId = await beginIntake(page);
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);
    await walkToArchive(page);

    let adviceRequests = 0;
    page.on("request", (r) => {
      if (r.method() === "POST" && r.url().includes("/advice")) adviceRequests += 1;
    });

    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();

    expect(adviceRequests, "Next Call must not submit advice").toBe(0);
    expect(await countTurns(request, campaignId), "still one resolved turn").toBe(1);

    // And the second turn is a genuinely different call, not a re-render of the first.
    await expect(page.getByText("Northbridge Public Schools")).toBeVisible();
  });
});
