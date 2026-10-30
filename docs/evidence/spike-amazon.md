# Amazon feasibility spike · 0.5

**Result: NO-GO for live Amazon extraction; fixture fallback selected.**
**Run date:** 2026-10-30. **Context:** unsigned Amazon.com session, storefront set
to deliver to Tunisia. This records the tested session, not a claim that Amazon
always blocks review text for every visitor or region.

## Live-page count sheet

Eligibility for this spike means a visible review card with extractable review text;
ratings summaries and aggregate customer-sentiment summaries do not count.
The candidate selector inspected was `[data-hook="review"]`. It is not yet an
implemented extension selector.

| Variant | Sample product | Visible review cards | Candidate selector matches | Result |
|---|---|---:|---:|---|
| Electronics / product page | Echo Dot pack, ASIN `B0HKL4CT1J` ([page](https://www.amazon.com/dp/B0HKL4CT1J)) | 0 | 0 | Customer reviews section prompts sign-in to see reviews |
| Home / cookware product page | Lodge 10.25-inch skillet, ASIN `B00006JSUA` ([page](https://www.amazon.com/dp/B00006JSUA)) | 0 | 0 | Customer reviews section prompts sign-in to see reviews |
| Books / paperback product page | *The Housemaid*, ASIN `1538742578` ([page](https://www.amazon.com/dp/1538742578)) | 0 | 0 | Customer reviews section prompts sign-in to see reviews |

**Eligible reviews:** 0 of the required minimum 15 total; no page reached five.
The ratings and review-count summaries were visible, but they were not review text
and were excluded from the count.

## Precision, stability, and hidden cards

- **Extraction precision:** not measurable on these pages. There were no extracted
  or visible eligible review cards, so a precision denominator does not exist; the
  ≥90% target is unmet, not passed.
- **Two-load result (electronics variant):** `[data-hook="review"]` matched 0 cards
  on each of two consecutive loads; the page showed the same sign-in prompt. The
  zero count is repeatable but gives no evidence that a positive selector is stable.
- **Hidden/collapsed cards:** not present in the anonymous page view; handling could
  not be validated against live Amazon markup.
- **Screenshots / saved live HTML:** none committed. The sampled pages exposed no
  review bodies to annotate or save. No sign-in, CAPTCHA, or access barrier was
  bypassed.

## Recorded fallback

Use local, hand-authored **synthetic** page fixtures for the demo while retaining a
page-adapter boundary. These fixtures are not captures of Amazon pages and do not
validate a live Amazon selector. They contain invented review text only, with a
visible-card count of five per variant and a collapsed-card case. The extension
does not yet extract reviews; Phase 1 must implement the fixture adapter before a
demo can scan these pages.

| Fallback fixture | Visible cards | Hidden/collapsed cards |
|---|---:|---:|
| `extension/mock/fixtures/amazon/standard.html` | 5 | 0 |
| `extension/mock/fixtures/amazon/collapsed.html` | 5 | 1 |
| `extension/mock/fixtures/amazon/compact.html` | 5 | 0 |

The fixture checks in `extension/tests/spike-fixtures.test.ts` verify the invented
card counts and 20-word eligibility floor; all four checks passed with Vitest 2.1.9
on 2026-10-30. They do **not** count as live Amazon precision or selector evidence.
Re-run the live spike only when review text is available through an authorized,
non-blocked page view, or seek professor approval for an alternate site.
