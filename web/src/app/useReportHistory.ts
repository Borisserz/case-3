/** Sidebar history + folders owner (out of App shell). */

import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  createFolder,
  deleteFolder,
  loadFolders,
  loadHistory,
  loadHistoryPayload,
  loadUserTurn,
  moveHistoryToFolder,
  pushHistory,
  renameFolder,
  saveRunPayload,
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
};

export function useReportHistory({
  busy,
  setMsgs,
  setChatTitle,
  showToast,
}: Deps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(() => loadHistory());
  const [folders, setFolders] = useState<HistoryFolder[]>(() => loadFolders());

  const rememberRun = useCallback(
    (result: RunResult) => {
      saveRunPayload(result);
      const title = reportTitle(result);
      setChatTitle(title);
      setHistory(
        pushHistory({
          id: result.run_id,
          title,
          runId: result.run_id,
          savedAt: Date.now(),
        }),
      );
    },
    [setChatTitle],
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
        const base = (stored || remote) as RunResult | null;
        if (!base) {
          showToast("Отчёт недоступен в этой сессии");
          return;
        }
        const result: RunResult = {
          ...base,
          ...(remote || {}),
          downloads: {
            ...(base.downloads || {}),
            ...(remote?.downloads || {}),
          },
          preview: remote?.preview?.blocks?.length
            ? remote.preview
            : base.preview,
          previews: remote?.previews?.length ? remote.previews : base.previews,
          user_text: remote?.user_text || base.user_text || "",
        };
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
            result.diagrams?.length,
        );
        if (!hasArtifact && !userText && !photos.length) {
          showToast("Отчёт недоступен в этой сессии");
          return;
        }
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
        if (hasArtifact) {
          next.push({
            id: uid(),
            role: "bot",
            text: reportReadyText(result),
            result,
          });
        }
        setMsgs(next);
      })();
    },
    [busy, setChatTitle, setMsgs, showToast],
  );

  const onTogglePin = useCallback((runId: string) => {
    setHistory(togglePinHistory(runId));
  }, []);

  const onMoveToFolder = useCallback((runId: string, folderId: string | null) => {
    setHistory(moveHistoryToFolder(runId, folderId));
  }, []);

  const onCreateFolder = useCallback((name: string) => {
    setFolders(createFolder(name));
  }, []);

  const onRenameFolder = useCallback((id: string, name: string) => {
    setFolders(renameFolder(id, name));
  }, []);

  const onDeleteFolder = useCallback((id: string) => {
    const next = deleteFolder(id);
    setFolders(next.folders);
    setHistory(next.history);
  }, []);

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
