import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const EXT = join(import.meta.dirname, "..");
const REPO = join(EXT, "..");
const CONTRACTS = join(REPO, "contracts", "v1");

const en = JSON.parse(readFileSync(join(EXT, "src", "i18n", "en.json"), "utf8"));
const fr = JSON.parse(readFileSync(join(EXT, "src", "i18n", "fr.json"), "utf8"));
const tokensCss = readFileSync(join(EXT, "src", "styles", "tokens.css"), "utf8");
const charterTokensCss = readFileSync(join(REPO, "docs", "design", "tokens.css"), "utf8");
const constants = JSON.parse(readFileSync(join(CONTRACTS, "constants.json"), "utf8"));
const popupHtml = readFileSync(join(EXT, "public", "popup.html"), "utf8");
const popupCss = readFileSync(join(EXT, "public", "popup.css"), "utf8");
const overlaySource = readFileSync(join(EXT, "src", "page-overlay.ts"), "utf8");

function flattenKeys(node: unknown, prefix = ""): string[] {
  if (node === null || typeof node !== "object") return [prefix];
  return Object.entries(node as Record<string, unknown>).flatMap(([key, value]) =>
    flattenKeys(value, prefix ? `${prefix}.${key}` : key),
  );
}

/* Normative copy deck (docs/product-decisions.md) — English side, verbatim. */
const NORMATIVE_UI: Record<string, string> = {
  "ui.estimateDisclaimer":
    "Estimated from text patterns. Does not verify purchase, identity, or truth.",
  "ui.lowEvidence": "Indicative — limited text",
  "ui.unknownHeading": "No estimate",
  "ui.unsupportedPage": "This page is not supported yet.",
  "ui.noReviewsFound": "No reviews found to analyze.",
  "ui.insufficientText": "Not enough text to estimate.",
  "ui.unsupportedLanguage": "This language is not supported yet.",
  "ui.timeout": "Analysis timed out. Try again.",
  "ui.unavailable": "Analysis is unavailable right now. Try again.",
  "ui.signalOnlyMode": "Descriptive signals only — no score",
  "ui.detailsAction": "Details",
  "ui.retryAction": "Retry",
  "ui.historyLabel": "History",
  "ui.clearHistoryAction": "Clear history",
};

describe("design system in code", () => {
  it("extension tokens.css is a verbatim copy of the charter value source", () => {
    expect(tokensCss).toBe(charterTokensCss);
  });

  it("English and French string files share the same key set", () => {
    const enKeys = flattenKeys(en).sort();
    const frKeys = flattenKeys(fr).sort();
    expect(frKeys).toEqual(enKeys);
  });

  it("band names match the contract verdict enum exactly", () => {
    const contractBands = constants.bands.map((b: { name: string }) => b.name).sort();
    const stringBands = Object.keys(en.band).sort();
    expect(stringBands).toEqual(contractBands);
  });

  it("signal summaries cover every contract signal kind", () => {
    const contractKinds = constants.signals.map((s: { kind: string }) => s.kind).sort();
    const summaryKeys = Object.keys(en.signal)
      .filter((key) => key !== "contributionsNote" && key !== "adequateEvidence")
      .sort();
    expect(summaryKeys).toEqual(contractKinds);
  });

  it("six solid trust stops per ledger and no gradients anywhere", () => {
    const dayBlock = tokensCss.slice(0, tokensCss.indexOf("[data-tl-theme"));
    const nightBlock = tokensCss.slice(tokensCss.indexOf("[data-tl-theme"));
    for (const [name, block] of [["day", dayBlock], ["night", nightBlock]] as const) {
      const stops = [...block.matchAll(/--tl-stop-\d:\s*(#[0-9A-Fa-f]{6})/g)].map((m) => m[1]);
      expect(stops, `${name} ledger stops`).toHaveLength(6);
      expect(new Set(stops).size, `${name} ledger unique stops`).toBe(6);
    }
    expect(tokensCss).not.toContain("gradient");
  });

  it("normative interface strings match the copy deck verbatim", () => {
    for (const [path, expected] of Object.entries(NORMATIVE_UI)) {
      const actual = path.split(".").reduce((node: unknown, part) => {
        return (node as Record<string, unknown>)?.[part];
      }, en as unknown);
      expect(actual, `en.json ${path}`).toBe(expected);
    }
  });

  it("normative band names match the copy deck verbatim", () => {
    const expected: Record<string, string> = {
      STRONG_MANIPULATION_SIGNALS: "Strong manipulation signals",
      LIKELY_MANIPULATED: "Likely manipulated",
      INCONCLUSIVE: "Inconclusive",
      MIXED_SIGNALS: "Mixed signals",
      LIKELY_ORGANIC: "Likely organic",
      STRONG_ORGANIC_SIGNALS: "Strong organic signals",
    };
    for (const [code, label] of Object.entries(expected)) {
      expect(en.band[code], `en.json band.${code}`).toBe(label);
    }
  });

  it("transport failure messages cover every request-error reason code", () => {
    const requestErrorCodes = constants.reasonCodes
      .filter((r: { scope: string }) => r.scope === "request_error")
      .map((r: { code: string }) => r.code)
      .sort();
    const transportCodes = Object.keys(en.transport).sort();
    expect(transportCodes).toEqual(requestErrorCodes);
  });

  it("keeps the popup keyboard operable with visible focus and a labelled live result region", () => {
    expect(popupHtml).toContain('<label for="review-text">');
    expect(popupHtml).toContain('id="result" role="status" aria-live="polite"');
    expect(popupHtml).toContain('type="button"');
    expect(popupCss).toContain("textarea:focus");
    expect(popupCss).toContain("button:focus-visible");
  });

  it("gives the page panel a named region, live status, and visible retry focus", () => {
    expect(overlaySource).toContain('panel.setAttribute("role", "region")');
    expect(overlaySource).toContain('panel.setAttribute("aria-live", "polite")');
    expect(overlaySource).toContain('article.setAttribute("aria-label"');
    expect(overlaySource).toContain("button:focus-visible");
  });
});
