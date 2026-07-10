import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// `restoreMocks` in vitest.config resets spies; React trees need explicit
// teardown or one test's DOM leaks into the next test's queries.
afterEach(() => {
  cleanup();
});
