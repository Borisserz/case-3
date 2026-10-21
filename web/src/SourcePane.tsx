/** Source / intent viewer: light markdown, search, copy. */

import { useMemo, useState } from "react";
import { renderLightMd } from "./lightMd";

type Props = {
  title: string;
  text: string;
  fileName?: string;
};

export function SourcePane({ title, text, fileName }: Props) {
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
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
    const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"));
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

  return (
    <div className="artifact-source">
      <div className="artifact-source-toolbar">
        <h2 className="artifact-source-title">{title}</h2>
        <div className="artifact-source-tools">
          <label className="artifact-source-search">
            <span className="sr-only">Поиск</span>
            <input
              type="search"
              placeholder="Найти…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <button
            type="button"
            className={`artifact-source-copy${copied ? " is-ok" : ""}`}
            onClick={() => void copyAll()}
          >
            {copied ? "Скопировано" : "Копировать"}
          </button>
        </div>
      </div>
      {html ? (
        <div
          className="artifact-source-md"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <pre className="artifact-source-pre">
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
            : text || "Нет текста источника."}
        </pre>
      )}
    </div>
  );
}
