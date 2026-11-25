import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { repairMermaidSource } from "./repairMermaidSource";

describe("repairMermaidSource", () => {
  it("repairs sequence diagram participant aliases missing participant keyword", () => {
    const raw = `sequenceDiagram
  АОН as Оператор
  Менеджер по продажам as Менеджер
  Менеджер по логистике as Логист
  АОН->>Менеджер: заявка на продажу
  Менеджер->>Логист: отгрузка
  Логист-->>АОН: подтверждение отгрузки`;

    const out = repairMermaidSource(raw);
    assert.match(out, /participant АОН as Оператор/);
    assert.match(out, /participant "Менеджер по продажам" as Менеджер/);
    assert.match(out, /participant "Менеджер по логистике" as Логист/);
    assert.match(out, /АОН->>Менеджер: заявка на продажу/);
  });

  it("quotes multi-word participant ids even if participant keyword is already present", () => {
    const raw = `sequenceDiagram
  participant Менеджер по продажам as Менеджер
  participant Оператор`;
    const out = repairMermaidSource(raw);
    assert.match(out, /participant "Менеджер по продажам" as Менеджер/);
    assert.match(out, /participant Оператор/);
  });

  it("does not alter sequence diagram lines that already have keywords or arrows", () => {
    const raw = `sequenceDiagram
  actor User as Клиент
  participant Svc as Сервис
  Note over User,Svc: Acts as boundary
  User->>Svc: request as payload`;

    const out = repairMermaidSource(raw);
    assert.match(out, /actor User as Клиент/);
    assert.match(out, /participant Svc as Сервис/);
    assert.match(out, /Note over User,Svc: Acts as boundary/);
    assert.match(out, /User->>Svc: request as payload/);
    assert.ok(!out.includes("participant actor"));
    assert.ok(!out.includes("participant Note"));
  });

  it("repairs class statements with leading colons (class A :::start)", () => {
    const raw = `flowchart TD
  A-->B
  class A :::start
  class B :::process`;
    const out = repairMermaidSource(raw);
    assert.ok(!out.includes(":::start"));
    assert.match(out, /class A start/);
    assert.match(out, /class B process/);
  });

  it("chains flowchart nodes when the model omitted every edge", () => {
    const raw = `flowchart TD
 S[Начало]:::start
 A[Загрузка данных]:::process
 B[Конкатенация признаков]:::process
 C[Обучение модели]:::process
 D[Предсказание]:::ok
  classDef start fill:#DCE6F0,stroke:#4E79A7,color:#1a2e22
  classDef ok fill:#D8EBE4,stroke:#59A14F,color:#1a2e22`;
    const out = repairMermaidSource(raw);
    assert.match(out, /S --> A/);
    assert.match(out, /A --> B/);
    assert.match(out, /B --> C/);
    assert.match(out, /C --> D/);
    assert.ok(out.indexOf("classDef ok") < out.indexOf("S --> A"));
  });

  it("does not add edges when the flowchart already has one", () => {
    const raw = `flowchart TD
  A[Start] --> B[Mid]
  C[End]`;
    const out = repairMermaidSource(raw);
    assert.equal(out.split("-->").length - 1, 1);
  });

  it("does not chain sequence diagrams", () => {
    const raw = `sequenceDiagram
  participant A as A
  participant B as B
  A->>B: hi`;
    const out = repairMermaidSource(raw);
    assert.ok(!out.includes("-->"));
  });

  it("repairs a two-colon role suffix on a node", () => {
    const raw = `flowchart TD
  A["Клиент<br/>Заявка"]::start --> B["Склад"]::process`;
    const out = repairMermaidSource(raw);
    assert.match(out, /A\["Клиент<br\/>Заявка"\]:::start/);
    assert.match(out, /B\["Склад"\]:::process/);
    assert.ok(!out.includes("]::start"));
  });
});
