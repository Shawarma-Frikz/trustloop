import { analyzeReviewBatch, type ReviewInput } from "./scoring-api.js";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "PING") {
    sendResponse({ ok: true });
    return;
  }

  if (message?.type === "ANALYZE_BATCH") {
    const reviews = message.reviews as ReviewInput[] | undefined;
    const languageHint = message.languageHint === "fr" ? "fr" : "en";
    if (!Array.isArray(reviews) || reviews.length < 1 || reviews.length > 10
      || reviews.some((review) => !review || typeof review.reviewKey !== "string"
        || !/^[A-Za-z0-9_-]{1,64}$/.test(review.reviewKey)
        || typeof review.text !== "string" || review.text.length < 1 || review.text.length > 2000)) {
      sendResponse({ ok: false, reasonCode: "INVALID_REQUEST" });
      return;
    }
    void analyzeReviewBatch(reviews, languageHint)
      .then((results) => sendResponse({ ok: true, results }))
      .catch(() => sendResponse({ ok: false, reasonCode: "SCORING_UNAVAILABLE" }));
    return true;
  }
});
