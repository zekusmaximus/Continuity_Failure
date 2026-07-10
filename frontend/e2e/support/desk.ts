import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Locators and steps for the Continuity Desk, expressed the way a player
 * perceives it: roles and visible names. No CSS hooks and no test ids — if a
 * control here stops being reachable by role and name, that is a real
 * regression in the interface, not in the test.
 */

export const header = (page: Page): Locator => page.getByRole("banner");
export const caseFile = (page: Page): Locator => page.getByRole("dialog", { name: "Case File" });

/** e.g. "TURN 1 / 10" in the masthead. */
export const turnBadge = (page: Page): Locator =>
  header(page).getByText(/^TURN \d+ \/ \d+$/);

export const primaryAction = (page: Page, name: string | RegExp): Locator =>
  page.getByRole("button", { name });

/** The campaign id the desk persisted into the URL. */
export function campaignIdFromUrl(page: Page): string {
  const id = new URL(page.url()).searchParams.get("campaign");
  if (!id) throw new Error(`No ?campaign= in ${page.url()}`);
  return id;
}

/** Fresh campaign from the intro screen; resolves once the first call is up. */
export async function beginIntake(page: Page): Promise<string> {
  await page.goto("/");
  await page.getByRole("button", { name: "Begin Intake" }).click();
  const guide = page.getByRole("dialog", { name: "Desk operating brief" });
  await expect(guide).toBeVisible();
  await guide.getByRole("button", { name: "Acknowledge briefing" }).click();
  await expect(page.getByText(/Incoming call · Turn 1/)).toBeVisible();
  return campaignIdFromUrl(page);
}

/** CALL → BRIEF → ADVICE, leaving the advice options on screen. */
export async function walkToAdvice(page: Page): Promise<void> {
  await primaryAction(page, "Accept Call").click();
  await primaryAction(page, "Skip to Advice").click();
  await expect(page.getByText(/Advisory · choose one recommendation/)).toBeVisible();
}

export const adviceOption = (page: Page, label: RegExp): Locator =>
  page.getByRole("radio", { name: label });

/** Submit the selected advice and land on the client decision. */
export async function sendAdvice(page: Page): Promise<void> {
  await primaryAction(page, "Send Advice").click();
  await expect(page.getByText(/Client decision · Turn \d+/)).toBeVisible();
}

/** CLIENT_DECISION → CONSEQUENCES → ARCHIVE. */
export async function walkToArchive(page: Page): Promise<void> {
  await primaryAction(page, "Review Consequences").click();
  await primaryAction(page, "Close Turn").click();
  await expect(page.getByText(/Turn archive · Turn \d+ filed/)).toBeVisible();
}

/** Open the Case File drawer and wait for it to be present. */
export async function openCaseFile(page: Page): Promise<Locator> {
  await header(page).getByRole("button", { name: "Case File" }).click();
  const drawer = caseFile(page);
  await expect(drawer).toBeVisible();
  return drawer;
}

/** "3 on file" — how many documents the drawer believes exist right now. */
export async function documentsOnFile(drawer: Locator): Promise<number> {
  const text = await drawer.getByText(/^\d+ on file$/).innerText();
  return Number.parseInt(text, 10);
}
