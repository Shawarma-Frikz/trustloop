import { readFileSync } from "node:fs";
import { join } from "node:path";
import { JSDOM } from "jsdom";
import { describe, expect, it } from "vitest";

const FIXTURES = join(import.meta.dirname, "../mock/fixtures/amazon");
const VARIANTS = ["standard", "collapsed", "compact"] as const;

describe("Phase 0.5 synthetic fallback fixtures", () => {
  it.each(VARIANTS)("%s has five eligible visible cards", (variant) => {
    const html = readFileSync(join(FIXTURES, `${variant}.html`), "utf8");
    const document = new JSDOM(html).window.document;

    expect(document.body.dataset.fixtureSource).toBe("synthetic");
    const cards = Array.from(document.querySelectorAll<HTMLElement>("[data-review-card]"));
    const visible = cards.filter((card) => !card.hidden && card.getAttribute("aria-hidden") !== "true");
    const eligible = visible.filter((card) => {
      const text = card.querySelector("[data-review-body]")?.textContent ?? "";
      return text.trim().split(/\s+/).filter(Boolean).length >= 20;
    });

    expect(eligible).toHaveLength(5);
  });

  it("excludes the collapsed card even when its text remains in the markup", () => {
    const html = readFileSync(join(FIXTURES, "collapsed.html"), "utf8");
    const document = new JSDOM(html).window.document;
    const cards = Array.from(document.querySelectorAll<HTMLElement>("[data-review-card]"));
    const hidden = cards.filter((card) => card.hidden || card.getAttribute("aria-hidden") === "true");

    expect(cards).toHaveLength(6);
    expect(hidden).toHaveLength(1);
  });
});
