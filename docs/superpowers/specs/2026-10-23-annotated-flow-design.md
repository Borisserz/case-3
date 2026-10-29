# Annotated flow — числа на схемах из Source

**Date:** 2026-10-23  
**Status:** approved (user selected «Annotated flow»)  
**Amends:** ADR-0007 · semantic diagrams · diagram repair

## Goal

Когда в Source есть **процесс/структура и числа**, Mermaid-схема показывает и то и другое: на блоках/рёбрах подписи вида `Склад · 1 240 шт`, `Отказ · 12%`. Числа **только из Source**. Рядом по-прежнему Chart.js для сравнения рядов.

## Non-goals

- Живые SQL/БД-агрегаторы (пункт 3 brainstorm).
- Рисовать bar/donut внутри Mermaid.
- Inject схем в PDF.

## Rules for LLM

1. Если у сущности/шага в Source есть величина — аннотировать label (` · ` или `<br/>`).
2. Не выдумывать цифры; не копировать весь chart series на схему (1–2 ключевые метрики на узел).
3. Charts остаются для визуализации рядов; схема — структура + ключевые KPI.

## Liber UI

Под canvas — полоска **метрик** (chips) + подсказка: блок = шт на этапе, стрелка = %/отвал. Легенда ролей кликабельна (highlight). PNG download + fullscreen scroll к верху. Без кнопки «Ещё вариант».

## Print / documents

**Не попадает в PDF/DOCX** (ADR-0007). Качество annotated flow — только Liber + PNG. В «документах» print-truth остаются charts/figures.

## Data source (v1)

Только Source / Intent-таблицы (вариант A brainstorm).

## QA prompt

`runs/_qa/PROMPT_большая_схема.md` + `annotated_flow_source.md` (локально).
