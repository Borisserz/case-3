/** Sidebar history + folders owner (out of App shell). */

import { useCallback, useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  needsSlidesHydrate,
  type SlidesPayload,
} from "../domain/attachSlidesPayload";
import {
  createFolder,
  deleteFolder,
  hydrateHistoryResult,
  loadFolders,
  loadHistory,
  loadHistoryPayload,
  loadUserTurn,
  mergeServerFolders,
  mergeServerHistory,
  moveHistoryToFolder,
  pushHistory,
  renameFolder,
  saveRunPayload,
  syncServerHistory,
  togglePinHistory,
  uploadedPhotoThumbs,
  type HistoryFolder,
  type HistoryItem,
} from "../domain/reportHistory";
import { reportReadyText, reportTitle, uid } from "../domain/runHelpers";
import type { Msg, RunResult } from "../domain/liberTypes";

type Deps = {
  busy: boolean;
  setMsgs: Dispatch<SetStateAction<Msg[]>>;
  setChatTitle: Dispatch<SetStateAction<string | null>>;
  showToast: (message: string, ms?: number) => void;
  openReportArtifact?: (msgId: string, result: RunResult) => void;
  onResetSurface?: () => void;
};

export function useReportHistory({
  busy,
  setMsgs,
  setChatTitle,
  showToast,
  openReportArtifact,
  onResetSurface,
}: Deps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => loadHistory());
  const [folders, setFolders] = useState<HistoryFolder[]>(() => loadFolders());

  // Hydrate history from server on mount
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/history");
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as {
          items?: HistoryItem[];
          folders?: HistoryFolder[];
        };
        if (cancelled) return;
        if (Array.isArray(data.items) && data.items.length > 0) {
          setHistory((prev) => mergeServerHistory(prev, data.items || []));
        }
        if (Array.isArray(data.folders) && data.folders.length > 0) {
          setFolders((prev) => mergeServerFolders(prev, data.folders || []));
        }
      } catch {
        /* ignore offline/server not ready */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const rememberRun = useCallback(
    (result: RunResult) => {
      saveRunPayload(result);
      const title = reportTitle(result);
      setChatTitle(title);
      const next = pushHistory({
        id: result.run_id,
        title,
        runId: result.run_id,
        savedAt: Date.now(),
      });
      setHistory(next);
      void syncServerHistory(next, folders);
    },
    [folders, setChatTitle],
  );

  const openHistoryItem = useCallback(
    (item: HistoryItem) => {
      if (busy) return;
      void (async () => {
        const stored = loadHistoryPayload(item.runId);
        let remote: RunResult | null = null;
        try {
          const res = await fetch(
            `/api/runs/${encodeURIComponent(item.runId)}/status`,
          );
          if (res.ok) remote = (await res.json()) as RunResult;
        } catch {
          /* session copy is enough */
        }
        let result = hydrateHistoryResult(stored, remote);
        if (!result) {
          showToast("Отчёт недоступен в этой сессии");
          return;
        }
        if (
          needsSlidesHydrate(result) ||
          result.output_mode === "presentation"
        ) {
          try {
            const sr = await fetch(
              `/api/runs/${encodeURIComponent(item.runId)}/slides`,
            );
            if (sr.ok) {
              const sp = (await sr.json()) as SlidesPayload;
              result = hydrateHistoryResult(stored, remote, sp) || result;
            }
          } catch {
            /* status payload is enough */
          }
        }
        saveRunPayload(result);
        const turn = loadUserTurn(item.runId);
        const userText = (turn?.text || result.user_text || "").trim();
        const photos = turn?.photos?.length
          ? turn.photos
          : uploadedPhotoThumbs(result.previews);
        const hasArtifact = Boolean(
          result.preview?.blocks?.length ||
            result.downloads?.pdf ||
            result.downloads?.pptx ||
            result.downloads?.deck_pdf ||
            result.diagrams?.length ||
            result.deck?.slides?.length ||
            result.slide_pngs?.length,
        );
        if (!hasArtifact && !userText && !photos.length) {
          showToast("Отчёт недоступен в этой сессии");
          return;
        }
        onResetSurface?.();
        setChatTitle(item.title || reportTitle(result));
        const next: Msg[] = [];
        if (userText || photos.length) {
          next.push({
            id: uid(),
            role: "user",
            text: userText,
            photos,
          });
        }
        let botMsgId: string | null = null;
        if (hasArtifact) {
          botMsgId = uid();
          next.push({
            id: botMsgId,
            role: "bot",
            text: reportReadyText(result),
            result,
          });
        }
        setMsgs(next);
        if (botMsgId && hasArtifact) {
          openReportArtifact?.(botMsgId, result);
        }
      })();
    },
    [
      busy,
      onResetSurface,
      openReportArtifact,
      setChatTitle,
      setMsgs,
      showToast,
    ],
  );

  const onTogglePin = useCallback(
    (runId: string) => {
      const next = togglePinHistory(runId);
      setHistory(next);
      void syncServerHistory(next, folders);
    },
    [folders],
  );

  const onMoveToFolder = useCallback(
    (runId: string, folderId: string | null) => {
      const next = moveHistoryToFolder(runId, folderId);
      setHistory(next);
      void syncServerHistory(next, folders);
    },
    [folders],
  );

  const onCreateFolder = useCallback(
    (name: string) => {
      const next = createFolder(name);
      setFolders(next);
      void syncServerHistory(history, next);
    },
    [history],
  );

  const onRenameFolder = useCallback(
    (id: string, name: string) => {
      const next = renameFolder(id, name);
      setFolders(next);
      void syncServerHistory(history, next);
    },
    [history],
  );

  const onDeleteFolder = useCallback(
    (id: string) => {
      const next = deleteFolder(id);
      setFolders(next.folders);
      setHistory(next.history);
      void syncServerHistory(next.history, next.folders);
    },
    [],
  );

  return {
    sidebarCollapsed,
    setSidebarCollapsed,
    history,
    folders,
    rememberRun,
    openHistoryItem,
    onTogglePin,
    onMoveToFolder,
    onCreateFolder,
    onRenameFolder,
    onDeleteFolder,
  };
}
