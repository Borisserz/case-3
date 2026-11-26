# ADR-0028: Silent Mermaid render retry for diagrams

## Status
Accepted

## Date
2026-11-26

## Context
LLM иногда отдаёт битый Mermaid (`NODE_DSTART` / узлы без ASCII id, текст между блоками без `-->`). Liber показывает «Не удалось отрисовать схему». Кнопка «Ещё вариант» уже чинит это вручную.

## Decision
После generate проверяем renderability (`mermaid_syntax_ok`: структурный фильтр + SVG через Playwright при наличии). При провале — до **2** тихих повторных вызовов той же generate-промпты (`complete_diagrams`). Пользователь видит спиннер, не ошибку. Исчерпали попытки — отдаём последний draft (как раньше).  
`regenerate_diagrams_in_run` идёт через `complete_diagrams`. Если `repair` ломает Mermaid — оставляем pre-repair draft.  
Env: `CASE3_DIAGRAM_RENDER_RETRIES` (default 2).

## Alternatives Considered

### Frontend auto-click «Ещё вариант»
- Pros: без бэкенда
- Cons: мелькает ошибка, лишний round-trip
- Rejected because: хуже UX

### Только ужесточить sanitize
- Pros: без LLM cost
- Cons: не покрывает все NODE_DSTART-кейсы
- Rejected as sole fix; sanitize остаётся, retry — страховка

## Consequences
- Positive: реже видна ошибка парсера; один код-путь для chat / diagram mode / Liber regenerate
- Negative: до +2 LLM вызовов и SVG-check latency на битых черновиках
