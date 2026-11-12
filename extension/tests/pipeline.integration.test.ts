import { readFileSync } from "node:fs";
import { join } from "node:path";
import { JSDOM } from "jsdom";
import { describe, expect, it, vi } from "vitest";
import { createPageScanner } from "../src/page-scanner.js";
import { installPageOverlay } from "../src/page-overlay.js";
import { analyzeReviewBatch } from "../src/scoring-api.js";
import { presentResult } from "../src/result-presentation.js";
import type { PublicResult } from "../src/scoring-api.js";

const FIXTURE = join(import.meta.dirname, "../mock/fixtures/amazon/standard.html");
const PAGE_URL = new URL("https://www.amazon.com/product-reviews/B012345678");

describe("fixture-to-panel integration", () => {
  it("scans saved markup through the adapter and API client, then renders the contract response", async () => {
    const dom = new JSDOM(readFileSync(FIXTURE, "utf8"));
    Object.defineProperty(dom.window.HTMLElement.prototype, "getBoundingClientRect", {
      value: () => ({ width: 240, height: 48, top: 0, right: 240, bottom: 48, left: 0, x: 0, y: 0, toJSON: () => ({}) }),
    });
    const document = dom.window.document;
    const capturedRequests: { id: string | null; body: Record<string, unknown> }[] = [];
    let returnedResults: PublicResult[] = [];

    const stubApi: typeof fetch = vi.fn(async (_input, init) => {
      const body = JSON.parse(String(init?.body)) as {
        adapterId: string;
        languageHint: string;
        reviews: { reviewKey: string; text: string }[];
      };
      const requestId = new Headers(init?.headers).get("X-Request-Id");
      capturedRequests.push({ id: requestId, body });
      returnedResults = body.reviews.map((review, index) => ({
        reviewKey: review.reviewKey,
        status: "SCORED",
        trustScore: 71 + index,
        verdict: "LIKELY_ORGANIC",
        evidenceQuality: "ADEQUATE",
        signals: [{ kind: "CONCRETE_DETAIL", summary: "A synthetic fixture signal", contribution: 0.2 }],
        modelVersion: "tl-text-1.1.0",
        engine: "MODEL",
      })) as PublicResult[];
      return new Response(JSON.stringify({ requestId, results: returnedResults }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const updatePanel = installPageOverlay(() => undefined, document, "open");
    const scanner = createPageScanner({
      document,
      getUrl: () => PAGE_URL,
      render: updatePanel,
      observe: false,
      isRendered: () => true,
      sendBatch: async (reviews, languageHint) => ({
        ok: true,
        results: await analyzeReviewBatch(reviews, languageHint, stubApi),
      }),
    });

    scanner.start();
    await vi.waitFor(() => expect(document.querySelector("#trustloop-overlay-host")?.shadowRoot?.querySelectorAll(".result")).toHaveLength(5));

    const panel = document.querySelector("#trustloop-overlay-host")?.shadowRoot;
    expect(panel?.querySelector("[role='status']")?.textContent).toBe("5 reviews found");
    expect(capturedRequests).toHaveLength(1);
    expect(capturedRequests[0].id).toMatch(/^ext-[0-9a-f-]{36}$/);
    expect(capturedRequests[0].body).toMatchObject({ adapterId: "amazon.reviews.v1", languageHint: "en" });
    const requestReviews = capturedRequests[0].body.reviews as { reviewKey: string; text: string }[];
    expect(requestReviews).toHaveLength(5);

    const cards = Array.from(panel!.querySelectorAll<HTMLElement>(".result"));
    expect(cards).toHaveLength(returnedResults.length);
    returnedResults.forEach((result, index) => {
      const presentation = presentResult(result, "en");
      const text = cards[index].textContent ?? "";
      expect(text).toContain(presentation.statusLabel);
      expect(text).toContain(presentation.headline);
      expect(text).toContain(presentation.scoreLine);
      expect(text).toContain(presentation.verdictLine);
      expect(text).toContain(presentation.evidenceLine);
      expect(text).toContain(presentation.engineLine);
      expect(text).not.toContain(result.reviewKey);
      expect(text).not.toContain(requestReviews[index].reviewKey);
      expect(text).not.toContain(requestReviews[index].text);
    });
    scanner.stop();
  });
});
