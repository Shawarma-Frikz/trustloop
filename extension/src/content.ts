import { amazonReviewAdapterManifest } from "./adapters/amazon.js";
import { installPageOverlay } from "./page-overlay.js";
import { createPageScanner, type BatchResponse } from "./page-scanner.js";

if (amazonReviewAdapterManifest.hosts.includes(location.hostname)) {
  let scanner: ReturnType<typeof createPageScanner>;
  const render = installPageOverlay(() => scanner?.retry());
  scanner = createPageScanner({
    document,
    getUrl: () => new URL(location.href),
    render,
    sendBatch: (reviews, languageHint) => new Promise<BatchResponse>((resolve) => {
      chrome.runtime.sendMessage({ type: "ANALYZE_BATCH", reviews, languageHint }, (response) => {
        if (chrome.runtime.lastError || !response || typeof response.ok !== "boolean") {
          resolve({ ok: false, reasonCode: "SCORING_UNAVAILABLE" });
          return;
        }
        resolve(response as BatchResponse);
      });
    }),
  });
  scanner.start();
  window.addEventListener("pagehide", () => scanner.stop(), { once: true });
}
