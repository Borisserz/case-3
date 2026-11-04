/** Presentation print downloads (PPTX + deck PDF) for rail header. */

export type DeckDownloadKind = "pptx" | "deck_pdf";

export type DeckDownloadLink = {
  kind: DeckDownloadKind;
  href: string;
  label: string;
  stale?: boolean;
  title?: string;
};

export function deckDownloadLinks(
  downloads?: Record<string, string> | null,
  opts?: { stale?: boolean },
): DeckDownloadLink[] {
  if (!downloads) return [];
  const stale = Boolean(opts?.stale);
  const title = stale
    ? "Устарели — нажмите Готово, чтобы обновить"
    : undefined;
  const out: DeckDownloadLink[] = [];
  if (downloads.pptx) {
    out.push({
      kind: "pptx",
      href: downloads.pptx,
      label: stale ? "PPTX · устарел" : "PPTX",
      stale,
      title,
    });
  }
  if (downloads.deck_pdf) {
    out.push({
      kind: "deck_pdf",
      href: downloads.deck_pdf,
      label: stale ? "PDF · устарел" : "PDF",
      stale,
      title,
    });
  }
  return out;
}
