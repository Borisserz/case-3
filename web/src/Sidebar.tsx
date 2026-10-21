/** Liber left rail — New · History · Settings (Mary anatomy, Liber IA). */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  IconHistory,
  IconLiberMark,
  IconPanelLeft,
  IconPlus,
  IconSettings,
} from "./icons";

export type HistoryItem = {
  id: string;
  title: string;
  runId: string;
  savedAt: number;
};

type Props = {
  collapsed: boolean;
  onToggle: () => void;
  healthReady: boolean;
  healthLabel: string;
  healthHint: string;
  history: HistoryItem[];
  historyOpen: boolean;
  onHistoryOpen: (open: boolean) => void;
  onNew: () => void;
  onOpenHistory: (item: HistoryItem) => void;
  onSettings: () => void;
  busy?: boolean;
};

export function Sidebar({
  collapsed,
  onToggle,
  healthReady,
  healthLabel,
  healthHint,
  history,
  historyOpen,
  onHistoryOpen,
  onNew,
  onOpenHistory,
  onSettings,
  busy = false,
}: Props) {
  const reduce = useReducedMotion();

  return (
    <aside
      className={`liber-sidebar${collapsed ? " is-collapsed" : ""}`}
      aria-label="Навигация Liber"
    >
      <div className="liber-sidebar-top">
        <div className="liber-sidebar-brand">
          <IconLiberMark size={collapsed ? 26 : 30} />
          <div className="liber-sidebar-brand-text liber-side-label" aria-hidden={collapsed}>
            <span className="liber-sidebar-word">Liber</span>
            <span
              className={`liber-sidebar-live${healthReady ? " ok" : ""}`}
              title={healthHint}
            >
              <span className="health-dot" aria-hidden />
              {healthLabel}
            </span>
          </div>
        </div>
        <button
          type="button"
          className="liber-sidebar-collapse"
          onClick={onToggle}
          aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
          title={collapsed ? "Развернуть" : "Свернуть"}
        >
          <IconPanelLeft size={16} />
        </button>
      </div>

      <button
        type="button"
        className="liber-sidebar-new"
        disabled={busy}
        onClick={onNew}
        title="Новый отчёт"
        aria-label="Новый отчёт"
      >
        <IconPlus size={16} />
        <span className="liber-side-label">Новый отчёт</span>
      </button>

      <nav className="liber-sidebar-nav" aria-label="Разделы">
        <button
          type="button"
          className={`liber-sidebar-item${historyOpen ? " is-active" : ""}`}
          disabled={busy}
          aria-expanded={historyOpen && !collapsed}
          aria-label="История"
          onClick={() => {
            if (collapsed) {
              onToggle();
              onHistoryOpen(true);
            } else {
              onHistoryOpen(!historyOpen);
            }
          }}
          title="История"
        >
          <IconHistory size={17} />
          <span className="liber-side-label">История</span>
          {history.length > 0 ? (
            <span className="liber-sidebar-count liber-side-label">{history.length}</span>
          ) : null}
        </button>
        <button
          type="button"
          className="liber-sidebar-item"
          onClick={onSettings}
          title="Настройки"
          aria-label="Настройки"
        >
          <IconSettings size={17} />
          <span className="liber-side-label">Настройки</span>
        </button>
      </nav>

      <AnimatePresence initial={false}>
        {historyOpen && !collapsed ? (
          <motion.div
            className="liber-sidebar-history"
            key="hist"
            initial={reduce ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={reduce ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            {history.length === 0 ? (
              <p className="liber-sidebar-history-empty">
                Пока пусто — соберите первый отчёт.
              </p>
            ) : (
              <ul>
                {history.map((h) => (
                  <li key={h.id}>
                    <button
                      type="button"
                      className="liber-sidebar-history-item"
                      onClick={() => onOpenHistory(h)}
                      title={h.title}
                    >
                      <span className="liber-sidebar-history-title">
                        {h.title}
                      </span>
                      <span className="liber-sidebar-history-meta">
                        {new Date(h.savedAt).toLocaleString("ru-RU", {
                          day: "numeric",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="liber-sidebar-foot">
        <p className="liber-sidebar-foot-label liber-side-label">
          Atelier
          <span>PDF · DOCX · Source</span>
        </p>
        <span className="liber-sidebar-foot-dot" aria-hidden />
      </div>
    </aside>
  );
}
