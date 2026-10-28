# TrustLoop — paste-ready Figma prompt

Use this file in three passes. Paste **Pass 1** into Figma AI (or hand it to a designer) to create the file and foundations. Then paste **Pass 2** for components and patterns, and **Pass 3** for the prototype and QA. Values come from `tokens.json`; `tokens.css` is the code mirror. Do not sample colours from the PDF.

If the tool cannot import variables, create them manually from the tables in Pass 1. Do not let it choose a template, a font pairing, or a colour palette.

---

## Pass 1 — File and foundations

```text
You are building a production Figma file for TrustLoop, a browser extension that estimates whether a product review's text patterns resemble manipulation. This is not a concept exploration. Execute the specification exactly; do not redesign it, add a mood, or substitute a trendier palette.

Create a Figma file named "TrustLoop — Graphic Charter v1.0". Add a cover frame at 1600 × 900 with the paper background #F7F3EA, the word "TrustLoop" in IBM Plex Sans SemiBold 48, the subtitle "Graphic charter · v1.0 · October 2026" in IBM Plex Mono 16, and the open-loop mark in petrol #14524B. No hero image, no mockup collage, no gradient.

FILE PAGES, in this order:
00 Cover
01 Foundations
02 Components
03 Patterns
04 Documents
99 Archive

HARD REFUSALS — these are identity rules, not preferences:
- Do not use Inter, Roboto, Poppins, Montserrat, DM Sans, Arial, or the system UI as the primary typeface.
- Do not use violet, indigo, blue-purple, neon green, pure black, or pure white as a surface.
- Do not use gradients, glassmorphism, blur, glow, neon, 3D, claymorphism, or soft drop shadows.
- Do not use emoji, sparkles, robots, brains, shields, checkmarks in circles, stars, avatars, stock photography, or illustrations of people.
- Do not use gauges, dials, donuts, progress rings, or speedometers.
- Do not round corners beyond 3 px. Do not turn every control into a pill.
- Do not center a hero, float cards on a gradient, or use a dashboard template.
- Do not create a page-level score, an average score, a site ranking, or a "trust score" for a product.
- Do not invent realistic review text, names, or faces. Use the placeholder strings in this brief.

COLOUR VARIABLES — create a collection named "Color" with two modes, Light and Night. Use these exact hex values.

Light mode:
paper #F7F3EA
panel #FCFAF5
panel-2 #F3EFE5
ink #1A1D1B
ink-2 #3E4440
muted #686D66
faint #8B8F86
rule #DAD3C5
rule-strong #BDB4A4
control #858A81
petrol #14524B
petrol-deep #0E3B36
petrol-soft #E4ECE8
rust #A24A2C
rust-soft #F1E3DC
brass #8A6A32
warn #6B4E16
warn-soft #F3EBD9
stop-1 #7C3223
stop-2 #A05634
stop-3 #746C5E
stop-4 #6F6C3A
stop-5 #47664E
stop-6 #174F45

Night mode:
paper #121615
panel #1A1F1D
panel-2 #222824
ink #EDE7D9
ink-2 #CDD2C8
muted #A7ACA2
faint #7F857B
rule #333A36
rule-strong #48514B
control #7F857B
petrol #79B3A4
petrol-deep #8FC3B5
petrol-soft #223029
rust #D08A6B
rust-soft #33241E
brass #D2B273
warn #D2B273
warn-soft #2E2A1E
stop-1 #C97A5E
stop-2 #D79A78
stop-3 #B0A794
stop-4 #BDB97A
stop-5 #8FB39A
stop-6 #6FB3A2
night-shadow #0A0D0C

Semantic aliases, both modes: surface = paper, surface-panel = panel, surface-inset = panel-2, text = ink, text-secondary = ink-2, text-muted = muted, text-nonessential = faint (non-text only in the product), border = rule, border-control = control, action = petrol, manipulation = rust, organic = petrol, evidence-low = brass. Never use faint for a sentence.

TYPE — install or use these families:
Newsreader 400/500/600 for document display and band names.
IBM Plex Sans 400/500/600 for interface and body.
IBM Plex Mono 400/500/600 for scores, units, versions, labels, and indices.

Create text styles with these exact names and values (size / line height, px):
Doc/Cover — Newsreader 500, 58 / 57, tracking −2.5%
Doc/H1 — Newsreader 500, 31 / 35, tracking −1.5%
Doc/H2 — Newsreader 500, 15 / 18
Doc/H3 — IBM Plex Sans 600, 11.2 / 15
Doc/Body — IBM Plex Sans 400, 9.6 / 14.6
Doc/Lede — Newsreader 400, 13.2 / 18.7
Doc/Small — IBM Plex Sans 400, 8.2 / 11.9
Doc/Micro — IBM Plex Mono 400, 7.2 / 10, tracking 6%
Panel/Score — IBM Plex Mono 500, 28 / 28, tracking −4%
Panel/Score Row — IBM Plex Mono 500, 23 / 23, tracking −4%
Panel/Band — Newsreader 500, 15 / 18
Panel/Body — IBM Plex Sans 400, 13 / 18.9
Panel/Meta — IBM Plex Sans 400, 10 / 14
Panel/Micro — IBM Plex Mono 400, 9 / 12.6
Panel/Tiny — IBM Plex Mono 400, 7.5 / 10 (only the 0/50/100 scale)

SPACE AND SHAPE VARIABLES — collection "Space": 1=4, 2=8, 3=12, 4=16, 6=24, 8=32, 12=48. Collection "Shape": radius 2, panel-radius 3, border 1, shadow offset 3. The only shadow is 3 px 3 px 0 #F3EFE5 in light and 3 px 3 px 0 #0A0D0C in night. It is a print offset, not a blur. Never use a blurred shadow.

LAYOUT VARIABLES — collection "Layout": panel-width 360, panel-min 320, panel-max 420, panel-gutter 16, header-min 44, footer-min 40, target-min 44, chip-height 26, chip-height-small 22, track-height 7, track-gap 1, marker-width 2, marker-height 15, options-max 680.

MOTION — collection "Motion": state 90 ms, fade 120 ms, expand 180 ms, skeleton 1400 ms, easing cubic-bezier(.2, 0, 0, 1). Do not add bounce or spring.

On 01 Foundations, lay out the palette as rectangular swatches with name, hex, and one line of use. Show the six trust stops in order as a single 7 px rule, not as six round chips. Show the type specimens at real size, with the three families and their roles. Show the 4 px spacing scale as ticks, not as cards. Add a short note: "Warm paper, petrol ink, earthy stops. No gradients anywhere in the product."

Do not create a logo exploration. Use the supplied mark: an 8.5 radius open circle drawn from 18.51,6.54 to 18.51,17.46 in a 24 × 24 viewBox, stroke 2, plus a 2.5 × 2.5 square at 17.24,10.78. The gap is on the right and the square sits in it. The loop is deliberately incomplete. Never close the circle, never add a checkmark, never rotate it.
```

---

## Pass 2 — Components and patterns

```text
Continue the TrustLoop file. Build components with variants, auto layout, and variables. Use component properties, not detached copies. No component may use a raw hex value outside the variables.

1. MEASURE / FULL
Frame 328 wide, auto layout vertical, gap 8. Contents:
- Row: score "73" in Panel/Score, band "Likely organic" in Panel/Band, baseline aligned, gap 8.
- Track: 6 segments, height 7, gap 1, width 20/20/15/15/15/15 percent, fills stop-1 through stop-6, radius 0.
- Marker: 2 × 15 px, ink, positioned at left = score percent of the track, top −4.
- Scale: 0 / 50 / 100 in Panel/Tiny, 0 left, 50 center, 100 right.
- Qualifier: 9 px mono, muted, preceded by a 11 px circled "i" in brass. Text: "Adequate evidence · Band 5 of 6".
Variants: State = Scored, Low, Signals only, Unknown.
Scored: score + band + six solid stops + marker + qualifier.
Low: same, qualifier reads "Indicative — limited text · Band 4 of 6" in brass.
Signals only: no score, no marker; six stops at 35% opacity; an em dash where the score would be; text "Descriptive signals only — no score" in Panel/Meta.
Unknown: no score, no marker; a dashed 1 px rule across the track width; text "No estimate" in Panel/Band and the reason below in Panel/Meta.
Never encode unknown as 0. Never show a number without a band.

2. MEASURE / ROW
Width auto, score 23 px, band 12.5 px, evidence 10 px, no scale. Same states. Used inside collapsed rows. Score right-aligned in a fixed 40 px column.

3. MEASURE / CHIP
A six-tick ladder, not a bar. Height 26, background panel, 1 px control border, 3 px left border in the band colour, radius 2. Contents: optional 11 px "i" icon, score in IBM Plex Mono 500 at 12 px, and a 6-tick group at 2.5 px wide with 1 px gaps; ticks below the score are at 30% opacity, the active tick is full band colour. Variants for bands 1–6, low, unknown, signals only, unavailable, and error. Low adds the brass "i" and the accessible name carries "Indicative — limited text". Unknown shows "—" and "No estimate" is never abbreviated in the accessible name. The visible chip may be 26 high; the hit area is 44 × 44 and must stay invisible.

4. REVIEW ROW
Width 360. Padding 10 16. Border bottom 1 px #E9E2D6. Grid columns 22 / 40 / 1fr / 12, gap 8, align center. Index in 9 px mono, faint. Score or state in 23 px mono, right aligned. Band in 12.5 px semibold; evidence line 10 px muted. Chevron 10 px, decorative. Top signal on a second line, 10.5 px muted, aligned under the score/band columns, max one line. Collapsed height 58–64; expanded adds a dashed 1 px top rule and 10 px top padding. One row expands at a time. Variants: Collapsed / Expanded, and Scored / Low / Unknown / Signals only.

5. PANEL
360 × 640, panel background, 1 px rule border, 3 px radius, 3 px hard offset shadow. Header 44 high, padding 0 16: mark 19 px + "TrustLoop" 12.5 semibold; right side language "EN / FR" in 9.5 mono and a 20 px settings control. Page bar: host in 8.5 mono uppercase muted, count "3 reviews found" in 11.5 ink-2, "Rescan" in 11 petrol with a 1 px underline. List is the only scrolling region, padding 2 0. Footer min 40, padding 8 16 9, top rule, 9 px muted disclaimer plus "tl-text-1.1.0 · contract v1" in 8 px mono.
Build a realistic default frame with exactly these rows:
01 · 81 · Likely organic · "Adequate evidence · Band 5 of 6" · top signal "Includes a concrete usage detail"
02 · 34 · Likely manipulated · "Adequate evidence · Band 2 of 6" · expanded · top signal "Reads like promotional copy"
03 · 64 · Mixed signals · "Indicative — limited text · Band 4 of 6" · top signal "Includes a concrete usage detail"
Page bar: "Example-shop.com" and "3 reviews found". Footer exactly: "Estimated from text patterns. Does not verify purchase, identity, or truth." / "tl-text-1.1.0 · contract v1".
Expanded row adds: Measure/Full at 34, the qualifier, a scale legend "← manipulative / organic →" in 7.5 mono, and three signal rows:
"Reads like promotional copy" ← 31%
"Repeats the same phrasing" ← 18%
"Includes a concrete usage detail" → 12%
Each signal row: 3 px axis, center tick, bar from center; manipulation bars rust, organic bars petrol; label 11.5, direction 8 mono, percentage 9 mono; a note "Contributions are normalized over all features; the top five do not add to 100%." in 7.5 mono muted. Do not make the three percentages sum to 100. Do not label contribution as confidence, probability, or accuracy.
Panel variants: Default, Low, Unknown, Signals only, Empty, Loading, Error, Stale. Width variants 360 / 320 / 420. Theme via variable mode, not duplicate components.

6. BUTTONS AND CONTROLS
Primary: petrol fill, paper text, 36 min height, 6 px vertical padding, 12 px horizontal, 2 px radius, 13 px semibold. Secondary: panel fill, 1 px control border, ink text. Quiet: text only, petrol, 1 px underline. Disabled: 40% opacity, no colour shift. Focus: 2 px petrol ring, 2 px offset. No pill radius. No icon-only button without an accessible name.
Switch: 34 × 20 track, 2 px radius, petrol when on, control border when off, 14 px square thumb, 90 ms. Label and helper text to the left, not inside the switch. Language control: "EN / FR" with the active language underlined in ink, the inactive in muted; 44 px target. Segmented control: 1 px control border, 2 px radius, active segment panel-2 with ink text; no sliding animation.

7. SIGNAL ROW
Full width. Header line: label 11.5 medium flex, direction 8 mono uppercase (← MANIP / → ORGANIC), optional contribution 9 mono right. Axis 3 px panel-2 with a 1 px center tick. Bar 3 px from the center; rust for manipulation, petrol for organic. Rows separated by 1 px #EEE8DC. No icons, no emoji, no sparklines.

8. EVIDENCE POPOVER
320 wide, panel, 1 px rule, 3 px radius, 8 px hard shadow. Title 13 semibold, body 11.5/1.5, close button 44 target, 1 px rule. Content explains evidence quality and the limits; it never quotes the review. Arrow 6 px, no blur.

9. HISTORY AND OPTIONS
Options page max 680 wide, paper background, 16 px gutter, sections separated by 1 px rules. History off by default. Row: host in 11 mono, time in 10 mono muted, result in 12 mono right. Empty state: "No scans yet." + "Open a supported product page to start." No illustration. Switch off. Helper: "Off by default. Stores host, time, and result — never review text." Clear history button secondary. Never show review text, review keys, reviewer names, URL paths, review counts, or a text fingerprint.

10. STATES
Empty: "No reviews found to analyze." + "How this works".
Unsupported: "This page is not supported yet." + "See supported pages".
Unknown: "No estimate" + the exact reason ("Not enough text to estimate.", "This language is not supported yet.", etc.).
Error: "Analysis is unavailable right now. Try again." + Retry.
Stale: rows remain; inline notice "Couldn't refresh. Showing the last result." + Retry.
Loading: three skeleton rows, 1.4 s pulse, reduced-motion static, polite live region "Reading reviews…". No spinner.
```

---

## Pass 3 — Prototype, documents, and QA

```text
Finish the TrustLoop file.

PROTOTYPE
- Chip click opens the panel with the matching row focused.
- Row click expands one row; a second click collapses it; opening another closes the first.
- Esc closes the evidence popover and returns focus to its button; a second Esc collapses the row.
- Language control switches every visible string between the copy-deck English and French. Do not auto-shrink text; let the French reflow.
- Rescan keeps rows visible, changes the page bar to "Rescanning…", then returns to "3 reviews found". On failure, keep rows and show "Couldn't refresh. Showing the last result." with Retry.
- History toggle shows the off state first. Do not animate the switch with a bounce.
- Prototype at 360 wide and at 320 wide. Confirm no horizontal scroll and no clipped French.

DOCUMENTS PAGE
- A4 report cover at 210 × 297 mm: paper, 14 mm petrol spine, mark and "TrustLoop" top, title "A second reading." in Newsreader 44, subtitle in 14, meta in 7 mono. No image.
- 16:9 slide master at 1280 × 720: margins 64, title 44/48, body 24/34, source 16/22. One claim per slide. No logo on every slide; mark only on title and closing.
- A6 landscape evidence card 105 × 74 mm: "How to read a result", score 51, band "Inconclusive", "Adequate evidence · Band 3 of 6", three short lines (score, band, signals), disclaimer. No logo beyond the small wordmark.
- A chart template: horizontal band distribution with direct labels, counts, a source line (dataset, n, date). No gauge, no donut, no page average.

QA BEFORE YOU FINISH
1. No raw hex, spacing, or duration outside variables.
2. Panel 360, min 320, max 420. Header 44, footer min 40. Rows 58–64 collapsed, 220–280 expanded.
3. Contrast in both modes: body 4.5:1, large text 3:1, non-text 3:1. Check muted on panel, petrol on panel, rust on panel, brass on panel, paper on each band, ink on band 2. Band 2 ink is 3.14:1 and is large-text only; do not set 10 px body on it.
4. No page score, no average, no ranking, no "trust score" for a product.
5. Unknown is never a number, never 0, never a blank. LOW always carries "Indicative — limited text".
6. Every chip's accessible name includes the score or state, band, and evidence. The 44 × 44 hit area is invisible.
7. French at 320: the disclaimer, LOW qualifier, and refresh notice do not clip or truncate.
8. 200% zoom, 400% reflow, reduced motion, forced colors: the six stops, marker, and tick ladder remain distinguishable without colour.
9. No gradients, blur, glass, emoji, stock people, gauges, or pill stacks.
10. Components are nested and named TL/*; no detached instances; 99 Archive holds only dated, labelled rejections.

At the end, export a PDF of 01 Foundations and 02 Components at 1× and name it "TrustLoop-Figma-Foundations-v1.0.pdf". Do not export the archive.
```

---

## Short prompt for a designer (if Figma AI is not used)

```text
Design the TrustLoop extension and charter in Figma, following the attached graphic charter PDF and tokens.json exactly. The look is warm paper (#F7F3EA), near-black ink (#1A1D1B), deep petrol (#14524B), rust (#A24A2C), and six earthy trust stops. Type is Newsreader for claims, IBM Plex Sans for interface, IBM Plex Mono for measurement. The signature component is a six-stop banded rule, not a gauge. Build the 360 px panel with three review rows, one expanded, an A4 report cover, a 16:9 slide master, and an A6 evidence card. No Inter, no violet, no gradients, no glass, no emoji, no gauges, no page score, no stock people. Unknown is a first-class state with no number. LOW always reads "Indicative — limited text". All strings are in the copy inventory; do not paraphrase them.
```
