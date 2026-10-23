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
} from "react";
import { DeckEditToolbar } from "./DeckEditToolbar";
import type { DeckIR, DeckSlide } from "./deckTypes";

type Props = {
  runId: string;
  deck: DeckIR;
  index: number;
  editing: boolean;
  saving?: boolean;
  onDeckChange: (deck: DeckIR) => void;
  onPatch: (slides: Partial<DeckSlide> & { id: string }[]) => Promise<void>;
};

function panelForSlide(style: DeckIR["style"] | undefined, slideIndex: number): string {
  const panels = style?.motif?.panels;
  if (panels && panels.length > 0) {
    return panels[slideIndex % panels.length] || panels[0];
  }
  const c = style?.colors || {};
  return c.panel || c.paper || "#f0ede4";
}

function cssVars(style?: DeckIR["style"], slideIndex = 0): CSSProperties {
  const c = style?.colors || {};
  const f = style?.fonts || {};
  const titleFont =
    f.title || f.display || '"Fraunces", "Iowan Old Style", Georgia, serif';
  const bodyFont =
    f.body || f.fallback_pptx || '"Source Sans 3", "Segoe UI", system-ui, sans-serif';
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

function mediaUrl(runId: string, id: string | undefined): string | null {
  if (!id) return null;
  return `/api/runs/${encodeURIComponent(runId)}/slides/media/${encodeURIComponent(id)}.png`;
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
  slideIndex,
}: {
  runId: string;
  slide: DeckSlide;
  brand: string;
  editing: boolean;
  onField: (patch: Partial<DeckSlide>) => void;
  splitTitle?: boolean;
  darkBleed?: boolean;
  motifPanels?: string[];
  slideIndex?: number;
}) {
  const layout = slide.layout;
  const mid = slide.chart_id || slide.media_id;
  const img = mediaUrl(runId, mid);
  const panels = motifPanels || [];
  const si = slideIndex ?? 0;

  if (layout === "title") {
    if (darkBleed) {
      return (
        <div className="deck-cv-inner deck-cv-title deck-cv-title--bleed">
          {img ? (
            <div className="deck-cv-bleed" aria-hidden>
              <img src={img} alt="" />
              <div className="deck-cv-bleed-veil" />
            </div>
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
              className="deck-cv-h1"
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
              className="deck-cv-h1"
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
          </div>
          <aside className="deck-cv-title-panel">
            {(() => {
              const metrics = parseHeroMetrics(slide.takeaway || "");
              if (metrics.length >= 2 && !editing) {
                return (
                  <div className="deck-cv-hero-metrics">
                    {metrics.map((m, i) => (
                      <div className="deck-cv-hero-metric" key={i}>
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
          className="deck-cv-h1"
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
    const ch =
      typeof slide.chapter === "number"
        ? String(slide.chapter).padStart(2, "0")
        : "—";
    return (
      <div className="deck-cv-inner deck-cv-section">
        <div className="deck-cv-brand">{brand}</div>
        <div className="deck-cv-section-main">
          <Editable
            className="deck-cv-h1"
            value={slide.title || ""}
            editing={editing}
            multiline
            onCommit={(v) => onField({ title: v })}
          />
          {slide.subtitle ? (
            <Editable
              className="deck-cv-sub"
              value={slide.subtitle}
              editing={editing}
              onCommit={(v) => onField({ subtitle: v })}
            />
          ) : null}
        </div>
        <aside className="deck-cv-section-panel" aria-hidden>
          <span>{ch}</span>
        </aside>
      </div>
    );
  }

  if (layout === "callout") {
    return (
      <div className="deck-cv-inner">
        <div className="deck-cv-brand">{brand}</div>
        <Head slide={slide} editing={editing} onField={onField} />
        <aside
          className="deck-cv-callout"
          style={
            panels.length
              ? {
                  background: panels[si % panels.length],
                  borderColor: "transparent",
                }
              : undefined
          }
        >
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
        </aside>
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
              </tr>
            ))}
          </tbody>
        </table>
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
              {k.delta ? (
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
              ) : null}
              {k.hint ? (
                <Editable
                  className="deck-cv-kpi-hint"
                  value={k.hint}
                  editing={editing}
                  onCommit={(v) => {
                    const next = kpis.map((x) => ({ ...x }));
                    next[i] = { ...next[i], hint: v };
                    onField({ kpis: next });
                  }}
                />
              ) : null}
            </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (
    layout === "chart_hero" ||
    layout === "media_hero" ||
    layout === "chart_split" ||
    layout === "media_split"
  ) {
    const split = layout.endsWith("_split");
    return (
      <div className={`deck-cv-inner${split ? " deck-cv-split" : ""}`}>
        <div className="deck-cv-brand">{brand}</div>
        {!split ? <Head slide={slide} editing={editing} onField={onField} compact /> : null}
        {split ? (
          <div className="deck-cv-split-grid">
            <div className="deck-cv-split-copy">
              <Head slide={slide} editing={editing} onField={onField} />
              {slide.body ? (
                <Editable
                  className="deck-cv-body"
                  value={slide.body}
                  editing={editing}
                  multiline
                  onCommit={(v) => onField({ body: v })}
                />
              ) : null}
              <Bullets slide={slide} editing={editing} onField={onField} />
            </div>
            <div className="deck-cv-media">
              {img ? <img src={img} alt="" /> : <div className="deck-cv-empty">Media</div>}
              {slide.caption ? (
                <Editable
                  className="deck-cv-cap"
                  value={slide.caption}
                  editing={editing}
                  onCommit={(v) => onField({ caption: v })}
                />
              ) : null}
            </div>
          </div>
        ) : (
          <>
            <div className="deck-cv-media deck-cv-media-hero">
              {img ? <img src={img} alt="" /> : <div className="deck-cv-empty">Media</div>}
            </div>
            {slide.caption ? (
              <Editable
                className="deck-cv-cap"
                value={slide.caption}
                editing={editing}
                onCommit={(v) => onField({ caption: v })}
              />
            ) : null}
          </>
        )}
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
        <div className="deck-cv-title-main deck-cv-title-main--bleed">
          <div className="deck-cv-brand">{brand}</div>
          <Head slide={slide} editing={editing} onField={onField} />
          <Bullets slide={slide} editing={editing} onField={onField} />
        </div>
      </div>
    );
  }

  // bullets / closing / fallback
  return (
    <div
      className={`deck-cv-inner${layout === "closing" ? " deck-cv-closing" : ""}`}
    >
      <div className="deck-cv-brand">{brand}</div>
      <Head slide={slide} editing={editing} onField={onField} />
      <Bullets slide={slide} editing={editing} onField={onField} />
    </div>
  );
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
        className="deck-cv-h2"
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
}: {
  slide: DeckSlide;
  editing: boolean;
  onField: (p: Partial<DeckSlide>) => void;
}) {
  const bullets = slide.bullets || [];
  if (!bullets.length) return null;
  return (
    <ul className="deck-cv-bullets">
      {bullets.map((b, i) => (
        <li key={i}>
          <Editable
            value={b}
            editing={editing}
            onCommit={(v) => {
              const next = [...bullets];
              next[i] = v;
              onField({ bullets: next });
            }}
          />
        </li>
      ))}
    </ul>
  );
}

export function DeckCanvas({
  runId,
  deck,
  index,
  editing,
  saving = false,
  onDeckChange,
  onPatch,
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
    const p = pending.current;
    pending.current = null;
    if (!p) return;
    await onPatch([p]);
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
          slideIndex={index}
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
