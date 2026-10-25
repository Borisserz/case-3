/** Smoke: several annotated-flow Mermaid samples → metrics extract. */
import assert from "node:assert/strict";
import { parseDiagramMetrics } from "./diagramMetrics";
import { canParseFlowchart } from "./diagramIr";
import { parseDiagramLegend } from "./diagramLegend";

const SAMPLES: { name: string; mermaid: string; minMetrics: number }[] = [
  {
    name: "deal-funnel",
    minMetrics: 5,
    mermaid: `flowchart TD
  A(["Лид<br/>340"]):::start --> B["Квалификация<br/>210"]:::process
  B --> C{Бюджет?}:::decision
  C -->|да · 88%| D(["Сделка<br/>185"]):::ok
  C -->|нет · 12%| E["Пауза · 25"]:::warn
  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22
  classDef process fill:#eef3ef,stroke:#6b8f76,color:#1a2e22
  classDef decision fill:#f5e6c8,stroke:#c4a35a,color:#1a2e22
  classDef ok fill:#cfe8d6,stroke:#5a9a6e,color:#1a2e22
  classDef warn fill:#f0d4d0,stroke:#b56a5e,color:#1a2e22
`,
  },
  {
    name: "warehouse-pipeline",
    minMetrics: 4,
    mermaid: `flowchart LR
  A["Приёмка · 1 240 шт"]:::start --> B["Размещение · 1 180"]:::process
  B --> C{Брак?}:::decision
  C -->|да · 5%| D["Возврат · 60"]:::warn
  C -->|нет · 95%| E["Отгрузка · 1 120"]:::ok
  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22
  classDef process fill:#eef3ef,stroke:#5a7a64,color:#1a2e22
  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22
  classDef ok fill:#cfe6d4,stroke:#3d7a4a,color:#1a2e22
  classDef warn fill:#f0ddd8,stroke:#a85a4a,color:#1a2e22
`,
  },
  {
    name: "approvals-chain",
    minMetrics: 3,
    mermaid: `flowchart TD
  A["Черновик · 42"]:::data --> B["Юрист"]:::process
  B --> C{ОК?}:::decision
  C -->|да| D["Подпись · 38"]:::ok
  C -->|нет · 4| E["Правки"]:::warn
  E --> B
  classDef data fill:#d9e6f0,stroke:#4a6f8c,color:#1a2e22
  classDef process fill:#eef3ef,stroke:#5a7a64,color:#1a2e22
  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22
  classDef ok fill:#cfe6d4,stroke:#3d7a4a,color:#1a2e22
  classDef warn fill:#f0ddd8,stroke:#a85a4a,color:#1a2e22
`,
  },
  {
    name: "structure-only",
    minMetrics: 0,
    mermaid: `flowchart TD
  A[Заявка]:::start --> B{Проверка}:::decision
  B -->|да| C[Готово]:::ok
  classDef start fill:#dce8df,stroke:#6b8f76,color:#1a2e22
  classDef decision fill:#f3e6c8,stroke:#b8893a,color:#1a2e22
  classDef ok fill:#cfe6d4,stroke:#3d7a4a,color:#1a2e22
`,
  },
];

for (const s of SAMPLES) {
  assert.equal(canParseFlowchart(s.mermaid), true, s.name);
  const metrics = parseDiagramMetrics(s.mermaid);
  const legend = parseDiagramLegend(s.mermaid);
  assert.ok(
    metrics.length >= s.minMetrics,
    `${s.name}: expected ≥${s.minMetrics} metrics, got ${metrics.length}`,
  );
  assert.ok(legend.length >= 2, `${s.name}: legend`);
  console.log(
    `✓ ${s.name}: metrics=${metrics.length} legend=${legend.length}`,
    metrics.map((m) => `${m.entity}=${m.metric}`).join("; "),
  );
}

console.log("smoke ok:", SAMPLES.length, "diagrams");
