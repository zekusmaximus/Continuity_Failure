import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));

/** `frontend/` */
export const FRONTEND_DIR = path.resolve(here, "..", "..");
/** repository root */
export const REPO_ROOT = path.resolve(FRONTEND_DIR, "..");
export const BACKEND_DIR = path.join(REPO_ROOT, "backend");

/** Scratch space for the throwaway database, backend log, and pid file. */
export const E2E_DIR = path.join(FRONTEND_DIR, ".e2e");

/**
 * The end-to-end database. It is deleted at the start of every run and never
 * points at `data/continuity_failure.sqlite3`, so a local playthrough is never
 * read, mutated, or destroyed by the suite.
 */
export const E2E_DB_PATH = path.join(E2E_DIR, "e2e.sqlite3");
export const BACKEND_PID_FILE = path.join(E2E_DIR, "backend.pid");
export const BACKEND_LOG_FILE = path.join(E2E_DIR, "backend.log");

// Fixed ports keep the Vite preview proxy target static across a backend
// restart. Both are asserted free before the suite starts.
export const BACKEND_PORT = 8100;
export const PREVIEW_PORT = 4173;

export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
export const PREVIEW_URL = `http://127.0.0.1:${PREVIEW_PORT}`;

/** Override when `python` is not the interpreter holding the backend deps. */
export const PYTHON = process.env.CF_PYTHON ?? "python";
