/** Live editable twin of deck IR (Julius-style; edit existing text only). */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { DeckEditToolbar } from "./DeckEditToolbar";
import { LiveChart } from "./LiveChart";
import { MermaidView } from "./MermaidView";
import { diagramLegendStrokes, officeFace } from "./deckStyle";
import type { DeckIR, DeckSlide } from "./deckTypes";

export type DeckMediaKind = "chart" | "photo" | "diagram";

type Props = {
  runId: string;
  deck: DeckIR;
  index: number;
  editing: boolean;
  saving?: boolean;
  /** Cache-bust for figures/ after regenerate. */
  mediaVersion?: number;
  openMediaId?: string | null;
  onMediaClick?: (id: string, kind: DeckMediaKind) => void;
  onDeckChange: (deck: DeckIR) => void;
  onPatch: (slides: Partial<DeckSlide> & { id: string }[]) => Promise<void>;
  /** Live chart HTML while the edit sheet is open. */
  previewHtml?: string | null;
  /** Mermaid source for dia_* so the slide shows the same scheme as the editor. */
  diagramMermaid?: string | null;
  /** Report palette for the four diagram legend dots. */
  diagramPalette?: string;
};

function panelForSlide(style: DeckIR["style"] | undefined, slideIndex: number): string {
  const panels = style?.motif?.panels;
  if (panels && panels.length > 0) {
    return panels[slideIndex % panels.length] || panels[0];
  }
  const c = style?.colors || {};
  return c.panel || c.paper || "#f0ede4";
}

function luma(hex: string): number {
  const h = (hex || "").replace("#", "");
  if (h.length !== 6) return 0;
  const ch = (c: number) => {
    const x = c / 255;
    return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
  };
  const r = ch(parseInt(h.slice(0, 2), 16));
  const g = ch(parseInt(h.slice(2, 4), 16));
  const b = ch(parseInt(h.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function cssVars(style?: DeckIR["style"], slideIndex = 0): CSSProperties {
  const c = style?.colors || {};
  const f = style?.fonts || {};
  const titleFont = officeFace(f.title || f.display, "title");
  const bodyFont = officeFace(f.body || f.fallback_pptx, "body");
  const accent = c.accent || "#4F6B14";
  const sheet = c.sheet || c.background || "#fffcf7";
  const paper = c.paper || sheet;
  const ink = c.ink || "#14161a";
  const options = [sheet, paper, ink];
  const dark = options.reduce((a, b) => (luma(a) < luma(b) ? a : b));
  const light = options.reduce((a, b) => (luma(a) > luma(b) ? a : b));
  const inkFor = (bg: string) => {
    let choice = luma(bg) >= 0.22 ? dark : light;
    if (Math.abs(luma(choice) - luma(bg)) < 0.12) choice = choice === dark ? light : dark;
    return choice;
  };
  let fieldB = options.reduce((a, b) =>
    Math.abs(luma(a) - luma(accent)) > Math.abs(luma(b) - luma(accent)) ? a : b,
  );
  if (fieldB.toUpperCase() === accent.toUpperCase()) {
    fieldB = luma(accent) >= 0.22 ? dark : light;
  }
  return {
    ["--deck-primary" as string]: c.primary || "#2E4208",
    ["--deck-accent" as string]: c.accent || "#4F6B14",
    ["--deck-ink" as string]: c.ink || "#14161a",
    ["--deck-ink-2" as string]: c.ink2 || "#2c3028",
    ["--deck-muted" as string]: c.muted || "#6A7160",
    ["--deck-paper" as string]: c.paper || "#f0ede4",
    ["--deck-sheet" as string]: c.sheet || c.background || "#fffcf7",
    ["--deck-rule" as string]: c.rule || "#e6e2d8",
    ["--deck-foil" as string]: c.foil || "#b8a36a",
    ["--deck-panel" as string]: panelForSlide(style, slideIndex),
    ["--deck-on-accent" as string]: inkFor(accent),
    ["--deck-field-b" as string]: fieldB,
    ["--deck-on-field-b" as string]: inkFor(fieldB),
    ["--deck-rail" as string]: c.primary || accent,
    ["--deck-on-rail" as string]: inkFor(c.primary || accent),
    ["--deck-font-title" as string]: titleFont,
    ["--deck-font-body" as string]: bodyFont,
  };
}

type EditFocus = {
  onFocusField: (el: HTMLElement, label: string) => void;
};

const EditFocusCtx = createContext<EditFocus>({
  onFocusField: () => undefined,
});

function Editable({
  value,
  className,
  editing,
  multiline,
  label = "Текст",
  onCommit,
}: {
  value: string;
  className?: string;
  editing: boolean;
  multiline?: boolean;
  label?: string;
  onCommit: (next: string) => void;
}) {
  const { onFocusField } = useContext(EditFocusCtx);
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (document.activeElement === el) return;
    if (el.innerText !== value) el.innerText = value;
  }, [value]);

  if (!editing) {
    return <span className={className}>{value}</span>;
  }
  const Tag = multiline ? "div" : "span";
  return (
    <Tag
      ref={ref as never}
      className={`deck-ed ${className || ""}`}
      contentEditable
      suppressContentEditableWarning
      role="textbox"
      data-deck-label={label}
      onFocus={(e) => onFocusField(e.currentTarget, label)}
      onBlur={(e) => {
        const next = (e.currentTarget.innerText || "").replace(/\s+/g, " ").trim();
        if (next !== value) onCommit(next);
      }}
      onKeyDown={(e) => {
        if (!multiline && e.key === "Enter") {
          e.preventDefault();
          (e.target as HTMLElement).blur();
        }
      }}
    />
  );
}

export function mediaUrl(
  runId: string,
  id: string | undefined,
  version?: number,
): string | null {
  if (!id) return null;
  const base = `/api/runs/${encodeURIComponent(runId)}/slides/media/${encodeURIComponent(id)}.png`;
  return version ? `${base}?v=${version}` : base;
}

function mediaKind(id: string): DeckMediaKind {
  if (id.startsWith("cht_")) return "chart";
  if (id.startsWith("dia_")) return "diagram";
  return "photo";
}

function mediaLabel(kind: DeckMediaKind): string {
  if (kind === "chart") return "Изменить график";
  if (kind === "diagram") return "Изменить схему";
  return "Изменить фото";
}

function MediaSlot({
  runId,
  mediaId,
  editing,
  open,
  version,
  hero,
  onMediaClick,
  previewHtml,
  diagramMermaid,
  children,
}: {
  runId: string;
  mediaId: string | undefined;
  editing: boolean;
  open?: boolean;
  version?: number;
  hero?: boolean;
  onMediaClick?: (id: string, kind: DeckMediaKind) => void;
  previewHtml?: string | null;
  diagramMermaid?: string | null;
  children?: ReactNode;
}) {
  const img = mediaUrl(runId, mediaId, version);
  const live = Boolean(previewHtml && mediaId?.startsWith("cht_"));
  const diagram = Boolean(diagramMermaid && mediaId?.startsWith("dia_"));
  const effectiveId = mediaId || "usr_01";
  const kind = mediaKind(effectiveId);
  const clickable = Boolean(editing && onMediaClick);
  const className = `deck-cv-media${hero ? " deck-cv-media-hero" : ""}${
    clickable ? " is-editable" : ""
  }${open ? " is-open" : ""}`;
  const body = live ? (
    <div className="deck-cv-live">
      <LiveChart html={previewHtml || ""} compact />
    </div>
  ) : diagram ? (
    <div className="deck-cv-diagram-live">
      <MermaidView source={diagramMermaid || ""} className="is-slide" />
    </div>
  ) : img ? (
    <img src={img} alt="" />
  ) : (
    <div className="deck-cv-empty deck-cv-empty--clickable">
      <span className="deck-cv-empty-icon" aria-hidden>📷</span>
      <span>{editing ? "+ Добавить фото" : "Медиа"}</span>
    </div>
  );
  if (clickable) {
    return (
      <button
        type="button"
        className={className}
        aria-label={mediaLabel(kind)}
        aria-pressed={open}
        onClick={() => onMediaClick?.(effectiveId, kind)}
      >
        {body}
        <span className="deck-cv-media-hint" aria-hidden>
          {mediaId ? "Изменить" : "+ Добавить"}
        </span>
        {children}
      </button>
    );
  }
  return (
    <div className={className}>
      {body}
      {children}
    </div>
  );
}

/** Julius title-panel KPIs from takeaway (mirrors parse_hero_metrics). */
function parseHeroMetrics(takeaway: string): { value: string; label: string }[] {
  const raw = (takeaway || "").trim();
  if (!raw) return [];
  const lines = raw.split(/\n/).map((l) => l.trim()).filter(Boolean);
  if (lines.length >= 2 && lines.length % 2 === 0) {
    const out: { value: string; label: string }[] = [];
    for (let i = 0; i < lines.length; i += 2) {
      out.push({ value: lines[i], label: lines[i + 1] || "" });
    }
    return out;
  }
  const chunks = raw.replace(/\|/g, "·").split("·").map((c) => c.trim()).filter(Boolean);
  const out: { value: string; label: string }[] = [];
  for (const ch of chunks) {
    const seps = [" — ", " – ", " - ", ": "];
    let paired = false;
    for (const sep of seps) {
      if (ch.includes(sep)) {
        const [left, right] = ch.split(sep, 2);
        if (left?.trim() && right?.trim()) {
          out.push({ value: left.trim(), label: right.trim() });
          paired = true;
          break;
        }
      }
    }
    if (!paired && ch) out.push({ value: ch, label: "" });
  }
  return out.length >= 2 ? out.slice(0, 4) : [];
}

function SlideBody({
  runId,
  slide,
  brand,
  editing,
  onField,
  splitTitle,
  darkBleed,
  motifPanels,
  mediaVersion,
  openMediaId,
  onMediaClick,
  previewHtml,
  diagramMermaid,
  diagramPalette,
}: {
  runId: string;
  slide: DeckSlide;
  brand: string;
  editing: boolean;
  onField: (patch: Partial<DeckSlide>) => void;
  splitTitle?: boolean;
  darkBleed?: boolean;
  motifPanels?: string[];
  mediaVersion?: number;
  openMediaId?: string | null;
  onMediaClick?: (id: string, kind: DeckMediaKind) => void;
  previewHtml?: string | null;
  diagramMermaid?: string | null;
  diagramPalette?: string;
}) {
  const layout = slide.layout;
  const mid = slide.chart_id || slide.media_id;
  const img = mediaUrl(runId, mid, mediaVersion);
  const panels = motifPanels || [];

  if (layout === "title") {
    if (darkBleed && img) {
      return (
        <div className="deck-cv-inner deck-cv-title deck-cv-title--bleed">
          {img ? (
            <div className="deck-cv-bleed" aria-hidden>
              <img src={img} alt="" />
              <div className="deck-cv-bleed-veil" />
            </div>
          ) : null}
          {editing ? (
            <button
              type="button"
              className="deck-cv-bleed-edit-btn"
              onClick={() => onMediaClick?.(mid || "usr_01", "photo")}
              title="Изменить фото обложки"
            >
              📷 Изменить фото
            </button>
          ) : null}
          <div className="deck-cv-title-main deck-cv-title-main--bleed">
            <div className="deck-cv-brand">{brand}</div>
            {slide.kicker ? (
              <Editable
                className="deck-cv-kicker"
                value={slide.kicker}
                editing={editing}
                onCommit={(v) => onField({ kicker: v })}
              />
            ) : null}
            <Editable
              className={`deck-cv-h1 ${lenClass(slide.title || "")}`}
              value={slide.title || ""}
              editing={editing}
              multiline
              label="Заголовок"
              onCommit={(v) => onField({ title: v })}
            />
            {slide.takeaway ? (
              <Editable
                className="deck-cv-takeaway"
                value={slide.takeaway}
                editing={editing}
                multiline
                label="Takeaway"
                onCommit={(v) => onField({ takeaway: v })}
              />
            ) : null}
            {slide.subtitle ? (
              <Editable
                className="deck-cv-sub"
                value={slide.subtitle}
                editing={editing}
                label="Подзаголовок"
                onCommit={(v) => onField({ subtitle: v })}
              />
            ) : null}
          </div>
        </div>
      );
    }
    if (splitTitle) {
      return (
        <div className="deck-cv-inner deck-cv-title deck-cv-title--split">
          <div className="deck-cv-title-main">
            <div className="deck-cv-brand">{brand}</div>
            {slide.kicker ? (
              <Editable
                className="deck-cv-kicker"
                value={slide.kicker}
                editing={editing}
                onCommit={(v) => onField({ kicker: v })}
              />
            ) : null}
            <Editable
              className={`deck-cv-h1 ${lenClass(slide.title || "")}`}
              value={slide.title || ""}
              editing={editing}
              multiline
              label="Заголовок"
              onCommit={(v) => onField({ title: v })}
            />
            {slide.subtitle ? (
              <Editable
                className="deck-cv-sub"
                value={slide.subtitle}
                editing={editing}
                label="Подзаголовок"
                onCommit={(v) => onField({ subtitle: v })}
              />
            ) : null}
            {(slide.bullets || []).length ? (
              <div className="deck-cv-pills">
                {(slide.bullets || []).slice(0, 4).map((b, i) => (
                  <span key={i} className="deck-cv-pill">{b}</span>
                ))}
              </div>
            ) : null}
          </div>
          <aside className="deck-cv-title-panel">
            {(() => {
              const metrics = parseHeroMetrics(slide.takeaway || "");
              if (metrics.length >= 2 && !editing) {
                return (
                  <div className="deck-cv-hero-metrics">
                    {metrics.map((m, i) => (
                      <div className="deck-cv-hero-metric" key={i}>
                        <span className="deck-cv-hero-idx">{String(i + 1).padStart(2, "0")}</span>
                        <div className="deck-cv-hero-val">{m.value}</div>
                        {m.label ? (
                          <div className="deck-cv-hero-lab">{m.label}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                );
              }
              return slide.takeaway ? (
                <Editable
                  className="deck-cv-takeaway"
                  value={slide.takeaway}
                  editing={editing}
                  multiline
                  label="Takeaway"
                  onCommit={(v) => onField({ takeaway: v })}
                />
              ) : null;
            })()}
          </aside>
        </div>
      );
    }
    if (!splitTitle) {
      return (
        <div className="deck-cv-inner deck-cv-title deck-cv-title--field">
          <div className="deck-cv-title-copy">
            <div className="deck-cv-brand">{brand}</div>
            {slide.kicker ? (
              <Editable
                className="deck-cv-kicker"
                value={slide.kicker}
                editing={editing}
                onCommit={(v) => onField({ kicker: v })}
              />
            ) : null}
            <Editable
              className={`deck-cv-h1 ${lenClass(slide.title || "")}`}
              value={slide.title || ""}
              editing={editing}
              multiline
              onCommit={(v) => onField({ title: v })}
            />
            {slide.takeaway ? (
              <Editable
                className="deck-cv-takeaway"
                value={slide.takeaway}
                editing={editing}
                onCommit={(v) => onField({ takeaway: v })}
              />
            ) : null}
            {slide.subtitle ? (
              <Editable
                className="deck-cv-sub"
                value={slide.subtitle}
                editing={editing}
                onCommit={(v) => onField({ subtitle: v })}
              />
            ) : null}
          </div>
          <div className="deck-cv-title-rail" aria-hidden />
        </div>
      );
    }
    return (
      <div className="deck-cv-inner deck-cv-title">
        <div className="deck-cv-brand">{brand}</div>
        {slide.kicker ? (
          <Editable
            className="deck-cv-kicker"
            value={slide.kicker}
            editing={editing}
            onCommit={(v) => onField({ kicker: v })}
          />
        ) : null}
        <Editable
          className={`deck-cv-h1 ${lenClass(slide.title || "")}`}
          value={slide.title || ""}
          editing={editing}
          multiline
          onCommit={(v) => onField({ title: v })}
        />
        {slide.takeaway ? (
          <Editable
            className="deck-cv-takeaway"
            value={slide.takeaway}
            editing={editing}
            onCommit={(v) => onField({ takeaway: v })}
          />
        ) : null}
        {slide.subtitle ? (
          <Editable
            className="deck-cv-sub"
            value={slide.subtitle}
            editing={editing}
            onCommit={(v) => onField({ subtitle: v })}
          />
        ) : null}
      </div>
    );
  }

  if (layout === "section") {
    return (
      <div className="deck-cv-inner deck-cv-section">
        <div className="deck-cv-brand">{brand}</div>
        <div className="deck-cv-section-main">
          <Editable
            className={`deck-cv-h1 ${lenClass(slide.title || "")}`}
            value={slide.title || ""}
            editing={editing}
            multiline
            onCommit={(v) => onField({ title: v })}
          />
        </div>
        <aside className="deck-cv-section-panel is-sentence">
          {slide.subtitle ? (
            <Editable
              className="deck-cv-section-line"
              value={slide.subtitle}
              editing={editing}
              multiline
              onCommit={(v) => onField({ subtitle: v })}
            />
          ) : null}
        </aside>
      </div>
    );
  }

  if (layout === "quote") {
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} />
        <blockquote className="deck-cv-quote">
          <p className="deck-cv-quote-text">{slide.definition || ""}</p>
          {slide.term ? <p className="deck-cv-quote-who">{slide.term}</p> : null}
          {slide.body ? <p className="deck-cv-quote-note">{slide.body}</p> : null}
        </blockquote>
      </div>
    );
  }

  if (layout === "callout") {
    return (
      <div className="deck-cv-inner deck-cv-title deck-cv-title--field">
        <div className="deck-cv-title-copy">
        <div className="deck-cv-brand">{brand}</div>
          <Editable
            className="deck-cv-callout-term"
            value={slide.term || ""}
            editing={editing}
            onCommit={(v) => onField({ term: v })}
          />
          <Editable
            className="deck-cv-callout-def"
            value={slide.definition || ""}
            editing={editing}
            multiline
            onCommit={(v) => onField({ definition: v })}
          />
          {slide.body ? (
            <Editable
              className="deck-cv-body"
              value={slide.body}
              editing={editing}
              multiline
              onCommit={(v) => onField({ body: v })}
            />
          ) : null}
        </div>
        <div className="deck-cv-title-rail" aria-hidden />
      </div>
    );
  }

  if (layout === "table_hero") {
    const rows = slide.rows || [];
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} compact />
        <table className="deck-cv-table">
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => {
                  const Tag = ri === 0 ? "th" : "td";
                  return (
                    <Tag key={ci}>
                      <Editable
                        value={cell}
                        editing={editing}
                        onCommit={(v) => {
                          const next = rows.map((r) => [...r]);
                          next[ri][ci] = v;
                          onField({ rows: next });
                        }}
                      />
                    </Tag>
                  );
                })}
                {editing ? (
                  <td className="deck-cv-table-op-cell">
                    {ri > 0 && rows.length > 2 ? (
                      <button
                        type="button"
                        className="deck-cv-inline-del"
                        title="Удалить строку"
                        onClick={(e) => {
                          e.stopPropagation();
                          const next = rows.filter((_, idx) => idx !== ri);
                          onField({ rows: next });
                        }}
                      >
                        ×
                      </button>
                    ) : null}
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
        {editing ? (
          <div className="deck-cv-table-actions">
            <button
              type="button"
              className="deck-cv-inline-add"
              onClick={(e) => {
                e.stopPropagation();
                const cols = rows[0]?.length || 3;
                const newRow = Array.from({ length: cols }, (_, i) =>
                  i === 0 ? "Новая строка" : "—",
                );
                onField({ rows: [...rows, newRow] });
              }}
            >
              + Строка таблицы
            </button>
          </div>
        ) : null}
        {slide.caption ? (
          <Editable
            className="deck-cv-cap"
            value={slide.caption}
            editing={editing}
            onCommit={(v) => onField({ caption: v })}
          />
        ) : null}
      </div>
    );
  }

  if (layout === "card_row") {
    const cards = slide.cards || [];
    const headSlide =
      slide.subtitle && !slide.takeaway
        ? { ...slide, takeaway: slide.subtitle }
        : slide;
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={headSlide} editing={editing} onField={onField} />
        <div
          className="deck-cv-narr-grid"
          style={{ ["--narr-cols" as string]: Math.max(1, Math.min(3, cards.length || 1)) }}
        >
          {cards.map((c, i) => {
            const pastel =
              panels.length > 0 ? panels[i % panels.length] : undefined;
            return (
              <article
                className="deck-cv-narr-card"
                key={i}
                style={pastel ? { background: pastel } : undefined}
              >
                {c.kicker ? (
                  <Editable
                    className="deck-cv-narr-kicker"
                    value={c.kicker}
                    editing={editing}
                    onCommit={(v) => {
                      const next = cards.map((x) => ({ ...x }));
                      next[i] = { ...next[i], kicker: v };
                      onField({ cards: next });
                    }}
                  />
                ) : null}
                <Editable
                  className="deck-cv-narr-title"
                  value={c.title || ""}
                  editing={editing}
                  onCommit={(v) => {
                    const next = cards.map((x) => ({ ...x }));
                    next[i] = { ...next[i], title: v };
                    onField({ cards: next });
                  }}
                />
                {c.body ? (
                  <Editable
                    className="deck-cv-narr-body"
                    value={c.body}
                    editing={editing}
                    multiline
                    onCommit={(v) => {
                      const next = cards.map((x) => ({ ...x }));
                      next[i] = { ...next[i], body: v };
                      onField({ cards: next });
                    }}
                  />
                ) : null}
              </article>
            );
          })}
        </div>
        {slide.caption ? (
          <Editable
            className="deck-cv-narr-gate"
            value={slide.caption}
            editing={editing}
            onCommit={(v) => onField({ caption: v })}
          />
        ) : null}
      </div>
    );
  }

  if (layout === "kpi_row" || layout === "scorecard") {
    const kpis = slide.kpis || [];
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} />
        <div
          className={`deck-cv-kpi-grid${layout === "scorecard" ? " is-score" : ""}`}
          style={{ ["--kpi-cols" as string]: Math.max(1, Math.min(4, kpis.length)) }}
        >
          {kpis.map((k, i) => {
            const pastel =
              panels.length > 0 ? panels[i % panels.length] : undefined;
            return (
            <div
              className={`deck-cv-kpi${pastel ? " is-pastel" : ""}`}
              key={i}
              style={
                pastel
                  ? { background: pastel, borderColor: "transparent" }
                  : undefined
              }
            >
              <Editable
                className="deck-cv-kpi-val"
                value={k.value || ""}
                editing={editing}
                onCommit={(v) => {
                  const next = kpis.map((x) => ({ ...x }));
                  next[i] = { ...next[i], value: v };
                  onField({ kpis: next });
                }}
              />
              <Editable
                className="deck-cv-kpi-lab"
                value={k.label || ""}
                editing={editing}
                onCommit={(v) => {
                  const next = kpis.map((x) => ({ ...x }));
                  next[i] = { ...next[i], label: v };
                  onField({ kpis: next });
                }}
              />
              {k.hint ? (
                <Editable
                  className="deck-cv-kpi-hint"
                  value={k.hint}
                  editing={editing}
                  multiline
                  onCommit={(v) => {
                    const next = kpis.map((x) => ({ ...x }));
                    next[i] = { ...next[i], hint: v };
                    onField({ kpis: next });
                  }}
                />
              ) : null}
              {k.delta ? (
                <div className="deck-cv-kpi-foot">
                  <Editable
                    className="deck-cv-kpi-delta"
                    value={k.delta}
                    editing={editing}
                    onCommit={(v) => {
                      const next = kpis.map((x) => ({ ...x }));
                      next[i] = { ...next[i], delta: v };
                      onField({ kpis: next });
                    }}
                  />
                </div>
              ) : null}
            </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (layout === "stat_hero") {
    const kpi = (slide.kpis || [])[0];
    return (
      <div className="deck-cv-inner deck-cv-stat deck-cv-stat--field">
        <div className="deck-cv-stat-fig">
          <div className="deck-cv-brand">{brand}</div>
          {slide.kicker ? (
            <Editable
              className="deck-cv-kicker"
              value={slide.kicker}
              editing={editing}
              onCommit={(v) => onField({ kicker: v })}
            />
          ) : null}
          {slide.title ? (
            <Editable
              className="deck-cv-h2"
              value={slide.title}
              editing={editing}
              multiline
              onCommit={(v) => onField({ title: v })}
            />
          ) : null}
          <div className="deck-cv-stat-val">{kpi?.value || ""}</div>
          <div className="deck-cv-stat-lab">{kpi?.label || ""}</div>
          {kpi?.delta ? <div className="deck-cv-stat-delta">{kpi.delta}</div> : null}
          {kpi?.hint ? <div className="deck-cv-stat-hint">{kpi.hint}</div> : null}
        </div>
        <div className="deck-cv-stat-notes">
          <Bullets slide={slide} editing={editing} onField={onField} bands />
        </div>
      </div>
    );
  }

  if (layout === "timeline") {
    const cards = slide.cards || [];
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} />
        <ol className="deck-cv-timeline">
          {cards.map((c, i) => (
            <li key={i}>
              <span className="deck-cv-time-num">{String(i + 1).padStart(2, "0")}</span>
              <span className="deck-cv-time">{c.kicker || ""}</span>
              <Editable
                className="deck-cv-time-title"
                value={c.title || ""}
                editing={editing}
                onCommit={(v) => {
                  const next = cards.map((x) => ({ ...x }));
                  next[i] = { ...next[i], title: v };
                  onField({ cards: next });
                }}
              />
              {c.body ? (
                <Editable
                  className="deck-cv-time-body"
                  value={c.body}
                  editing={editing}
                  multiline
                  onCommit={(v) => {
                    const next = cards.map((x) => ({ ...x }));
                    next[i] = { ...next[i], body: v };
                    onField({ cards: next });
                  }}
                />
              ) : null}
            </li>
          ))}
        </ol>
      </div>
    );
  }

  if (layout === "compare") {
    const cards = (slide.cards || []).slice(0, 2);
    return (
      <div className="deck-cv-inner deck-cv-compare-stage">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} />
        <div className="deck-cv-compare deck-cv-compare--fields">
          {cards.map((c, i) => (
            <article key={i} className={i === 0 ? "is-a" : "is-b"}>
              {c.kicker ? <p className="deck-cv-compare-k">{c.kicker}</p> : null}
              <p className="deck-cv-compare-t">{c.title || ""}</p>
              {c.body ? <p className="deck-cv-compare-b">{c.body}</p> : null}
              <p className="deck-cv-compare-i">{String(i + 1).padStart(2, "0")}</p>
            </article>
          ))}
        </div>
      </div>
    );
  }

  if (layout === "chart_hero" || (layout === "media_hero" && String(slide.media_id || "").startsWith("dia_"))) {
    const line = slide.caption || slide.takeaway || slide.title || "";
    const isDiagram = layout !== "chart_hero";
    const legend = diagramLegendStrokes(diagramPalette);
    return (
      <div className={`deck-cv-inner deck-cv-chart-field${isDiagram ? " is-diagram" : ""}`}>
        <aside className="deck-cv-chart-rail">
          <div className="deck-cv-brand">{brand}</div>
          <Head slide={slide} editing={editing} onField={onField} compact />
          {line ? <div className="deck-cv-chart-line">{line}</div> : null}
          {isDiagram ? (
            <ul className="deck-cv-dia-legend">
              <li><i style={{ background: legend.start }} />Старт</li>
              <li><i style={{ background: legend.decision }} />Решение</li>
              <li><i style={{ background: legend.ok }} />Успех</li>
              <li><i style={{ background: legend.warn }} />Риск</li>
            </ul>
          ) : null}
        </aside>
        <MediaSlot
          runId={runId}
          mediaId={mid}
          editing={editing}
          open={Boolean(mid && openMediaId === mid)}
          version={mediaVersion}
          hero
          onMediaClick={onMediaClick}
          previewHtml={previewHtml}
          diagramMermaid={diagramMermaid}
        />
      </div>
    );
  }

  if (layout === "media_hero") {
    const line = slide.caption || slide.takeaway || slide.title || "";
    return (
      <div className="deck-cv-inner deck-cv-chart-field">
        <aside className="deck-cv-chart-rail">
          <div className="deck-cv-brand">{brand}</div>
          <Head slide={slide} editing={editing} onField={onField} compact />
          {line ? <div className="deck-cv-chart-line">{line}</div> : null}
        </aside>
        <MediaSlot
          runId={runId}
          mediaId={mid}
          editing={editing}
          open={Boolean(mid && openMediaId === mid)}
          version={mediaVersion}
          hero
          onMediaClick={onMediaClick}
        />
      </div>
    );
  }

  if (layout === "chart_split" || layout === "media_split") {
    const splitDiagram = layout === "media_split" && String(slide.media_id || "").startsWith("dia_");
    const legend = diagramLegendStrokes(diagramPalette);
    return (
      <div className={`deck-cv-inner deck-cv-chart-field${splitDiagram ? " is-diagram" : ""}`}>
        <div className="deck-cv-chart-copy">
          <div className="deck-cv-brand">{brand}</div>
          <Head slide={slide} editing={editing} onField={onField} />
          <Bullets slide={slide} editing={editing} onField={onField} bands />
          {splitDiagram ? (
            <ul className="deck-cv-dia-legend">
              <li><i style={{ background: legend.start }} />Старт</li>
              <li><i style={{ background: legend.decision }} />Решение</li>
              <li><i style={{ background: legend.ok }} />Успех</li>
              <li><i style={{ background: legend.warn }} />Риск</li>
            </ul>
          ) : null}
        </div>
        <MediaSlot
          runId={runId}
          mediaId={mid}
          editing={editing}
          open={Boolean(mid && openMediaId === mid)}
          version={mediaVersion}
          hero
          onMediaClick={onMediaClick}
          previewHtml={previewHtml}
          diagramMermaid={diagramMermaid}
        />
      </div>
    );
  }

  if (layout === "closing" && darkBleed) {
    return (
      <div className="deck-cv-inner deck-cv-title deck-cv-title--bleed">
        {img ? (
          <div className="deck-cv-bleed" aria-hidden>
            <img src={img} alt="" />
            <div className="deck-cv-bleed-veil" />
          </div>
        ) : null}
        {editing ? (
          <button
            type="button"
            className="deck-cv-bleed-edit-btn"
            onClick={() => onMediaClick?.(mid || "usr_01", "photo")}
            title="Изменить фото слайда"
          >
            📷 Изменить фото
          </button>
        ) : null}
        <div className="deck-cv-title-main deck-cv-title-main--bleed">
          <div className="deck-cv-brand">{brand}</div>
          <Head slide={slide} editing={editing} onField={onField} />
          <Bullets slide={slide} editing={editing} onField={onField} />
        </div>
      </div>
    );
  }

  if (layout === "closing") {
    const number = closingNumber(slide);
    const decision = (slide.bullets || []).map((b) => b.trim()).filter(Boolean).join(" ");
    const hasBullets = (slide.bullets || []).some((b) => b.trim());
    return (
      <div className="deck-cv-inner deck-cv-closing deck-cv-closing--split">
        <div className="deck-cv-close-a">
          <div className="deck-cv-brand">{brand}</div>
          {number ? (
            <>
              <div className="deck-cv-close-num">{number.value}</div>
              {number.label ? (
                <div className="deck-cv-close-lab">{number.label}</div>
              ) : null}
              {slide.title ? (
                <Editable
                  className="deck-cv-h2"
                  value={slide.title}
                  editing={editing}
                  multiline
                  onCommit={(v) => onField({ title: v })}
                />
              ) : null}
            </>
          ) : (
            <Head slide={slide} editing={editing} onField={onField} />
          )}
        </div>
        <div className="deck-cv-close-b">
          {hasBullets ? (
            <Bullets slide={slide} editing={editing} onField={onField} bands />
          ) : (
            <div className="deck-cv-close-decision">{decision || slide.title || ""}</div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="deck-cv-inner">
      <div className="deck-cv-brand">{brand}</div>
      <Head slide={slide} editing={editing} onField={onField} />
      <Bullets
        slide={slide}
        editing={editing}
        onField={onField}
        bands={layout === "bullets"}
      />
    </div>
  );
}

function lenClass(text: string): string {
  const n = text.trim().split(/\s+/).filter(Boolean).length;
  if (n <= 6) return "is-short";
  if (n <= 12) return "is-mid";
  return "is-long";
}

function closingNumber(slide: DeckSlide): { value: string; label: string } | null {
  const raw = (slide.takeaway || "").trim();
  if (!raw) return null;
  const line = raw.split("\n").map((s) => s.trim()).filter(Boolean)[0] || "";
  for (const sep of [" — ", " – ", " - "]) {
    if (line.includes(sep)) {
      const [value, label] = line.split(sep);
      if (value.trim() && label.trim() && value.trim().length <= 24) {
        return { value: value.trim(), label: label.trim() };
      }
    }
  }
  if (line.length <= 24) return { value: line, label: "" };
  return null;
}

function Head({
  slide,
  editing,
  onField,
  compact,
}: {
  slide: DeckSlide;
  editing: boolean;
  onField: (p: Partial<DeckSlide>) => void;
  compact?: boolean;
}) {
  return (
    <header className={`deck-cv-head${compact ? " is-compact" : ""}`}>
      {slide.kicker ? (
        <Editable
          className="deck-cv-kicker"
          value={slide.kicker}
          editing={editing}
          onCommit={(v) => onField({ kicker: v })}
        />
      ) : null}
      <Editable
        className={`deck-cv-h2 ${lenClass(slide.title || "")}`}
        value={slide.title || ""}
        editing={editing}
        multiline
        onCommit={(v) => onField({ title: v })}
      />
      {slide.takeaway ? (
        <Editable
          className="deck-cv-takeaway"
          value={slide.takeaway}
          editing={editing}
          onCommit={(v) => onField({ takeaway: v })}
        />
      ) : null}
    </header>
  );
}

function Bullets({
  slide,
  editing,
  onField,
  bands = false,
}: {
  slide: DeckSlide;
  editing: boolean;
  onField: (p: Partial<DeckSlide>) => void;
  bands?: boolean;
}) {
  const bullets = slide.bullets || [];
  if (!bullets.length && !editing) return null;
  return (
    <div className="deck-cv-bullets-wrap">
      <ul className={`deck-cv-bullets${bands ? " deck-cv-bullets--bands" : ""}`}>
        {bullets.map((b, i) => (
          <li key={i}>
            <div className="deck-cv-bullet-row">
              <Editable
                value={b}
                editing={editing}
                onCommit={(v) => {
                  const next = [...bullets];
                  next[i] = v;
                  onField({ bullets: next });
                }}
              />
              {editing && bullets.length > 1 ? (
                <button
                  type="button"
                  className="deck-cv-inline-del"
                  title="Удалить пункт"
                  onClick={(e) => {
                    e.stopPropagation();
                    const next = bullets.filter((_, idx) => idx !== i);
                    onField({ bullets: next });
                  }}
                >
                  ×
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
      {editing ? (
        <div className="deck-cv-bullet-actions">
          <button
            type="button"
            className="deck-cv-inline-add"
            onClick={(e) => {
              e.stopPropagation();
              onField({ bullets: [...bullets, "Новый тезис"] });
            }}
          >
            + Пункт списка
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function DeckCanvas({
  runId,
  deck,
  index,
  editing,
  saving = false,
  mediaVersion = 0,
  openMediaId = null,
  onMediaClick,
  onDeckChange,
  onPatch,
  previewHtml = null,
  diagramMermaid = null,
  diagramPalette,
}: Props) {
  const slides = deck.slides || [];
  const slide = slides[Math.min(Math.max(0, index), Math.max(0, slides.length - 1))];
  const brand = deck.style?.brand_mark || "LIBER · ATELIER";
  const packId = deck.style?.pack_id || "";
  const darkBleed =
    packId === "botanical" ||
    Boolean(
      deck.style &&
        (deck.style as { motif?: { atmosphere?: string; hero_bleed?: boolean } })
          .motif?.atmosphere === "dark" &&
        (deck.style as { motif?: { hero_bleed?: boolean } }).motif?.hero_bleed,
    );
  const splitTitle =
    !darkBleed &&
    (packId === "relay" ||
      packId === "pastel" ||
      packId === "board" ||
      packId === "signal" ||
      packId === "studio" ||
      packId === "atelier" ||
      packId === "ink" ||
      packId === "voltage" ||
      parseHeroMetrics(slide?.takeaway || "").length >= 2 ||
      Boolean(
        deck.style &&
          typeof (deck.style as { motif?: { split?: number } }).motif?.split ===
            "number",
      ));
  const pending = useRef<(Partial<DeckSlide> & { id: string }) | null>(null);
  const timer = useRef<number | null>(null);
  const [focusLabel, setFocusLabel] = useState("Текст");
  const [focusRect, setFocusRect] = useState<DOMRect | null>(null);
  const [toolbarOn, setToolbarOn] = useState(false);

  const flush = useCallback(async () => {
    // Drain edits typed while a save was in flight.
    for (;;) {
      const p = pending.current;
      pending.current = null;
      if (!p) return;
      await onPatch([p]);
    }
  }, [onPatch]);

  const onField = useCallback(
    (patch: Partial<DeckSlide>) => {
      if (!slide) return;
      const nextSlides = slides.map((s) =>
        s.id === slide.id ? { ...s, ...patch } : s,
      );
      onDeckChange({ ...deck, slides: nextSlides });
      pending.current = {
        ...(pending.current?.id === slide.id ? pending.current : { id: slide.id }),
        ...patch,
        id: slide.id,
      };
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        void flush();
      }, 700);
    },
    [deck, flush, onDeckChange, slide, slides],
  );

  const onFocusField = useCallback((el: HTMLElement, label: string) => {
    setFocusLabel(label);
    setFocusRect(el.getBoundingClientRect());
    setToolbarOn(true);
  }, []);

  useEffect(() => {
    if (!editing) {
      setToolbarOn(false);
      return;
    }
    const onScroll = () => {
      const el = document.activeElement;
      if (el instanceof HTMLElement && el.classList.contains("deck-ed")) {
        setFocusRect(el.getBoundingClientRect());
      }
    };
    const onFocusOut = (e: FocusEvent) => {
      const next = e.relatedTarget;
      if (next instanceof HTMLElement && next.closest(".deck-edit-toolbar")) return;
      window.setTimeout(() => {
        const a = document.activeElement;
        if (!(a instanceof HTMLElement) || !a.classList.contains("deck-ed")) {
          setToolbarOn(false);
        }
      }, 0);
    };
    window.addEventListener("scroll", onScroll, true);
    document.addEventListener("focusout", onFocusOut);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, [editing]);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  const vars = useMemo(
    () => cssVars(deck.style, index),
    [deck.style, index],
  );
  const focusApi = useMemo(() => ({ onFocusField }), [onFocusField]);
  if (!slide) return null;

  return (
    <EditFocusCtx.Provider value={focusApi}>
      <div
        className={`deck-cv${editing ? " is-editing" : ""}`}
        style={vars}
        data-layout={slide.layout}
        data-pack={packId || undefined}
        data-slide-index={index}
      >
        <SlideBody
          runId={runId}
          slide={slide}
          brand={brand}
          editing={editing}
          onField={onField}
          splitTitle={splitTitle}
          darkBleed={darkBleed}
          motifPanels={deck.style?.motif?.panels}
          mediaVersion={mediaVersion}
          openMediaId={openMediaId}
          onMediaClick={onMediaClick}
          previewHtml={previewHtml}
          diagramMermaid={diagramMermaid}
          diagramPalette={packId || diagramPalette}
        />
        <div className="deck-cv-footer" aria-hidden>
          {brand}
        </div>
      </div>
      <DeckEditToolbar
        visible={editing && toolbarOn}
        anchor={focusRect}
        label={focusLabel}
        saving={saving}
      />
    </EditFocusCtx.Provider>
  );
}
