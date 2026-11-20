/** Settings: drop a Stimulsoft PNG and table PDF, then show the markdown. */

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import {
  emptyDashboardDrop,
  parseDashboard,
  takeDashboardFiles,
  type DashboardDrop,
  type DashboardParseResult,
} from "./domain/dashboardParse";
import {
  splitDashboardBlocks,
  type DashboardBlock,
} from "./domain/dashboardTables";
import { useFocusTrap } from "./useFocusTrap";

type Props = {
  onClose: () => void;
};

function TableGrid({
  block,
}: {
  block: Extract<DashboardBlock, { kind: "table" }>;
}) {
  const pinRef = useRef<HTMLDivElement>(null);
  const restRef = useRef<HTMLDivElement>(null);
  const syncing = useRef(false);
  const restHeader = block.header.slice(1);

  useLayoutEffect(() => {
    const pinRows = pinRef.current?.querySelectorAll("tr");
    const restRows = restRef.current?.querySelectorAll("tr");
    if (!pinRows) return;
    pinRows.forEach((row, index) => {
      const other = restRows?.[index];
      row.style.height = "";
      if (other) other.style.height = "";
      const height = Math.max(
        row.getBoundingClientRect().height,
        other?.getBoundingClientRect().height ?? 0,
      );
      const px = `${Math.ceil(height)}px`;
      row.style.height = px;
      if (other) other.style.height = px;
    });
  }, [block]);

  function syncScroll(from: HTMLDivElement, to: HTMLDivElement | null) {
    if (!to || syncing.current) return;
    syncing.current = true;
    to.scrollTop = from.scrollTop;
    syncing.current = false;
  }

  function markRow(index: number | null) {
    for (const root of [pinRef.current, restRef.current]) {
      root?.querySelectorAll("tbody tr").forEach((row, rowIndex) => {
        row.classList.toggle("is-hot", rowIndex === index);
      });
    }
  }

  return (
    <div className={`stimul-split${restHeader.length === 0 ? " is-pin-only" : ""}`}>
      <div
        className="stimul-pin"
        ref={pinRef}
        onScroll={(event) => syncScroll(event.currentTarget, restRef.current)}
      >
        <table className="stimul-grid">
          <thead>
            <tr>
              <th className="is-label" scope="col">
                {block.header[0] || ""}
              </th>
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                onMouseEnter={() => markRow(rowIndex)}
                onMouseLeave={() => markRow(null)}
              >
                <td className="is-label">{row[0] || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {restHeader.length === 0 ? null : (
        <div
          className="stimul-grid-scroll"
          ref={restRef}
          onScroll={(event) => syncScroll(event.currentTarget, pinRef.current)}
        >
          <table className="stimul-grid">
            <thead>
              <tr>
                {restHeader.map((cell, column) => (
                  <th
                    key={column}
                    className={block.numeric[column + 1] ? "is-num" : "is-label"}
                    scope="col"
                  >
                    {cell}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  onMouseEnter={() => markRow(rowIndex)}
                  onMouseLeave={() => markRow(null)}
                >
                  {restHeader.map((_, column) => (
                    <td
                      key={column}
                      className={block.numeric[column + 1] ? "is-num" : "is-label"}
                    >
                      {row[column + 1] || ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function DashboardReadout({ markdown }: { markdown: string }) {
  const blocks = splitDashboardBlocks(markdown);
  const tables = blocks.filter(
    (block): block is Extract<DashboardBlock, { kind: "table" }> =>
      block.kind === "table",
  );
  const widest = tables.reduce((max, block) => Math.max(max, block.header.length), 0);
  const rowCount = tables.reduce((sum, block) => sum + block.rows.length, 0);
  return (
    <div className="stimul-readout">
      {tables.length > 0 ? (
        <p className="stimul-meta">
          {tables.length === 1 ? "Одна таблица" : `Таблиц: ${tables.length}`}
          {`. ${widest} столбцов, ${rowCount} строк. Шапка и первый столбец остаются на месте, остальное листается.`}
        </p>
      ) : null}
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return (
            <h3 key={index} className="stimul-read-title">
              {block.text}
            </h3>
          );
        }
        if (block.kind === "text") {
          return (
            <p key={index} className="stimul-read-text">
              {block.text}
            </p>
          );
        }
        return <TableGrid key={index} block={block} />;
      })}
    </div>
  );
}

export function StimulsoftParseModal({ onClose }: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [drop, setDrop] = useState<DashboardDrop>(emptyDashboardDrop);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<DashboardParseResult | null>(null);
  const [copied, setCopied] = useState(false);
  useFocusTrap(dialogRef, { active: true });

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  function addFiles(list: FileList | File[] | null) {
    if (!list || list.length === 0) return;
    setDrop((current) => takeDashboardFiles(Array.from(list), current));
    setError("");
    setResult(null);
  }

  async function run() {
    if (!drop.png && !drop.pdf) {
      setError("Перетащите PNG, PDF или оба файла.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError("");
    setCopied(false);
    try {
      const parsed = await parseDashboard(
        drop.png,
        drop.pdf,
        fetch,
        controller.signal,
      );
      if (!controller.signal.aborted) setResult(parsed);
    } catch (exc) {
      if (controller.signal.aborted) return;
      setResult(null);
      setError(exc instanceof Error ? exc.message : "Не удалось разобрать.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function copyMarkdown() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.markdown);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

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
      onDragOver={(event) => {
        event.preventDefault();
        event.stopPropagation();
      }}
      onDrop={(event) => {
        event.preventDefault();
        event.stopPropagation();
      }}
    >
      <div className={`stimul-sheet${result ? " is-result" : ""}`}>
        <header className="settings-modal-head">
          <div>
            <p className="settings-modal-eyebrow">настройки · стимулсофт</p>
            <h2 id={titleId} className="settings-modal-title">
              {result ? "Таблица" : "Разобрать дашборд"}
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

        <div className="settings-modal-body">
          {result ? (
            <div className="stimul-result">
              {result.warnings.length > 0 ? (
                <ul className="stimul-warnings">
                  {result.warnings.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              ) : null}
              <DashboardReadout markdown={result.markdown} />
            </div>
          ) : (
            <>
              <p className="stimul-lead">
                Перетащите PNG снимка и PDF таблицы. Можно оба сразу или по
                одному. Отчёт от этого не собирается.
              </p>
              <button
                type="button"
                className={`stimul-drop${over ? " is-over" : ""}`}
                onClick={() => inputRef.current?.click()}
                onDragEnter={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setOver(true);
                }}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setOver(true);
                }}
                onDragLeave={() => setOver(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setOver(false);
                  addFiles(event.dataTransfer.files);
                }}
              >
                Поле для PNG и PDF
                <span>или нажмите и выберите файлы</span>
              </button>
              <input
                ref={inputRef}
                className="stimul-file"
                type="file"
                accept=".png,.pdf,image/png,application/pdf"
                multiple
                onChange={(event) => {
                  addFiles(event.target.files);
                  event.target.value = "";
                }}
              />
              <ul className="stimul-slots">
                <li>PNG: {drop.png ? drop.png.name : "не выбран"}</li>
                <li>PDF: {drop.pdf ? drop.pdf.name : "не выбран"}</li>
              </ul>
              {drop.rejected.length > 0 ? (
                <p className="stimul-reject">
                  Не взял: {drop.rejected.join(", ")}. Нужны .png и .pdf.
                </p>
              ) : null}
              {error ? <p className="stimul-error">{error}</p> : null}
              {busy ? (
                <p className="stimul-busy">
                  Разбираю. Снимок идёт в модель, это может занять пару минут.
                </p>
              ) : null}
            </>
          )}
        </div>

        <footer className="settings-modal-foot stimul-foot">
          {result ? (
            <>
              <button type="button" className="stimul-secondary" onClick={copyMarkdown}>
                {copied ? "Скопировано" : "Скопировать"}
              </button>
              <button
                type="button"
                className="settings-modal-done"
                onClick={() => {
                  setResult(null);
                  setCopied(false);
                }}
              >
                Другие файлы
              </button>
            </>
          ) : (
            <button
              type="button"
              className="settings-modal-done"
              disabled={busy || (!drop.png && !drop.pdf)}
              onClick={() => void run()}
            >
              {busy ? "Разбираю…" : "Разобрать"}
            </button>
          )}
        </footer>
      </div>
    </div>
  );
}
