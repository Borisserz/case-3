/** Normalize PDF caption / figure label into search needles (longest first). */

export function pdfSearchNeedles(
  caption?: string | null,
  figureId?: string | null,
): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    const t = s.replace(/\s+/g, " ").trim();
    if (t.length < 3 || seen.has(t.toLowerCase())) return;
    seen.add(t.toLowerCase());
    out.push(t);
  };

  const cap = (caption || "").trim();
  if (cap) {
    push(cap);
    // "Рис. 2: Foo" / "Илл. 1: Foo" → also try "Foo"
    const bare = cap.replace(
      /^(Рис\.|Илл\.|Fig\.|Figure)\s*\d+\s*[:.\-—–]?\s*/i,
      "",
    );
    if (bare && bare !== cap) push(bare);
  }
  if (figureId) push(figureId);
  return out;
}

function normPdfText(s: string): string {
  return s.toLowerCase().replace(/\s+/g, " ").trim();
}

/** True if page text contains any needle (space-insensitive fallback). */
export function pageTextMatchesNeedle(pageText: string, needle: string): boolean {
  const hay = normPdfText(pageText);
  const n = normPdfText(needle);
  if (!n || n.length < 3) return false;
  if (hay.includes(n)) return true;
  // pdf.js often splits "Рис. 2" → try compact form
  const hayC = hay.replace(/\s/g, "");
  const nC = n.replace(/\s/g, "");
  return nC.length >= 3 && hayC.includes(nC);
}
