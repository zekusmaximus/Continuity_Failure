import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Component/integration tests only. Anything that needs a real browser, a real
// FastAPI process, or real SQLite lives in `e2e/` and runs under Playwright.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    unstubGlobals: true,
    unstubEnvs: true,
  },
});
