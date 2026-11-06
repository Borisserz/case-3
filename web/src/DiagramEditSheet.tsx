/** Edit Mermaid source with live preview — Apply persists via API. */

import { useEffect, useMemo, useRef, useState } from "react";
import { MermaidView } from "./MermaidView";
import { useFocusTrap } from "./useFocusTrap";

type Props = {
  open: boolean;
  title: string;
  mermaid: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onApply: (mermaid: string, title: string) => void;
};

type Snippet = { label: string; insert: string; hint: string };

function getSnippetsForSource(src: string): Snippet[] {
  const trimmed = src.trim();
  if (/^sequenceDiagram\b/i.test(trimmed)) {
    return [
      { label: "+ Запрос ->>", insert: "    Alice->>Bob: Запрос", hint: "Стрелка вызова с текстом" },
      { label: "+ Ответ -->>", insert: "    Bob-->>Alice: Ответ", hint: "Пунктирная стрелка ответа" },
      { label: "+ Участник", insert: "    participant U as Пользователь", hint: "Объявление участника" },
      { label: "+ Заметка", insert: "    Note over Alice,Bob: Согласование", hint: "Поясняющая плашка" },
      { label: "+ Блок loop", insert: "    loop Повтор\n        Alice->>Bob: Ping\n    end", hint: "Циклическое действие" },
    ];
  }
  if (/^mindmap\b/i.test(trimmed)) {
    return [
      { label: "+ Корень (( ))", insert: "  root((Главная мысль))", hint: "Центральный узел карты" },
      { label: "+ Ветка", insert: "    Ветка", hint: "Направление 1-го уровня" },
      { label: "+ Подтема [ ]", insert: "      node[Деталь]", hint: "Прямоугольный блок" },
      { label: "+ Круг ( )", insert: "      sub((Пункт))", hint: "Круглый узел" },
      { label: "+ Иконка", insert: "      ::icon(fa fa-check)", hint: "Иконка FontAwesome" },
    ];
  }
  if (/^timeline\b/i.test(trimmed)) {
    return [
      { label: "+ Раздел", insert: "    section 2026 Q1", hint: "Период времени" },
      { label: "+ Этап", insert: "    Этап 1 : Задача A : Задача B", hint: "События этапа" },
    ];
  }
  return [
    { label: "+ Блок [ ]", insert: "  Block[Текст блока]", hint: "Прямоугольный узел" },
    { label: "+ Процесс ([ ])", insert: "  Step([Процесс])", hint: "Округлый процесс" },
    { label: "+ Решение { }", insert: "  Check{Условие?}", hint: "Ромб условия" },
    { label: "+ Стрелка -->", insert: "  A -->|Да| B", hint: "Связь с условием" },
    { label: "+ Пунктир -.->", insert: "  A -.-> B", hint: "Слабая связь" },
  ];
}

export function DiagramEditSheet({
  open,
  title: initialTitle,
  mermaid: initialMermaid,
  busy,
  error,
  onCancel,
  onApply,
}: Props) {
  const [title, setTitle] = useState(initialTitle);
  const [src, setSrc] = useState(initialMermaid);
  const [syntaxErr, setSyntaxErr] = useState<string | null>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useFocusTrap(sheetRef, { active: open });

  useEffect(() => {
    if (!open) return;
    setTitle(initialTitle);
    setSrc(initialMermaid);
    setSyntaxErr(null);
  }, [open, initialTitle, initialMermaid]);

  const snippets = useMemo(() => getSnippetsForSource(src), [src]);

  const insertSnippet = (snippet: string) => {
    const ta = textareaRef.current;
    if (!ta) {
      setSrc((prev) => (prev.endsWith("\n") || !prev ? prev : prev + "\n") + snippet + "\n");
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const before = src.slice(0, start);
    const after = src.slice(end);
    const needsPrefixNl = before.length > 0 && !before.endsWith("\n");
    const insertText = (needsPrefixNl ? "\n" : "") + snippet + "\n";
    const next = before + insertText + after;
    setSrc(next);
    setTimeout(() => {
      ta.focus();
      const pos = start + insertText.length;
      ta.setSelectionRange(pos, pos);
    }, 0);
  };

  if (!open) return null;

  return (
    <div className="diagram-edit-backdrop" role="presentation" onClick={onCancel}>
      <div
        ref={sheetRef}
        className="diagram-edit-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Редактировать схему"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="diagram-edit-head">
          <h3 className="diagram-edit-title">Правка Mermaid</h3>
          <button
            type="button"
            className="diagram-edit-close"
            aria-label="Закрыть"
            onClick={onCancel}
          >
            ×
          </button>
        </header>

        <label className="diagram-edit-field">
          <span>Заголовок</span>
          <input
            type="text"
            value={title}
            maxLength={80}
            onChange={(e) => setTitle(e.target.value)}
            disabled={busy}
          />
        </label>

        <div className="diagram-edit-field">
          <div className="diagram-edit-snippets-bar">
            <span className="diagram-edit-snippets-label">Быстрые вставки:</span>
            <div className="chips">
              {snippets.map((snip) => (
                <button
                  key={snip.label}
                  type="button"
                  className="btn ghost chip-btn"
                  title={snip.hint}
                  onClick={() => insertSnippet(snip.insert)}
                  disabled={busy}
                >
                  {snip.label}
                </button>
              ))}
            </div>
          </div>
          <textarea
            ref={textareaRef}
            value={src}
            onChange={(e) => setSrc(e.target.value)}
            rows={12}
            spellCheck={false}
            disabled={busy}
          />
        </div>

        <div className="diagram-edit-status-row">
          {syntaxErr ? (
            <span className="diagram-edit-status is-err" role="alert" title={syntaxErr}>
              <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor" aria-hidden>
                <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 3.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4.5zm0 7a.875.875 0 1 1 0-1.75.875.875 0 0 1 0 1.75z" />
              </svg>
              {syntaxErr.length > 70 ? syntaxErr.slice(0, 70) + "…" : syntaxErr}
            </span>
          ) : (
            <span className="diagram-edit-status is-ok">
              <svg viewBox="0 0 16 16" width="12" height="12" fill="currentColor" aria-hidden>
                <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0z" />
              </svg>
              Синтаксис корректен
            </span>
          )}
        </div>

        <div className="diagram-edit-preview" aria-label="Превью">
          <MermaidView
            source={src}
            className="is-edit-preview"
            onError={setSyntaxErr}
          />
        </div>

        {error ? (
          <p className="diagram-edit-err" role="alert">
            {error}
          </p>
        ) : null}

        <footer className="diagram-edit-actions">
          <button type="button" className="btn ghost" onClick={onCancel} disabled={busy}>
            Отмена
          </button>
          <button
            type="button"
            className="btn primary diagram-pane-png"
            disabled={busy || !src.trim() || Boolean(syntaxErr)}
            title={syntaxErr ? "Исправьте ошибку в коде Mermaid перед применением" : undefined}
            onClick={() => onApply(src, title)}
          >
            {busy ? "…" : "Применить"}
          </button>
        </footer>
      </div>
    </div>
  );
}
