import manifest from "./amazon-reviews.v1.json";

export { manifest as amazonReviewAdapterManifest };

export interface ReviewForAnalysis {
  reviewKey: string;
  text: string;
}

export type ExtractionResult =
  | { status: "READY"; reviews: ReviewForAnalysis[] }
  | { status: "UNSUPPORTED_PAGE" | "NO_REVIEWS_FOUND" | "INSUFFICIENT_TEXT"; reviews: ReviewForAnalysis[] };

export interface ExtractionOptions {
  isRendered?: (element: HTMLElement) => boolean;
  salt?: Uint8Array;
}

const PATH_PATTERN = new RegExp(manifest.pathPattern);

export function supportsAmazonReviewPage(url: URL): boolean {
  return url.protocol === "https:"
    && manifest.hosts.includes(url.hostname)
    && PATH_PATTERN.test(url.pathname);
}

function defaultIsRendered(element: HTMLElement): boolean {
  for (let current: HTMLElement | null = element; current; current = current.parentElement) {
    if (current.hidden || current.getAttribute("aria-hidden") === "true") return false;
    const style = current.ownerDocument.defaultView?.getComputedStyle(current);
    if (style?.display === "none" || style?.visibility === "hidden" || style?.visibility === "collapse") return false;
  }
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

export function normalizeReviewText(text: string): string {
  return text.normalize("NFKC").replace(/\s+/gu, " ").trim();
}

function wordCount(text: string): number {
  return text ? text.split(/\s+/u).length : 0;
}

function stableCardIdentity(card: HTMLElement): string | null {
  const reviewId = card.getAttribute("data-review-id");
  if (reviewId && /^[A-Za-z0-9_-]{1,128}$/.test(reviewId)) return `id:${reviewId}`;
  const id = card.id;
  if (id && /^customer_review-[A-Za-z0-9_-]{1,128}$/.test(id)) return `id:${id}`;
  return null;
}

async function saltedKey(identity: string, salt: Uint8Array): Promise<string> {
  const bytes = new TextEncoder().encode(`${manifest.id}\u0000${Array.from(salt).join(",")}\u0000${identity}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const key = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `r-${key.slice(0, 40)}`;
}

export function createPageSalt(): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(32));
}

export async function extractEligibleReviews(
  document: Document,
  pageUrl: URL,
  options: ExtractionOptions = {},
): Promise<ExtractionResult> {
  if (!supportsAmazonReviewPage(pageUrl)) return { status: "UNSUPPORTED_PAGE", reviews: [] };

  const isRendered = options.isRendered ?? defaultIsRendered;
  const salt = options.salt ?? createPageSalt();
  const selector = manifest.cardSelectors.join(",");
  const cards = Array.from(document.querySelectorAll<HTMLElement>(selector));
  if (cards.length === 0) return { status: "NO_REVIEWS_FOUND", reviews: [] };

  const reviews: ReviewForAnalysis[] = [];
  const seenKeys = new Set<string>();
  let hadVisibleReviewBody = false;
  for (const card of cards) {
    if (!isRendered(card)) continue;
    const body = card.querySelector<HTMLElement>(manifest.bodySelectors.join(","));
    if (!body || !isRendered(body)) continue;
    hadVisibleReviewBody = true;
    const text = normalizeReviewText(body.innerText || body.textContent || "");
    if (text.length === 0 || text.length > manifest.maximumCharacters || wordCount(text) < manifest.minimumWords) continue;

    const identity = stableCardIdentity(card) ?? `text:${text.toLocaleLowerCase("und")}`;
    const reviewKey = await saltedKey(identity, salt);
    if (seenKeys.has(reviewKey)) continue;
    seenKeys.add(reviewKey);
    reviews.push({ reviewKey, text });
  }

  if (reviews.length > 0) return { status: "READY", reviews };
  return { status: hadVisibleReviewBody ? "INSUFFICIENT_TEXT" : "NO_REVIEWS_FOUND", reviews: [] };
}
