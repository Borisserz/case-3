/** Source / intent viewer: light markdown, search, copy. */

import { useMemo, useState } from "react";

type Props = {
  title: string;
  text: string;
  fileName?: string;
};

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Safe-ish markdown → HTML (escaped first). */
function renderLightMd(raw: string, query: string): string {
  let s = escapeHtml(raw);
  // fenced code
  s = s.replace(/```([\s\S]*?)```/g, (_m, code: string) => {
    return `<pre class="src-code"><code>${code.trim()}</code></pre>`;
  });
  // headings
  s = s.replace(/^### (.+)$/gm, '<h4 class="src-h">$1</h4>');
  s = s.replace(/^## (.+)$/gm, '<h3 class="src-h">$1</h3>');
  s = s.replace(/^# (.+)$/gm, '<h2 class="src-h">$1</h2>');
  // bold / italic
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/_([^_\n]+)_/g, "<em>$1</em>");
  // lists
  s = s.replace(/^- (.+)$/gm, '<li class="src-li">$1</li>');
  s = s.replace(/(?:<li class="src-li">.*<\/li>\n?)+/g, (block) => {
    return `<ul class="src-ul">${block}</ul>`;
  });
  // paragraphs: blank lines
  s = s
    .split(/\n{2,}/)
    .map((chunk) => {
      if (/^<(h[2-4]|ul|pre)/.test(chunk.trim())) return chunk;
      return `<p class="src-p">${chunk.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("");

  if (query.trim()) {
    const q = escapeHtml(query.trim());
    const re = new RegExp(
      `(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );
    s = s.replace(re, '<mark class="src-hit">$1</mark>');
  }
  return s;
}

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
