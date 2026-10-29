# Liber History — папки и закрепление

**Date:** 2026-10-23  
**Status:** shipped (session)

## Goal

В боковой «Истории»: закреплять чаты и раскладывать по папкам без бэкенда.

## Model

- `HistoryItem`: `pinned?`, `folderId?`
- `HistoryFolder`: `{ id, name, createdAt }`
- Storage: `sessionStorage` keys `liber-report-history` + `liber-history-folders`
- Sort: pinned first, then `savedAt` desc

## UX

- Toolbar «Новая папка»
- Groups: Закреплённые → named folders → Без папки / Недавние
- Row hover: pin · move-to-folder menu
- Folder: rename / delete (chats stay, folderId cleared)

## Non-goals

- Sync across devices · drag-and-drop · server history
