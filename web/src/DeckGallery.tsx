/** Julius-style Preview grid — all slides at once + structure DnD. */

import { motion } from "framer-motion";
import { useState } from "react";

type Props = {
  slidePngs: string[];
  activeIndex: number;
  onSelect: (index: number) => void;
  titles?: string[];
  canStructure?: boolean;
  onReorder?: (from: number, to: number) => void;
  onDuplicate?: (index: number) => void;
  onDelete?: (index: number) => void;
  onAddSlide?: (afterIndex?: number) => void;
};

export function DeckGallery({
  slidePngs,
  activeIndex,
  onSelect,
  titles = [],
  canStructure = false,
  onReorder,
  onDuplicate,
  onDelete,
  onAddSlide,
}: Props) {
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  if (!slidePngs.length) return null;
  return (
    <div className="deck-gallery" role="list" aria-label="Все слайды">
      {slidePngs.map((url, i) => {
        const title = (titles[i] || "").trim();
        const label = title || `Слайд ${i + 1}`;
        return (
          <motion.div
            key={url}
            role="listitem"
            className={`deck-gallery-card${i === activeIndex ? " is-active" : ""}${dragFrom === i ? " is-dragging" : ""}`}
            draggable={canStructure && Boolean(onReorder)}
            onDragStart={() => setDragFrom(i)}
            onDragEnd={() => setDragFrom(null)}
            onDragOver={(e) => {
              if (canStructure && onReorder) e.preventDefault();
            }}
            onDrop={(e) => {
              e.preventDefault();
              if (dragFrom != null && onReorder) onReorder(dragFrom, i);
              setDragFrom(null);
            }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.28,
              delay: Math.min(i * 0.03, 0.35),
              ease: [0.22, 1, 0.36, 1],
            }}
            whileHover={{ y: -2 }}
            title={
              canStructure
                ? `${label} · перетащите для порядка`
                : label
            }
          >
            <button
              type="button"
              className="deck-gallery-hit"
              onClick={() => onSelect(i)}
            >
              <span className="deck-gallery-frame">
                <img src={url} alt={label} draggable={false} />
                <span className="deck-gallery-num">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </span>
              <span className="deck-gallery-caption">
                <span className="deck-gallery-caption-title">{label}</span>
              </span>
            </button>
            {canStructure && (onDuplicate || onDelete) ? (
              <div className="deck-gallery-ops" role="group" aria-label="Слайд">
                {onDuplicate ? (
                  <button
                    type="button"
                    className="deck-gallery-op"
                    title="Дублировать"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDuplicate(i);
                    }}
                  >
                    +
                  </button>
                ) : null}
                {onDelete ? (
                  <button
                    type="button"
                    className="deck-gallery-op is-danger"
                    title="Удалить"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(i);
                    }}
                  >
                    ×
                  </button>
                ) : null}
              </div>
            ) : null}
          </motion.div>
        );
      })}
      {canStructure && onAddSlide ? (
        <motion.div
          role="listitem"
          className="deck-gallery-card deck-gallery-card--add"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.28,
            delay: Math.min(slidePngs.length * 0.03, 0.35),
            ease: [0.22, 1, 0.36, 1],
          }}
          whileHover={{ y: -2 }}
        >
          <button
            type="button"
            className="deck-gallery-add-btn"
            onClick={() => onAddSlide(slidePngs.length - 1)}
            title="Добавить новый слайд"
          >
            <span className="deck-gallery-add-frame">
              <span className="deck-gallery-add-icon" aria-hidden>+</span>
            </span>
            <span className="deck-gallery-caption">
              <span className="deck-gallery-caption-title">Добавить слайд</span>
            </span>
          </button>
        </motion.div>
      ) : null}
    </div>
  );
}
