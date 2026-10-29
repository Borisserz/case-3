# Deck PDF vertical rail — plan

> **For agentic workers:** implement tasks in order; TDD where logic is non-trivial.

**Spec:** `docs/superpowers/specs/2026-10-24-deck-pdf-vertical-rail-design.md`

## Files

| File | Role |
|------|------|
| `web/src/DeckSlidesFilm.tsx` | NEW — vertical film + anchors |
| `web/src/styles/chat.css` (or presentation.css) | Film styles |
| `web/src/ArtifactRail.tsx` | Tab `slides`, drop Export |
| `web/src/ArtifactCard.tsx` / `DeckPdfGallery.tsx` / `DeckFileCard.tsx` | Open paths + download, no foot CTAs |
| `web/src/PresentationPane.tsx` | Drop Export chrome |
| `web/src/App.tsx` / `ChatMessages.tsx` | `onOpenDeckSlides` |

## Tasks

1. Remove Export + open-footer buttons.
2. Add `DeckSlidesFilm` + CSS.
3. Add rail tab `slides`; wire open from PDF gallery / card.
4. Smoke: PPTX → presentation; PDF → slides film + download.
