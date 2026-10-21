/** Shared PDF / DOCX download dropdown (rail + chat card). */

import { useEffect, useId, useRef, useState } from "react";

type Props = {
  downloads?: Record<string, string>;
  /** Extra class on the trigger button */
  className?: string;
  /** Compact label for cards */
  label?: string;
  pulse?: boolean;
};

export function ExportMenu({
  downloads,
  className = "",
  label = "Export",
  pulse = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const pdf = downloads?.pdf;
  const docx = downloads?.docx;
  const hasAny = Boolean(pdf || docx);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (!hasAny) return null;

  return (
    <div
      className={`export-menu${open ? " is-open" : ""}${pulse ? " is-pulse" : ""} ${className}`.trim()}
      ref={rootRef}
    >
      <button
        type="button"
        className="export-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
        <span className="export-menu-caret" aria-hidden>
          ▾
        </span>
      </button>
      {open && (
        <div className="export-menu-panel" role="menu" id={menuId}>
          {pdf && (
            <a
              role="menuitem"
              href={pdf}
              download
              className="export-menu-item"
              onClick={() => setOpen(false)}
            >
              PDF
            </a>
          )}
          {docx && (
            <a
              role="menuitem"
              href={docx}
              download
              className="export-menu-item"
              onClick={() => setOpen(false)}
            >
              DOCX
            </a>
          )}
        </div>
      )}
    </div>
  );
}
