import { amazonReviewAdapterManifest, extractEligibleReviews, supportsAmazonReviewPage, type ReviewForAnalysis } from "./adapters/amazon.js";
import { canManuallyRetry, type PublicResult } from "./scoring-api.js";
import { PageSessionStore } from "./session-store.js";

export type BatchResponse =
  | { ok: true; results: PublicResult[] }
  | { ok: false; reasonCode: string };

export type PageState = {
  status: "SCANNING" | "UNSUPPORTED_PAGE" | "NO_REVIEWS_FOUND" | "INSUFFICIENT_TEXT" | "COMPLETE" | "UNAVAILABLE";
  results: PublicResult[];
  retryAvailable: boolean;
};

export interface ScannerOptions {
  document: Document;
  getUrl: () => URL;
  sendBatch: (reviews: ReviewForAnalysis[], languageHint: "en" | "fr") => Promise<BatchResponse>;
  render: (state: PageState) => void;
  now?: () => number;
  setTimer?: typeof setTimeout;
  clearTimer?: typeof clearTimeout;
  observe?: boolean;
  isRendered?: (element: HTMLElement) => boolean;
}

export function mutationRescanDelay(now: number, lastScanAt: number): number {
  return Math.max(
    amazonReviewAdapterManifest.scanDebounceMs,
    amazonReviewAdapterManifest.minimumRescanIntervalMs - (now - lastScanAt),
  );
}

export function createPageScanner(options: ScannerOptions) {
  const now = options.now ?? Date.now;
  const setTimer = options.setTimer ?? globalThis.setTimeout.bind(globalThis);
  const clearTimer = options.clearTimer ?? globalThis.clearTimeout.bind(globalThis);
  const session = new PageSessionStore();
  const results = new Map<string, PublicResult>();
  let retryQueue: ReviewForAnalysis[] = [];
  let lastScanAt = Number.NEGATIVE_INFINITY;
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let busy = false;
  let scanQueued = false;
  let stopped = false;
  let observer: MutationObserver | undefined;

  const state = (status: PageState["status"]): PageState => ({
    status,
    results: [...results.values()],
    retryAvailable: retryQueue.length > 0,
  });

  async function send(reviews: ReviewForAnalysis[], isRetry = false): Promise<void> {
    const retainedForRetry = new Map<string, ReviewForAnalysis>(
      (isRetry ? [] : retryQueue).map((review) => [review.reviewKey, review]),
    );
    for (let index = 0; index < reviews.length; index += amazonReviewAdapterManifest.batchSize) {
      const batch = reviews.slice(index, index + amazonReviewAdapterManifest.batchSize);
      const languageHint = options.document.documentElement.lang.toLowerCase().startsWith("fr") ? "fr" : "en";
      try {
        const response = await options.sendBatch(batch, languageHint);
        if (!response.ok) {
          batch.forEach((review) => retainedForRetry.set(review.reviewKey, review));
          continue;
        }
        response.results.forEach((result, itemIndex) => {
          results.set(result.reviewKey, result);
          if (canManuallyRetry(result)) retainedForRetry.set(result.reviewKey, batch[itemIndex]);
        });
      } catch {
        batch.forEach((review) => retainedForRetry.set(review.reviewKey, review));
      }
    }
    retryQueue = [...retainedForRetry.values()];
    options.render(state(retryQueue.length > 0 ? "UNAVAILABLE" : "COMPLETE"));
  }

  async function scan(): Promise<void> {
    if (stopped) return;
    if (busy) {
      scanQueued = true;
      return;
    }
    busy = true;
    lastScanAt = now();
    options.render(state("SCANNING"));
    try {
      const extracted = await extractEligibleReviews(options.document, options.getUrl(), {
        salt: session.salt,
        isRendered: options.isRendered,
      });
      if (extracted.status !== "READY") {
        if (results.size === 0) options.render(state(extracted.status));
        return;
      }
      const fresh = extracted.reviews.filter((review) => session.markSeen(review.reviewKey));
      if (fresh.length > 0) {
        await send(fresh);
      } else if (results.size > 0) {
        options.render(state(retryQueue.length > 0 ? "UNAVAILABLE" : "COMPLETE"));
      }
    } finally {
      busy = false;
      if (scanQueued) {
        scanQueued = false;
        scheduleScan();
      }
    }
  }

  function scheduleScan(): void {
    if (stopped) return;
    if (debounceTimer !== undefined) clearTimer(debounceTimer);
    const delay = mutationRescanDelay(now(), lastScanAt);
    debounceTimer = setTimer(() => void scan(), delay);
  }

  function start(): void {
    stopped = false;
    if (!supportsAmazonReviewPage(options.getUrl())) {
      options.render(state("UNSUPPORTED_PAGE"));
      return;
    }
    if (options.observe !== false) {
      const Observer = options.document.defaultView?.MutationObserver;
      if (Observer) observer = new Observer((records) => {
        const meaningful = records.some((record) => {
          const target = record.target.nodeType === 1
            ? record.target as Element
            : record.target.parentElement;
          return !target?.closest("#trustloop-overlay-host");
        });
        if (meaningful) scheduleScan();
      });
    }
    if (observer) {
      observer.observe(options.document.documentElement, { subtree: true, childList: true, attributes: true,
        attributeFilter: ["hidden", "aria-hidden", "aria-expanded", "class", "style"] });
    }
    void scan();
  }

  async function retry(): Promise<void> {
    if (stopped || busy || retryQueue.length === 0) return;
    busy = true;
    options.render(state("SCANNING"));
    try {
      await send([...retryQueue], true);
    } finally {
      busy = false;
      if (scanQueued) {
        scanQueued = false;
        scheduleScan();
      }
    }
  }

  function stop(): void {
    stopped = true;
    observer?.disconnect();
    if (debounceTimer !== undefined) clearTimer(debounceTimer);
  }

  return { start, scan, retry, stop, seenCount: () => session.size };
}
