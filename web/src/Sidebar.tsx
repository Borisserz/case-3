/** Liber left rail — New · History (pin + folders) · Settings. */

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useMemo, useState } from "react";
import {
  IconChevron,
  IconFolder,
  IconHistory,
  IconLiberMark,
  IconPanelLeft,
  IconPin,
  IconPlus,
  IconSettings,
} from "./icons";
import type { HistoryFolder, HistoryItem } from "./reportHistory";

export type { HistoryItem, HistoryFolder };

type Props = {
  collapsed: boolean;
  onToggle: () => void;
  healthReady: boolean;
  healthLabel: string;
  healthHint: string;
  history: HistoryItem[];
  folders: HistoryFolder[];
  historyOpen: boolean;
  onHistoryOpen: (open: boolean) => void;
  onNew: () => void;
  onOpenHistory: (item: HistoryItem) => void;
  onTogglePin: (runId: string) => void;
  onMoveToFolder: (runId: string, folderId: string | null) => void;
  onCreateFolder: (name: string) => void;
  onRenameFolder: (id: string, name: string) => void;
  onDeleteFolder: (id: string) => void;
  onSettings: () => void;
  busy?: boolean;
};

function formatMeta(savedAt: number): string {
  return new Date(savedAt).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function HistoryRow({
  item,
  folders,
  onOpen,
  onTogglePin,
  onMoveToFolder,
  busy,
}: {
  item: HistoryItem;
  folders: HistoryFolder[];
  onOpen: () => void;
  onTogglePin: () => void;
  onMoveToFolder: (folderId: string | null) => void;
  busy: boolean;
}) {
  const [menu, setMenu] = useState(false);
  return (
    <li className={`liber-hist-row${item.pinned ? " is-pinned" : ""}`}>
      <button
        type="button"
        className="liber-sidebar-history-item"
        onClick={onOpen}
        title={item.title}
        disabled={busy}
      >
        {item.pinned ? (
          <IconPin size={12} className="liber-hist-pin-mark" />
        ) : null}
        <span className="liber-sidebar-history-title">{item.title}</span>
        <span className="liber-sidebar-history-meta">
          {formatMeta(item.savedAt)}
        </span>
      </button>
      <div className="liber-hist-actions">
        <button
          type="button"
          className={`liber-hist-act${item.pinned ? " is-on" : ""}`}
          title={item.pinned ? "Открепить" : "Закрепить"}
          aria-label={item.pinned ? "Открепить" : "Закрепить"}
          disabled={busy}
          onClick={(e) => {
            e.stopPropagation();
            onTogglePin();
          }}
        >
          <IconPin size={14} />
        </button>
        <div className="liber-hist-menu-wrap">
          <button
            type="button"
            className={`liber-hist-act${menu ? " is-on" : ""}`}
            title="В папку"
            aria-label="Переместить в папку"
            aria-expanded={menu}
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation();
              setMenu((v) => !v);
            }}
          >
            <IconFolder size={14} />
          </button>
          {menu ? (
            <div className="liber-hist-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                className={!item.folderId ? "is-active" : undefined}
                onClick={() => {
                  onMoveToFolder(null);
                  setMenu(false);
                }}
              >
                Без папки
              </button>
              {folders.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  role="menuitem"
                  className={item.folderId === f.id ? "is-active" : undefined}
                  onClick={() => {
                    onMoveToFolder(f.id);
                    setMenu(false);
                  }}
                >
                  {f.name}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </li>
  );
}

function FolderBlock({
  title,
  icon,
  items,
  folders,
  defaultOpen = true,
  folderId,
  onOpenHistory,
  onTogglePin,
  onMoveToFolder,
  onRename,
  onDelete,
  busy,
}: {
  title: string;
  icon?: "pin" | "folder";
  items: HistoryItem[];
  folders: HistoryFolder[];
  defaultOpen?: boolean;
  folderId?: string;
  onOpenHistory: (item: HistoryItem) => void;
  onTogglePin: (runId: string) => void;
  onMoveToFolder: (runId: string, folderId: string | null) => void;
  onRename?: (name: string) => void;
  onDelete?: () => void;
  busy: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(title);

  if (items.length === 0 && !folderId) return null;

  return (
    <section className="liber-hist-group">
      <div className="liber-hist-group-head">
        <button
          type="button"
          className="liber-hist-group-toggle"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className={`liber-hist-chev${open ? " is-open" : ""}`}>
            <IconChevron size={12} />
          </span>
          {icon === "pin" ? <IconPin size={13} /> : null}
          {icon === "folder" ? <IconFolder size={13} /> : null}
          {renaming ? (
            <input
              className="liber-hist-rename"
              value={nameDraft}
              autoFocus
              maxLength={40}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setNameDraft(e.target.value)}
              onBlur={() => {
                onRename?.(nameDraft);
                setRenaming(false);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  onRename?.(nameDraft);
                  setRenaming(false);
                }
                if (e.key === "Escape") setRenaming(false);
              }}
            />
          ) : (
            <span className="liber-hist-group-title">{title}</span>
          )}
          <span className="liber-hist-group-count">{items.length}</span>
        </button>
        {folderId && onRename && onDelete ? (
          <div className="liber-hist-group-tools">
            <button
              type="button"
              className="liber-hist-act"
              title="Переименовать"
              aria-label="Переименовать папку"
              onClick={() => {
                setNameDraft(title);
                setRenaming(true);
              }}
            >
              <span className="liber-hist-act-glyph" aria-hidden>
                Aa
              </span>
            </button>
            <button
              type="button"
              className="liber-hist-act liber-hist-act-danger"
              title="Удалить папку"
              aria-label="Удалить папку"
              onClick={() => {
                if (
                  window.confirm(`Удалить папку «${title}»? Чаты останутся.`)
                ) {
                  onDelete();
                }
              }}
            >
              ×
            </button>
          </div>
        ) : null}
      </div>
      {open ? (
        <ul className="liber-hist-list">
          {items.length === 0 ? (
            <li className="liber-hist-empty-folder">Пусто</li>
          ) : (
            items.map((h) => (
              <HistoryRow
                key={h.id}
                item={h}
                folders={folders}
                busy={busy}
                onOpen={() => onOpenHistory(h)}
                onTogglePin={() => onTogglePin(h.runId)}
                onMoveToFolder={(fid) => onMoveToFolder(h.runId, fid)}
              />
            ))
          )}
        </ul>
      ) : null}
    </section>
  );
}

export function Sidebar({
  collapsed,
  onToggle,
  healthReady,
  healthLabel,
  healthHint,
  history,
  folders,
  historyOpen,
  onHistoryOpen,
  onNew,
  onOpenHistory,
  onTogglePin,
  onMoveToFolder,
  onCreateFolder,
  onRenameFolder,
  onDeleteFolder,
  onSettings,
  busy = false,
}: Props) {
  const reduce = useReducedMotion();
  const [creating, setCreating] = useState(false);
  const [folderName, setFolderName] = useState("");

  const pinned = useMemo(
    () => history.filter((h) => h.pinned),
    [history],
  );
  const unpinned = useMemo(
    () => history.filter((h) => !h.pinned),
    [history],
  );
  const loose = useMemo(
    () => unpinned.filter((h) => !h.folderId),
    [unpinned],
  );

  const submitFolder = () => {
    const n = folderName.trim();
    if (!n) {
      setCreating(false);
      return;
    }
    onCreateFolder(n);
    setFolderName("");
    setCreating(false);
  };

  return (
    <aside
      className={`liber-sidebar${collapsed ? " is-collapsed" : ""}`}
      aria-label="Навигация Liber"
    >
      <div className="liber-sidebar-top">
        <div className="liber-sidebar-brand">
          <IconLiberMark size={collapsed ? 26 : 30} />
          <div
            className="liber-sidebar-brand-text liber-side-label"
            aria-hidden={collapsed}
          >
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
            <span className="liber-sidebar-count liber-side-label">
              {history.length}
            </span>
          ) : null}
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
            <div className="liber-hist-toolbar">
              {creating ? (
                <form
                  className="liber-hist-create"
                  onSubmit={(e) => {
                    e.preventDefault();
                    submitFolder();
                  }}
                >
                  <span className="liber-hist-create-icon" aria-hidden>
                    <IconFolder size={15} />
                  </span>
                  <input
                    value={folderName}
                    onChange={(e) => setFolderName(e.target.value)}
                    placeholder="Название папки…"
                    maxLength={40}
                    autoFocus
                    aria-label="Название папки"
                  />
                  <button
                    type="submit"
                    className="liber-hist-create-go"
                    disabled={!folderName.trim()}
                  >
                    Создать
                  </button>
                  <button
                    type="button"
                    className="liber-hist-create-cancel"
                    aria-label="Отмена"
                    title="Отмена"
                    onClick={() => {
                      setCreating(false);
                      setFolderName("");
                    }}
                  >
                    ×
                  </button>
                </form>
              ) : (
                <button
                  type="button"
                  className="liber-hist-add-folder"
                  onClick={() => setCreating(true)}
                >
                  <span className="liber-hist-add-ico" aria-hidden>
                    <IconPlus size={12} />
                  </span>
                  Новая папка
                </button>
              )}
            </div>

            {history.length === 0 && folders.length === 0 ? (
              <p className="liber-sidebar-history-empty">
                Пока пусто — соберите первый отчёт.
              </p>
            ) : (
              <div className="liber-hist-body">
                <FolderBlock
                  title="Закреплённые"
                  icon="pin"
                  items={pinned}
                  folders={folders}
                  defaultOpen
                  onOpenHistory={onOpenHistory}
                  onTogglePin={onTogglePin}
                  onMoveToFolder={onMoveToFolder}
                  busy={busy}
                />
                {folders.map((f) => (
                  <FolderBlock
                    key={f.id}
                    title={f.name}
                    icon="folder"
                    folderId={f.id}
                    items={unpinned.filter((h) => h.folderId === f.id)}
                    folders={folders}
                    defaultOpen
                    onOpenHistory={onOpenHistory}
                    onTogglePin={onTogglePin}
                    onMoveToFolder={onMoveToFolder}
                    onRename={(name) => onRenameFolder(f.id, name)}
                    onDelete={() => onDeleteFolder(f.id)}
                    busy={busy}
                  />
                ))}
                <FolderBlock
                  title={folders.length ? "Без папки" : "Недавние"}
                  items={loose}
                  folders={folders}
                  defaultOpen
                  onOpenHistory={onOpenHistory}
                  onTogglePin={onTogglePin}
                  onMoveToFolder={onMoveToFolder}
                  busy={busy}
                />
                {history.length === 0 ? (
                  <p className="liber-sidebar-history-empty">
                    Папки готовы — отчёты появятся после сборки.
                  </p>
                ) : null}
              </div>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="liber-sidebar-foot">
        <button
          type="button"
          className="liber-sidebar-item liber-sidebar-settings"
          onClick={onSettings}
          title="Настройки"
          aria-label="Настройки"
        >
          <IconSettings size={17} />
          <span className="liber-side-label">Настройки</span>
        </button>
        <p className="liber-sidebar-foot-label liber-side-label">
          Atelier
          <span>PDF · DOCX · Source</span>
        </p>
        <span className="liber-sidebar-foot-dot" aria-hidden />
      </div>
    </aside>
  );
}
