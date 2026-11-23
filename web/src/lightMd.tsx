/** Safe-ish markdown → HTML (escape first). Shared by Source + chat summary. */

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Light markdown for Liber chat / Source pane. */
function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableRow(line: string): boolean {
  return /^\s*\|.+\|\s*$/.test(line);
}

function isTableSep(line: string): boolean {
  return /^\s*\|[\s:|-]+\|\s*$/.test(line) && line.includes("-");
}

function renderTables(src: string): string {
  const lines = src.split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    if (
      isTableRow(lines[i]) &&
      i + 1 < lines.length &&
      isTableSep(lines[i + 1])
    ) {
      const head = splitTableRow(lines[i]);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      const th = head.map((cell) => `<th>${cell}</th>`).join("");
      const body = rows
        .map((row) => {
          const cells = head.map((_, idx) => `<td>${row[idx] || ""}</td>`).join("");
          return `<tr>${cells}</tr>`;
        })
        .join("");
      out.push(
        `<table class="msg-table"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table>`,
      );
      continue;
    }
    out.push(lines[i]);
    i += 1;
  }
  return out.join("\n");
}

/** A "2. Вывод" glued to the previous sentence becomes its own paragraph. */
export function spaceAnswer(raw: string): string {
  let text = (raw || "").replace(/\r\n/g, "\n");
  text = text.replace(
    /([.!?…:%»"])[ \t]+(\d{1,2})\.\s+(?=\p{L})/gu,
    "$1\n\n$2. ",
  );
  text = text.replace(/([^\n])\n(?=\d{1,2}\.\s+\p{L})/gu, "$1\n\n");
  return text;
}

export function renderLightMd(raw: string, query = ""): string {
  let s = escapeHtml(spaceAnswer(raw));
  s = s.replace(/```([\s\S]*?)```/g, (_m, code: string) => {
    return `<pre class="src-code"><code>${code.trim()}</code></pre>`;
  });
  s = s.replace(/^### (.+)$/gm, '<h4 class="src-h">$1</h4>');
  s = s.replace(/^## (.+)$/gm, '<h3 class="src-h">$1</h3>');
  s = s.replace(/^# (.+)$/gm, '<h2 class="src-h">$1</h2>');
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/_([^_\n]+)_/g, "<em>$1</em>");
  s = renderTables(s);
  s = s.replace(/^- (.+)$/gm, '<li class="src-li">$1</li>');
  s = s.replace(/(?:<li class="src-li">.*<\/li>\n?)+/g, (block) => {
    return `<ul class="src-ul">${block}</ul>`;
  });
  s = s
    .split(/\n{2,}/)
    .map((chunk) => {
      if (/^<(h[2-4]|ul|pre|table)/.test(chunk.trim())) return chunk;
      if (chunk.includes("<table")) {
        return chunk
          .split(/(<table[\s\S]*?<\/table>)/)
          .map((part) => {
            if (part.startsWith("<table")) return part;
            const trimmed = part.trim();
            if (!trimmed) return "";
            if (/^<(h[2-4]|ul|pre)/.test(trimmed)) return part;
            return `<p class="src-p">${part.replace(/\n/g, "<br/>")}</p>`;
          })
          .join("");
      }
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

export function MsgMarkdown({
  text,
  streaming = false,
  className = "",
}: {
  text: string;
  streaming?: boolean;
  className?: string;
}) {
  const html = renderLightMd(text || "");
  return (
    <div
      className={`msg-body msg-md${streaming ? " is-streaming" : ""}${className ? ` ${className}` : ""}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
