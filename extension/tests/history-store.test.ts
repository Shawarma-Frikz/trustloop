import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearHistory, getHistory, isHistoryEnabled, recordHistoryResults, setHistoryEnabled } from "../src/history-store.js";
import type { PublicResult } from "../src/scoring-api.js";

const ENABLED = "trustloop.history.enabled";
const RECORDS = "trustloop.history.records";
const secretText = "PRIVATE_REVIEW_SENTINEL_do_not_persist";

const scoredResult: PublicResult = {
  reviewKey: "review-key-secret",
  status: "SCORED",
  trustScore: 73,
  verdict: "LIKELY_ORGANIC",
  evidenceQuality: "ADEQUATE",
  engine: "MODEL",
  modelVersion: "tl-text-1.1.0",
  signals: [{ kind: "CONCRETE_DETAIL", summary: secretText, contribution: 0.2 }],
};

describe("metadata-only local history", () => {
  let state: Record<string, unknown>;

  beforeEach(() => {
    state = {};
    const local = {
      get: vi.fn(async (key: string) => ({ [key]: state[key] })),
      set: vi.fn(async (values: Record<string, unknown>) => { Object.assign(state, values); }),
    };
    vi.stubGlobal("chrome", { storage: { local, onChanged: { addListener: vi.fn() } } });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("is off by default and writes nothing until the user opts in", async () => {
    expect(await isHistoryEnabled()).toBe(false);
    await recordHistoryResults([scoredResult], "www.amazon.com", "amazon.reviews.v1");
    expect(state).toEqual({});
  });

  it("stores only the approved metadata fields when enabled", async () => {
    await setHistoryEnabled(true);
    await recordHistoryResults([scoredResult], "www.amazon.com", "amazon.reviews.v1", new Date("2026-11-10T12:00:00Z"));
    const saved = state[RECORDS] as Record<string, unknown>[];
    expect(saved).toHaveLength(1);
    expect(Object.keys(saved[0]).sort()).toEqual([
      "adapterId", "engine", "evidenceQuality", "hostname", "modelVersion", "status", "timestamp", "trustScore", "verdict",
    ]);
    expect(JSON.stringify(state)).not.toContain(secretText);
    expect(JSON.stringify(state)).not.toContain("review-key-secret");
    expect(JSON.stringify(state)).not.toContain("https://");
  });

  it("drops records older than 30 days and caps history at 100 entries", async () => {
    const now = new Date("2026-11-10T12:00:00Z");
    await setHistoryEnabled(true);
    state[RECORDS] = [
      { timestamp: "2026-10-01T00:00:00.000Z", hostname: "old.example", adapterId: "amazon.reviews.v1", status: "UNKNOWN", engine: "MODEL" },
      ...Array.from({ length: 100 }, (_, index) => ({
        timestamp: new Date(now.getTime() - index * 1000).toISOString(),
        hostname: "www.amazon.com", adapterId: "amazon.reviews.v1", status: "UNKNOWN", engine: "MODEL",
      })),
    ];
    await recordHistoryResults([scoredResult], "www.amazon.com", "amazon.reviews.v1", now);
    const saved = state[RECORDS] as Record<string, unknown>[];
    expect(saved).toHaveLength(100);
    expect(saved.every((record) => record.hostname !== "old.example")).toBe(true);
    expect(saved[0].status).toBe("SCORED");
  });

  it("clears records while leaving the opt-in preference intact", async () => {
    await setHistoryEnabled(true);
    await recordHistoryResults([scoredResult], "www.amazon.com", "amazon.reviews.v1");
    await clearHistory();
    expect(state[RECORDS]).toEqual([]);
    expect(await isHistoryEnabled()).toBe(true);
  });
});
