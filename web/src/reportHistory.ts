/** Local report history — sessionStorage only (no backend). */

import type { HistoryItem } from "./Sidebar";

const KEY = "liber-report-history";
const LAST = "liber-last-report";
const MAX = 12;

export type StoredRun = {
  run_id: string;
  status: string;
  downloads: Record<string, string>;
  preview?: {
    title?: string;
    blocks?: unknown[];
  };
  charts_ok?: number;
  figures_ok?: number;
  charts_planned?: string[];
  figures_planned?: string[];
  warnings?: string[];
  previews?: { id: string; kind: string; url: string }[];
};

export function loadHistory(): HistoryItem[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return [];
    const list = JSON.parse(raw) as HistoryItem[];
    return Array.isArray(list) ? list.slice(0, MAX) : [];
  } catch {
    return [];
  }
}

export function pushHistory(item: HistoryItem): HistoryItem[] {
  const prev = loadHistory().filter((h) => h.runId !== item.runId);
  const next = [item, ...prev].slice(0, MAX);
  try {
    sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* quota */
  }
  return next;
}

export function loadLastReport(): StoredRun | null {
  try {
    const raw = sessionStorage.getItem(LAST);
    if (!raw) return null;
    return JSON.parse(raw) as StoredRun;
  } catch {
    return null;
  }
}

export function loadHistoryPayload(runId: string): StoredRun | null {
  try {
    const raw = sessionStorage.getItem(`liber-run-${runId}`);
    if (!raw) return null;
    return JSON.parse(raw) as StoredRun;
  } catch {
    return null;
  }
}

export function saveRunPayload(result: StoredRun): void {
  try {
    sessionStorage.setItem(LAST, JSON.stringify(result));
    if (result.run_id) {
      sessionStorage.setItem(
        `liber-run-${result.run_id}`,
        JSON.stringify(result),
      );
    }
  } catch {
    /* quota */
  }
}
