import { afterEach, describe, expect, test, vi } from "vitest";

import { ApiError, api, newIdempotencyKey } from "../src/api/client";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

/** A fetch stub that plays a scripted sequence of outcomes, one per call. */
function scriptedFetch(steps: Array<() => Promise<Response> | Response>) {
  let call = 0;
  const fn = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
    const step = steps[Math.min(call, steps.length - 1)];
    call += 1;
    return step();
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const ok = (body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json", ...headers },
  });

const errorBody = (status: number, error: string) =>
  new Response(JSON.stringify({ detail: { error, message: "nope", request_id: "r" } }), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("newIdempotencyKey", () => {
  test("mints a distinct key per call", () => {
    const keys = new Set(Array.from({ length: 500 }, () => newIdempotencyKey()));
    expect(keys.size).toBe(500);
  });
});

describe("submitAdvice retry semantics", () => {
  test("retries a transport failure and reuses the same request body", async () => {
    vi.useFakeTimers();
    const fetchMock = scriptedFetch([
      () => Promise.reject(new TypeError("Failed to fetch")), // dropped in transit
      () => ok({ turn_number: 1 }), // succeeds on retry
    ]);

    const key = "fixed-key";
    const promise = api.submitAdvice("c1", "full_disclosure", 1, key, `memo_${"1".repeat(32)}`, 2);
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result).toEqual({ turn_number: 1 });
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // The retried body is byte-identical, so the backend replays rather than
    // resolving a second turn. This is the client half of at-most-once.
    const bodyOf = (i: number) => {
      const init = fetchMock.mock.calls[i]?.[1] as RequestInit | undefined;
      return JSON.parse(String(init?.body));
    };
    const first = bodyOf(0);
    const second = bodyOf(1);
    expect(first).toEqual(second);
    expect(second.idempotency_key).toBe(key);
    expect(second.memo_id).toBe(`memo_${"1".repeat(32)}`);
    expect(second.memo_revision).toBe(2);
  });

  test("never retries a 4xx verdict", async () => {
    const fetchMock = scriptedFetch([() => errorBody(409, "stale_turn")]);

    await expect(api.submitAdvice("c1", "full_disclosure", 1, "k", `memo_${"1".repeat(32)}`, 1)).rejects.toMatchObject({
      code: "stale_turn",
      status: 409,
    });
    // A decided answer must be delivered as-is, not retried.
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  test("gives up after exhausting retries on a persistent 500", async () => {
    vi.useFakeTimers();
    const fetchMock = scriptedFetch([() => errorBody(500, "unexpected_error")]);

    const promise = api.submitAdvice("c1", "full_disclosure", 1, "k", `memo_${"1".repeat(32)}`, 1).catch((e) => e);
    await vi.runAllTimersAsync();
    const error = await promise;

    expect(error).toBeInstanceOf(ApiError);
    // Initial attempt + two backoff retries.
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});

describe("error decoding", () => {
  test("surfaces the backend's stable error code and player-safe message", async () => {
    scriptedFetch([
      () =>
        new Response(
          JSON.stringify({
            detail: {
              error: "campaign_terminal",
              message: "This engagement has closed.",
              request_id: "req-9",
            },
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
    ]);

    const error = (await api.getCurrent("c1").catch((e) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("campaign_terminal");
    expect(error.message).toBe("This engagement has closed.");
    expect(error.requestId).toBe("req-9");
  });

  test("maps a thrown fetch to a network_error", async () => {
    scriptedFetch([() => Promise.reject(new TypeError("Failed to fetch"))]);
    const error = (await api.getCurrent("c1").catch((e) => e)) as ApiError;
    expect(error.code).toBe("network_error");
    expect(error.status).toBe(0);
  });
});
