import { defineConfig, devices } from "@playwright/test";

import { BACKEND_URL, PREVIEW_PORT, PREVIEW_URL } from "./e2e/support/env";

/**
 * End-to-end suite: a real Chromium against the real FastAPI backend and a real
 * SQLite file. Durable resume and idempotent turn resolution are the properties
 * under test, so neither the backend nor the database is faked here.
 *
 * The backend is started by `e2e/global-setup.ts` rather than by `webServer`,
 * because one spec restarts it mid-run. Only the frontend is Playwright's.
 */
export default defineConfig({
  testDir: "./e2e",
  // One worker, no parallelism: the specs share one backend process and one
  // database, and the restart spec takes that backend down.
  fullyParallel: false,
  workers: 1,
  // No retries. A journey that only passes on the second attempt is a bug
  // report, not a pass.
  retries: 0,
  forbidOnly: !!process.env.CI,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [["github"], ["list"]] : [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",

  use: {
    baseURL: PREVIEW_URL,
    trace: "retain-on-failure",
    video: "off",
    screenshot: "off",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],

  // Serves the actual production build, so `npm run test:e2e` also proves the
  // bundle the player would receive. `reuseExistingServer: false` prevents a
  // stale preview from serving yesterday's assets.
  webServer: {
    command: `npm run build && npm run preview -- --host 127.0.0.1 --port ${PREVIEW_PORT} --strictPort`,
    url: PREVIEW_URL,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { CF_BACKEND_URL: BACKEND_URL },
  },
});
