# Output format (mandatory)

Return **exactly two** fenced blocks, in this order:

1. ` ```json ` … metadata **in this key order**: `charts` (full Chart.js `html`) → `diagrams` (Mermaid) → `figures` (short photo prompts) … ` ``` `  ← **FIRST**; charts/diagrams before figures so heavy HTML survives length limits
2. ` ```latex ` … **complete** XeLaTeX `\documentclass` … `\end{document}` … ` ``` `

Never put only a fragment (`\section` without `\documentclass`). Never omit `\documentclass`.
Always finish the closing ``` of **both** fences — do not stop mid-table.
Prefer a compact body (short sections) over a truncated draft. **Aim for up to {{MAX_CHARTS}} charts** when Source has numbers — shorten prose / fewer photos before dropping charts. Never soft-cap at 2 when the budget is higher.

JSON schema (key order mandatory):

```json
{
  "charts": [
    {
      "id": "cht_01",
      "type": "bar",
      "caption": "Клиенты по годам, 2024–2025",
      "width": "0.85\\textwidth",
      "html": "<canvas id=\"c1\" width=\"1100\" height=\"560\"></canvas><script>new Chart(document.getElementById('c1'),{type:'bar',data:{labels:['2024','2025'],datasets:[{label:'Клиенты',data:[12,28],backgroundColor:['#E85D04','#2A9D8F'],borderRadius:6}]},options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}},animation:false}});window.__CASE3_CHART_READY=true;</script>"
    }
  ],
  "diagrams": [
    {
      "id": "dia_01",
      "title": "Процесс согласования",
      "type": "flowchart",
      "mermaid": "flowchart TD\n  A[Заявка]:::start --> B{ОК?}:::decision\n  B -->|да| C[Готово]:::ok\n  B -->|нет| A\n  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22\n  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22\n  classDef ok fill:#cfe6d4,stroke:#3d7a4a,color:#1a2e22"
    }
  ],
  "figures": [
    {
      "id": "fig_01",
      "caption": "Подпись на русском",
      "prompt": "English photo prompt: sharp detailed photograph, natural light, no text overlays, no watermark",
      "width": "0.85\\textwidth"
    }
  ]
}
```

Figure/chart `width`: prefer `0.85\\textwidth`; if **2+ charts** use `0.82\\textwidth` (pipeline clamps above `0.92`, and to `0.82` when several charts). Canvas height ≤ 560.

If {{MAX_IMAGES}} is 0 → `"figures": []`. If {{MAX_CHARTS}} is 0 → `"charts": []`. If {{MAX_DIAGRAMS}} is 0 → `"diagrams": []`.

**Diagrams are Liber UI-only:** never emit `%CASE3_DIAG` slots, never `\includegraphics` for diagrams, never put Mermaid inside TeX.
