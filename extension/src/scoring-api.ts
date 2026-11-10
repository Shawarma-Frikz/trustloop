export interface PublicResult {
  reviewKey: string;
  status: "SCORED" | "SIGNALS_ONLY" | "UNKNOWN";
  trustScore?: number | null;
  verdict?: string | null;
  evidenceQuality?: "LOW" | "ADEQUATE" | null;
  reasonCode?: string | null;
  signals: PublicSignal[];
  modelVersion?: string | null;
  engine: "MODEL" | "SIGNALS_ONLY";
}

export interface PublicSignal {
  kind: string;
  summary: string;
  contribution?: number | null;
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
  if (typeof result.reviewKey !== "string"
    || !["SCORED", "SIGNALS_ONLY", "UNKNOWN"].includes(String(result.status))
    || !["MODEL", "SIGNALS_ONLY"].includes(String(result.engine))
    || !Array.isArray(result.signals) || result.signals.length > 5
    || !result.signals.every((signal) => signal !== null && typeof signal === "object"
      && typeof signal.kind === "string" && typeof signal.summary === "string")) return false;

  if (result.status === "SCORED") {
    return result.engine === "MODEL" && Number.isInteger(result.trustScore)
      && Number(result.trustScore) >= 0 && Number(result.trustScore) <= 100
      && ["STRONG_MANIPULATION_SIGNALS", "LIKELY_MANIPULATED", "INCONCLUSIVE", "MIXED_SIGNALS", "LIKELY_ORGANIC", "STRONG_ORGANIC_SIGNALS"].includes(String(result.verdict))
      && ["LOW", "ADEQUATE"].includes(String(result.evidenceQuality))
      && typeof result.modelVersion === "string" && (result.reasonCode === undefined || result.reasonCode === null);
  }
  if (result.status === "SIGNALS_ONLY") {
    return result.engine === "SIGNALS_ONLY" && isAbsent(result.trustScore)
      && isAbsent(result.verdict) && isAbsent(result.modelVersion)
      && ["LOW", "ADEQUATE"].includes(String(result.evidenceQuality))
      && isAbsent(result.reasonCode)
      && result.signals.every((signal) => isAbsent(signal.contribution));
  }
  return result.reasonCode !== undefined
    && ["INSUFFICIENT_TEXT", "UNSUPPORTED_LANGUAGE", "SCORING_TIMEOUT", "SCORING_UNAVAILABLE"].includes(String(result.reasonCode))
    && isAbsent(result.trustScore) && isAbsent(result.verdict);
}

function isAbsent(value: unknown): value is null | undefined {
  return value === undefined || value === null;
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
