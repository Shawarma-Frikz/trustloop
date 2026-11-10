import { analyzeOneReview, AnalyzeRequestError, type PublicResult } from "./scoring-api.js";
import { presentResult as makePresentation } from "./result-presentation.js";

function required<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`TrustLoop popup is missing ${selector}`);
  return element;
}

const form = required<HTMLFormElement>("#analysis-form");
const textInput = required<HTMLTextAreaElement>("#review-text");
const analyzeButton = required<HTMLButtonElement>("#analyze-button");
const resultRegion = required<HTMLElement>("#result");
const resultStatus = required<HTMLElement>("#result-status");
const resultTitle = required<HTMLElement>("#result-title");
const resultMessage = required<HTMLElement>("#result-message");
const retryButton = required<HTMLButtonElement>("#retry-button");

let lastText: string | null = null;

function presentError(message: string, retryable: boolean): void {
  resultRegion.hidden = false;
  resultRegion.dataset.state = "error";
  resultRegion.setAttribute("aria-label", `No estimate. ${message}`);
  resultStatus.textContent = "No estimate";
  resultTitle.textContent = "No estimate";
  resultMessage.textContent = message;
  retryButton.hidden = !retryable;
}

function renderResult(result: PublicResult): void {
  const language = navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
  const view = makePresentation(result, language);
  resultRegion.hidden = false;
  resultRegion.dataset.state = result.status === "UNKNOWN" ? "error" : "ready";
  resultStatus.textContent = view.statusLabel;
  resultRegion.setAttribute("aria-label", view.accessibleLabel);
  resultTitle.textContent = view.headline;
  resultMessage.textContent = [
    view.scoreLine, view.verdictLine, view.qualifier, view.reasonLine,
    view.evidenceLine, view.engineLine, ...view.signals,
  ].filter(Boolean).join(". ");
  retryButton.hidden = !view.retryAvailable;
}

async function submit(text: string): Promise<void> {
  analyzeButton.disabled = true;
  retryButton.disabled = true;
  resultRegion.hidden = false;
  resultRegion.dataset.state = "ready";
  resultRegion.setAttribute("aria-busy", "true");
  resultTitle.textContent = "Analyzing…";
  resultStatus.textContent = "Analyzing";
  resultMessage.textContent = "Text is sent to the local API for this request.";
  retryButton.hidden = true;
  try {
    renderResult(await analyzeOneReview(text));
  } catch (error) {
    const retryable = error instanceof AnalyzeRequestError ? error.retryable : true;
    presentError(error instanceof Error ? error.message : "Analysis is unavailable.", retryable);
  } finally {
    resultRegion.setAttribute("aria-busy", "false");
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
