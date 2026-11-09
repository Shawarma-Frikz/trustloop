export interface PublicResult {
  reviewKey: string;
  status: "SCORED" | "SIGNALS_ONLY" | "UNKNOWN";
  trustScore?: number;
  verdict?: string;
  reasonCode?: string;
  signals: unknown[];
}

export interface ReviewInput {
  reviewKey: string;
  text: string;
}

export class AnalyzeRequestError extends Error {
  constructor(message: string, readonly retryable: boolean) {
    super(message);
    this.name = "AnalyzeRequestError";
  }
}

export function canManuallyRetry(result: PublicResult): boolean {
  return result.status === "UNKNOWN"
    && ["SCORING_TIMEOUT", "SCORING_UNAVAILABLE"].includes(result.reasonCode ?? "");
}

function isPublicResult(value: unknown): value is PublicResult {
  if (value === null || typeof value !== "object") return false;
  const result = value as Record<string, unknown>;
  return typeof result.reviewKey === "string"
    && ["SCORED", "SIGNALS_ONLY", "UNKNOWN"].includes(String(result.status))
    && Array.isArray(result.signals);
}

export async function analyzeOneReview(
  text: string,
  fetcher: typeof fetch = fetch,
): Promise<PublicResult> {
  const response = await analyzeReviewBatch([{ reviewKey: "manual-1", text }], "en", fetcher);
  return response[0];
}

export async function analyzeReviewBatch(
  reviews: ReviewInput[],
  languageHint: "en" | "fr",
  fetcher: typeof fetch = fetch,
): Promise<PublicResult[]> {
  let response: Response;
  try {
    response = await fetcher("http://127.0.0.1:8080/api/v1/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Request-Id": `ext-${crypto.randomUUID()}`,
      },
      body: JSON.stringify({
        adapterId: "amazon.reviews.v1",
        languageHint,
        reviews,
      }),
    });
  } catch {
    throw new AnalyzeRequestError("Cannot reach the local TrustLoop API.", true);
  }

  if (!response.ok) {
    throw new AnalyzeRequestError(
      response.status === 429 ? "Too many requests. Wait a moment, then retry." : "The API rejected this request.",
      response.status === 429 || response.status >= 500,
    );
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new AnalyzeRequestError("The API returned an unreadable response.", true);
  }
  const results = (body as { results?: unknown } | null)?.results;
  if (!Array.isArray(results) || results.length !== reviews.length || !results.every(isPublicResult)
    || results.some((result, index) => result.reviewKey !== reviews[index].reviewKey)) {
    throw new AnalyzeRequestError("The API response did not match the expected contract.", true);
  }
  return results;
}
