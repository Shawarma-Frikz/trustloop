# TrustLoop design source of truth

**Status:** v1.0 · October 2026. The graphic charter PDF is the presentation copy; the HTML fragments, `tokens.css`, and `tokens.json` are the editable source. Figma is the working file, not the baseline.

This directory holds the visual system for the TrustLoop extension, options page, report, defense slides, and handouts. It implements decision D20 and stops where product decisions stop: band boundaries, band names, score meaning, and interface copy belong to [product decisions](../product-decisions.md), not to this charter.

## Files

| File | Role |
|---|---|
| `TrustLoop-Graphic-Charter-v1.0.pdf` | The versioned deliverable. Read this first. |
| `src/00-front.html` | Head, CSS, cover, document control, contents. Opens the document. |
| `src/01-brand.html` | Sections 01–02: the idea, positioning, mark, principles, refusals. |
| `src/02-colour.html` | Section 03: palette, trust stops, contrast, night ledger. |
| `src/03-type-space.html` | Sections 04–05: type families, scales, layout, panel geometry, host placement. |
| `src/04-measure-components.html` | Sections 06–07: the measure, sizes, components, panel, history, options. |
| `src/05-states-integration.html` | Section 08: state matrix, loading, failure, chips on the host page. |
| `src/06-language-a11y.html` | Sections 09–11: voice, bilingual copy, accessibility, motion. |
| `src/07-tokens-figma.html` | Sections 12–14: tokens, Figma build, handoff. |
| `src/08-defense-closing.html` | Section 15, Appendix A, closing. Closes the document. |
| `tokens.css` | CSS custom properties for the extension and options page. |
| `tokens.json` | DTCG-like token export for Figma variables and tooling. |
| `figma-prompt.md` | Three paste-ready prompts for Figma AI or a designer. |
| `assets/mark.svg` | The open-loop mark, one colour via `currentColor`. |
| `assets/wordmark.svg` | Horizontal lockup, mark plus live text. |

The fragments are concatenated in numeric order into `graphic-charter.html`. `00-front.html` opens `<body>`; `08-defense-closing.html` closes it. Do not open a fragment in a browser on its own and judge the layout; it has no `<head>`.

## Authority

When two documents disagree, the order is:

1. [Product decisions](../product-decisions.md) — bands, score meaning, copy deck, privacy, history.
2. [Model plan](../model-plan.md) — signals, evidence gate, contributions, language coverage.
3. This charter — visual and interaction rules.
4. The Figma working file.

A mockup never overrides a normative string. If the copy deck and a screen disagree, the screen is wrong. The copy inventory in Appendix A marks every string this charter adds as **proposed**; proposed does not mean approved.

## What is fixed here

- Warm paper, ink, petrol, rust, brass; six solid trust stops. No gradients in the product.
- Newsreader for display and band names, IBM Plex Sans for interface, IBM Plex Mono for measurement. No Inter or system UI as the primary face.
- A 4 px space base. Panel 360 px, minimum 320, maximum 420. Gutter 16 px. Header 44 px.
- The banded rule is the signature component. No gauge, donut, dial, or ring.
- Unknown has no number. LOW keeps its score and carries “Indicative — limited text”. Signals only says “Descriptive signals only — no score”.
- No page score, no product average, no reviewer ranking, no identity or truth claim.
- History is off by default, local only, and metadata only: host, time, adapter, status, result, evidence, engine, model version, reason code. Never review text, review keys, reviewer names, URL paths, review counts, or a text fingerprint.
- English and French share the same claim. The French UI is translated; model coverage is gated per language (D13, D23) and the interface never implies coverage.

## Regenerating the PDF

The PDF is rendered from the concatenated HTML with headless Chrome. Fonts load from Google Fonts; the product itself self-hosts the same families, but the document may use the CDN.

```bash
cat src/00-front.html src/01-brand.html src/02-colour.html src/03-type-space.html \
    src/04-measure-components.html src/05-states-integration.html \
    src/06-language-a11y.html src/07-tokens-figma.html src/08-defense-closing.html \
    > graphic-charter.html
```

Then print to A4 with backgrounds enabled. Use an absolute output path; a relative path can fail on Windows with an access error.

```bash
chrome --headless --disable-gpu --no-pdf-header-footer --print-to-pdf="C:\absolute\path\TrustLoop-Graphic-Charter-v1.0.pdf" "C:\absolute\path\graphic-charter.html"
```

The contents table holds literal page numbers. Render once, read the chapter starts from the PDF, update the numbers in `00-front.html`, then render again. Only the second render is the deliverable. After it, stamp the folios and set bookmarks and metadata with PyMuPDF; the PDF is not finished until the contents, folios, and bookmarks agree.

The document is designed for A4 with 15 mm side margins and 16 mm bottom margin; the cover is full bleed. If a printer requires a different stock or margin, adjust `@page` in `00-front.html`, not the individual sections.

## Assets

`mark.svg` is the only approved mark: an open circle with a square in the gap, drawn in a 24 × 24 viewBox, stroke 2. The gap is intentional. Do not close the circle, add a checkmark, rotate it, or place it inside a shield.

`wordmark.svg` uses live text in IBM Plex Sans SemiBold. Outline the text before sending it to a print shop or embedding it where the font is unavailable. The mark uses `currentColor`; the wordmark uses petrol for the mark and ink for the word, with a dark-mode media query. For one-colour reproduction, set both to the same ink.

No photography, illustration, mascot, avatar, or emoji belongs in this system. The product is a measurement instrument, not a character.

## Copy boundary

The normative copy deck is in [product decisions](../product-decisions.md#copy-deck). This charter adds interface strings the deck does not yet contain — “Adequate evidence”, “Band N of 6”, “Rescan”, compact chip labels, empty/history strings, and transport-failure sentences. They are listed in Appendix A as proposed and must be approved in both languages before implementation.

Do not concatenate strings in code. “Band” + number + “of 6” breaks French word order and pluralisation. Build each sentence whole, from the deck.

## Revision and handoff

A change is a charter revision when it alters colour, type, spacing, a component's anatomy, a state, or a token. To revise:

1. Change the HTML fragment and, if values changed, `tokens.css` and `tokens.json`.
2. Re-render the PDF, update the contents, bookmarks, version, and export date.
3. Record the change in the D20 row of the decision register.
4. Update the Figma cover frame to the same version and date.
5. Check that no normative string or band boundary moved.

Minor revisions use v1.1; a new visual direction uses v2.0. The PDF file name carries the version. Never ship a Figma link as the only record: export the PDF and keep this directory current.

## Definition of done for a design change

- All states in Section 08 exist: default, hover, focus, expanded, LOW, unknown, signals only, loading, empty, error, stale.
- Contrast passes WCAG 2.2 AA in light and night; no meaning is carried by colour alone.
- 320 px French, 200% zoom, 400% reflow, reduced motion, and forced colours pass Section 10.
- Every string matches Appendix A; no truncation, no placeholder English in a French frame.
- No page aggregate, no identity claim, no score for unknown, no gauge.
- Tokens, PDF, Figma, and copy inventory share one version and one export date.

## Licence

Newsreader, IBM Plex Sans, and IBM Plex Mono are licensed under the SIL Open Font License. Keep the licence files beside the self-hosted WOFF2 files in the extension and list them in `NOTICE`. Do not request fonts from a third-party server at runtime: it would leak the page session and break offline use.
