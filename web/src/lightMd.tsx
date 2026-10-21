/** Safe-ish markdown → HTML (escape first). Shared by Source + chat summary. */

export function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Light markdown for Liber chat / Source pane. */
export function renderLightMd(raw: string, query = ""): string {
  let s = escapeHtml(raw);
  s = s.replace(/```([\s\S]*?)```/g, (_m, code: string) => {
    return `<pre class="src-code"><code>${code.trim()}</code></pre>`;
  });
  s = s.replace(/^### (.+)$/gm, '<h4 class="src-h">$1</h4>');
  s = s.replace(/^## (.+)$/gm, '<h3 class="src-h">$1</h3>');
  s = s.replace(/^# (.+)$/gm, '<h2 class="src-h">$1</h2>');
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/_([^_\n]+)_/g, "<em>$1</em>");
  s = s.replace(/^- (.+)$/gm, '<li class="src-li">$1</li>');
  s = s.replace(/(?:<li class="src-li">.*<\/li>\n?)+/g, (block) => {
    return `<ul class="src-ul">${block}</ul>`;
  });
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
