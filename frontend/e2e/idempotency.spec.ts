import { expect, test } from "@playwright/test";

import { countTurns, createCampaign, submitAdvice } from "./support/api";
import {
  adviceOption,
  beginIntake,
  primaryAction,
  turnBadge,
  walkToAdvice,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

test.describe("at-most-once turn resolution", () => {
  /**
   * The failure this guards against: the request reaches FastAPI, the turn
   * commits to SQLite, and *then* the response is lost. The client cannot know
   * whether the write happened, so `requestWithRetry` retries the identical body
   * — same idempotency key. The backend must replay the original result rather
   * than resolve a second turn.
   *
   * `route.fetch()` genuinely forwards the request before `route.abort()` throws
   * the answer away, so this reproduces a dropped response rather than a dropped
   * request.
   */
  test("a lost response is retried under the same key and resolves one turn", async ({
    page,
    request,
  }) => {
    const campaignId = await beginIntake(page);
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await primaryAction(page, "Create desk template").click();
    await expect(page.getByText(/Memo attached for send/)).toBeVisible();

    const submittedKeys: string[] = [];
    let dropped = false;

    await page.route("**/api/campaigns/*/advice", async (route) => {
      const body = route.request().postDataJSON() as { idempotency_key: string };
      submittedKeys.push(body.idempotency_key);

      if (!dropped) {
        dropped = true;
        // Let the backend see it and commit, then lose the answer in transit.
        await route.fetch();
        await route.abort("connectionreset");
        return;
      }
      await route.continue();
    });

    const replays: string[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/advice")) {
        replays.push(res.headers()["idempotent-replay"] ?? "absent");
      }
    });

    await primaryAction(page, "Send Advice").click();

    // The player never sees an error: the retry recovered the committed result.
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await expect(page.getByText(/System alert/)).toBeHidden();

    expect(submittedKeys.length, "one drop, one retry").toBe(2);
    expect(submittedKeys[0], "the retry must reuse the key").toBe(submittedKeys[1]);
    expect(replays, "the surviving response was a replay").toContain("true");

    // The whole point: the turn resolved once, not twice.
    expect(await countTurns(request, campaignId)).toBe(1);
    await expect(turnBadge(page)).toHaveText("TURN 1 / 10");
  });

  /** Same key, different payload is a client bug and must be refused, not replayed. */
  test("reusing a key with a different payload is a conflict", async ({ request }) => {
    const campaignId = await createCampaign(request);

    const first = await submitAdvice(request, campaignId, {
      adviceId: "full_disclosure",
      expectedTurn: 1,
      idempotencyKey: "shared-key",
    });
    expect(first.status).toBe(200);

    const clash = await submitAdvice(request, campaignId, {
      adviceId: "delay_disclosure",
      expectedTurn: 1,
      idempotencyKey: "shared-key",
    });
    expect(clash.status).toBe(409);
    expect((clash.body.detail as { error: string }).error).toBe("idempotency_key_conflict");

    expect(await countTurns(request, campaignId)).toBe(1);
  });
});
