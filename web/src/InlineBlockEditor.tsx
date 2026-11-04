/** Compact inline editor for one active preview prose / heading / list block. */

import { useEffect, useRef, useState } from "react";

type Common = {
  busy?: boolean;
  error?: string | null;
  saveLabel?: string;
  onCancel?: () => void;
  autoFocus?: boolean;
  /** Hide Save/Cancel row — blur / Enter / ⌘↵ still apply. */
  hideActions?: boolean;
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
  hideActions = false,
}: ProseProps) {
  const [text, setText] = useState(initialText);
  const headingRef = useRef<HTMLInputElement | null>(null);
  const paraRef = useRef<HTMLTextAreaElement | null>(null);
  const skipBlurRef = useRef(false);
  useEffect(() => {
    setText(initialText);
  }, [initialText]);
  useEffect(() => {
    if (!autoFocus) return;
    const el = kind === "heading" ? headingRef.current : paraRef.current;
    el?.focus({ preventScroll: true });
  }, [autoFocus, kind]);

  const dirty = text.trim() !== (initialText || "").trim();

  const commit = () => {
    const t = text.trim();
    if (!t || !dirty || busy) return;
    skipBlurRef.current = true;
    onSave(t);
  };

  const discard = () => {
    skipBlurRef.current = true;
    setText(initialText);
    onCancel?.();
  };

  const onBlurCommit = () => {
    if (skipBlurRef.current) {
      skipBlurRef.current = false;
      return;
    }
    if (dirty && !busy && text.trim()) commit();
    else if (!busy) onCancel?.();
  };

  return (
    <div className={`inline-block-editor is-${kind}${busy ? " is-busy" : ""}`}>
      {kind === "heading" ? (
        <input
          ref={headingRef}
          className="inline-block-input is-heading"
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onBlur={onBlurCommit}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              e.stopPropagation();
              discard();
              return;
            }
            if (e.key === "Enter" && dirty && !busy) {
              e.preventDefault();
              commit();
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
          onBlur={onBlurCommit}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              e.stopPropagation();
              discard();
              return;
            }
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && dirty && !busy) {
              e.preventDefault();
              commit();
            }
          }}
        />
      )}
      {hideActions ? (
        <p className="inline-block-hint is-solo">
          {kind === "paragraph" ? "⌘↵ · Esc · blur" : "Enter · Esc · blur"}
        </p>
      ) : (
        <div className="inline-block-actions">
          <button
            type="button"
            className="inline-block-save"
            disabled={busy || !dirty || !text.trim()}
            onMouseDown={() => {
              skipBlurRef.current = true;
            }}
            onClick={commit}
          >
            {busy ? "Сохраняю…" : saveLabel}
          </button>
          <button
            type="button"
            className="inline-block-cancel"
            disabled={busy}
            onMouseDown={() => {
              skipBlurRef.current = true;
            }}
            onClick={discard}
          >
            Отмена
          </button>
          {kind === "paragraph" ? (
            <span className="inline-block-hint">⌘↵ · Esc</span>
          ) : (
            <span className="inline-block-hint">Enter · Esc</span>
          )}
        </div>
      )}
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
  hideActions = false,
}: ListProps) {
  const seed = (initialItems || []).join("\n");
  const [text, setText] = useState(seed);
  const areaRef = useRef<HTMLTextAreaElement | null>(null);
  const skipBlurRef = useRef(false);
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

  const commit = () => {
    if (!items.length || !dirty || busy) return;
    skipBlurRef.current = true;
    onSave(items);
  };

  const discard = () => {
    skipBlurRef.current = true;
    setText(seed);
    onCancel?.();
  };

  const onBlurCommit = () => {
    if (skipBlurRef.current) {
      skipBlurRef.current = false;
      return;
    }
    if (dirty && !busy && items.length) commit();
    else if (!busy) onCancel?.();
  };

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
        onBlur={onBlurCommit}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
            discard();
            return;
          }
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && dirty && !busy) {
            e.preventDefault();
            commit();
          }
        }}
      />
      {hideActions ? (
        <p className="inline-block-hint is-solo">⌘↵ · Esc · blur</p>
      ) : (
        <div className="inline-block-actions">
          <button
            type="button"
            className="inline-block-save"
            disabled={busy || !dirty || items.length < 1}
            onMouseDown={() => {
              skipBlurRef.current = true;
            }}
            onClick={commit}
          >
            {busy ? "Сохраняю…" : saveLabel}
          </button>
          <button
            type="button"
            className="inline-block-cancel"
            disabled={busy}
            onMouseDown={() => {
              skipBlurRef.current = true;
            }}
            onClick={discard}
          >
            Отмена
          </button>
          <span className="inline-block-hint">⌘↵ · Esc</span>
        </div>
      )}
      {error ? <p className="err">{error}</p> : null}
    </div>
  );
}
