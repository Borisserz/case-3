/** Full-screen Markdown modal for any attached document + original download. */

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { SourceAttachment } from "./domain/liberTypes";
import {
  resolveOriginalDownload,
  sourceModalEyebrow,
} from "./domain/sourceRead";
import { renderLightMd } from "./lightMd";
import { useFocusTrap } from "./useFocusTrap";

type Props = {
  docs: SourceAttachment[];
  startIndex?: number;
  onClose: () => void;
  onSave?: (index: number, text: string) => void;
};

export function SourceReadModal({ docs, startIndex = 0, onClose, onSave }: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const [activeIdx, setActiveIdx] = useState(startIndex);
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const editingRef = useRef(false);
  editingRef.current = editing;
  useFocusTrap(dialogRef, { active: true });

  const openKey = docs.map((doc) => doc.fileName || doc.title).join("\n");

  useEffect(() => {
    setActiveIdx(startIndex);
    setQuery("");
    setEditing(false);
    setCopied(false);
  }, [openKey, startIndex]);

  const safeIdx = Math.min(activeIdx, Math.max(0, docs.length - 1));
  const activeDoc = docs[safeIdx] || docs[0];

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (editingRef.current) {
        setEditing(false);
        return;
      }
      onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  const html = useMemo(
    () => (activeDoc ? renderLightMd(activeDoc.text || "", query) : ""),
    [activeDoc, query],
  );

  function beginEdit() {
    setDraft(activeDoc?.text || "");
    setEditing(true);
    window.setTimeout(() => editorRef.current?.focus(), 0);
  }

  function saveEdit() {
    const next = draft.replace(/\r\n/g, "\n");
    if (!next.trim()) return;
    onSave?.(safeIdx, next);
    setEditing(false);
  }

  if (!activeDoc) return null;

  const heading = activeDoc.title || activeDoc.fileName || "Документ";
  const eyebrow = sourceModalEyebrow(activeDoc);
  const downloadTarget = resolveOriginalDownload(activeDoc);

  async function copyMarkdown() {
    try {
      await navigator.clipboard.writeText(activeDoc.text || "");
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  }

  function downloadBlobFallback() {
    if (downloadTarget.kind !== "blob") return;
    const blob = new Blob([downloadTarget.text], {
      type: "text/markdown;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadTarget.fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      ref={dialogRef}
      className="stimul-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="stimul-sheet is-read">
        <header className="settings-modal-head">
          <div>
            <p className="settings-modal-eyebrow">{eyebrow}</p>
            <h2 id={titleId} className="settings-modal-title">
              {heading}
            </h2>
          </div>
          <div className="dash-read-head-controls">
            {editing ? null : (
              <input
                type="search"
                className="dash-read-search"
                placeholder="Найти в документе…"
                aria-label="Поиск по документу"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            )}
            {editing ? (
              <>
                <button
                  type="button"
                  className="stimul-download-btn"
                  onClick={saveEdit}
                >
                  Сохранить
                </button>
                <button
                  type="button"
                  className="stimul-copy-btn"
                  onClick={() => setEditing(false)}
                >
                  Отмена
                </button>
              </>
            ) : (
              <button
                type="button"
                className="stimul-copy-btn"
                onClick={beginEdit}
              >
                Изменить
              </button>
            )}
            {editing ? null : (
            <button
              type="button"
              className={`stimul-copy-btn${copied ? " is-ok" : ""}`}
              onClick={() => void copyMarkdown()}
            >
              {copied ? "Скопировано" : "Копировать"}
            </button>
            )}
            {downloadTarget.kind === "url" ? (
              <a
                className="stimul-download-btn"
                href={downloadTarget.href}
                download={downloadTarget.fileName || true}
              >
                Скачать оригинал
              </a>
            ) : (
              <button
                type="button"
                className="stimul-download-btn"
                onClick={downloadBlobFallback}
              >
                Скачать оригинал
              </button>
            )}
            <button
              type="button"
              className="settings-modal-x"
              onClick={onClose}
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
        </header>
        <div className="settings-modal-body source-read-body">
          {docs.length > 1 ? (
            <nav className="dash-read-nav" aria-label="Прикреплённые документы">
              {docs.map((doc, idx) => (
                <button
                  key={`${doc.fileName || doc.title}-${idx}`}
                  type="button"
                  className={idx === safeIdx ? "is-active" : undefined}
                  onClick={() => {
                    setActiveIdx(idx);
                    setCopied(false);
                    setEditing(false);
                  }}
                >
                  {doc.fileName || doc.title}
                </button>
              ))}
            </nav>
          ) : null}
          {editing ? (
            <textarea
              ref={editorRef}
              className="source-read-editor"
              aria-label="Текст документа"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              spellCheck
            />
          ) : activeDoc.text?.trim() ? (
            <div
              className="msg-body msg-md source-read-md"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          ) : (
            <p className="stimul-read-text">В документе нет текста для предпросмотра.</p>
          )}
        </div>
      </div>
    </div>
  );
}
