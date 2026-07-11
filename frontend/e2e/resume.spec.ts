import { expect, test } from "@playwright/test";

import { restartBackend } from "./support/backend";
import { countTurns } from "./support/api";
import {
  adviceOption,
  beginIntake,
  campaignIdFromUrl,
  primaryAction,
  sendAdvice,
  turnBadge,
  walkToAdvice,
  walkToArchive,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

/** Play one turn and stop on the second call. Returns the campaign id. */
async function playOneTurn(page: import("@playwright/test").Page): Promise<string> {
  const campaignId = await beginIntake(page);
  await walkToAdvice(page);
  await adviceOption(page, FULL_DISCLOSURE).check();
  await sendAdvice(page);
  await walkToArchive(page);
  await primaryAction(page, "Next Call").click();
  await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
  return campaignId;
}

test.describe("durable resume", () => {
  test("a resolved turn survives refresh and backend restart until Next Call", async ({ page }) => {
    await beginIntake(page);
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);

    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 1 / 10");
    await expect(page.getByText("Northbridge Public Schools")).toHaveCount(0);

    await primaryAction(page, "Review Consequences").click();
    await expect(page.getByText("How the state moved")).toBeVisible();
    await restartBackend();
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 1 / 10");

    await primaryAction(page, "Review Consequences").click();
    await primaryAction(page, "Close Turn").click();
    await expect(page.getByText(/Turn archive · Turn 1 filed/)).toBeVisible();
    await page.reload();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 1 / 10");

    await primaryAction(page, "Review Consequences").click();
    await primaryAction(page, "Close Turn").click();
    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
  });

  test("a refresh reopens the same campaign from the URL", async ({ page }) => {
    const campaignId = await playOneTurn(page);

    await page.reload();

    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
    expect(campaignIdFromUrl(page)).toBe(campaignId);
  });

  test("local storage reopens the campaign when the URL is bare", async ({ page }) => {
    const campaignId = await playOneTurn(page);

    // Navigate to the naked origin: only local storage can name the campaign now.
    await page.goto("/");

    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
    expect(campaignIdFromUrl(page)).toBe(campaignId);
  });

  /**
   * The point of Batch 1. The campaign lives in SQLite, not in the process, so
   * killing and restarting FastAPI against the same database file must leave the
   * engagement exactly where the player left it — same turn, same resolved
   * history, still playable.
   */
  test("the campaign survives a backend restart", async ({ page, request }) => {
    const campaignId = await playOneTurn(page);
    expect(await countTurns(request, campaignId)).toBe(1);

    await restartBackend();

    await page.reload();

    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
    expect(await countTurns(request, campaignId)).toBe(1);

    // Not just readable — still advanceable.
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await sendAdvice(page);
    expect(await countTurns(request, campaignId)).toBe(2);
  });

  /**
   * A campaign id that no longer resolves must return the player to a usable
   * intake screen with an explanation, not a blank or wedged desk.
   */
  test("an unknown campaign id falls back to intake with an explanation", async ({
    page,
  }) => {
    await page.goto("/?campaign=does-not-exist");

    await expect(page.getByRole("button", { name: "Begin Intake" })).toBeVisible();
    await expect(page.getByText(/could not be reopened/i)).toBeVisible();
  });

  /** The resume screen lists real prior engagements and reopens them. */
  test("a recent engagement can be reopened from the intro screen", async ({ page }) => {
    const campaignId = await playOneTurn(page);

    await page.evaluate(() => window.localStorage.clear());
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Begin Intake" })).toBeVisible();

    await page.getByRole("button", { name: /Northbridge Water Failure/ }).first().click();

    await expect(turnBadge(page)).toBeVisible();
    expect(campaignIdFromUrl(page)).toBeTruthy();
    // The most recent engagement is the one we just played.
    expect(campaignIdFromUrl(page)).toBe(campaignId);
  });
});
