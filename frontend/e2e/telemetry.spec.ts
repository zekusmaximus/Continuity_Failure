import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";

import { TELEMETRY_EVENT_TYPES } from "../src/telemetry/events";
import {
  adviceOption,
  beginIntake,
  openCaseFile,
  primaryAction,
  turnBadge,
  walkToAdvice,
  walkToArchive,
} from "./support/desk";

const FULL_DISCLOSURE = /Full disclosure and emergency conservation order/;

// Free-form prose typed into the memo during this journey. If any of it
// reaches the telemetry export, the closed vocabulary has been broken.
const MEMO_SENTINEL =
  "PLAYTEST-SENTINEL prose: recommend full disclosure before the rumor cycle turns.";

async function openPlaytestData(page: Page): Promise<Locator> {
  const drawer = await openCaseFile(page);
  await drawer.getByRole("tab", { name: "Playtest Data" }).click();
  await expect(drawer.getByText("Local playtest data")).toBeVisible();
  return drawer;
}

function eventCountReadout(drawer: Locator): Locator {
  return drawer.locator("dt:text-is('Events on record') + dd");
}

test.describe("local playtest telemetry", () => {
  /**
   * The A2 journey: collection is off by default in the packaged build, the
   * player switches it on, plays a real turn (typing free-form memo prose on
   * the way), and the explicit JSON export contains the manifest plus closed-
   * vocabulary events only — no memo text. Clearing sits behind a
   * confirmation and never touches the campaign.
   */
  test("one turn is measured, exported without memo prose, and cleared", async ({
    page,
  }) => {
    await beginIntake(page);

    // Packaged/public builds collect nothing until the player opts in.
    let drawer = await openPlaytestData(page);
    const toggle = drawer.getByRole("checkbox", {
      name: /Collect local playtest events/,
    });
    await expect(toggle).not.toBeChecked();
    await expect(eventCountReadout(drawer)).toHaveText("0");
    await toggle.check();
    await page.keyboard.press("Escape");

    // One real turn, with player-typed prose in the memo of record.
    await walkToAdvice(page);
    await adviceOption(page, FULL_DISCLOSURE).check();
    await primaryAction(page, "Create desk template").click();
    await expect(page.getByText(/Memo attached for send/)).toBeVisible();
    await page.getByLabel("Memo content").fill(MEMO_SENTINEL);
    await page.getByRole("button", { name: "Save new revision" }).click();
    await expect(page.getByText(/· revision 2 ·/)).toBeVisible();
    await primaryAction(page, "Send Advice").click();
    await expect(page.getByText(/Client decision · Turn 1/)).toBeVisible();
    await walkToArchive(page);
    await primaryAction(page, "Next Call").click();
    await expect(page.getByText(/Incoming call · Turn 2/)).toBeVisible();

    // Export is explicit, and the payload is manifest + events, nothing else.
    drawer = await openPlaytestData(page);
    const count = Number(await eventCountReadout(drawer).innerText());
    expect(count).toBeGreaterThan(0);
    // The panel's readout is a snapshot from when it rendered; the drawer
    // opening itself is recorded just after. The export must match what is
    // actually in storage at click time.
    const storedCount = await page.evaluate(
      () =>
        (
          JSON.parse(
            window.localStorage.getItem("continuity-failure.telemetry.v1") ?? "[]",
          ) as unknown[]
        ).length,
    );
    expect(storedCount).toBeGreaterThanOrEqual(count);

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      drawer.getByRole("button", { name: "Export JSON" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("continuity-failure-playtest.json");
    const raw = readFileSync((await download.path())!, "utf8");

    expect(raw).not.toContain("PLAYTEST-SENTINEL");
    expect(raw).not.toContain("rumor cycle");

    const payload = JSON.parse(raw) as {
      manifest: Record<string, unknown>;
      events: Array<Record<string, unknown>>;
    };
    expect(Object.keys(payload).sort()).toEqual(["events", "manifest"]);
    expect(payload.manifest.schema_version).toBe(1);
    expect(payload.manifest.app_version).toBe("0.1.0");
    expect(payload.manifest.ruleset_version).toBe("3");
    expect(typeof payload.manifest.variant_id).toBe("string");
    expect(typeof payload.manifest.exported_at).toBe("string");

    expect(payload.events.length).toBe(storedCount);
    for (const event of payload.events) {
      expect(event.schema_version).toBe(1);
      expect(TELEMETRY_EVENT_TYPES).toContain(event.event_type);
    }
    const seenTypes = new Set(payload.events.map((event) => event.event_type));
    expect(seenTypes.has("phase_entered")).toBe(true);
    expect(seenTypes.has("phase_left")).toBe(true);
    expect(seenTypes.has("advice_selected")).toBe(true);
    expect(seenTypes.has("case_file_opened")).toBe(true);

    // Clearing requires confirmation, and backing out keeps the data.
    await drawer.getByRole("button", { name: "Clear local data" }).click();
    await drawer.getByRole("button", { name: "Keep data" }).click();
    expect(Number(await eventCountReadout(drawer).innerText())).toBeGreaterThan(0);

    await drawer.getByRole("button", { name: "Clear local data" }).click();
    await drawer
      .getByRole("button", { name: "Delete playtest data" })
      .click();
    await expect(eventCountReadout(drawer)).toHaveText("0");
    await page.keyboard.press("Escape");

    // Clearing telemetry never clears the campaign: the same engagement
    // reopens at the same turn after a reload.
    await page.reload();
    await expect(turnBadge(page)).toHaveText("TURN 2 / 10");
  });
});
