import { analyzeOneReview, AnalyzeRequestError, canManuallyRetry, type PublicResult } from "./scoring-api.js";

function required<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`TrustLoop popup is missing ${selector}`);
  return element;
}

const form = required<HTMLFormElement>("#analysis-form");
const textInput = required<HTMLTextAreaElement>("#review-text");
const analyzeButton = required<HTMLButtonElement>("#analyze-button");
const resultRegion = required<HTMLElement>("#result");
const resultTitle = required<HTMLElement>("#result-title");
const resultMessage = required<HTMLElement>("#result-message");
const retryButton = required<HTMLButtonElement>("#retry-button");

let lastText: string | null = null;

function presentError(message: string, retryable: boolean): void {
  resultRegion.hidden = false;
  resultRegion.dataset.state = "error";
  resultTitle.textContent = "No estimate";
  resultMessage.textContent = message;
  retryButton.hidden = !retryable;
}

function presentResult(result: PublicResult): void {
  resultRegion.hidden = false;
  resultRegion.dataset.state = result.status === "UNKNOWN" ? "error" : "ready";
  resultTitle.textContent = result.status === "SCORED" && result.trustScore !== undefined
    ? `Estimated trust score: ${result.trustScore}/100`
    : result.status === "SIGNALS_ONLY" ? "Descriptive signals only" : "No estimate";
  resultMessage.textContent = result.status === "UNKNOWN"
    ? result.reasonCode === "SCORING_TIMEOUT"
      ? "Analysis timed out. You can retry this review manually."
      : result.reasonCode === "SCORING_UNAVAILABLE"
        ? "Analysis is unavailable right now. You can retry this review manually."
        : "There is not enough supported evidence to provide an estimate."
    : result.verdict ?? "Estimated from text patterns; this does not establish whether a review is genuine.";
  retryButton.hidden = !canManuallyRetry(result);
}

async function submit(text: string): Promise<void> {
  analyzeButton.disabled = true;
  retryButton.disabled = true;
  resultRegion.hidden = false;
  resultRegion.dataset.state = "ready";
  resultTitle.textContent = "Analyzing…";
  resultMessage.textContent = "Text is sent to the local API for this request.";
  retryButton.hidden = true;
  try {
    presentResult(await analyzeOneReview(text));
  } catch (error) {
    const retryable = error instanceof AnalyzeRequestError ? error.retryable : true;
    presentError(error instanceof Error ? error.message : "Analysis is unavailable.", retryable);
  } finally {
    analyzeButton.disabled = false;
    retryButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = textInput.value.trim();
  if (!text) {
    textInput.focus();
    return;
  }
  lastText = text;
  void submit(text);
});

retryButton.addEventListener("click", () => {
  if (lastText !== null) void submit(lastText);
});
