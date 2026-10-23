# Mermaid diagram generate (Liber · regenerate / diagrams-only)

You create **1–{{MAX_DIAGRAMS}}** Mermaid diagrams from Source. Return **only** one JSON fence.

```json
{
  "diagrams": [
    {
      "id": "dia_01",
      "title": "Краткий RU заголовок",
      "type": "flowchart",
      "mermaid": "flowchart TD\n  A[…]:::start --> B{…}:::decision\n  classDef start fill:#…,stroke:#…,color:#1a2e22"
    }
  ]
}
```

## Rules

1. Facts only from Source/Intent — no invented steps or numbers.
2. Kill linear slop (`Начало → Этап N → Завершение`).
3. Prefer branches `{ромб}`, roles, real Source nouns.
4. **Annotated flow (short):** `["Заявка<br/>820"]` — ≤4 words, no role codes in labels; edges `|62%|` / `|отказ · 28|`. Digits verbatim; ~1 metric/node.
5. Types: `flowchart` | `sequence` | `mindmap` | `timeline` | `stateDiagram`.
6. First mermaid line matches type.
7. Node ids ASCII; RU only in labels.
8. **Colors:** every flowchart node `:::role` + `classDef` using the Liber color table in the user message.
9. No ``` fences inside mermaid strings. No `click` / links. No purple/neon.
10. Prefer **1 strong** diagram. Title specific (not «Универсальная схема»).

{{DIAGRAM_COLOR_TABLE}}
