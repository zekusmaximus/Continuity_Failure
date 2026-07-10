import { stopBackend } from "./support/backend";

/** Always reclaim the port, even when the suite failed. */
export default async function globalTeardown(): Promise<void> {
  await stopBackend().catch(() => {
    /* nothing left to stop */
  });
}
