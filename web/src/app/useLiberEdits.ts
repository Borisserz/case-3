/** Liber Preview edit/undo handlers (charts, figures, tables, paragraphs). */

import { useRef, type Dispatch, type MutableRefObject, type SetStateAction } from "react";
import type { ChartEditRequest } from "../ChartEditSheet";
import type { ImageEditRequest } from "../ImageEditModal";
import type { ParagraphEditRequest } from "../ParagraphEditSheet";
import type { TableEditRequest } from "../TableEditSheet";
import { asDownloads } from "../domain/runHelpers";
import type { RunResult } from "../domain/liberTypes";
import { mapTableEditHttpError, postJsonEdit } from "./postJsonEdit";

export type EditBusy = { msgId: string; figureId: string } | null;
export type EditError = { msgId: string; figureId: string; message: string } | null;
export type UndoOffer = { msgId: string; runId: string } | null;

type ApplyEditPayload = (
  msgId: string,
  runId: string,
  data: {
    preview?: RunResult["preview"];
    downloads?: RunResult["downloads"];
    warnings?: string[];
    media_status?: RunResult["media_status"];
    diagrams?: RunResult["diagrams"];
    undo?: { kind?: string; target?: string } | null;
  },
  toastText: string,
) => void;

type Args = {
  applyEditPayload: ApplyEditPayload;
  setEditBusy: Dispatch<SetStateAction<EditBusy>>;
  setEditError: Dispatch<SetStateAction<EditError>>;
  setUndoOffer: Dispatch<SetStateAction<UndoOffer>>;
  setToast: Dispatch<SetStateAction<string | null>>;
  undoOffer: UndoOffer;
  undoBusyRef?: MutableRefObject<boolean>;
};

export function useLiberEdits({
  applyEditPayload,
  setEditBusy,
  setEditError,
  setUndoOffer,
  setToast,
  undoOffer,
  undoBusyRef: undoBusyRefProp,
}: Args) {
  const editLock = useRef(false);
  const undoBusyLocal = useRef(false);
  const undoBusyRef = undoBusyRefProp ?? undoBusyLocal;

  async function undoLastEdit() {
    if (!undoOffer || undoBusyRef.current) return;
    undoBusyRef.current = true;
    const { msgId, runId } = undoOffer;
    try {
      const res = await fetch(
        `/api/runs/${encodeURIComponent(runId)}/undo`,
        { method: "POST" },
      );
      const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : typeof data.error === "string"
              ? data.error
              : res.statusText || "undo failed",
        );
      }
      applyEditPayload(msgId, runId, { ...data, undo: null }, "Правка отменена");
      setUndoOffer(null);
    } catch (err) {
      setToast(err instanceof Error ? err.message : String(err));
      window.setTimeout(() => setToast(null), 3200);
    } finally {
      undoBusyRef.current = false;
    }
  }

  async function editFigure(
    msgId: string,
    runId: string,
    req: ChartEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    editLock.current = true;
    setEditError(null);
    setEditBusy({ msgId, figureId: req.figureId });
    try {
      const data = await postJsonEdit(
        `/api/runs/${encodeURIComponent(runId)}/charts/${encodeURIComponent(req.figureId)}/edit`,
        {
          palette: req.palette,
          style: req.styleNotes,
          chart_type: req.chartType,
          formats: "both",
        },
      );
      applyEditPayload(msgId, runId, data, "Отчёт обновлён");
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: req.figureId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editImage(
    msgId: string,
    runId: string,
    req: ImageEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    editLock.current = true;
    setEditError(null);
    setEditBusy({ msgId, figureId: req.figureId });
    try {
      const data = await postJsonEdit(
        `/api/runs/${encodeURIComponent(runId)}/figures/${encodeURIComponent(req.figureId)}/edit`,
        {
          mode: req.mode,
          prompt: req.prompt,
          caption: req.caption,
          formats: "both",
        },
        "image edit failed",
      );
      applyEditPayload(
        msgId,
        runId,
        data,
        req.mode === "edit" ? "Фото изменено" : "Фото сгенерировано заново",
      );
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: req.figureId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editTable(
    msgId: string,
    runId: string,
    req: TableEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    const rid = (runId || "").trim();
    if (!rid) {
      setEditError({
        msgId,
        figureId: `tab:${req.tableIndex}`,
        message:
          "Нет run_id — открой отчёт из свежего запуска, не из пустой сессии",
      });
      return false;
    }
    editLock.current = true;
    const tableId = `tab:${req.tableIndex}`;
    setEditError(null);
    setEditBusy({ msgId, figureId: tableId });
    try {
      const data = await postJsonEdit(
        `/api/runs/${encodeURIComponent(rid)}/tables/${req.tableIndex}/edit`,
        {
          caption: req.caption,
          headers: req.headers,
          rows: req.rows,
          formats: "both",
        },
        "table edit failed",
      );
      applyEditPayload(
        msgId,
        rid,
        {
          preview: data.preview as RunResult["preview"],
          downloads: asDownloads(data.downloads, {}),
          warnings: Array.isArray(data.warnings)
            ? data.warnings.filter((w): w is string => typeof w === "string")
            : undefined,
          media_status: data.media_status as RunResult["media_status"],
          undo: data.undo as { kind?: string; target?: string } | null,
        },
        "Таблица обновлена",
      );
      return true;
    } catch (err) {
      const mapped = mapTableEditHttpError(err);
      setEditError({
        msgId,
        figureId: tableId,
        message: mapped.message,
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  async function editParagraph(
    msgId: string,
    runId: string,
    req: ParagraphEditRequest,
  ): Promise<boolean> {
    if (editLock.current) return false;
    const rid = (runId || "").trim();
    if (!rid) {
      setEditError({
        msgId,
        figureId: `para:${req.paragraphIndex}`,
        message: "Нет run_id — открой отчёт из свежего запуска",
      });
      return false;
    }
    editLock.current = true;
    const paraId = `para:${req.paragraphIndex}`;
    setEditError(null);
    setEditBusy({ msgId, figureId: paraId });
    try {
      const data = await postJsonEdit(
        `/api/runs/${encodeURIComponent(rid)}/paragraphs/${req.paragraphIndex}/edit`,
        { text: req.text, formats: "both" },
        "paragraph edit failed",
      );
      applyEditPayload(
        msgId,
        rid,
        {
          preview: data.preview as RunResult["preview"],
          downloads: asDownloads(data.downloads, {}),
          warnings: Array.isArray(data.warnings)
            ? data.warnings.filter((w): w is string => typeof w === "string")
            : undefined,
          media_status: data.media_status as RunResult["media_status"],
          undo: data.undo as { kind?: string; target?: string } | null,
        },
        "Абзац обновлён",
      );
      return true;
    } catch (err) {
      setEditError({
        msgId,
        figureId: paraId,
        message: err instanceof Error ? err.message : String(err),
      });
      return false;
    } finally {
      setEditBusy(null);
      editLock.current = false;
    }
  }

  return {
    editFigure,
    editImage,
    editTable,
    editParagraph,
    undoLastEdit,
  };
}
