# Liber — схема как peer-артефакт у отчёта

**Date:** 2026-10-23  
**Status:** approved (user)  
**Amends:** ADR-0007 · composer modes · Artifact rail

## Goal

При генерации **документа (Отчёт)** схема — третий артефакт **рядом с превью**, не тихая ссылка под PDF.  
Режим **Схема** — только схема (как сейчас).

## UX

| Режим | Поведение |
|-------|-----------|
| Отчёт / auto | Rail tabs: **Превью · Схема · PDF** (+ Source). В чате: карточка PDF + peer-карточка схемы |
| Схема | Только Mermaid; rail сразу на «Схема»; без PDF/DOCX |
| Презентация | Без схем Liber (как ADR/modes) |

## Non-goals

- Inject схем в PDF (ADR-0007)
- Auto-open вкладки Схема при каждом отчёте (остаёмся на Превью; вкладка видна рядом)

## Code

- `ArtifactRail` tab order · `ArtifactCard` peer stack · `liberModes` copy
