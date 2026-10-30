# TrustLoop annotation codebook · v1.0

**Status:** proposed for sign-off, 2026-10-30. Applies to the held-out manual
evaluation sample (see [sample-plan.md](sample-plan.md)). Derives from the label
definition in [model plan](../model-plan.md) §3; a change to this codebook is a
model-plan change and requires a decision-register entry (D02, D04, D12).

## 0. What the label means

The label describes **text patterns only**. It is not a claim that a review is true
or false, that a reviewer acted with intent, or that a purchase did or did not
happen. *Organic* means "reads as a spontaneous review"; *manipulated* means "exhibits
a defined manipulation pattern with enough context to support the label".

Forbidden words in annotations and downstream copy: fake, bot, spam account,
verified, proven, confidence, accuracy.

## 1. Labels

| Label | Definition | Sufficient condition |
|---|---|---|
| `organic` | The text shows no manipulation pattern under §2 and reads as a spontaneous review. | No §2 pattern fires, and the text contains at least one authenticating element (§3). |
| `manipulated` | The text exhibits at least one defined manipulation pattern **with enough context to support the label**. | At least one §2 pattern fires and the annotator can point to the concrete textual evidence. |
| `uncertain` | The text is too short, too ambiguous, or mixes signals such that neither label is defensible. | Any exclusion in §4 applies, or the annotator cannot point to concrete evidence for either label. |

`uncertain` is a first-class label. It is excluded from training and from the
primary gate metrics, never coerced into `organic` or `manipulated`.

## 2. Manipulation patterns (checklist)

A pattern fires only when the annotator can point to the concrete words that
trigger it. "Feels off" is not a pattern.

| # | Pattern | Observable evidence | Typical limits |
|---|---|---|---|
| M1 | Templated or duplicated wording | Sentence frames, slogan-like openings, or near-identical clauses that could be swapped between reviews. | Repetition also occurs in authentic reviews; require boilerplate structure, not just a repeated phrase. |
| M2 | Generic promotional phrasing | Marketing lexicon ("must-have", "game changer", "you won't regret"), call-to-action, or brochure rhythm with no customer stake. | Domain-dependent; enthusiasm alone does not fire M2. |
| M3 | Repeated superlatives / absolute claims | Stacked superlatives or unverifiable absolutes ("perfect in every way", "best product ever made"). | Stylistic signal; genuine fans write this way too. Needs company of another signal or extreme density. |
| M4 | Coordinated boilerplate | Product-spec recitation without personal use (feature list copied from packaging or listing). | Specification can be useful; fire only when it dominates and no use context appears. |
| M5 | Marketing voice, no customer account | No first-person experience, no usage context; reads as advertising copy for the reader rather than an account for other customers. | The strongest single pattern; still cite the concrete absence/presence, not an impression of intent. |

## 3. Authenticating elements (organic side)

Not required individually, but at least one should be present for `organic`:

- A concrete usage detail: where, when, how long, with what, compared to what.
- A balanced account: likes one aspect, dislikes another, with specifics.
- Idiosyncratic, uneven, or personal wording that resists templating.
- A plausible story of use whose details would be costly to invent consistently.

## 4. Explicit exclusions

The following are **never sufficient** for `manipulated` on their own:

- Negative opinion, poor grammar, typos, or ALL-CAPS.
- Short length by itself (handled by the evidence gate, not the label).
- Incentivized but honestly disclosed reviews, unless the text itself is deceptive
  under §2.
- Disagreement with other reviewers, sarcasm, humour, or unusual style.
- Star rating, reviewer name, avatar, verified-purchase badge, or any metadata —
  **annotations use review text only**.

Mark `uncertain` when: the text is under ~20 words; translation artefacts dominate;
the review is a question, complaint about delivery, or non-evaluation; or M-pattern
evidence and authenticating elements balance with nothing to break the tie.

## 5. Annotation procedure

1. Read the whole review once before labelling.
2. Run the §2 checklist. For each fired pattern, note the exact words (these notes
   stay in the annotation sheet, never in the repository).
3. Check §3 for authenticating elements.
4. Assign `organic`, `manipulated`, or `uncertain` with a one-sentence rationale
   citing the evidence, or write `uncertain` with the blocking reason.
5. Rate labelling difficulty: `easy` / `hard`. `hard` items are the adjudication
   candidates.

## 6. Quality protocol

- **Two annotators** label every item independently, blind to each other's labels
  and to any model output.
- **Cohen's kappa** is computed on the three-label set. The sample is usable only
  if kappa ≥ 0.60. Below 0.60: rewrite the codebook section that drove
  disagreement, re-annotate a fresh calibration batch, and reassess before
  proceeding.
- **Adjudication:** a third pass resolves every disagreement. The adjudicated label
  is the evaluation label; the pre-adjudication labels are kept to report kappa and
  per-pattern confusion.
- **Order effects:** annotators work in a different random order per annotator;
  items are not grouped by site or product.
- **Blindness:** annotators never see star ratings, reviewer identifiers, or which
  site a review came from during labelling.

## 7. Mapping public dataset labels (training data only)

Public corpus labels are mapped explicitly and the mapping is reported; labels are
never merged silently ([model plan](../model-plan.md) §3):

| Corpus label | Maps to | Caveat carried into the model card |
|---|---|---|
| Ott et al. truthful | `organic` proxy | Crowdsourced "truthful", hotel domain, not verified purchases. |
| Ott et al. deceptive | `manipulated` proxy | Crowdsourced deception written for pay; pattern strength may exceed commercial manipulation. |
| Yelp filtered | not used as a label | Platform filter signal, not ground truth; evaluation-only, never training. |
| GraphConsis Amazon fake | `manipulated` proxy only if review-level | Reviewer-level labels must not become review labels (D22 caveat). |

## 8. Worked examples (invented text)

> **Example A · manipulated (M2+M5).** "This wireless charger is an absolute
> game-changer and a must-have for everyone! You won't regret buying it. Perfect
> gift, perfect quality, perfect price. Buy now!" — Promotional lexicon density,
> call-to-action, no usage context. No authenticating element. Label:
> `manipulated`; patterns M2, M5.

> **Example B · organic.** "Bought this for my daughter's dorm in September. The
> cable frayed at the connector by November, and support sent a replacement without
> much fuss — the new one has held up since. Charging speed is fine, nothing
> special." — Concrete usage detail, balanced account, idiosyncratic wording.
> Label: `organic`.

> **Example C · uncertain.** "Great product, highly recommend!" — Eleven words, one
> generic positive claim, no usable evidence either way. Label: `uncertain`,
> reason: insufficient text for a defensible pattern call.

> **Example D · organic despite imperfections.** "its ok i guess?? battery dies
> faster then advertised but for the price whatevs. would maybe buy again" — Poor
> grammar and a middling tone are exclusions (§4), not manipulation patterns. One
> concrete detail (battery life vs advertisement). Label: `organic`.

> **Example E · manipulated (M4).** "Features: 10,000 mAh capacity, dual USB-C
> output, LED display, aluminium shell, 18-month warranty. Specifications meet all
> advertised requirements. Excellent product." — Specification recitation
> dominating the text with no use context; brochure structure. Label:
> `manipulated`; pattern M4.

## 9. Sign-off

The codebook is signed off when both annotators have labelled the calibration batch
(≥ 30 items, invented or public-corpus texts, never live reviews), kappa on that
batch is ≥ 0.60, and each remaining disagreement has a written resolution rule that
is added to this document as a numbered addendum.
