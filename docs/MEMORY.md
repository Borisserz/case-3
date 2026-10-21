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
Parked backlog: [`plans/2026-10-20-liber-ux-polish-roadmap.md`](superpowers/plans/2026-10-20-liber-ux-polish-roadmap.md).

---

## Быстрый маршрут по задаче

| Задача | Сначала |
|--------|---------|
| Баг пайплайна / PDF | KI-pipeline → KI-tex-render → ADR-0001 |
| График / палитра / edit | KI-charts → ADR-0002 |
| Liber UI | KI-liber-ui → ADR-0003 |
| Фото / Image API | KI-image-api → ADR-0004 → specs image-api |
| Деплой на винду | knowledge/ops-windows.md |
| «Почему не PPTX» | knowledge/parked-pptx.md |

---

## Как писать новое

1. **Решение архитектуры** → новый `docs/adr/NNNN-slug.md`, статус Accepted, обновить [`adr/README.md`](adr/README.md).
2. **Подсистема изменилась** → правка KI в `.agents/knowledge/`.
3. **Фича в работе** → `docs/superpowers/specs/` + `plans/`.
4. **Термин / gotcha** → `docs/knowledge/`.

Не раздувай README — он только quick start; глубина здесь.
