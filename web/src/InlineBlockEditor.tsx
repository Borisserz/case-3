/** Compact inline editor for one active preview prose / heading / list block. */

import { useEffect, useRef, useState } from "react";

type Common = {
  busy?: boolean;
  error?: string | null;
  saveLabel?: string;
  onCancel?: () => void;
  autoFocus?: boolean;
};

type ProseProps = Common & {
  kind: "paragraph" | "heading";
  initialText: string;
  rows?: number;
  onSave: (text: string) => void;
};

type ListProps = Common & {
  kind: "list";
  initialItems: string[];
  ordered?: boolean;
  onSave: (items: string[]) => void;
};

export type InlineBlockEditorProps = ProseProps | ListProps;

export function InlineBlockEditor(props: InlineBlockEditorProps) {
  if (props.kind === "list") {
    return <ListInline {...props} />;
  }
  return <ProseInline {...props} />;
}

function ProseInline({
  kind,
  initialText,
  rows = kind === "heading" ? 1 : 5,
  busy,
  error,
  saveLabel = "Сохранить",
  onSave,
  onCancel,
  autoFocus = true,
}: ProseProps) {
  const [text, setText] = useState(initialText);
  const headingRef = useRef<HTMLInputElement | null>(null);
  const paraRef = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => {
    setText(initialText);
  }, [initialText]);
  useEffect(() => {
    if (!autoFocus) return;
    const el = kind === "heading" ? headingRef.current : paraRef.current;
    el?.focus({ preventScroll: true });
  }, [autoFocus, kind]);
  const dirty = text.trim() !== (initialText || "").trim();
  return (
    <div className={`inline-block-editor is-${kind}${busy ? " is-busy" : ""}`}>
      {kind === "heading" ? (
        <input
          ref={headingRef}
          className="inline-block-input is-heading"
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              e.stopPropagation();
              setText(initialText);
              onCancel?.();
              return;
            }
            if (e.key === "Enter" && dirty && !busy) {
              e.preventDefault();
              const t = text.trim();
              if (t) onSave(t);
            }
          }}
        />
      ) : (
        <textarea
          ref={paraRef}
          className="inline-block-input is-paragraph"
          rows={rows}
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              e.stopPropagation();
              setText(initialText);
              onCancel?.();
              return;
            }
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && dirty && !busy) {
              e.preventDefault();
              const t = text.trim();
              if (t) onSave(t);
            }
          }}
        />
      )}
      <div className="inline-block-actions">
        <button
          type="button"
          className="inline-block-save"
          disabled={busy || !dirty || !text.trim()}
          onClick={() => {
            const t = text.trim();
            if (t) onSave(t);
          }}
        >
          {busy ? "Сохраняю…" : saveLabel}
        </button>
        <button
          type="button"
          className="inline-block-cancel"
          disabled={busy}
          onClick={() => {
            setText(initialText);
            onCancel?.();
          }}
        >
          Отмена
        </button>
        {kind === "paragraph" ? (
          <span className="inline-block-hint">⌘↵ · Esc</span>
        ) : (
          <span className="inline-block-hint">Enter · Esc</span>
        )}
      </div>
      {error ? <p className="err">{error}</p> : null}
    </div>
  );
}

function ListInline({
  initialItems,
  ordered,
  busy,
  error,
  saveLabel = "Сохранить",
  onSave,
  onCancel,
  autoFocus = true,
}: ListProps) {
  const seed = (initialItems || []).join("\n");
  const [text, setText] = useState(seed);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => {
    setText((initialItems || []).join("\n"));
  }, [initialItems]);
  useEffect(() => {
    if (!autoFocus) return;
    areaRef.current?.focus({ preventScroll: true });
  }, [autoFocus]);
  const items = text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const dirty = text.replace(/\s+$/, "") !== seed.replace(/\s+$/, "");
  return (
    <div className={`inline-block-editor is-list${busy ? " is-busy" : ""}`}>
      <p className="inline-block-eyebrow">
        {ordered ? "Нумерованный список" : "Маркированный список"} · один пункт =
        строка
      </p>
      <textarea
        ref={areaRef}
        className="inline-block-input is-list"
        rows={Math.max(3, items.length + 1)}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            setText(seed);
            onCancel?.();
            return;
          }
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && dirty && !busy) {
            e.preventDefault();
            if (items.length) onSave(items);
          }
        }}
      />
      <div className="inline-block-actions">
        <button
          type="button"
          className="inline-block-save"
          disabled={busy || !dirty || items.length < 1}
          onClick={() => {
            if (items.length) onSave(items);
          }}
        >
          {busy ? "Сохраняю…" : saveLabel}
        </button>
        <button
          type="button"
          className="inline-block-cancel"
          disabled={busy}
          onClick={() => {
            setText(seed);
            onCancel?.();
          }}
        >
          Отмена
        </button>
        <span className="inline-block-hint">⌘↵ · Esc</span>
      </div>
      {error ? <p className="err">{error}</p> : null}
    </div>
  );
}
