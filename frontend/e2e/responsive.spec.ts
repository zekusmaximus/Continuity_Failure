import { expect, test, type Page } from "@playwright/test";

import {
  adviceOption,
  beginIntake,
  openCaseFile,
  primaryAction,
  sendAdvice,
  walkToAdvice,
} from "./support/desk";

/**
 * Layout contracts, checked by measurement rather than by screenshot. Two
 * properties hold at every width: the page never scrolls sideways, and the one
 * primary action of the current phase is fully on screen and clickable.
 */

const VIEWPORTS = [
  { name: "narrow phone", width: 390, height: 844 },
  { name: "wide desktop", width: 1440, height: 900 },
] as const;

/** The document must never be wider than its own viewport. */
async function expectNoHorizontalOverflow(page: Page, where: string): Promise<void> {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      // Name the widest offender so a failure is actionable.
      widest: [...document.querySelectorAll<HTMLElement>("body *")]
        .map((el) => ({
          selector: el.tagName.toLowerCase() + (el.className ? `.${String(el.className).split(" ")[0]}` : ""),
          right: Math.round(el.getBoundingClientRect().right),
        }))
        .sort((a, b) => b.right - a.right)
        .slice(0, 3),
    };
  });

  expect(
    overflow.scrollWidth,
    `${where}: page scrolls horizontally (${overflow.scrollWidth}px content in ` +
      `${overflow.clientWidth}px viewport). Widest: ` +
      overflow.widest.map((w) => `${w.selector}@${w.right}px`).join(", "),
  ).toBeLessThanOrEqual(overflow.clientWidth + 1);
}

/** The phase's primary action must be visible, in-viewport, and hittable. */
async function expectPrimaryActionUsable(
  page: Page,
  name: string,
  where: string,
): Promise<void> {
  const button = primaryAction(page, name);
  await expect(button, `${where}: "${name}" must be visible`).toBeVisible();
  await expect(button, `${where}: "${name}" must be in the viewport`).toBeInViewport();
  await expect(button, `${where}: "${name}" must be enabled`).toBeEnabled();

  const viewport = page.viewportSize()!;
  const box = (await button.boundingBox())!;
  expect(box.x, `${where}: "${name}" is clipped on the left`).toBeGreaterThanOrEqual(0);
  expect(
    box.x + box.width,
    `${where}: "${name}" is clipped on the right`,
  ).toBeLessThanOrEqual(viewport.width + 1);
}

for (const viewport of VIEWPORTS) {
  test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("primary controls stay usable and the page never scrolls sideways", async ({
      page,
    }) => {
      const where = viewport.name;

      await page.goto("/");
      await expectNoHorizontalOverflow(page, `${where} / intake`);
      await expectPrimaryActionUsable(page, "Begin Intake", `${where} / intake`);

      await beginIntake(page);
      await expectNoHorizontalOverflow(page, `${where} / call`);
      await expectPrimaryActionUsable(page, "Accept Call", `${where} / call`);
      for (const name of ["Case File", "Desk Guide", "New Engagement"]) {
        const control = page.getByRole("button", { name });
        await expect(control, `${where}: header control ${name}`).toBeVisible();
        await expect(control, `${where}: header control ${name}`).toBeInViewport();
      }

      await walkToAdvice(page);
      await expectNoHorizontalOverflow(page, `${where} / advice`);
      await adviceOption(page, /Full disclosure and emergency conservation order/).check();
      const send = primaryAction(page, "Send Advice");
      await expect(send, `${where} / advice: send control must stay in the viewport`).toBeInViewport();
      await expect(send, `${where} / advice: send stays guarded until a memo is attached`).toBeDisabled();

      await sendAdvice(page);
      await expectNoHorizontalOverflow(page, `${where} / client decision`);
      await expectPrimaryActionUsable(
        page,
        "Review Consequences",
        `${where} / client decision`,
      );

      // The Case File is the densest surface in the app; it is where a narrow
      // viewport is most likely to blow out the layout.
      const drawer = await openCaseFile(page);
      await expect(drawer).toBeInViewport();
      await expectNoHorizontalOverflow(page, `${where} / case file`);
      await drawer.getByRole("tab", { name: "Full State" }).click();
      await expectNoHorizontalOverflow(page, `${where} / case file · full state`);
      await page.keyboard.press("Escape");
    });
  });
}
