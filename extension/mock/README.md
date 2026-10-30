# Panel mock (design-system proof)

Step 0.3 proof of done: a static panel mock **rendered from the token file and the
bilingual string file**, with a non-colour verdict cue and no gradient anywhere.

## Run it

The mock loads `src/i18n/*.json` with `fetch`, so it needs HTTP — opening the HTML
file directly (`file://`) is blocked by the browser. From the `extension/` folder:

```powershell
..\.venv\Scripts\python.exe -m http.server 8123
```

Then open <http://localhost:8123/mock/panel-mock.html>.

Toggle **EN / FR** in the top bar: the whole panel re-renders from the other string
file. Nothing visible is hardcoded in English.

## What it proves

- Every colour, size, and space resolves through `src/styles/tokens.css` (a verbatim
  copy of `docs/design/tokens.css`, guarded by a test).
- Every visible string resolves through `src/i18n/<lang>.json`.
- Six solid trust stops, widths 20/20/15/15/15/15 (charter 6.3).
- The chip ladder (six ticks, current band taller and in ink) is the non-colour
  verdict cue (charter 6.5).
- The three measure states from charter 6.4: scored, signals only, unknown.
  Unknown shows no number, no marker, and an outlined track — never zero.
- Pluralisation and word order stay inside each language's template
  ("{count} reviews found" / "{count} avis trouvés", "Band {n} of 6" /
  "Bande {n} sur 6"); nothing is concatenated across languages.

## String provenance (charter Appendix A)

- `band.*` — normative (copy deck, `docs/product-decisions.md`).
- `ui.estimateDisclaimer` … `ui.clearHistoryAction` — normative (14 interface strings).
- `signal.REPEATED_PHRASING` … `signal.LEXICAL_VARIETY` — English normative, French proposed.
- `signal.adequateEvidence`, `page.bandPosition`, `page.rescanAction`, `chip.*`,
  `page.readingReviews`, `page.rescanning`, `page.reviewsFound`, `page.reviewCount`,
  `history.*`, `action.*`, `control.settings`, `notice.refreshFailure` — proposed.
- `transport.*` — proposed (messages; actions reuse `ui.retryAction` / `ui.reloadAction`).

Proposed strings ship in the mock as a proposal; they become normative only when the
copy deck changes in both languages (charter Appendix A.7).

Also present in the mock but not yet in Appendix A: `signal.contributionsNote`
(from charter figure 7.6) and the signal-axis end labels ("manipulative" /
"organic"). Both need deck approval before the shipping panel uses them.

## Not covered here

- Self-hosted fonts (Newsreader, IBM Plex Sans/Mono): fallbacks (Georgia, Segoe UI,
  Consolas) render until WOFF2 files are bundled in a later step. No third-party font
  CDN is used at runtime, per the charter licence rule.
- Night ledger: toggle `data-tl-theme="night"` on any root to preview; the mock
  defaults to the day ledger.
- This is a design proof, not the shipping panel. Phase 1 moves these styles into the
  extension shadow DOM and wires the real contract responses.
