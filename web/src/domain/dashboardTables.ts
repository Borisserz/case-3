/** Turn dashboard markdown into headings and real tables. Numbers stay as printed. */

export type DashboardBlock =
  | { kind: "heading"; text: string }
  | { kind: "text"; text: string }
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
    const text = prose.join("\n").trim();
    prose.length = 0;
    if (!text) return;
    for (const paragraph of text.split(/\n{2,}/)) {
      const clean = paragraph.trim();
      if (!clean || MACHINE_LINE.test(clean)) continue;
      const heading = /^(#{1,3}) (.+)$/.exec(clean);
      if (heading && !clean.includes("\n")) {
        blocks.push({ kind: "heading", text: heading[2].trim() });
        continue;
      }
      const kept = clean
        .split("\n")
        .filter((line) => !MACHINE_LINE.test(line.trim()))
        .join("\n")
        .trim();
      if (kept) blocks.push({ kind: "text", text: kept });
    }
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
      const header = splitRow(line);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && isTableRow(lines[index])) {
        const cells = splitRow(lines[index]);
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
