# case-3 — карта памяти (3 уровня)

Единая точка входа для людей и агентов. Читай это **до** крупных правок.

```text
L1  Рабочий контекст     AGENTS.md · .cursor/rules · этот файл · открытый чат
L2  Граф кода            codebase-memory-mcp / code-review-graph (проект case-3)
L3  Долгосрочная память  docs/adr · .agents/knowledge · docs/knowledge · docs/superpowers
```

---

## L1 — Рабочий контекст (сессия)

| Артефакт | Зачем |
|----------|--------|
| [`AGENTS.md`](../AGENTS.md) | Контракт для агента: стек, запреты, куда смотреть |
| [`.cursor/rules/case3-memory.mdc`](../.cursor/rules/case3-memory.mdc) | Always-on: «сначала MEMORY» |
| [`README.md`](../README.md) | Запуск Windows / Qwen / Image API |
| [`docs/knowledge/repo-map.md`](knowledge/repo-map.md) | Что за папка / куда смотреть |
| [`docs/knowledge/windows-final-run.md`](knowledge/windows-final-run.md) | Win readiness + 3 промпта финал-прогона |
| Текущий чат | Задача «сейчас»; не считается источником истины без коммита в L3 |

**Правило:** если решение переживает один чат — запиши в ADR или KI, не оставляй только в диалоге.

---

## L2 — Граф кода

После индексации:

```bash
# через MCP codebase-memory: index_repository
# repo_path = /Users/borisserzhanovich/Projects/case-3
# name = case-3, mode = fast|full
```

Использовать для: «где pipeline stage», impact radius, поиск символов.  
Не дублировать длинные выдержки кода в markdown — ссылайся на пути.

Статус (2026-10-21): проект **`case-3`** проиндексирован (`mode=fast`, ~2.8k nodes).  
Примечание: папка `docs/` часто исключается из графа — ADR/KI живут в git как L3-файлы; граф — для кода.  
Если `list_projects` не показывает `case-3` — `index_repository` снова.

---

## L3 — Долгосрочная память (в репо)

### ADRs — *почему так*

[`docs/adr/`](adr/) — нумерованные решения. Шаблон: [`0000-template.md`](adr/0000-template.md).

### KI-карточки — *как устроена подсистема*

[`.agents/knowledge/`](../.agents/knowledge/) — короткие карточки (входные точки, инварианты, gotchas).

### Knowledge — *операционка и карта*

[`docs/knowledge/`](knowledge/) — глоссарий, system map, Windows desk, parked ideas.

### Superpowers — *спеки и планы фич*

[`docs/superpowers/`](superpowers/) — design + implementation plans (не ADR).

| Тип | Папка |
|-----|--------|
| Spec | `docs/superpowers/specs/` |
| Plan | `docs/superpowers/plans/` |

Активный UX: soft-premium shell — [`specs/2026-10-21-liber-soft-premium-ui-design.md`](superpowers/specs/2026-10-21-liber-soft-premium-ui-design.md) · ADR-0006.  
Chrome palette: Quiet Mono — [`specs/2026-10-23-liber-quiet-mono-ui-design.md`](superpowers/specs/2026-10-23-liber-quiet-mono-ui-design.md) (olive/cream chrome заменён).  
Premium refactor (полный desk): [`specs/2026-10-22-liber-premium-ui-refactor-design.md`](superpowers/specs/2026-10-22-liber-premium-ui-refactor-design.md) · [`plans/2026-10-22-liber-premium-ui-refactor.md`](superpowers/plans/2026-10-22-liber-premium-ui-refactor.md).  
Frontend modules (pre-Angular): [`specs/2026-10-25-liber-frontend-modules-design.md`](superpowers/specs/2026-10-25-liber-frontend-modules-design.md) · plan Week1 [`plans/2026-10-25-liber-frontend-modules-week1.md`](superpowers/plans/2026-10-25-liber-frontend-modules-week1.md) · map [`web/ARCHITECTURE.md`](../web/ARCHITECTURE.md).  
Parked backlog: [`plans/2026-10-20-liber-ux-polish-roadmap.md`](superpowers/plans/2026-10-20-liber-ux-polish-roadmap.md).  
Simplify-for-agents (hygiene + tracks A/B/C): [`plans/2026-10-29-liber-simplify-for-agents.md`](superpowers/plans/2026-10-29-liber-simplify-for-agents.md).
Active polish handoff (G3/G9/TOC/collapse/PPTX fonts/gallery→Slide): [`plans/2026-10-25-liber-polish-batch-a-handoff.md`](superpowers/plans/2026-10-25-liber-polish-batch-a-handoff.md).  
Deferred (A leftovers + B edit cycle; gate = LLM chat memory): [`knowledge/backlog-deferred-2026-10-25.md`](knowledge/backlog-deferred-2026-10-25.md). **B21 Undo shipped** 2026-10-26 (`run_undo.py` · `POST /undo` · toast «Отменить»); **B19 batch recolor = rejected**.  
A11 native PPTX charts **done** — [`specs/2026-10-26-liber-pptx-native-charts-design.md`](superpowers/specs/2026-10-26-liber-pptx-native-charts-design.md).  
DOCX native charts **done** — [`specs/2026-10-26-liber-docx-native-charts-design.md`](superpowers/specs/2026-10-26-liber-docx-native-charts-design.md) (`docx_charts.py` post-pandoc).  
Report depth C1/C2/C4 **done** (paragraph edit · Source citations · landscape tables) — KI-liber-ui / KI-tex-render · spec `2026-10-25-liber-report-depth-c1-c2-c4`. **C7 DOCX lists done** 2026-10-29 (`docx_lists.py`). Remaining C: TOC+LoF / 1-pager parked; C6 rejected.  
Resume failed stage **done** 2026-10-29 (`resume_pipeline` · `POST /resume` · «Продолжить») — I queue/retention/installer still parked.  
Deck/diagram D/E **done** (Present polish · structure ops · SVG) — KI-liber-deck / KI-liber-ui · spec `2026-10-25-liber-d-e-present-structure-svg`. Rejected D/E stay parked.  
Image G **done** (health chip · pack style-lock · brand-safe) — KI-image-api · [`knowledge/image-brand-safe-and-pack-lock.md`](knowledge/image-brand-safe-and-pack-lock.md). Excel Source — backlog **F** future.  
Desk: SSE v1 + **2A** + **2B** + **finish** (mode scripts · `meta.steps[]`) done — [`knowledge/desk-live-progress-and-health.md`](knowledge/desk-live-progress-and-health.md). Sound + desk health **rejected**. Atelier critique — backlog **J** later.  
«Новое» (K): Ask-the-document после LLM memory; Infographic poster + PDF/DOCX ingest — maybe later think; остальной brainstorm K — rejected (см. backlog **K**).

---

## Быстрый маршрут по задаче

| Задача | Сначала |
|--------|---------|
| Промпт LLM (правка / новый) | [`prompt/MANIFEST.md`](../prompt/MANIFEST.md) → `case3.prompts` · spec `2026-10-30-prompt-catalog` |
| Баг пайплайна / PDF | KI-pipeline → KI-tex-render → ADR-0001 |
| График / палитра / edit | KI-charts → ADR-0002 |
| Таблица / абзац в Preview (edit) | KI-liber-ui · `table_edit.py` / `paragraph_edit.py` · specs table-edit + `2026-10-25-liber-report-depth-c1-c2-c4` |
| Citations / landscape tables | KI-tex-render · `citations.py` · `maybe_landscape_wide_tables` |
| Liber UI | KI-liber-ui → ADR-0003 · ADR-0006 |
| Структура web/ (модули → Angular) | spec `2026-10-25-liber-frontend-modules-design` |
| Схемы Mermaid (UI) | ADR-0007 → KI-liber-ui / KI-pipeline · repair+premium · **edit/legend/regen** `2026-10-23-liber-diagram-edit-legend` |
| Inline схемы в Preview | spec+plan `liber-inline-preview-diagrams` (после Liber refactor: `liberTypes` / rail) |
| Фото / Image API | KI-image-api → ADR-0004 → specs image-api |
| Имена media (`fig_`/`cht_`/photo) | KI-media-names |
| Деплой на винду | knowledge/ops-windows.md |
| Презентация / PPTX deck | ADR-0008 · KI-liber-deck · structures `2026-10-22-liber-deck-structures-design` (arc ≠ colors) · Julius UX parity · packs + **structure_id** |
| Полный аудит / top-10 probes | [`docs/audits/`](audits/) |
| Отложенные фичи / цикл правок / «новое» K | [`knowledge/backlog-deferred-2026-10-25.md`](knowledge/backlog-deferred-2026-10-25.md) |
| Аудит кода (improve/delete/reuse) | [`knowledge/codebase-audit-2026-10-29.md`](knowledge/codebase-audit-2026-10-29.md) |

---

## Как писать новое

1. **Решение архитектуры** → новый `docs/adr/NNNN-slug.md`, статус Accepted, обновить [`adr/README.md`](adr/README.md).
2. **Подсистема изменилась** → правка KI в `.agents/knowledge/`.
3. **Фича в работе** → `docs/superpowers/specs/` + `plans/`.
4. **Термин / gotcha** → `docs/knowledge/`.

Не раздувай README — он только quick start; глубина здесь.
