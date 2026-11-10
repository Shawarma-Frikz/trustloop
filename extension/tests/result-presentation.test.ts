import { describe, expect, it } from "vitest";
import { presentResult } from "../src/result-presentation.js";
import type { PublicResult } from "../src/scoring-api.js";

const adequateScored: PublicResult = {
  reviewKey: "r-test",
  status: "SCORED",
  trustScore: 73,
  verdict: "LIKELY_ORGANIC",
  evidenceQuality: "ADEQUATE",
  engine: "MODEL",
  modelVersion: "tl-text-1.1.0",
  signals: [{ kind: "CONCRETE_DETAIL", summary: "Includes a concrete detail" }],
};

describe("accessible result states", () => {
  it("shows scored adequate results with score, band, evidence, engine, and signals", () => {
    const view = presentResult(adequateScored, "en");
    expect(view.scoreLine).toBe("Trust score: 73/100");
    expect(view.verdictLine).toBe("Verdict: Likely organic");
    expect(view.evidenceLine).toBe("Evidence: Adequate evidence");
    expect(view.engineLine).toBe("Engine: Model");
    expect(view.signals).toContain("Includes a concrete usage detail");
    expect(view.accessibleLabel).toContain("Trust score: 73/100");
    expect(view.accessibleLabel).toContain("Evidence: Adequate evidence");
    expect(view.accessibleLabel).toContain("Engine: Model");
    expect(view.qualifier).toBeUndefined();
  });

  it("keeps a low-evidence score and band while adding the exact qualifier", () => {
    const view = presentResult({
      ...adequateScored, trustScore: 24, verdict: "LIKELY_MANIPULATED", evidenceQuality: "LOW",
    }, "en");
    expect(view.scoreLine).toBe("Trust score: 24/100");
    expect(view.verdictLine).toBe("Verdict: Likely manipulated");
    expect(view.qualifier).toBe("Indicative — limited text");
    expect(view.accessibleLabel).toContain("Indicative — limited text");
  });

  it("shows signals-only with no score or verdict", () => {
    const view = presentResult({
      reviewKey: "r-test", status: "SIGNALS_ONLY", evidenceQuality: "ADEQUATE",
      engine: "SIGNALS_ONLY", signals: [{ kind: "GENERIC_WORDING", summary: "Generic wording", contribution: undefined }],
    }, "en");
    expect(view.headline).toBe("Descriptive signals only — no score");
    expect(view.scoreLine).toBeUndefined();
    expect(view.verdictLine).toBeUndefined();
    expect(view.accessibleLabel).toContain("No score");
    expect(view.accessibleLabel).toContain("No verdict");
    expect(view.engineLine).toBe("Engine: Signals only");
  });

  it("shows unknown with a reason, no numeric placeholder, and retry only when useful", () => {
    const timedOut: PublicResult = {
      reviewKey: "r-test", status: "UNKNOWN", reasonCode: "SCORING_TIMEOUT",
      engine: "MODEL", signals: [],
    };
    const view = presentResult(timedOut, "en");
    expect(view.headline).toBe("No estimate");
    expect(view.scoreLine).toBeUndefined();
    expect(view.verdictLine).toBeUndefined();
    expect(view.reasonLine).toBe("Reason: Analysis timed out. Try again.");
    expect(view.retryAvailable).toBe(true);
    expect(view.accessibleLabel).toContain("Evidence: Unavailable");

    const unavailable = presentResult({ ...timedOut, reasonCode: "SCORING_UNAVAILABLE" }, "en");
    expect(unavailable.reasonLine).toBe("Reason: Analysis is unavailable right now. Try again.");
    expect(unavailable.retryAvailable).toBe(true);
    expect(unavailable.scoreLine).toBeUndefined();

    const insufficient = presentResult({ ...timedOut, reasonCode: "INSUFFICIENT_TEXT" }, "fr");
    expect(insufficient.retryAvailable).toBe(false);
    expect(insufficient.scoreLine).toBeUndefined();
    expect(insufficient.accessibleLabel).toContain("Aucun score");
  });
});
