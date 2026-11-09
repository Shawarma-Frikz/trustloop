import type { PageState } from "./page-scanner.js";
import en from "./i18n/en.json";
import fr from "./i18n/fr.json";

function element<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

export function installPageOverlay(onRetry: () => void): (state: PageState) => void {
  const host = document.createElement("div");
  host.id = "trustloop-overlay-host";
  const shadow = host.attachShadow({ mode: "closed" });
  const style = element("style");
  style.textContent = `
    :host { all: initial; }
    .panel { position: fixed; z-index: 2147483647; right: 18px; bottom: 18px; width: 320px;
      max-height: 45vh; overflow: auto; padding: 14px; box-sizing: border-box;
      background: #faf8f1; color: #153d39; border: 1px solid #c9c0af; border-top: 3px solid #14544d;
      box-shadow: 0 4px 18px #0003; font: 13px/1.45 "Segoe UI", sans-serif; }
    h2 { margin: 0 0 6px; font: 600 20px/1.1 Georgia, serif; }
    p { margin: 4px 0 8px; }
    ul { margin: 8px 0; padding-left: 18px; }
    li { margin: 4px 0; overflow-wrap: anywhere; }
    button { border: 0; background: #14544d; color: white; padding: 7px 12px; font-weight: 600; cursor: pointer; }
    button:focus-visible { outline: 3px solid #cf7955; outline-offset: 2px; }
    .note { color: #52615d; font-size: 11px; }
  `;
  const panel = element("section");
  panel.className = "panel";
  panel.setAttribute("role", "region");
  panel.setAttribute("aria-label", "TrustLoop review analysis");
  panel.setAttribute("aria-live", "polite");
  const title = element("h2", "TrustLoop");
  const status = element("p");
  const results = element("ul");
  const disclaimer = element("p", "Text-pattern estimates only; they do not verify a purchase, identity, or truth.");
  disclaimer.className = "note";
  const retry = element("button", "Retry");
  retry.type = "button";
  retry.hidden = true;
  retry.addEventListener("click", onRetry);
  panel.append(title, status, results, disclaimer, retry);
  shadow.append(style, panel);
  (document.body ?? document.documentElement).append(host);

  return (state: PageState) => {
    const copy = document.documentElement.lang.toLowerCase().startsWith("fr") ? fr : en;
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
      const summary = result.status === "SCORED"
        ? `${result.trustScore ?? "—"}/100 · ${copy.band[result.verdict as keyof typeof en.band] ?? copy.ui.unknownHeading}`
        : result.status === "SIGNALS_ONLY"
          ? copy.ui.signalOnlyMode
          : `${copy.ui.unknownHeading} · ${result.reasonCode === "SCORING_TIMEOUT" ? copy.ui.timeout : result.reasonCode === "SCORING_UNAVAILABLE" ? copy.ui.unavailable : result.reasonCode ?? "UNKNOWN"}`;
      const reviewLabel = document.documentElement.lang.toLowerCase().startsWith("fr") ? "Avis" : "Review";
      return element("li", `${reviewLabel} ${index + 1}: ${summary}`);
    }));
    retry.hidden = !state.retryAvailable;
    retry.disabled = state.status === "SCANNING";
  };
}
