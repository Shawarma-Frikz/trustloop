import type { PageState } from "./page-scanner.js";
import { presentResult } from "./result-presentation.js";
import en from "./i18n/en.json";
import fr from "./i18n/fr.json";

function element<K extends keyof HTMLElementTagNameMap>(
  documentRef: Document,
  tag: K,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = documentRef.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

export function installPageOverlay(
  onRetry: () => void,
  documentRef: Document = document,
  shadowMode: ShadowRootMode = "closed",
): (state: PageState) => void {
  const host = documentRef.createElement("div");
  host.id = "trustloop-overlay-host";
  const shadow = host.attachShadow({ mode: shadowMode });
  const style = element(documentRef, "style");
  style.textContent = `
    :host { all: initial; }
    .panel { position: fixed; z-index: 2147483647; right: 18px; bottom: 18px; width: 360px;
      max-height: 55vh; overflow: auto; padding: 14px; box-sizing: border-box;
      background: #faf8f1; color: #153d39; border: 1px solid #c9c0af; border-top: 3px solid #14544d;
      box-shadow: 0 4px 18px #0003; font: 13px/1.45 "Segoe UI", sans-serif; }
    h2 { margin: 0 0 6px; font: 600 20px/1.1 Georgia, serif; }
    p { margin: 4px 0 8px; }
    .results { display: grid; gap: 8px; margin: 8px 0; }
    .result { border: 1px solid #c9c0af; padding: 9px; overflow-wrap: anywhere; }
    .badge { display: inline-block; border: 1px solid currentColor; padding: 2px 6px; font-size: 11px; font-weight: 700; }
    h3 { margin: 6px 0; font-size: 15px; }
    .detail { margin: 3px 0; }
    .qualifier { font-weight: 700; }
    .signals { margin: 4px 0; padding-left: 18px; }
    button { border: 0; background: #14544d; color: white; padding: 7px 12px; font-weight: 600; cursor: pointer; }
    button:focus-visible { outline: 3px solid #cf7955; outline-offset: 2px; }
    .note { color: #52615d; font-size: 11px; }
  `;
  const panel = element(documentRef, "section");
  panel.className = "panel";
  panel.setAttribute("role", "region");
  panel.setAttribute("aria-label", "TrustLoop review analysis");
  panel.setAttribute("aria-live", "polite");
  panel.setAttribute("aria-relevant", "text additions");
  const title = element(documentRef, "h2", "TrustLoop");
  const status = element(documentRef, "p");
  status.setAttribute("role", "status");
  const results = element(documentRef, "div");
  results.className = "results";
  const disclaimer = element(documentRef, "p", "Text-pattern estimates only; they do not verify a purchase, identity, or truth.");
  disclaimer.className = "note";
  const retry = element(documentRef, "button", "Retry");
  retry.type = "button";
  retry.hidden = true;
  retry.addEventListener("click", onRetry);
  panel.append(title, status, results, disclaimer, retry);
  shadow.append(style, panel);
  (documentRef.body ?? documentRef.documentElement).append(host);

  return (state: PageState) => {
    const language = documentRef.documentElement.lang.toLowerCase().startsWith("fr") ? "fr" : "en";
    const copy = language === "fr" ? fr : en;
    disclaimer.textContent = copy.ui.estimateDisclaimer;
    retry.textContent = copy.ui.retryAction;
    retry.setAttribute("aria-label", copy.ui.retryAction);
    panel.dataset.reasonCode = state.status === "UNSUPPORTED_PAGE" ? "UNSUPPORTED_PAGE" : "";
    if (state.status === "SCANNING") status.textContent = copy.page.readingReviews;
    else if (state.status === "UNSUPPORTED_PAGE") status.textContent = copy.ui.unsupportedPage;
    else if (state.status === "NO_REVIEWS_FOUND") status.textContent = copy.ui.noReviewsFound;
    else if (state.status === "INSUFFICIENT_TEXT") status.textContent = copy.ui.insufficientText;
    else if (state.status === "UNAVAILABLE") status.textContent = copy.ui.unavailable;
    else {
      const phrase = state.results.length === 1 ? copy.page.reviewsFound.one : copy.page.reviewsFound.other;
      status.textContent = phrase.replace("{count}", String(state.results.length));
    }
    results.replaceChildren(...state.results.map((result, index) => {
      const view = presentResult(result, language);
      const article = element(documentRef, "article");
      article.className = "result";
      article.setAttribute("aria-label", `${copy.ui.reviewLabel} ${index + 1}. ${view.accessibleLabel}`);
      const badge = element(documentRef, "span", view.statusLabel);
      badge.className = "badge";
      const heading = element(documentRef, "h3", view.headline);
      article.append(badge, heading);
      for (const detail of [view.scoreLine, view.verdictLine, view.qualifier, view.reasonLine, view.evidenceLine, view.engineLine]) {
        if (!detail) continue;
        const paragraph = element(documentRef, "p", detail);
        paragraph.className = detail === view.qualifier ? "detail qualifier" : "detail";
        article.append(paragraph);
      }
      if (view.signals.length > 0) {
        const list = element(documentRef, "ul");
        list.className = "signals";
        view.signals.forEach((signal) => list.append(element(documentRef, "li", signal)));
        article.append(list);
      }
      return article;
    }));
    retry.hidden = !state.retryAvailable;
    retry.disabled = state.status === "SCANNING";
  };
}
