/** Compact inline editor for preview prose / heading / list in full edit mode. */

import { useEffect, useState } from "react";

type Common = {
  busy?: boolean;
  error?: string | null;
  saveLabel?: string;
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
}: ProseProps) {
  const [text, setText] = useState(initialText);
  useEffect(() => {
    setText(initialText);
  }, [initialText]);
  const dirty = text.trim() !== (initialText || "").trim();
  return (
    <div className={`inline-block-editor is-${kind}${busy ? " is-busy" : ""}`}>
      {kind === "heading" ? (
        <input
          className="inline-block-input is-heading"
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && dirty && !busy) {
              e.preventDefault();
              const t = text.trim();
              if (t) onSave(t);
            }
          }}
        />
      ) : (
        <textarea
          className="inline-block-input is-paragraph"
          rows={rows}
          value={text}
          disabled={busy}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
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
        {kind === "paragraph" ? (
          <span className="inline-block-hint">⌘↵ сохранить</span>
        ) : null}
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
}: ListProps) {
  const seed = (initialItems || []).join("\n");
  const [text, setText] = useState(seed);
  useEffect(() => {
    setText((initialItems || []).join("\n"));
  }, [initialItems]);
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
        className="inline-block-input is-list"
        rows={Math.max(3, items.length + 1)}
        value={text}
        disabled={busy}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
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
        <span className="inline-block-hint">⌘↵ сохранить</span>
      </div>
      {error ? <p className="err">{error}</p> : null}
    </div>
  );
}
