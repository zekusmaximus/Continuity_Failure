import { expect, test, type Page } from "@playwright/test";

import { countTurns, getSummary } from "./support/api";
import {
  adviceOption,
  campaignIdFromUrl,
  primaryAction,
  sendAdvice,
  turnBadge,
  walkToAdvice,
  walkToArchive,
} from "./support/desk";

// The hot-summer route from the wave-2 witnesses: three contractor squeezes
// fire the turn-4 terms ultimatum naturally, the desk reaches CRITICAL from
// turn 9, and the campaign still completes in 10 turns.
const CONTRACTOR = /Pressure the contractor privately/;
const STATE_SUPPORT = /Request state emergency support immediately/;
const CONTROLLED = /Controlled disclosure with hospital and school mitigation/;
const MUTUAL_AID = /Convene regional mutual aid/;

/** Select an option, opening the off-brief alternatives disclosure if needed. */
async function selectAdvice(page: Page, advice: RegExp) {
  const radio = adviceOption(page, advice);
  if (!(await radio.isVisible())) {
    await page.getByText(/Strategic alternatives · off-brief/).click();
  }
  await radio.check();
}

async function playGuidedTurn(page: Page, advice: RegExp) {
  await walkToAdvice(page);
  await selectAdvice(page, advice);
  await sendAdvice(page);
  await walkToArchive(page);
  await primaryAction(page, "Next Call").click();
}

async function playExpeditedTurn(
  page: Page,
  advice: RegExp,
  { allocate = false, last = false }: { allocate?: boolean; last?: boolean } = {},
) {
  await expect(
    page.getByText(/Expedited review · the complete call package/),
  ).toBeVisible();
  await primaryAction(page, "Compose Advice").click();
  await selectAdvice(page, advice);
  if (allocate) {
    // CRITICAL: the AdvicePhase allocation fieldset gates the submission.
    await page.getByRole("radio", { name: "Live data" }).check();
  }
  await primaryAction(page, "Create desk template").click();
  await expect(page.getByText(/Memo attached for send/)).toBeVisible();
  await primaryAction(page, "Send Advice").click();
  await expect(page.getByText(/Client decision · Turn \d+/)).toBeVisible();
  await primaryAction(page, "Review Consequences").click();
  await primaryAction(page, "Close Turn").click();
  if (!last) await primaryAction(page, "Next Call").click();
}

test.describe("expedited review and replay framing", () => {
  /**
   * Wave 3 C2+C3 in one authored journey: an alternate intake (Hot Summer),
   * two guided turns before the expedited offer exists, a full expedited
   * campaign through the naturally firing turn-4 ultimatum variant and the
   * CRITICAL allocations of turns 9–10, a mid-review refresh, the terminal
   * dossier, and the replay invitation into a second, distinct campaign.
   */
  test("a full expedited hot-summer campaign completes and invites a deliberate second run", async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);

    // C3 intake framing: baseline is primary; the alternate is one click away.
    await page.goto("/");
    await expect(page.getByRole("radio", { name: /Baseline engagement/ })).toBeChecked();
    await page.getByText("Alternate intake conditions").click();
    await page.getByRole("radio", { name: /Hot Summer/ }).check();
    await page.getByRole("button", { name: "Begin Intake" }).click();
    const guide = page.getByRole("dialog", { name: "Desk operating brief" });
    await expect(guide).toBeVisible();
    await guide.getByRole("button", { name: "Acknowledge briefing" }).click();
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();
    const firstCampaignId = campaignIdFromUrl(page);

    // Turns 1–2 run guided; the expedited offer does not exist yet.
    await expect(page.getByRole("radio", { name: /Expedited review/ })).toHaveCount(0);
    await playGuidedTurn(page, CONTRACTOR);
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();
    await expect(page.getByRole("radio", { name: /Expedited review/ })).toHaveCount(0);
    await playGuidedTurn(page, CONTRACTOR);
    await expect(page.getByText(/Incoming call · Turn 3/)).toBeVisible();

    // Two acknowledged turns: the explicit preference appears. Switching is
    // presentation only and the stepper names the active mode.
    await page.getByRole("radio", { name: /Expedited review/ }).check();
    await expect(
      page.getByRole("tablist", { name: "Turn phases · expedited review" }),
    ).toBeVisible();
    await playExpeditedTurn(page, CONTRACTOR);

    // Turn 4: the contractor terms ultimatum fires naturally on this route;
    // the composed review shows the variant call, not the base opening.
    await expect(page.getByText(/Incoming call · Turn 4/)).toBeVisible();

    // Mid-review refresh: the local preference and the current package survive.
    await page.reload();
    await expect(
      page.getByText(/Expedited review · the complete call package/),
    ).toBeVisible();
    await expect(turnBadge(page)).toHaveText("TURN 4 / 10");
    await playExpeditedTurn(page, CONTRACTOR);

    // Turn 5, with a keyboard-navigation check on the short spine while the
    // resolved presentation keeps Review/Advice/Decision reachable.
    await expect(page.getByText(/Incoming call · Turn 5/)).toBeVisible();
    await primaryAction(page, "Compose Advice").click();
    await selectAdvice(page, STATE_SUPPORT);
    await primaryAction(page, "Create desk template").click();
    await expect(page.getByText(/Memo attached for send/)).toBeVisible();
    await primaryAction(page, "Send Advice").click();
    await expect(page.getByText(/Client decision · Turn 5/)).toBeVisible();

    await page.getByRole("tab", { name: /^Decision\b.*current phase/ }).focus();
    await page.keyboard.press("ArrowLeft");
    await expect(
      page.getByRole("tab", { name: /^Advice\b.*current phase/ }),
    ).toBeFocused();
    await page.keyboard.press("ArrowLeft");
    await expect(
      page.getByRole("tab", { name: /^Review\b.*current phase/ }),
    ).toBeFocused();
    // The read-only review is the frozen package; the record is unchanged.
    await expect(
      page.getByText(/Expedited review · the complete call package/),
    ).toBeVisible();
    await page.getByRole("tab", { name: /^Decision\b/ }).click();
    await expect(page.getByText(/Client decision · Turn 5/)).toBeVisible();

    await primaryAction(page, "Review Consequences").click();
    await primaryAction(page, "Close Turn").click();
    await primaryAction(page, "Next Call").click();
    await playExpeditedTurn(page, CONTROLLED);
    await playExpeditedTurn(page, MUTUAL_AID);
    await playExpeditedTurn(page, CONTRACTOR);

    // Turns 9–10: CRITICAL. The allocation gate is unchanged in expedited
    // mode — Send Advice holds until one subsystem carries the turn.
    await expect(page.getByText(/Incoming call · Turn 9/)).toBeVisible();
    await playExpeditedTurn(page, CONTROLLED, { allocate: true });
    await expect(page.getByText(/Incoming call · Turn 10/)).toBeVisible();
    await playExpeditedTurn(page, MUTUAL_AID, { allocate: true, last: true });

    // Terminal: each submission resolved exactly one turn, ten in total.
    await expect(page.getByText(/Engagement completed/)).toBeVisible();
    expect(await countTurns(request, firstCampaignId)).toBe(10);
    await primaryAction(page, "View Campaign Dossier").click();
    await expect(page.getByRole("heading", { name: /Campaign dossier/ })).toBeVisible();

    // The record proves the variant call was on the line this run.
    await expect(page.getByText(/call_04_terms_ultimatum/).first()).toBeVisible();

    // C3 replay invitation: facts already on the record, then back to intake
    // with an alternate preselected — and no campaign until Begin Intake.
    await expect(page.getByText("hot_summer · ruleset 3")).toBeVisible();
    await expect(page.getByText(/Weakest axis/)).toBeVisible();
    await page
      .getByRole("button", { name: "Reopen intake with alternate conditions" })
      .click();
    await expect(page.getByRole("button", { name: "Begin Intake" })).toBeVisible();
    const preselected = page.getByRole("radio", { name: /Strained Finances/ });
    await expect(preselected).toBeChecked();
    expect(campaignIdFromUrl(page)).toBe(firstCampaignId);

    // Only the explicit choice starts the second run — a distinct campaign
    // under distinct conditions.
    await page.getByRole("button", { name: "Begin Intake" }).click();
    await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();
    const secondCampaignId = campaignIdFromUrl(page);
    expect(secondCampaignId).not.toBe(firstCampaignId);
    expect((await getSummary(request, firstCampaignId)).status).toBe("COMPLETED");
    const secondSummary = await getSummary(request, secondCampaignId);
    expect(secondSummary.status).toBe("ACTIVE");
    expect(await countTurns(request, secondCampaignId)).toBe(0);
  });
});
