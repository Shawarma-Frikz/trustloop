import { JSDOM } from "jsdom";
import { describe, expect, it, vi } from "vitest";
import { createPageScanner, mutationRescanDelay, type BatchResponse, type PageState } from "../src/page-scanner.js";
import type { ReviewForAnalysis } from "../src/adapters/amazon.js";
import { PageSessionStore } from "../src/session-store.js";

const page = new URL("https://www.amazon.com/dp/B012345678");
const reviewText = (index: number) => `Review ${index}: I used this item every weekday for several weeks. It fits in my bag and works reliably, though the latch takes two hands to close.`;

function makeDocument(count: number): Document {
  const dom = new JSDOM("<!doctype html><html lang='fr'><body><main></main></body></html>");
  Object.defineProperty(dom.window.HTMLElement.prototype, "getBoundingClientRect", {
    value: () => ({ width: 240, height: 48, top: 0, right: 240, bottom: 48, left: 0, x: 0, y: 0, toJSON: () => ({}) }),
  });
  const main = dom.window.document.querySelector("main")!;
  for (let index = 0; index < count; index++) main.append(card(dom.window.document, index));
  return dom.window.document;
}

function card(document: Document, index: number): HTMLElement {
  const item = document.createElement("article");
  item.dataset.reviewCard = "";
  item.dataset.reviewId = `fixture-${index}`;
  const body = document.createElement("p");
  body.dataset.reviewBody = "";
  body.textContent = reviewText(index);
  item.append(body);
  return item;
}

describe("page scanning, batching, and session dedup", () => {
  it("keeps only salted keys in an isolated in-memory page session", () => {
    const firstPage = new PageSessionStore();
    const nextPage = new PageSessionStore();
    expect(firstPage.markSeen("r-a1b2")).toBe(true);
    expect(firstPage.markSeen("r-a1b2")).toBe(false);
    expect(firstPage.size).toBe(1);
    expect(nextPage.size).toBe(0);
    expect(Array.from(firstPage.salt)).not.toEqual(Array.from(nextPage.salt));
  });

  it("enforces both the debounce and minimum rescan delay", () => {
    expect(mutationRescanDelay(1_000, 1_000)).toBe(2_000);
    expect(mutationRescanDelay(3_000, 1_000)).toBe(750);
    expect(mutationRescanDelay(1_800, 1_000)).toBe(1_200);
  });

  it("batches at ten, sends fresh reviews once, and survives DOM churn", async () => {
    const document = makeDocument(12);
    const sentSizes: number[] = [];
    const languageHints: string[] = [];
    const render = vi.fn<(state: PageState) => void>();
    const sendBatch = vi.fn(async (reviews: ReviewForAnalysis[], languageHint: "en" | "fr"): Promise<BatchResponse> => {
      sentSizes.push(reviews.length);
      languageHints.push(languageHint);
      return {
        ok: true,
        results: reviews.map(({ reviewKey }) => ({
          reviewKey, status: "SCORED" as const, trustScore: 75,
          verdict: "LIKELY_ORGANIC", signals: [],
        })),
      };
    });
    const scanner = createPageScanner({ document, getUrl: () => page, sendBatch, render, observe: false, isRendered: () => true });

    scanner.start();
    await vi.waitFor(() => expect(sentSizes).toEqual([10, 2]));
    await scanner.scan();
    expect(sentSizes).toEqual([10, 2]);
    expect(scanner.seenCount()).toBe(12);

    document.querySelector("main")!.append(card(document, 0));
    document.querySelector("main")!.append(card(document, 12));
    await scanner.scan();

    expect(sentSizes).toEqual([10, 2, 1]);
    expect(languageHints).toEqual(["fr", "fr", "fr"]);
    expect(render).toHaveBeenLastCalledWith(expect.objectContaining({ status: "COMPLETE", results: expect.any(Array) }));
    scanner.stop();
  });

  it("offers a deliberate retry for transient unknowns without automatic retry", async () => {
    const document = makeDocument(1);
    const sendBatch = vi.fn(async (reviews: ReviewForAnalysis[]): Promise<BatchResponse> => ({
      ok: true,
      results: reviews.map(({ reviewKey }) => ({
        reviewKey, status: "UNKNOWN" as const, reasonCode: "SCORING_UNAVAILABLE", signals: [],
      })),
    }));
    const scanner = createPageScanner({ document, getUrl: () => page, sendBatch, render: vi.fn(), observe: false, isRendered: () => true });

    scanner.start();
    await vi.waitFor(() => expect(sendBatch).toHaveBeenCalledTimes(1));
    await scanner.scan();
    expect(sendBatch).toHaveBeenCalledTimes(1);
    await scanner.retry();
    expect(sendBatch).toHaveBeenCalledTimes(2);
    scanner.stop();
  });

  it("debounces DOM churn and observes the two-second minimum rescan interval", async () => {
    const document = makeDocument(1);
    const sendBatch = vi.fn(async (reviews: ReviewForAnalysis[]): Promise<BatchResponse> => ({
      ok: true,
      results: reviews.map(({ reviewKey }) => ({
        reviewKey, status: "SCORED" as const, trustScore: 74,
        verdict: "LIKELY_ORGANIC", signals: [],
      })),
    }));
    const render = vi.fn<(state: PageState) => void>();
    const scanner = createPageScanner({ document, getUrl: () => page, sendBatch, render, isRendered: () => true });

    scanner.start();
    await vi.waitFor(() => expect(sendBatch).toHaveBeenCalledTimes(1));
    const renderCountBeforeChurn = render.mock.calls.length;
    document.querySelector("main")!.append(card(document, 0));
    await vi.waitFor(() => expect(render.mock.calls.length).toBeGreaterThanOrEqual(renderCountBeforeChurn + 2), { timeout: 3500 });

    expect(sendBatch).toHaveBeenCalledTimes(1);
    scanner.stop();
  });

  it("renders an explicit unsupported-page state", async () => {
    const document = makeDocument(1);
    const render = vi.fn<(state: PageState) => void>();
    const sendBatch = vi.fn();
    const scanner = createPageScanner({
      document,
      getUrl: () => new URL("https://www.amazon.com/gp/bestsellers"),
      sendBatch,
      render,
      observe: false,
    });

    scanner.start();
    await vi.waitFor(() => expect(render).toHaveBeenLastCalledWith({ status: "UNSUPPORTED_PAGE", results: [], retryAvailable: false }));
    expect(render).toHaveBeenCalledWith({ status: "UNSUPPORTED_PAGE", results: [], retryAvailable: false });
    expect(sendBatch).not.toHaveBeenCalled();
    scanner.stop();
  });
});
