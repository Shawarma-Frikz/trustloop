/*
  TrustLoop panel mock · renderer.
  Every visible string comes from src/i18n/<lang>.json; every colour, size,
  and space comes from tokens.css via mock.css. No string is concatenated
  across languages: plural and band-position sentences are whole templates.
*/

const root = document.getElementById("mock-root");

const STRINGS_URL = {
  en: "../src/i18n/en.json",
  fr: "../src/i18n/fr.json",
};

/* Invention for the mock only — no real review data. */
const REVIEWS = [
  {
    index: "01",
    status: "SCORED",
    score: 81,
    band: "LIKELY_ORGANIC",
    bandNumber: 5,
    evidence: "ADEQUATE",
    topSignal: "CONCRETE_DETAIL",
    expanded: false,
  },
  {
    index: "02",
    status: "SCORED",
    score: 34,
    band: "LIKELY_MANIPULATED",
    bandNumber: 2,
    evidence: "ADEQUATE",
    topSignal: "PROMOTIONAL_TONE",
    expanded: true,
    signals: [
      { kind: "PROMOTIONAL_TONE", direction: "manipulative", contribution: 0.31 },
      { kind: "REPEATED_PHRASING", direction: "manipulative", contribution: 0.18 },
      { kind: "CONCRETE_DETAIL", direction: "organic", contribution: 0.12 },
    ],
  },
  {
    index: "03",
    status: "SCORED",
    score: 64,
    band: "MIXED_SIGNALS",
    bandNumber: 4,
    evidence: "LOW",
    topSignal: "CONCRETE_DETAIL",
    expanded: false,
  },
];

const BAND_WIDTHS = [20, 20, 15, 15, 15, 15];

let lang = "en";
let S = null;

function t(path, vars) {
  let node = S;
  for (const part of path.split(".")) {
    node = node?.[part];
  }
  if (node == null) return path;
  if (typeof node === "object") {
    const n = vars?.count ?? 0;
    const form = n === 1 ? node.one : node.other;
    if (form == null) return path;
    node = form;
  }
  return node.replace(/\{(\w+)\}/g, (_, k) => String(vars?.[k] ?? `{${k}}`));
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function pctLabel(value) {
  const nbsp = lang === "fr" ? " " : "";
  return `${Math.round(value * 100)}${nbsp}%`;
}

function markerLeft(score) {
  return `calc(${score}% - 1px)`;
}

/* ---------- measure ---------- */

function renderMeasure(review) {
  const wrap = el("div", "tl-measure");

  const top = el("div", "tl-mtop");
  top.append(el("span", "tl-mscore", String(review.score)));
  top.append(el("span", "tl-mband", t(`band.${review.band}`)));
  wrap.append(top);

  const track = el("div", "tl-track");
  BAND_WIDTHS.forEach((width, i) => {
    const seg = el("span", `tl-seg${i + 1}`);
    seg.style.width = `${width}%`;
    track.append(seg);
  });
  const marker = el("i", "tl-marker");
  marker.style.left = markerLeft(review.score);
  track.append(marker);
  wrap.append(track);

  wrap.append(renderScale());

  const qual = el("div", "tl-qual");
  const low = review.evidence === "LOW";
  if (low) qual.classList.add("tl-qual-low");
  qual.append(el("span", "tl-i", "i"));
  const label = low ? t("ui.lowEvidence") : t("signal.adequateEvidence");
  qual.append(document.createTextNode(` ${label} · ${t("page.bandPosition", { n: review.bandNumber })}`));
  wrap.append(qual);

  return wrap;
}

function renderScale() {
  const scale = el("div", "tl-mscale");
  scale.append(el("span", null, "0"));
  scale.append(el("span", null, "50"));
  scale.append(el("span", null, "100"));
  return scale;
}

/* ---------- signal rows ---------- */

function renderSignals(signals) {
  const frag = document.createDocumentFragment();

  const scale = el("div", "tl-sigscale");
  scale.append(el("span", null, "← manipulative"));
  scale.append(el("span", null, "organic →"));
  frag.append(scale);

  for (const signal of signals) {
    const row = el("div", "tl-sig");

    const head = el("div", "tl-sighead");
    head.append(el("span", "tl-siglabel", t(`signal.${signal.kind}`)));
    const manipulative = signal.direction === "manipulative";
    head.append(el("span", `tl-dir ${manipulative ? "manip" : "org"}`, manipulative ? "←" : "→"));
    head.append(el("span", "tl-pct", pctLabel(signal.contribution)));
    row.append(head);

    const axis = el("div", "tl-axis");
    const bar = el("span", "tl-bar");
    const width = Math.min(Math.abs(signal.contribution) * 50, 50);
    if (manipulative) {
      bar.style.left = `${50 - width}%`;
    } else {
      bar.style.left = "50%";
    }
    bar.style.width = `${width}%`;
    bar.style.background = manipulative ? "var(--tl-manipulation)" : "var(--tl-organic)";
    axis.append(bar);
    row.append(axis);

    frag.append(row);
  }

  frag.append(el("div", "tl-signote", t("signal.contributionsNote")));
  return frag;
}

/* ---------- review rows ---------- */

function renderReviewRow(review) {
  const rev = el("div", "tl-rev");
  const row = el("div", "tl-row");

  row.append(el("span", "tl-idx", review.index));
  row.append(el("span", "tl-score", String(review.score)));

  const middle = el("div");
  middle.append(el("div", "tl-band", t(`band.${review.band}`)));
  const ev = el("div", "tl-ev");
  const low = review.evidence === "LOW";
  const label = low ? t("ui.lowEvidence") : t("signal.adequateEvidence");
  if (low) {
    const lowWrap = el("span", "tl-ev-low");
    lowWrap.append(el("span", "tl-i", "i"));
    lowWrap.append(document.createTextNode(` ${label} · ${t("page.bandPosition", { n: review.bandNumber })}`));
    ev.append(lowWrap);
  } else {
    ev.textContent = `${label} · ${t("page.bandPosition", { n: review.bandNumber })}`;
  }
  middle.append(ev);
  row.append(middle);

  row.append(el("span", "tl-chev", review.expanded ? "⌃" : "⌄"));
  rev.append(row);

  rev.append(el("div", "tl-top", t(`signal.${review.topSignal}`)));

  if (review.expanded) {
    const detail = el("div", "tl-detail");
    detail.append(renderMeasure(review));
    detail.append(renderSignals(review.signals));
    rev.append(detail);
  }

  return rev;
}

/* ---------- state blocks ---------- */

function renderStateBlock(kind) {
  const box = el("div", "tl-statebox");

  if (kind === "signals-only") {
    const head = el("div");
    head.append(el("span", "tl-statetitle", t("ui.signalOnlyMode")));
    box.append(head);
    box.append(el("div", "tl-statebody"));
    const signals = [
      { kind: "PROMOTIONAL_TONE", direction: "manipulative" },
      { kind: "REPEATED_PHRASING", direction: "manipulative" },
    ];
    for (const signal of signals) {
      const row = el("div", "tl-sig");
      const head2 = el("div", "tl-sighead");
      head2.append(el("span", "tl-siglabel", t(`signal.${signal.kind}`)));
      head2.append(el("span", "tl-dir manip", "←"));
      row.append(head2);
      box.append(row);
    }
    return box;
  }

  /* unknown */
  const head = el("div", "tl-mtop");
  head.append(el("span", "tl-score none", "—"));
  head.append(el("span", "tl-statetitle", t("ui.unknownHeading")));
  box.append(head);
  box.append(el("div", "tl-statebody", t("ui.insufficientText")));

  const rule = el("div", "tl-unknownrule");
  [20, 20, 15, 15, 15].forEach((width) => {
    const seg = el("i");
    seg.style.width = `${width}%`;
    rule.append(seg);
  });
  box.append(rule);
  box.append(renderScale());

  return box;
}

/* ---------- chips ---------- */

function renderChipLadder(bandNumber) {
  const ticks = el("span", "tl-ticks");
  for (let i = 1; i <= 6; i += 1) {
    ticks.append(el("i", i === bandNumber ? "on" : null));
  }
  return ticks;
}

function renderChips() {
  const wrap = el("div", "mock-chips");
  wrap.append(el("h3", "mock-chips-title", "INLINE CHIPS · HOST PAGE · 1×"));

  const scored = el("span", "chip");
  scored.append(el("span", null, "73"));
  scored.append(renderChipLadder(5));
  wrap.append(scored);

  const low = el("span", "chip");
  low.append(el("span", null, "64"));
  low.append(renderChipLadder(4));
  const lowQual = el("span", null, `· ${t("ui.lowEvidence")}`);
  lowQual.style.cssText = "font-family:var(--tl-font-sans);font-size:var(--tl-panel-micro-size);color:var(--tl-evidence-low);";
  low.append(lowQual);
  wrap.append(low);

  const unknown = el("span", "chip unknown");
  unknown.append(el("span", null, t("ui.unknownHeading")));
  wrap.append(unknown);

  const signalsOnly = el("span", "chip unknown");
  signalsOnly.append(el("span", null, t("chip.signalsOnly")));
  wrap.append(signalsOnly);

  return wrap;
}

/* ---------- panel ---------- */

const MARK = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <path d="M18.51 6.54 A8.5 8.5 0 1 0 18.51 17.46" fill="none" stroke="currentColor" stroke-width="2"/>
  <rect x="17.24" y="10.78" width="2.5" height="2.5" fill="currentColor"/>
</svg>`;

const GEAR = `
<svg class="tl-gear" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-cap="square" aria-hidden="true" focusable="false">
  <path d="M3 6h9M15 6h2M3 14h3M9 14h8"/>
  <circle cx="13.5" cy="6" r="1.7"/>
  <circle cx="7.5" cy="14" r="1.7"/>
</svg>`;

function renderPanel() {
  const panel = el("section", "tl-panel");

  const head = el("header", "tl-head");
  const brand = el("div", "tl-brand");
  brand.innerHTML = MARK;
  brand.append(el("span", null, t("brandName")));
  head.append(brand);
  const tools = el("div", "tl-head-tools");
  const langCtl = el("div", "tl-lang");
  const en = el("b", null, "EN");
  const sep = el("span", null, "/");
  const fr = el("span", null, "FR");
  if (lang === "fr") {
    langCtl.append(fr, sep, en);
  } else {
    langCtl.append(en, sep, fr);
  }
  tools.append(langCtl);
  const gearWrap = el("span");
  gearWrap.innerHTML = GEAR;
  tools.append(gearWrap);
  head.append(tools);
  panel.append(head);

  const pagebar = el("div", "tl-pagebar");
  const site = el("div");
  site.append(el("div", "tl-site", "example-shop.com"));
  site.append(el("div", "tl-count", t("page.reviewsFound", { count: 3 })));
  pagebar.append(site);
  const rescan = el("div", "tl-rescan", t("page.rescanAction"));
  rescan.setAttribute("role", "button");
  rescan.tabIndex = 0;
  pagebar.append(rescan);
  panel.append(pagebar);

  const list = el("div", "tl-list");
  for (const review of REVIEWS) {
    list.append(renderReviewRow(review));
  }
  list.append(renderStateBlock("unknown"));
  list.append(renderStateBlock("signals-only"));
  panel.append(list);

  const foot = el("footer", "tl-foot");
  foot.append(el("div", null, t("ui.estimateDisclaimer")));
  foot.append(el("div", "tl-meta", "tl-text-1.1.0 · contract v1"));
  panel.append(foot);

  return panel;
}

/* ---------- boot ---------- */

async function loadStrings(nextLang) {
  const res = await fetch(STRINGS_URL[nextLang]);
  if (!res.ok) throw new Error(`failed to load ${STRINGS_URL[nextLang]}`);
  return res.json();
}

async function render(nextLang) {
  lang = nextLang;
  S = await loadStrings(lang);
  document.documentElement.lang = lang;
  document.querySelectorAll(".mock-lang button").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.lang === lang);
  });
  root.replaceChildren(renderPanel(), renderChips());
}

document.querySelectorAll(".mock-lang button").forEach((btn) => {
  btn.addEventListener("click", () => {
    if (btn.dataset.lang !== lang) render(btn.dataset.lang);
  });
});

render(lang).catch((err) => {
  root.textContent = `Mock failed to load: ${err.message}. Serve the extension folder over HTTP (see mock/README.md) instead of opening this file directly.`;
});
