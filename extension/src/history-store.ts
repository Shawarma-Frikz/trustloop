import contract from "../../contracts/v1/constants.json";
import type { PublicResult } from "./scoring-api.js";

const ENABLED_KEY = "trustloop.history.enabled";
const RECORDS_KEY = "trustloop.history.records";
const MAX_ENTRIES = contract.constants.LOCAL_HISTORY_MAX_ENTRIES;
const MAX_AGE_MS = contract.constants.LOCAL_HISTORY_MAX_AGE_DAYS * 24 * 60 * 60 * 1000;

export interface HistoryRecord {
  timestamp: string;
  hostname: string;
  adapterId: string;
  status: PublicResult["status"];
  trustScore?: number;
  verdict?: string;
  evidenceQuality?: "LOW" | "ADEQUATE";
  engine: PublicResult["engine"];
  modelVersion?: string;
  reasonCode?: string;
}

export async function isHistoryEnabled(): Promise<boolean> {
  const stored = await chrome.storage.local.get(ENABLED_KEY);
  return stored[ENABLED_KEY] === true;
}

export async function setHistoryEnabled(enabled: boolean): Promise<void> {
  await chrome.storage.local.set({ [ENABLED_KEY]: enabled });
}

function sanitizeRecord(value: unknown): HistoryRecord | null {
  if (value === null || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (typeof item.timestamp !== "string" || !Number.isFinite(Date.parse(item.timestamp))
    || typeof item.hostname !== "string" || !/^[A-Za-z0-9.-]{1,253}$/.test(item.hostname)
    || typeof item.adapterId !== "string" || !/^[A-Za-z0-9._-]{1,64}$/.test(item.adapterId)
    || !["SCORED", "SIGNALS_ONLY", "UNKNOWN"].includes(String(item.status))
    || !["MODEL", "SIGNALS_ONLY"].includes(String(item.engine))) return null;

  const record: HistoryRecord = {
    timestamp: item.timestamp,
    hostname: item.hostname,
    adapterId: item.adapterId,
    status: item.status as HistoryRecord["status"],
    engine: item.engine as HistoryRecord["engine"],
  };
  if (Number.isInteger(item.trustScore) && Number(item.trustScore) >= 0 && Number(item.trustScore) <= 100) {
    record.trustScore = Number(item.trustScore);
  }
  if (typeof item.verdict === "string" && /^[A-Z_]{1,64}$/.test(item.verdict)) record.verdict = item.verdict;
  if (item.evidenceQuality === "LOW" || item.evidenceQuality === "ADEQUATE") record.evidenceQuality = item.evidenceQuality;
  if (typeof item.modelVersion === "string" && /^tl-text-\d+\.\d+\.\d+$/.test(item.modelVersion)) {
    record.modelVersion = item.modelVersion;
  }
  if (typeof item.reasonCode === "string" && /^[A-Z_]{1,64}$/.test(item.reasonCode)) record.reasonCode = item.reasonCode;
  return record;
}

function retainRecent(records: unknown, now: number): HistoryRecord[] {
  if (!Array.isArray(records)) return [];
  return records.map(sanitizeRecord).filter((record): record is HistoryRecord => record !== null)
    .filter((record) => now - Date.parse(record.timestamp) <= MAX_AGE_MS)
    .sort((left, right) => Date.parse(right.timestamp) - Date.parse(left.timestamp))
    .slice(0, MAX_ENTRIES);
}

export async function getHistory(): Promise<HistoryRecord[]> {
  const stored = await chrome.storage.local.get(RECORDS_KEY);
  const original = stored[RECORDS_KEY];
  const records = retainRecent(original, Date.now());
  if (Array.isArray(original) && JSON.stringify(original) !== JSON.stringify(records)) {
    await chrome.storage.local.set({ [RECORDS_KEY]: records });
  }
  return records;
}

export async function clearHistory(): Promise<void> {
  await chrome.storage.local.set({ [RECORDS_KEY]: [] });
}

export async function recordHistoryResults(
  results: readonly PublicResult[],
  hostname: string,
  adapterId: string,
  now = new Date(),
): Promise<void> {
  if (!(await isHistoryEnabled())) return;
  const safeHostname = /^[A-Za-z0-9.-]{1,253}$/.test(hostname) ? hostname : "manual";
  const safeAdapterId = /^[A-Za-z0-9._-]{1,64}$/.test(adapterId) ? adapterId : "manual.input";
  const stored = await chrome.storage.local.get(RECORDS_KEY);
  const existing = retainRecent(stored[RECORDS_KEY], now.getTime());
  const additions = results.map((result): HistoryRecord => {
    const record: HistoryRecord = {
      timestamp: now.toISOString(),
      hostname: safeHostname,
      adapterId: safeAdapterId,
      status: result.status,
      engine: result.engine,
    };
    if (Number.isInteger(result.trustScore)) record.trustScore = result.trustScore as number;
    if (typeof result.verdict === "string") record.verdict = result.verdict;
    if (result.evidenceQuality === "LOW" || result.evidenceQuality === "ADEQUATE") {
      record.evidenceQuality = result.evidenceQuality;
    }
    if (typeof result.modelVersion === "string") record.modelVersion = result.modelVersion;
    if (typeof result.reasonCode === "string") record.reasonCode = result.reasonCode;
    return record;
  });
  await chrome.storage.local.set({ [RECORDS_KEY]: [...additions.reverse(), ...existing].slice(0, MAX_ENTRIES) });
}
