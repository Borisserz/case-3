/** Julius-style Preview grid — all slides at once. */

import { motion } from "framer-motion";

type Props = {
  slidePngs: string[];
  activeIndex: number;
  onSelect: (index: number) => void;
  titles?: string[];
};

export function DeckGallery({
  slidePngs,
  activeIndex,
  onSelect,
  titles = [],
}: Props) {
  if (!slidePngs.length) return null;
  return (
    <div className="deck-gallery" role="list" aria-label="Все слайды">
      {slidePngs.map((url, i) => {
        const title = (titles[i] || "").trim();
        const label = title || `Слайд ${i + 1}`;
        return (
          <motion.button
            key={url}
            type="button"
            role="listitem"
            className={`deck-gallery-card${i === activeIndex ? " is-active" : ""}`}
            onClick={() => onSelect(i)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.28,
              delay: Math.min(i * 0.03, 0.35),
              ease: [0.22, 1, 0.36, 1],
            }}
            whileHover={{ y: -2 }}
            title={label}
          >
            <span className="deck-gallery-frame">
              <img src={url} alt={label} />
              <span className="deck-gallery-num">{String(i + 1).padStart(2, "0")}</span>
            </span>
            <span className="deck-gallery-caption">
              <span className="deck-gallery-caption-title">{label}</span>
            </span>
          </motion.button>
        );
      })}
    </div>
  );
}
