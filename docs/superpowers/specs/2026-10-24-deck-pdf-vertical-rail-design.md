# Deck PDF vertical rail — design

**Date:** 2026-10-24  
**Status:** approved (chat)

## Goal

Two deck artifacts stay distinct:

| Artifact | Open | Rail |
|----------|------|------|
| PPTX | click preview | **Презентация** (twin / Present / edit) — unchanged |
| Deck PDF | click preview | **Слайды** — vertical PNG film + anchors `1…N` + **Скачать** |

## UX rules

1. No footer «Открыть презентацию →» / «Открыть в панели →» — open only via preview click.
2. No shared **Export** in rail / PresentationPane header — download lives on each artifact card (+ Скачать in Слайды head).
3. PDF chat card: compact preview + **Скачать** (deck_pdf URL).
4. Слайды rail: wide frames stacked top→bottom, soft gap, right rail of number anchors; click jumps; scroll syncs active.

## Out of scope

- IR editor / Present mode for PPTX.
- Report PDF tab behavior.
