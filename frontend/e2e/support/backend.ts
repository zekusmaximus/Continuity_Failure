import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";

import {
  BACKEND_DIR,
  BACKEND_LOG_FILE,
  BACKEND_PID_FILE,
  BACKEND_PORT,
  BACKEND_URL,
  E2E_DB_PATH,
  E2E_DIR,
  PYTHON,
  REPO_ROOT,
} from "./env";

/**
 * Lifecycle control for the end-to-end FastAPI process.
 *
 * Playwright's own `webServer` can only start a process once, but one journey
 * has to prove a campaign survives a backend restart against the same database.
 * So the backend is owned here instead: global setup starts it, global teardown
 * stops it, and the restart spec is free to cycle it in between. The pid is
 * written to disk because global setup and the test workers are different
 * processes and both need a handle on it.
 */

const HEALTH_TIMEOUT_MS = 45_000;
const POLL_INTERVAL_MS = 200;

function readPid(): number | null {
  if (!fs.existsSync(BACKEND_PID_FILE)) return null;
  const pid = Number.parseInt(fs.readFileSync(BACKEND_PID_FILE, "utf8").trim(), 10);
  return Number.isFinite(pid) ? pid : null;
}

function killTree(pid: number): void {
  if (process.platform === "win32") {
    // uvicorn under `python -m` can own child handles; /T takes the tree so a
    // survivor never holds port 8100 into the next run.
    spawnSync("taskkill", ["/pid", String(pid), "/T", "/F"], { stdio: "ignore" });
    return;
  }
  try {
    process.kill(-pid, "SIGTERM");
  } catch {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      /* already gone */
    }
  }
}

async function isHealthy(): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/health`, {
      signal: AbortSignal.timeout(1_000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/** Poll until `predicate` holds. Never a fixed sleep — the condition is the gate. */
async function waitFor(
  predicate: () => Promise<boolean>,
  what: string,
  timeoutMs = HEALTH_TIMEOUT_MS,
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
  const log = fs.existsSync(BACKEND_LOG_FILE)
    ? fs.readFileSync(BACKEND_LOG_FILE, "utf8").slice(-4000)
    : "(no backend log)";
  throw new Error(
    `Timed out after ${timeoutMs}ms waiting for ${what}.\n` +
      `Backend log tail:\n${log}\n` +
      `Is '${PYTHON}' the interpreter with the backend installed? ` +
      `Override with CF_PYTHON.`,
  );
}

export const waitForBackendUp = () => waitFor(isHealthy, `backend ${BACKEND_URL}/health`);
export const waitForBackendDown = () =>
  waitFor(async () => !(await isHealthy()), "backend to stop responding", 15_000);

/**
 * Start uvicorn against the throwaway database. Detached, so it outlives the
 * worker that spawned it; the pid file is how teardown finds it again.
 */
export async function startBackend(): Promise<void> {
  fs.mkdirSync(E2E_DIR, { recursive: true });
  const log = fs.openSync(BACKEND_LOG_FILE, "a");

  const child = spawn(
    PYTHON,
    [
      "-m",
      "uvicorn",
      "app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(BACKEND_PORT),
      "--log-level",
      "warning",
    ],
    {
      cwd: BACKEND_DIR,
      detached: true,
      stdio: ["ignore", log, log],
      env: {
        ...process.env,
        // `engine` and `memory` live at the repo root; `app` resolves from cwd.
        PYTHONPATH: REPO_ROOT,
        // Hermetic: never the developer's data/continuity_failure.sqlite3.
        CF_DATABASE_PATH: E2E_DB_PATH,
        // No model calls, no network, no API key required. Memo drafting still
        // works and returns the deterministic system fallback.
        CF_AI_ENABLED: "false",
        PYTHONUNBUFFERED: "1",
      },
    },
  );

  if (child.pid === undefined) throw new Error("Failed to spawn the backend process.");
  fs.writeFileSync(BACKEND_PID_FILE, String(child.pid), "utf8");
  child.unref();

  await waitForBackendUp();
}

/** Stop the backend and wait until it truly stops answering. */
export async function stopBackend(): Promise<void> {
  const pid = readPid();
  if (pid !== null) {
    killTree(pid);
    fs.rmSync(BACKEND_PID_FILE, { force: true });
  }
  await waitForBackendDown();
}

/** Cycle the process. The database file is untouched, so state must survive. */
export async function restartBackend(): Promise<void> {
  await stopBackend();
  await startBackend();
}

/** Wipe any prior run's database so every suite starts from an empty archive. */
export function resetDatabase(): void {
  fs.mkdirSync(E2E_DIR, { recursive: true });
  for (const suffix of ["", "-wal", "-shm"]) {
    fs.rmSync(`${E2E_DB_PATH}${suffix}`, { force: true });
  }
  fs.rmSync(BACKEND_LOG_FILE, { force: true });
}

/** Fail loudly rather than silently testing against a server we do not own. */
export async function assertPortFree(): Promise<void> {
  if (await isHealthy()) {
    throw new Error(
      `Something is already serving ${BACKEND_URL}. Stop it (or the leftover ` +
        `e2e backend: see ${BACKEND_PID_FILE}) and re-run.`,
    );
  }
}
