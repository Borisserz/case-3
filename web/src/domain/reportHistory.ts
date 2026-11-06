/** Local report history — sessionStorage only (no backend). */

const KEY = "liber-report-history";
const FOLDERS_KEY = "liber-history-folders";
const LAST = "liber-last-report";
const MAX = 24;

export type HistoryItem = {
  id: string;
  title: string;
  runId: string;
  savedAt: number;
  pinned?: boolean;
  folderId?: string | null;
};

export type HistoryFolder = {
  id: string;
  name: string;
  createdAt: number;
};

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

function sortHistory(list: HistoryItem[]): HistoryItem[] {
  return [...list].sort((a, b) => {
    const ap = a.pinned ? 1 : 0;
    const bp = b.pinned ? 1 : 0;
    if (ap !== bp) return bp - ap;
    return (b.savedAt || 0) - (a.savedAt || 0);
  });
}

export function loadHistory(): HistoryItem[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return [];
    const list = JSON.parse(raw) as HistoryItem[];
    if (!Array.isArray(list)) return [];
    return sortHistory(
      list.map((h) => ({
        ...h,
        pinned: Boolean(h.pinned),
        folderId: h.folderId || null,
      })),
    ).slice(0, MAX);
  } catch {
    return [];
  }
}

function writeHistory(list: HistoryItem[]): HistoryItem[] {
  const next = sortHistory(list).slice(0, MAX);
  try {
    sessionStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* quota */
  }
  return next;
}

export function pushHistory(item: HistoryItem): HistoryItem[] {
  const prev = loadHistory();
  const existing = prev.find((h) => h.runId === item.runId);
  const merged: HistoryItem = {
    ...item,
    pinned: item.pinned ?? existing?.pinned ?? false,
    folderId:
      item.folderId !== undefined
        ? item.folderId
        : (existing?.folderId ?? null),
  };
  const rest = prev.filter((h) => h.runId !== item.runId);
  return writeHistory([merged, ...rest]);
}

export function updateHistoryItem(
  runId: string,
  patch: Partial<Pick<HistoryItem, "pinned" | "folderId" | "title">>,
): HistoryItem[] {
  const next = loadHistory().map((h) =>
    h.runId === runId ? { ...h, ...patch } : h,
  );
  return writeHistory(next);
}

export function togglePinHistory(runId: string): HistoryItem[] {
  const cur = loadHistory().find((h) => h.runId === runId);
  if (!cur) return loadHistory();
  return updateHistoryItem(runId, { pinned: !cur.pinned });
}

export function moveHistoryToFolder(
  runId: string,
  folderId: string | null,
): HistoryItem[] {
  return updateHistoryItem(runId, { folderId });
}

export function loadFolders(): HistoryFolder[] {
  try {
    const raw = sessionStorage.getItem(FOLDERS_KEY);
    if (!raw) return [];
    const list = JSON.parse(raw) as HistoryFolder[];
    return Array.isArray(list)
      ? list.sort((a, b) => a.name.localeCompare(b.name, "ru"))
      : [];
  } catch {
    return [];
  }
}

function writeFolders(list: HistoryFolder[]): HistoryFolder[] {
  const next = [...list].sort((a, b) => a.name.localeCompare(b.name, "ru"));
  try {
    sessionStorage.setItem(FOLDERS_KEY, JSON.stringify(next));
  } catch {
    /* quota */
  }
  return next;
}

export function createFolder(name: string): HistoryFolder[] {
  const trimmed = name.trim().slice(0, 40);
  if (!trimmed) return loadFolders();
  const folders = loadFolders();
  if (folders.some((f) => f.name.toLowerCase() === trimmed.toLowerCase())) {
    return folders;
  }
  const folder: HistoryFolder = {
    id: `fld_${Date.now().toString(36)}`,
    name: trimmed,
    createdAt: Date.now(),
  };
  return writeFolders([...folders, folder]);
}

export function renameFolder(id: string, name: string): HistoryFolder[] {
  const trimmed = name.trim().slice(0, 40);
  if (!trimmed) return loadFolders();
  return writeFolders(
    loadFolders().map((f) => (f.id === id ? { ...f, name: trimmed } : f)),
  );
}

export function deleteFolder(id: string): {
  folders: HistoryFolder[];
  history: HistoryItem[];
} {
  const folders = writeFolders(loadFolders().filter((f) => f.id !== id));
  const history = writeHistory(
    loadHistory().map((h) =>
      h.folderId === id ? { ...h, folderId: null } : h,
    ),
  );
  return { folders, history };
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

export type StoredUserTurn = {
  text: string;
  photos?: { url: string; name?: string }[];
};

function userTurnKey(runId: string): string {
  return `liber-user-${runId}`;
}

export function saveUserTurn(runId: string, turn: StoredUserTurn): void {
  if (!runId) return;
  const photos = (turn.photos || []).filter(
    (p) => p.url && !p.url.startsWith("blob:"),
  );
  try {
    sessionStorage.setItem(
      userTurnKey(runId),
      JSON.stringify({ text: turn.text || "", photos }),
    );
  } catch {
    /* quota */
  }
}

export function loadUserTurn(runId: string): StoredUserTurn | null {
  try {
    const raw = sessionStorage.getItem(userTurnKey(runId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredUserTurn;
    if (!parsed || typeof parsed.text !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function uploadedPhotoThumbs(
  previews?: { id?: string; url?: string }[] | null,
): { url: string; name: string }[] {
  return (previews || [])
    .filter((p) => (p.id || "").startsWith("usr_") && Boolean(p.url))
    .map((p) => ({ url: String(p.url), name: String(p.id) }));
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
