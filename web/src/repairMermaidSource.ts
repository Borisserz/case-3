/** Soft-repair LLM Mermaid before render (mirrors case3.diagrams.sanitize). */

const CLASS_ASSIGN =
  /^([ \t]*)class(?!Def\b)[ \t]+([A-Za-z][\w,-]*)[ \t]+(.+?)\s*$/i;
const EDGE_LABEL_SPACES = /([-=.~]{2,})\s+\|([^|]+)\|\s+/g;

function repairClassAssignLines(src: string): string {
  return src
    .split("\n")
    .flatMap((line) => {
      const m = CLASS_ASSIGN.exec(line);
      if (!m) return [line];
      const indent = m[1] ?? "";
      const nodes = (m[2] ?? "")
        .split(",")
        .map((n) => n.trim())
        .filter(Boolean);
      const names = (m[3] ?? "").trim().split(/\s+/).filter(Boolean);
      if (names.length <= 1) return [line];
      if (
        names.length === nodes.length &&
        names.every((n) => /^[A-Za-z][\w-]*$/.test(n))
      ) {
        return nodes.map((node, i) => `${indent}class ${node} ${names[i]}`);
      }
      // Unmappable — drop (:::role / classDef may still style).
      return [];
    })
    .join("\n");
}

/** Repair broken `class A,B foo bar` lines + edge-label spaces for live Mermaid. */
export function repairMermaidSource(source: string): string {
  let raw = (source || "").trim();
  if (!raw) return raw;
  raw = repairClassAssignLines(raw);
  raw = raw.replace(EDGE_LABEL_SPACES, "$1|$2| ");
  return raw;
}
