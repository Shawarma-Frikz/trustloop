export interface PublicResult {
  reviewKey: string;
  status: "SCORED" | "SIGNALS_ONLY" | "UNKNOWN";
  trustScore?: number;
  verdict?: string;
  reasonCode?: string;
  signals: unknown[];
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
        languageHint: "en",
        reviews: [{ reviewKey: "manual-1", text }],
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
  if (!Array.isArray(results) || results.length !== 1 || !isPublicResult(results[0])) {
    throw new AnalyzeRequestError("The API response did not match the expected contract.", true);
  }
  return results[0];
}
