/** Full-screen readout of a parsed dashboard. Tables stay wide enough to read. */

import { useEffect, useId, useRef } from "react";
import { shotTitle, splitPackedSources } from "./domain/dashboardCapture";
import { splitDashboardBlocks } from "./domain/dashboardTables";
import type { DashboardBlock } from "./domain/dashboardTables";
import { useFocusTrap } from "./useFocusTrap";

type Props = {
  title: string;
  text: string;
  onClose: () => void;
};

function cellClass(numeric: boolean): string {
  return numeric ? "is-num" : "is-label";
}

function BlockView({ block }: { block: DashboardBlock }) {
  if (block.kind === "heading") {
    return <h3 className="stimul-read-title">{block.text}</h3>;
  }
  if (block.kind === "text") {
    return <p className="stimul-read-text">{block.text}</p>;
  }
  if (block.kind === "list") {
    return (
      <ul className="stimul-read-list">
        {block.items.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
      </ul>
    );
  }
  return (
    <div className="stimul-grid-scroll">
      <table className="stimul-grid">
        <thead>
          <tr>
            {block.header.map((cell, index) => (
              <th key={index} className={cellClass(block.numeric[index])}>
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {block.header.map((_, index) => (
                <td key={index} className={cellClass(block.numeric[index])}>
                  {row[index] || ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DashboardReadModal({ title, text, onClose }: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, { active: true });
  const docs = splitPackedSources(text).map((doc) => ({
    title: shotTitle(doc.name, doc.markdown),
    blocks: splitDashboardBlocks(doc.markdown),
  }));
  const heading = docs.length === 1 ? docs[0].title : title;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div
      ref={dialogRef}
      className="stimul-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="stimul-sheet is-read">
        <header className="settings-modal-head">
          <div>
            <p className="settings-modal-eyebrow">дашборд · числа как на экране</p>
            <h2 id={titleId} className="settings-modal-title">
              {heading}
            </h2>
          </div>
          <button
            type="button"
            className="settings-modal-x"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </header>
        <div className="settings-modal-body dash-read-body">
          {docs.length > 1 ? (
            <nav className="dash-read-nav" aria-label="Снимки">
              {docs.map((doc, index) => (
                <button
                  key={`${doc.title}-${index}`}
                  type="button"
                  onClick={() =>
                    document
                      .getElementById(`dash-read-${index}`)
                      ?.scrollIntoView({ block: "start" })
                  }
                >
                  {doc.title}
                </button>
              ))}
            </nav>
          ) : null}
          {docs.length ? (
            docs.map((doc, index) => (
              <section
                key={`${doc.title}-${index}`}
                id={`dash-read-${index}`}
                className="stimul-readout"
              >
                {docs.length > 1 ? (
                  <h3 className="stimul-read-title">{doc.title}</h3>
                ) : null}
                {doc.blocks.map((block, blockIndex) => (
                  <BlockView key={blockIndex} block={block} />
                ))}
              </section>
            ))
          ) : (
            <p className="stimul-read-text">В снимке нет текста.</p>
          )}
        </div>
      </div>
    </div>
  );
}
