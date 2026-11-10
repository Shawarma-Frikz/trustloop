import { describe, expect, it, vi } from "vitest";
import { analyzeOneReview, canManuallyRetry, type PublicResult } from "../src/scoring-api.js";

const unknown: PublicResult = {
  reviewKey: "manual-1",
  status: "UNKNOWN",
  reasonCode: "SCORING_UNAVAILABLE",
  engine: "MODEL",
  signals: [],
};

describe("manual scoring retry", () => {
  it("offers retry only for transient scoring unknown states", () => {
    expect(canManuallyRetry(unknown)).toBe(true);
    expect(canManuallyRetry({ ...unknown, reasonCode: "SCORING_TIMEOUT" })).toBe(true);
    expect(canManuallyRetry({ ...unknown, reasonCode: "INSUFFICIENT_TEXT" })).toBe(false);
    expect(canManuallyRetry({ ...unknown, status: "SCORED", reasonCode: undefined })).toBe(false);
  });

  it("makes one request and leaves retry initiation to a later user action", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [unknown] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));

    const result = await analyzeOneReview("A manually entered review with sufficient text.", fetcher);

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher).toHaveBeenCalledWith("http://127.0.0.1:8080/api/v1/analyze", expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ "X-Request-Id": expect.stringMatching(/^ext-/) }),
    }));
    expect(result).toMatchObject({ status: "UNKNOWN", reasonCode: "SCORING_UNAVAILABLE" });
  });

  it("accepts contract-shaped unknowns with nullable optional fields without turning them into a score", async () => {
    const responseResult = {
      ...unknown,
      trustScore: null,
      verdict: null,
      evidenceQuality: null,
      modelVersion: "tl-text-1.1.0",
    };
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [responseResult] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));

    const result = await analyzeOneReview("A sufficiently long review body used for this contract test.", fetcher);

    expect(result.status).toBe("UNKNOWN");
    expect(result.trustScore).toBeNull();
    expect(canManuallyRetry(result)).toBe(true);
  });

  it("rejects an unknown result that tries to carry a numeric placeholder", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [{ ...unknown, trustScore: 0 }] }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    await expect(analyzeOneReview("A sufficiently long review body used for this contract test.", fetcher))
      .rejects.toMatchObject({ retryable: true });
  });
});
