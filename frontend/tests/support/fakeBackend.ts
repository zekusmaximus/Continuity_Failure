import { vi } from "vitest";

import currentTurn1 from "../fixtures/current-turn-1.json";
import currentTurn2 from "../fixtures/current-turn-2.json";
import currentTurn3 from "../fixtures/current-turn-3.json";
import adviceTurn1 from "../fixtures/advice-turn-1.json";
import adviceTurn2 from "../fixtures/advice-turn-2.json";
import turns0 from "../fixtures/turns-0.json";
import turns1 from "../fixtures/turns-1.json";
import turns2 from "../fixtures/turns-2.json";
import dossier from "../fixtures/dossier.json";

/**
 * An in-process stand-in for the FastAPI backend.
 *
 * Every payload it returns was captured from the real engine (see
 * `fixtures/generate_fixtures.py`), and it enforces the contracts the component
 * under test actually depends on: `expected_turn` revision guarding, at-most-
 * once resolution per idempotency key, and refusal to advance a terminal
 * campaign. It is a fake, not a mock of the behaviour under test — the same
 * properties are proven against the real backend in `e2e/`.
 */

export const CAMPAIGN_ID = "test-campaign";
export const FULL_DISCLOSURE = "full_disclosure";

const CURRENT_BY_TURN = [currentTurn1, currentTurn2, currentTurn3];
const ADVICE_BY_TURN = [adviceTurn1, adviceTurn2];
const TURNS_BY_RESOLVED = [turns0, turns1, turns2];

export interface RecordedRequest {
  method: string;
  path: string;
  body: Record<string, unknown> | null;
}

type Injection =
  | { kind: "status"; status: number; error: string; message: string }
  | { kind: "network" };

interface Options {
  /** Campaigns that already exist when the app boots (the resume screen). */
  recent?: unknown[];
}

export interface FakeBackend {
  install(): void;
  readonly requests: RecordedRequest[];
  /** Requests to `path` that matched, in order. */
  requestsFor(fragment: string, method?: string): RecordedRequest[];
  /** How many turns the fake has genuinely resolved. Replays do not count. */
  readonly resolvedTurns: number;
  /** Queue one failure for the next request whose path contains `fragment`. */
  failNext(fragment: string, injection: Injection): void;
  /** Idempotency keys the client sent on `/advice`, in order. */
  readonly adviceKeys: string[];
  campaignsCreated: number;
}

const json = (body: unknown, init: ResponseInit = {}): Response =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json", "X-Request-ID": "req-test" },
    ...init,
  });

const errorResponse = (status: number, error: string, message: string): Response =>
  json({ detail: { error, message, request_id: "req-test" } }, { status });

export function createFakeBackend(options: Options = {}): FakeBackend {
  let turnNumber = 1; // the revision the campaign is currently at
  let resolved = 0; // turns actually advanced
  let campaignsCreated = 0;
  const idempotency = new Map<string, { fingerprint: string; response: unknown }>();
  const requests: RecordedRequest[] = [];
  const adviceKeys: string[] = [];
  const injections: { fragment: string; injection: Injection }[] = [];

  function takeInjection(path: string): Injection | null {
    const index = injections.findIndex((i) => path.includes(i.fragment));
    if (index === -1) return null;
    return injections.splice(index, 1)[0].injection;
  }

  async function handle(input: string, init?: RequestInit): Promise<Response> {
    const method = (init?.method ?? "GET").toUpperCase();
    const path = input;
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null;
    requests.push({ method, path, body });

    const injected = takeInjection(path);
    if (injected?.kind === "network") throw new TypeError("Failed to fetch");
    if (injected?.kind === "status") {
      return errorResponse(injected.status, injected.error, injected.message);
    }

    if (method === "POST" && /\/api\/campaigns$/.test(path)) {
      campaignsCreated += 1;
      turnNumber = 1;
      resolved = 0;
      idempotency.clear();
      const summary = CURRENT_BY_TURN[0].summary;
      return json({
        id: CAMPAIGN_ID,
        name: summary.name,
        status: "ACTIVE",
        turn_number: 1,
        max_turns: summary.max_turns,
      });
    }

    if (method === "GET" && /\/api\/campaigns\?/.test(path)) {
      return json(options.recent ?? []);
    }

    if (!path.includes(CAMPAIGN_ID)) {
      return errorResponse(404, "campaign_not_found", "Campaign not found.");
    }

    if (method === "GET" && path.endsWith("/current")) {
      return json(CURRENT_BY_TURN[turnNumber - 1]);
    }

    if (method === "GET" && path.endsWith("/turns")) {
      return json(TURNS_BY_RESOLVED[resolved]);
    }

    if (method === "GET" && path.endsWith("/dossier")) {
      return json(dossier);
    }

    if (method === "GET" && path.endsWith("/model-runs")) {
      return json([]);
    }

    if (method === "POST" && path.endsWith("/memo")) {
      return json({
        status: "fallback",
        source: "system",
        draft: {
          recommendation: "System draft",
          rationale: "Deterministic fallback.",
          operational_steps: [],
          communications: "",
          likely_opposition: [],
          second_order_risks: [],
          fallback_plan: "",
        },
      });
    }

    if (method === "POST" && path.endsWith("/advice")) {
      const key = String(body?.idempotency_key ?? "");
      const expected = Number(body?.expected_turn);
      const fingerprint = `${body?.advice_id}:${expected}`;
      adviceKeys.push(key);

      // Replay first, exactly as campaign_service.submit_advice orders it: an
      // honest retry of a committed turn must not trip the now-stale revision.
      const prior = idempotency.get(key);
      if (prior) {
        if (prior.fingerprint !== fingerprint) {
          return errorResponse(409, "idempotency_key_conflict", "Key reused with a different payload.");
        }
        return json(prior.response, { headers: { "Idempotent-Replay": "true" } });
      }

      if (turnNumber > ADVICE_BY_TURN.length) {
        return errorResponse(409, "campaign_terminal", "This engagement has closed.");
      }
      if (expected !== turnNumber) {
        return errorResponse(409, "stale_turn", "The engagement record has moved on.");
      }

      const response = ADVICE_BY_TURN[turnNumber - 1];
      idempotency.set(key, { fingerprint, response });
      turnNumber += 1;
      resolved += 1;
      return json(response, { headers: { "Idempotent-Replay": "false" } });
    }

    return errorResponse(404, "campaign_not_found", `No route for ${method} ${path}`);
  }

  return {
    install() {
      vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => handle(String(input), init)));
    },
    requests,
    requestsFor(fragment, method) {
      return requests.filter(
        (r) => r.path.includes(fragment) && (method === undefined || r.method === method),
      );
    },
    get resolvedTurns() {
      return resolved;
    },
    failNext(fragment, injection) {
      injections.push({ fragment, injection });
    },
    adviceKeys,
    get campaignsCreated() {
      return campaignsCreated;
    },
  } as FakeBackend;
}
