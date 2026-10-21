# Liber Artifact Rail Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: executing-plans / incremental-implementation.  
> **Goal:** Julius-style artifact sidecar for Liber chat.

**Spec:** `docs/superpowers/specs/2026-10-21-liber-artifact-rail-design.md`

## Files

| Path | Action |
|------|--------|
| `web/src/ExportMenu.tsx` | create |
| `web/src/ArtifactCard.tsx` | create |
| `web/src/ContextPlaque.tsx` | create |
| `web/src/ArtifactRail.tsx` | create |
| `web/src/ReportView.tsx` | add `showPdf` / `showDownloads` props |
| `web/src/App.tsx` | activeArtifact, layout split, wire triggers |
| `web/src/styles.css` | desk-split, rail, plaque, card, overlay |
| `.agents/knowledge/KI-liber-ui.md` | update entry points |
| `docs/adr/0003-liber-chat-first-ui.md` | short consequence note |

## Tasks

1. ExportMenu + ArtifactCard + ContextPlaque  
2. ArtifactRail (tabs, motion, content)  
3. ReportView flags; App wiring + styles  
4. `npm run build`; smoke; start `web`  

## Polish v1.1 (done 2026-10-21)

1. Resize grip + `liber-rail-width` + dblclick reset  
2. RailToc + figure «PDF» → controlled `PdfFirstPage` page  
3. `PdfThumb` + badge «обновлено»  
4. `SourcePane` md / search / copy  
5. Tab ink, pdf skeleton, overlay focus trap / aria-modal  
