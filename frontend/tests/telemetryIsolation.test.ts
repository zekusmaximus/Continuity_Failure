import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

// Wave-3 guarantee 3.1: telemetry is browser-side presentation only. The
// deterministic engine and the backend services must never import, reference,
// or depend on it. This scan is the executable form of that boundary.

// Vitest runs with the frontend directory as its working directory.
const repoRoot = join(process.cwd(), "..");

function walk(dir: string, extension: string, skip: Set<string>): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (skip.has(entry)) continue;
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      found.push(...walk(path, extension, skip));
    } else if (entry.endsWith(extension)) {
      found.push(path);
    }
  }
  return found;
}

const SKIP_DIRS = new Set(["__pycache__", "node_modules", ".git"]);

describe("telemetry isolation", () => {
  it("is never referenced by engine code", () => {
    for (const file of walk(join(repoRoot, "engine"), ".py", SKIP_DIRS)) {
      expect(readFileSync(file, "utf8"), file).not.toMatch(/telemetry/i);
    }
  });

  it("is never referenced by backend services", () => {
    for (const file of walk(join(repoRoot, "backend"), ".py", SKIP_DIRS)) {
      expect(readFileSync(file, "utf8"), file).not.toMatch(/telemetry/i);
    }
  });

  it("imports nothing outside its own directory", () => {
    // The telemetry domain is self-contained: no gameplay module, API client,
    // or component may be pulled into the event/store/session layer, so its
    // privacy properties never depend on the rest of the app.
    const telemetryDir = join(process.cwd(), "src", "telemetry");
    const selfContained = ["events.ts", "store.ts", "session.ts", "summary.ts"];
    for (const file of walk(telemetryDir, ".ts", SKIP_DIRS)) {
      if (!selfContained.some((name) => file.endsWith(name))) continue;
      const source = readFileSync(file, "utf8");
      for (const match of source.matchAll(/from\s+"([^"]+)"/g)) {
        expect(match[1], `${file} imports ${match[1]}`).toMatch(/^\.\//);
      }
    }
  });
});
