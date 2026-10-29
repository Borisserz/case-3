/** Sidebar history + folders owner (out of App shell). */

import { useCallback, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  createFolder,
  deleteFolder,
  loadFolders,
  loadHistory,
  loadHistoryPayload,
  moveHistoryToFolder,
  pushHistory,
  renameFolder,
  saveRunPayload,
  togglePinHistory,
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
      const stored = loadHistoryPayload(item.runId);
      if (!stored?.preview?.blocks?.length) {
        showToast("Отчёт недоступен в этой сессии");
        return;
      }
      const result = stored as RunResult;
      const id = uid();
      setChatTitle(item.title || reportTitle(result));
      setMsgs([
        {
          id,
          role: "bot",
          text: reportReadyText(result),
          result,
        },
      ]);
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
