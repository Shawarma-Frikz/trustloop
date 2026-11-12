import { readFileSync } from "node:fs";
import { join } from "node:path";
import { JSDOM } from "jsdom";
import { describe, expect, it } from "vitest";
import { amazonReviewAdapterManifest, extractEligibleReviews, supportsAmazonReviewPage } from "../src/adapters/amazon.js";

const FIXTURES = join(import.meta.dirname, "../mock/fixtures/amazon");
const manifest = amazonReviewAdapterManifest;
const fixtureName = (path: string) => path.split("/").at(-1)!.replace(/\.html$/u, "");
const supportedFixtures = manifest.fixtures.supported.map(fixtureName);
const pageUrl = new URL("https://www.amazon.com/product-reviews/B012345678");

function fixtureDocument(variant: string): Document {
  const dom = new JSDOM(readFileSync(join(FIXTURES, `${variant}.html`), "utf8"));
  Object.defineProperty(dom.window.HTMLElement.prototype, "getBoundingClientRect", {
    value: () => ({ width: 240, height: 48, top: 0, right: 240, bottom: 48, left: 0, x: 0, y: 0, toJSON: () => ({}) }),
  });
  return dom.window.document;
}

const fixedSalt = new Uint8Array(32).fill(7);

describe("Amazon adapter manifest and fixtures", () => {
  it("declares a versioned scope, selectors, eligibility rules, and existing fixtures", () => {
    expect(manifest.id).toBe("amazon.reviews.v1");
    expect(manifest.version).toMatch(/^\d+\.\d+\.\d+$/u);
    expect(manifest.description.trim().length).toBeGreaterThan(30);
    expect(manifest.supportedPages).toContain("https://www.amazon.com/dp/<ASIN>");
    expect(manifest.supportedPages).toContain("https://www.amazon.fr/product-reviews/<ASIN>");
    expect(manifest.cardSelectors.length).toBeGreaterThan(0);
    expect(manifest.bodySelectors.length).toBeGreaterThan(0);
    expect(manifest.eligibility).toMatchObject({
      renderedOnly: true,
      excludeHiddenAncestors: true,
      requireNonEmptyBody: true,
      normalization: "NFKC_WHITESPACE_COLLAPSE",
      minimumWords: 20,
      maximumCharacters: 2000,
    });
    for (const fixture of [...manifest.fixtures.supported, manifest.fixtures.unsupported]) {
      expect(readFileSync(join(import.meta.dirname, "..", fixture), "utf8")).toContain("data-fixture-source=\"synthetic\"");
    }
  });

  it.each(supportedFixtures)("extracts five eligible reviews from the %s saved fixture", async (variant) => {
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
    const result = await extractEligibleReviews(
      fixtureDocument(fixtureName(manifest.fixtures.unsupported)),
      new URL(manifest.fixtures.unsupportedTestUrl),
      { salt: fixedSalt },
    );
    expect(result).toEqual({ status: "UNSUPPORTED_PAGE", reviews: [] });
  });

  it("accepts each documented host only on its documented review/product route", () => {
    for (const host of manifest.hosts) {
      const supported = manifest.supportedPages
        .filter((page) => page.startsWith(`https://${host}/`))
        .map((page) => page.replace("<ASIN>", "B012345678"));
      expect(supported.length).toBeGreaterThan(0);
      for (const page of supported) expect(supportsAmazonReviewPage(new URL(page))).toBe(true);
      expect(supportsAmazonReviewPage(new URL(`https://${host}/gp/bestsellers`))).toBe(false);
    }
  });
});
