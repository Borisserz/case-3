/** Source / intent viewer: light markdown, search, copy; draft click-to-edit. */

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import {
  enterSourceEdit,
  exitSourceEditOnBlur,
  exitSourceEditOnKey,
  type SourceViewMode,
} from "./domain/sourceDraftEdit";
import { renderLightMd } from "./lightMd";

type Props = {
  title: string;
  text: string;
  fileName?: string;
  /** Pre-run sourceDraft only — enables click-to-edit. */
  editable?: boolean;
  onTextChange?: (text: string) => void;
};

export function SourcePane({
  title,
  text,
  fileName,
  editable = false,
  onTextChange,
}: Props) {
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const [mode, setMode] = useState<SourceViewMode>("preview");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const editing = editable && mode === "editing";

  useEffect(() => {
    if (!editable && mode === "editing") setMode("preview");
  }, [editable, mode]);

  useEffect(() => {
    if (!editing) return;
    const el = textareaRef.current;
    if (!el) return;
    el.focus();
    const len = el.value.length;
    el.setSelectionRange(len, len);
  }, [editing]);

  const looksMd =
    /\.(md|markdown)$/i.test(fileName || title) ||
    /^#{1,3}\s|```|\*\*/m.test(text);

  const html = useMemo(
    () => (looksMd ? renderLightMd(text, query) : null),
    [looksMd, text, query],
  );

  const plainHighlight = useMemo(() => {
    if (looksMd || !query.trim()) return null;
    const q = query.trim();
    const parts = text.split(
      new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"),
    );
    return parts;
  }, [looksMd, text, query]);

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  }

  function startEdit() {
    setMode(enterSourceEdit(editable, mode));
  }

  function onEditorKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    const next = exitSourceEditOnKey(e.key, mode);
    if (next !== mode) {
      e.preventDefault();
      e.stopPropagation();
      setMode(next);
    }
  }

  function onEditorBlur() {
    setMode(exitSourceEditOnBlur(mode));
  }

  const emptyLabel = "Нет текста источника.";
  const bodyText = text || "";

  return (
    <div className={`artifact-source${editing ? " is-editing" : ""}`}>
      <div className="artifact-source-toolbar">
        <h2 className="artifact-source-title">{title}</h2>
        <div className="artifact-source-tools">
          {!editing ? (
            <label className="artifact-source-search">
              <span className="sr-only">Поиск</span>
              <input
                type="search"
                placeholder="Найти…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          ) : (
            <span className="artifact-source-edit-hint muted">
              Esc — готово
            </span>
          )}
          <button
            type="button"
            className={`artifact-source-copy${copied ? " is-ok" : ""}`}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => void copyAll()}
          >
            {copied ? "Скопировано" : "Копировать"}
          </button>
        </div>
      </div>

      {editing ? (
        <textarea
          ref={textareaRef}
          className="artifact-source-editor"
          value={bodyText}
          aria-label="Редактировать Source"
          onChange={(e) => onTextChange?.(e.target.value)}
          onKeyDown={onEditorKeyDown}
          onBlur={onEditorBlur}
          spellCheck={false}
        />
      ) : html ? (
        <div
          className={`artifact-source-md${editable ? " is-editable" : ""}`}
          role={editable ? "button" : undefined}
          tabIndex={editable ? 0 : undefined}
          onClick={editable ? startEdit : undefined}
          onKeyDown={
            editable
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    startEdit();
                  }
                }
              : undefined
          }
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <pre
          className={`artifact-source-pre${editable ? " is-editable" : ""}`}
          role={editable ? "button" : undefined}
          tabIndex={editable ? 0 : undefined}
          onClick={editable ? startEdit : undefined}
          onKeyDown={
            editable
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    startEdit();
                  }
                }
              : undefined
          }
        >
          {plainHighlight
            ? plainHighlight.map((part, i) =>
                part.toLowerCase() === query.trim().toLowerCase() ? (
                  <mark key={i} className="src-hit">
                    {part}
                  </mark>
                ) : (
                  <span key={i}>{part}</span>
                ),
              )
            : bodyText || emptyLabel}
        </pre>
      )}
    </div>
  );
}
