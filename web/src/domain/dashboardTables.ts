/** Turn dashboard markdown into headings and real tables. Numbers stay as printed. */

export type DashboardBlock =
  | { kind: "heading"; text: string }
  | { kind: "text"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "table"; header: string[]; rows: string[][]; numeric: boolean[] };

const MACHINE_LINE =
  /^(?:# Данные дашборда|Числа скопированы из ячеек PDF\.|Числа в разделе «Таблица PDF».*|Текст ниже — чтение снимка\..*|Раздел «Экран» — подписи.*)$/;

const NUMBER_CELL = /^[+\-−]?\d[\d\s\u00a0]*(?:[.,]\d+)?%?$/;

function splitRow(line: string): string[] {
  const body = line.trim().replace(/^\|/, "").replace(/\|$/, "");
  const cells: string[] = [];
  let current = "";
  for (let index = 0; index < body.length; index += 1) {
    const char = body[index];
    if (char === "\\" && body[index + 1] === "|") {
      current += "|";
      index += 1;
      continue;
    }
    if (char === "|") {
      cells.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current.trim());
  return cells;
}

function isTableRow(line: string): boolean {
  return /^\s*\|.+\|\s*$/.test(line);
}

function isSeparator(line: string): boolean {
  return /^\s*\|[\s:|-]+\|\s*$/.test(line) && line.includes("-");
}

const BULLET = /^\s*(?:[-*•]|\d+\.)\s+(.+)$/;
const BOLD_TITLE = /^\s*\*\*[^*]+\*\*\s*$/;
const RULE = /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/;

/** Qwen writes **bold** and * bullets. The window shows the words, not the marks. */
export function stripInline(value: string): string {
  return value
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/(^|[\s(])\*([^*\n]+?)\*(?=[\s).,;:]|$)/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function numericColumns(header: string[], rows: string[][]): boolean[] {
  return header.map((_, column) => {
    if (column === 0) return false;
    let filled = 0;
    let numeric = 0;
    for (const row of rows) {
      const cell = (row[column] || "").trim();
      if (!cell) continue;
      filled += 1;
      if (NUMBER_CELL.test(cell)) numeric += 1;
    }
    return filled > 0 && numeric / filled >= 0.6;
  });
}

export function splitDashboardBlocks(markdown: string): DashboardBlock[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: DashboardBlock[] = [];
  const prose: string[] = [];

  function flushProse() {
    const lines = prose.splice(0);
    let list: string[] = [];
    let text: string[] = [];
    function flushList() {
      if (!list.length) return;
      blocks.push({ kind: "list", items: list });
      list = [];
    }
    function flushText() {
      const joined = text.join("\n").trim();
      text = [];
      if (joined) blocks.push({ kind: "text", text: joined });
    }
    for (const raw of lines) {
      const line = raw.trim();
      if (!line || RULE.test(line) || MACHINE_LINE.test(line)) continue;
      if (BOLD_TITLE.test(line)) {
        flushList();
        flushText();
        blocks.push({ kind: "heading", text: stripInline(line) });
        continue;
      }
      const heading = /^(#{1,3})\s+(.+)$/.exec(line);
      if (heading) {
        flushList();
        flushText();
        blocks.push({ kind: "heading", text: stripInline(heading[2]) });
        continue;
      }
      const bullet = BULLET.exec(line);
      if (bullet) {
        flushText();
        const item = stripInline(bullet[1]);
        if (item) list.push(item);
        continue;
      }
      flushList();
      const plain = stripInline(line);
      if (plain) text.push(plain);
    }
    flushList();
    flushText();
  }

  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (
      isTableRow(line) &&
      index + 1 < lines.length &&
      isSeparator(lines[index + 1])
    ) {
      flushProse();
      const header = splitRow(line).map(stripInline);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && isTableRow(lines[index])) {
        const cells = splitRow(lines[index]).map(stripInline);
        while (cells.length < header.length) cells.push("");
        rows.push(cells.slice(0, header.length));
        index += 1;
      }
      if (header.length > 0) {
        blocks.push({
          kind: "table",
          header,
          rows,
          numeric: numericColumns(header, rows),
        });
      }
      continue;
    }
    prose.push(line);
    index += 1;
  }
  flushProse();
  return blocks;
}
