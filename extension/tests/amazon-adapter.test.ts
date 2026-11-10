import { readFileSync } from "node:fs";
import { join } from "node:path";
import { JSDOM } from "jsdom";
import { describe, expect, it } from "vitest";
import { extractEligibleReviews, supportsAmazonReviewPage } from "../src/adapters/amazon.js";

const FIXTURES = join(import.meta.dirname, "../mock/fixtures/amazon");
const variants = ["standard", "collapsed", "compact", "dom-hook"] as const;
const pageUrl = new URL("https://www.amazon.com/product-reviews/B012345678");

function fixtureDocument(variant: string): Document {
  const dom = new JSDOM(readFileSync(join(FIXTURES, `${variant}.html`), "utf8"));
  Object.defineProperty(dom.window.HTMLElement.prototype, "getBoundingClientRect", {
    value: () => ({ width: 240, height: 48, top: 0, right: 240, bottom: 48, left: 0, x: 0, y: 0, toJSON: () => ({}) }),
  });
  return dom.window.document;
}

const fixedSalt = new Uint8Array(32).fill(7);

describe("Amazon adapter v1", () => {
  it.each(variants)("extracts five eligible reviews from the %s saved fixture", async (variant) => {
    const result = await extractEligibleReviews(fixtureDocument(variant), pageUrl, { salt: fixedSalt });
    expect(result.status).toBe("READY");
    if (result.status !== "READY") return;
    expect(result.reviews).toHaveLength(5);
    expect(result.reviews.every(({ text }) => text.trim().split(/\s+/u).length >= 20)).toBe(true);
    expect(result.reviews.every(({ reviewKey }) => /^r-[a-f0-9]{40}$/.test(reviewKey))).toBe(true);
    expect(JSON.stringify(result.reviews)).not.toContain("customer_review-");
  });

  it("excludes hidden/collapsed text even when it remains in the DOM", async () => {
    const result = await extractEligibleReviews(fixtureDocument("collapsed"), pageUrl, { salt: fixedSalt });
    expect(result.status).toBe("READY");
    if (result.status !== "READY") return;
    expect(result.reviews).toHaveLength(5);
    expect(result.reviews.some(({ text }) => text.includes("collapsed example"))).toBe(false);
  });

  it("keeps keys stable within one page session and changes them with a new salt", async () => {
    const document = fixtureDocument("standard");
    const first = await extractEligibleReviews(document, pageUrl, { salt: fixedSalt });
    const second = await extractEligibleReviews(document, pageUrl, { salt: fixedSalt });
    const nextSession = await extractEligibleReviews(document, pageUrl, { salt: new Uint8Array(32).fill(8) });
    expect(first.status).toBe("READY");
    expect(second.status).toBe("READY");
    expect(nextSession.status).toBe("READY");
    if (first.status === "READY" && second.status === "READY" && nextSession.status === "READY") {
      expect(second.reviews.map((review) => review.reviewKey)).toEqual(first.reviews.map((review) => review.reviewKey));
      expect(nextSession.reviews[0].reviewKey).not.toBe(first.reviews[0].reviewKey);
    }
  });

  it("rejects unsupported hosts and non-review routes", () => {
    expect(supportsAmazonReviewPage(new URL("https://www.amazon.com/gp/bestsellers"))).toBe(false);
    expect(supportsAmazonReviewPage(new URL("https://example.com/product-reviews/B012345678"))).toBe(false);
    expect(supportsAmazonReviewPage(new URL("http://www.amazon.fr/product-reviews/B012345678"))).toBe(false);
  });

  it("accepts Amazon's slug-prefixed product detail route", () => {
    expect(supportsAmazonReviewPage(new URL(
      "https://www.amazon.com/Hanes-EcoSmart-Fleece-Sweatshirt-Stonewashed/dp/B071JYV6LN/ref=sr_1_9",
    ))).toBe(true);
  });

  it("returns the explicit unsupported state for an unsupported fixture URL", async () => {
    const result = await extractEligibleReviews(fixtureDocument("unsupported"), new URL("https://www.amazon.com/gp/bestsellers"), { salt: fixedSalt });
    expect(result).toEqual({ status: "UNSUPPORTED_PAGE", reviews: [] });
  });
});
