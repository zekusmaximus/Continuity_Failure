import fs from "node:fs";

import { BACKEND_PID_FILE } from "./support/env";
import { assertPortFree, resetDatabase, startBackend, stopBackend } from "./support/backend";

/**
 * Reclaim anything a crashed run left behind, wipe the database, start a fresh
 * backend. Nothing here depends on the Vite preview server, so it is safe
 * regardless of which Playwright starts first.
 */
export default async function globalSetup(): Promise<void> {
  if (fs.existsSync(BACKEND_PID_FILE)) {
    await stopBackend().catch(() => {
      /* stale pid for a process that is already dead */
    });
  }
  await assertPortFree();
  resetDatabase();
  await startBackend();
}
