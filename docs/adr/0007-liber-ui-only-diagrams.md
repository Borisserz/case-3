# ADR-0007: Liber UI-only Mermaid diagrams

## Status
Accepted

## Date
2026-10-21

## Context
Нужны смысловые схемы (процесс, структура, ветвления) вместе с отчётом. Chart.js покрывает числа; PDF уже print truth. Пользователь выбрал: схемы **только в Liber**, с скачиванием PNG — без inject в PDF/DOCX.

## Decision
- LLM JSON получает `diagrams[]` (Mermaid) рядом с `figures` / `charts`.
- Нет TeX-слотов `%CASE3_DIAG`, нет Playwright/inject стадии для схем.
- Liber Artifact rail: Document tabs (Preview·PDF·Source) + Diagram strip; fullscreen portal; client PNG.
- Soft-fail: битый Mermaid отбрасывается; pipeline остаётся `ok`.
- Cap: `CASE3_MAX_DIAGRAMS` / Settings 0–3 (default 2).

## Alternatives Considered

### Mermaid → PNG → TeX inject (like charts)
- Pros: единый print path
- Cons: пользователь отказался от PDF; усложняет inject
- Rejected

### Second LLM call after TeX
- Pros: чище system_tex
- Cons: latency/cost
- Rejected for v1

## Consequences
- Preview/PDF не содержат схем — только Liber + optional PNG download.
- Prompt must teach structural vs numeric (diagrams vs charts).
- ADR-0001 print truth unchanged for charts/photos.

## See
Spec: `docs/superpowers/specs/2026-10-21-liber-semantic-diagrams-design.md`  
Plan: `docs/superpowers/plans/2026-10-21-liber-semantic-diagrams.md`
