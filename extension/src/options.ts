import { clearHistory, getHistory, isHistoryEnabled, setHistoryEnabled, type HistoryRecord } from "./history-store.js";
import en from "./i18n/en.json";
import fr from "./i18n/fr.json";

const language = navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
const copy = language === "fr" ? fr : en;
document.documentElement.lang = language;

function required<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) throw new Error(`TrustLoop options page is missing ${selector}`);
  return element;
}

const enabled = required<HTMLInputElement>("#history-enabled");
const list = required<HTMLOListElement>("#history-list");
const emptyState = required<HTMLParagraphElement>("#empty-state");
const clearButton = required<HTMLButtonElement>("#clear-history");

required<HTMLElement>("#history-title").textContent = copy.history.title;
required<HTMLElement>("#history-list-title").textContent = copy.ui.historyLabel;
required<HTMLElement>("#toggle-label").textContent = copy.history.toggleLabel;
required<HTMLElement>("#privacy-helper").textContent = copy.history.privacyHelper;
required<HTMLElement>("#disabled-helper").textContent = copy.history.disabledHelper;
clearButton.textContent = copy.ui.clearHistoryAction;

function resultLabel(record: HistoryRecord): string {
  if (record.status === "SCORED") {
    const band = record.verdict ? copy.band[record.verdict as keyof typeof en.band] ?? record.verdict : "";
    return [copy.history.scored, record.trustScore === undefined ? "" : `${record.trustScore}/100`, band]
      .filter(Boolean).join(" · ");
  }
  if (record.status === "SIGNALS_ONLY") return copy.history.signalsOnly;
  return [copy.history.unknown, record.reasonCode].filter(Boolean).join(" · ");
}

function renderRecord(record: HistoryRecord): HTMLLIElement {
  const item = document.createElement("li");
  item.className = "history-row";
  const host = document.createElement("span");
  host.className = "host";
  host.textContent = record.hostname === "manual" ? copy.history.manual : record.hostname;
  const timestamp = document.createElement("time");
  timestamp.className = "timestamp";
  timestamp.dateTime = record.timestamp;
  timestamp.textContent = new Date(record.timestamp).toLocaleString(language);
  const result = document.createElement("span");
  result.className = "result";
  result.textContent = resultLabel(record);
  const details = document.createElement("span");
  details.className = "details";
  details.textContent = [
    record.adapterId,
    record.evidenceQuality,
    record.engine,
    record.modelVersion,
  ].filter(Boolean).join(" · ");
  item.append(host, timestamp, result, details);
  return item;
}

async function refresh(): Promise<void> {
  const [historyEnabled, records] = await Promise.all([isHistoryEnabled(), getHistory()]);
  enabled.checked = historyEnabled;
  clearButton.disabled = records.length === 0;
  emptyState.hidden = records.length !== 0;
  emptyState.replaceChildren();
  if (records.length === 0) {
    emptyState.append(document.createTextNode(copy.history.noScans));
    const guidance = document.createElement("span");
    guidance.textContent = copy.history.emptyGuidance;
    emptyState.append(guidance);
  }
  list.replaceChildren(...records.map(renderRecord));
}

enabled.addEventListener("change", () => {
  void setHistoryEnabled(enabled.checked).then(refresh);
});

clearButton.addEventListener("click", () => {
  if (!window.confirm(copy.history.clearConfirm)) return;
  void clearHistory().then(refresh);
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "local" && (changes["trustloop.history.enabled"] || changes["trustloop.history.records"])) {
    void refresh();
  }
});

void refresh();
